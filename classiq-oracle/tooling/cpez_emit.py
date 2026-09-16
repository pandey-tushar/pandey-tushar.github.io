"""CP-EZ: 18-wire ACCUMULATION-AWARE emitter for the 57-node value DAG.

The unmodelled game: a wire carries an XOR-accumulation of node values, a
toggle may target any wire, and an operand is free whenever some wire's
current value already equals it.

Wire model (symbolic 70-bit: bits 0-11 raw, 12-68 nodes, 69 const):
  - ancillas 12..17 hold 0 or a CLEAN node atom n_k  (usable by any operand)
  - data wire j holds RAW(j) ^ (XOR of node values) (usable by operands
    carrying raw bit j -- this is the accumulation trick)
Operands are assembled in place, consumed, then un-assembled, so scratch is
transient.  Node residence is Belady-evicted with recomputation.
"""
import sys, os, collections
sys.path.insert(0,'/home/user/classiq-challenge')
import cpeu_dag as U
import cpet_vdag as V
import cpdh_core as DH
from cpae_core import ops_to_qc, mirror
from qiskit import transpile

N, PH, nmask, A = U.load()
CST = U.CST
LEV = A['lev']
NN  = len(N)
def NODE(k): return 1 << (12+k)
def RAW(j):  return 1 << j
def raws(o): return [w for w in range(12) if (o>>w)&1]
def nods(o): return [j for j in range(NN) if (o>>(12+j))&1]

class Emit:
    def __init__(self):
        self.V   = [RAW(w) if w < 12 else 0 for w in range(18)]
        self.vops= []      # value-changing ops (mirrored at the end)
        self.seq = []      # full sequence incl. phase ops
        self.home= {}      # node k -> wire carrying n_k
        self.ncx = 0
        self.pins= []

    def emit(self, op, value=True):
        self.seq.append(op)
        if value: self.vops.append(op)

    def cx(self, a, b):
        self.emit(('cx', a, b)); self.V[b] ^= self.V[a]; self.ncx += 1
    def xg(self, b):
        self.emit(('x', b)); self.V[b] ^= CST

    def toggle(self, i, t):
        """apply node i onto wire t; operands must already sit on wires."""
        hs = self.oper_wires[i]
        nm = 'ccx' if len(hs) == 2 else 'c3x'
        self.emit((nm,) + tuple(hs) + (t,))
        self.V[t] ^= NODE(i)

    # ---------------------------------------------------------------- atoms
    def find(self, val):
        for w in range(18):
            if self.V[w] == val: return w
        return None
    def clean_node(self, k):
        w = self.home.get(k)
        if w is not None and self.V[w] == NODE(k): return w
        return self.find(NODE(k))

    def nodes_on(self, w):
        return [k for k, ww in self.home.items() if ww == w]

    def ensure_raw(self, j, guard=0):
        """restore data wire j to its bare raw bit by uncomputing residents."""
        if self.V[j] == RAW(j): return True
        if guard > 6: return False
        for k in list(self.nodes_on(j)):
            self.uncompute(k, {}, guard+1)
        if (self.V[j] >> 69) & 1: self.xg(j)
        return self.V[j] == RAW(j)

    def free_anc(self, avoid=()):
        for w in range(12, 18):
            if self.V[w] == 0 and w not in avoid: return w
        return None

    # ------------------------------------------------------------- assembly
    def assemble(self, o, avoid, hostban=()):
        """return (wire, undo_ops_count) with V[wire]==o; emits CX/X."""
        w = self.find(o)
        if w is not None and w not in avoid: return w, []
        R, S = raws(o), nods(o)
        # choose host: a data wire of one of o's raw bits, else a free ancilla
        host = None
        for j in R:
            if j not in avoid and j not in hostban and (self.V[j] & ~o) == 0:
                host = j; break
        if host is None:
            host = self.free_anc(avoid)
        if host is None:
            for j in R:
                if j in avoid or j in hostban: continue
                if self.ensure_raw(j) and (self.V[j] & ~o) == 0:
                    host = j; break
        if host is None:
            for j in R:
                if j not in avoid and j not in hostban: host = j; break
        if host is None: raise RuntimeError('no host for %s' % bin(o))
        delta = self.V[host] ^ o
        undo = []
        for j in raws(delta):
            src = self.find(RAW(j))
            if src is None:
                self.ensure_raw(j)
                src = self.find(RAW(j))
            if src is None: raise RuntimeError('raw %d unavailable' % j)
            self.cx(src, host); undo.append(('cx', src, host))
        for k in nods(delta):
            src = self.clean_node(k)
            if src is None: raise RuntimeError('node %d unavailable' % k)
            self.cx(src, host); undo.append(('cx', src, host))
        if (delta >> 69) & 1:
            self.xg(host); undo.append(('x', host))
        assert self.V[host] == o, (bin(self.V[host]), bin(o))
        return host, undo

    def unassemble(self, undo):
        for op in reversed(undo):
            if op[0] == 'cx': self.cx(op[1], op[2])
            else: self.xg(op[1])

    # --------------------------------------------------------------- driver
    def place(self, i, nextuse, protect=()):
        """pick a wire to hold node i's value."""
        # prefer a data wire j such that RAW(j)^NODE(i) (plus what's there) is
        # directly an operand of a future consumer -- the accumulation hit
        if os.environ.get('ACCUM','0') != '1':
            w = self.free_anc()
            if w is not None: return w
            cand = [(nextuse.get(k, 10**9), k, ww) for k, ww in self.home.items()
                    if ww >= 12 and self.V[ww] == NODE(k) and k not in protect and not any(k in P for P in self.pins)]
            if not cand: raise RuntimeError('no ancilla and nothing evictable')
            _, k, ww = max(cand)
            self.uncompute(k, nextuse)
            return ww
        want = set()
        for c in range(NN):
            for o in N[c]:
                if (o >> (12+i)) & 1: want.add(o)
        for t in PH:
            for o in t:
                if (o >> (12+i)) & 1: want.add(o)
        for w in range(12):
            if (self.V[w] ^ NODE(i)) in want: return w
        w = self.free_anc()
        if w is not None: return w
        # Belady: evict the resident node whose next use is furthest away
        cand = [(nextuse.get(k, 10**9), k, ww) for k, ww in self.home.items()
                if ww >= 12 and self.V[ww] == NODE(k) and k not in protect and not any(k in P for P in self.pins)]
        if cand:
            _, k, ww = max(cand)
            self.uncompute(k, nextuse)
            return ww
        for w in range(12):
            if self.V[w] == RAW(w): return w
        raise RuntimeError('no placement')

    def ensure_node(self, k, nextuse, avoid=(), guard=0):
        if self.clean_node(k) is not None: return
        if os.environ.get('ACCUM','0') == '1':
            for w in range(12):
                if self.V[w] == (RAW(w) ^ NODE(k)): return
        self.compute(k, nextuse, avoid, guard+1)

    def compute(self, i, nextuse, avoid=(), guard=0):
        if guard > 8: raise RuntimeError('recursion guard on node %d' % i)
        for o in N[i]:
            for k in nods(o): self.ensure_node(k, nextuse, avoid, guard+1)
        protect = set(k for o in N[i] for k in nods(o))
        self.pins.append(protect)
        try:
            return self._compute(i, nextuse, avoid, guard, protect)
        finally:
            self.pins.pop()

    def _compute(self, i, nextuse, avoid, guard, protect):
        t = self.place(i, nextuse, protect)   # evict FIRST, while data wires are clean
        avoid_base = avoid
        idx = sorted(range(len(N[i])), key=lambda a: -len(raws(N[i][a])))
        used = [None]*len(N[i]); undos = [None]*len(N[i]); seq = []
        for pos, a in enumerate(idx):
            rem = set(j for b in idx[pos+1:] for j in raws(N[i][b]))
            av = tuple(avoid_base) + tuple(w for w in used if w is not None) + (t,)
            w, u = self.assemble(N[i][a], av, tuple(rem))
            used[a] = w; undos[a] = u; seq.append(a)
        nm = 'ccx' if len(used) == 2 else 'c3x'
        self.emit((nm,) + tuple(used) + (t,)); self.V[t] ^= NODE(i)
        self.home[i] = t
        for a in reversed(seq): self.unassemble(undos[a])

    def uncompute(self, i, nextuse, guard=0):
        t = self.home.get(i)
        if t is None: return
        prot = set(k for o in N[i] for k in nods(o))
        self.pins.append(prot)
        try:
            for o in N[i]:
                for k in nods(o): self.ensure_node(k, nextuse, (t,), guard+1)
            self._uncompute_body(i, t)
        finally:
            self.pins.pop()
        del self.home[i]
        return

    def _uncompute_body(self, i, t):
        avoid = ()
        avoid_base = ()
        idx = sorted(range(len(N[i])), key=lambda a: -len(raws(N[i][a])))
        used = [None]*len(N[i]); undos = [None]*len(N[i]); seq = []
        for pos, a in enumerate(idx):
            rem = set(j for b in idx[pos+1:] for j in raws(N[i][b]))
            av = tuple(avoid_base) + tuple(w for w in used if w is not None) + (t,)
            w, u = self.assemble(N[i][a], av, tuple(rem))
            used[a] = w; undos[a] = u; seq.append(a)
        nm = 'ccx_dg' if len(used) == 2 else 'c3x_dg'
        self.emit((nm,) + tuple(used) + (t,)); self.V[t] ^= NODE(i)
        for a in reversed(seq): self.unassemble(undos[a])

def run():
    E = Emit()
    order = sorted(range(NN), key=lambda i: (LEV[i], i))
    # next-use table for Belady
    cons = collections.defaultdict(list)
    for pos, i in enumerate(order):
        for o in N[i]:
            for k in nods(o): cons[k].append(pos)
    phases = V.vdag(list(__import__('pickle').load(open('cpen_search_11.pkl','rb'))[1]))[2]
    for pos, i in enumerate(order):
        nextuse = {k: min([p for p in cons[k] if p > pos], default=10**9)
                   for k in list(E.home)}
        E.compute(i, nextuse, ())
    # phase terms: need all seeds co-resident
    for (kind, ph) in phases:
        o_ = [U.norm(r, s) for (r, s) in ph]
        for o in o_:
            for k in nods(o): E.ensure_node(k, {}, ())
        used = []; undos = []
        for o in o_:
            w, u = E.assemble(o, tuple(used)); used.append(w); undos.append(u)
        E.emit((kind,) + tuple(used), value=False)
        for u in reversed(undos): E.unassemble(u)
    full = E.seq + mirror(E.vops)
    return full, E

if __name__ == '__main__':
    import cpet_wide as W
    full, E = run()
    ph, dirty = W.replay(full, 18)
    bad = bin(ph ^ DH.want_mask('LOGO')).count('1')
    print('ops %d  cx %d  mismatch %d  dirty %s' % (len(full), E.ncx, bad, dirty))
    if bad == 0 and not dirty:
        qc = ops_to_qc(full, n=18)
        t = transpile(qc, basis_gates=['u3','cx'], optimization_level=2, seed_transpiler=0)
        print('  EXACT.  opt2 depth %d cx %d' % (t.depth(), t.count_ops().get('cx',0)))
