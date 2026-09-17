"""cpfm: one-wire-per-function layout for one side (9 wires: data 0-5, anc 6-8).

Every function f_i (64-bit table over the side's 6 bits) is accumulated onto
its own wire t_i: data wire (contents become raw ^ f_i) or ancilla.  A gate may
read a data literal raw only while that wire is still clean; literals of dirty
wires come through cached products on scratch ancillas.  Compute half only;
the mirror (reverse, daggers) is appended for depth and exactness.
"""
import sys, random, itertools, pickle
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfk_syn as SY
import cpfh_core as C
from cpae_core import model_depth

M64 = (1 << 64) - 1
RM9 = list(C.RM[:6]) + [0, 0, 0]
INV = {'ccx': 'ccx_dg', 'ccx_dg': 'ccx', 'c3x': 'c3x_dg', 'c3x_dg': 'c3x', 'cx': 'cx', 'x': 'x'}

def cube_tab(lits):
    return sum(1 << v for v in range(64) if all(((v >> b) & 1) == val for b, val in lits.items()))

CUBES = []
for k in range(0, 7):
    for bits in itertools.combinations(range(6), k):
        for vals in itertools.product([0, 1], repeat=k):
            d = dict(zip(bits, vals)); CUBES.append((d, cube_tab(d)))

def gcost(k):  # gates for a k-literal cube, all literals raw
    return 1 if k <= 3 else (2 if k <= 5 else 3)

_COV = {}
def cover(f):
    if f in _COV: return _COV[f]
    r = _cover(f); _COV[f] = r; return r

def _cover(f):
    """greedy XOR cube cover of f or its complement; returns (const, [lit dicts])."""
    best = None
    for const in (0, 1):
        rem = f ^ (M64 if const else 0); pcs = []
        while rem:
            b = None; w0 = bin(rem).count('1')
            for l, t in CUBES:
                if not t: continue
                g = w0 - bin(rem ^ t).count('1')
                if g <= 0: continue
                sc = g / gcost(len(l))
                if b is None or sc > b[0]: b = (sc, l, t)
            rem ^= b[2]; pcs.append(b[1])
        c = sum(gcost(len(l)) for l in pcs)
        if best is None or c < best[0]: best = (c, const, pcs)
    return best[1], best[2]

class Side:
    def __init__(self, scratch):
        self.ops = []; self.scratch = list(scratch); self.cache = {}   # frozenset(lits) -> wire
        self.dirty = set(); self.fail = None
    def emit(self, op): self.ops.append(op)
    def mcx(self, ctrls, t, dg=False):
        """ctrls: list of (wire, val); negative literal via X around."""
        neg = [w for w, v in ctrls if v == 0]
        for w in neg: self.emit(('x', w))
        ws = [w for w, v in ctrls]
        if len(ws) == 0: self.emit(('x', t))
        elif len(ws) == 1: self.emit(('cx', ws[0], t))
        elif len(ws) == 2: self.emit(('ccx_dg' if dg else 'ccx', ws[0], ws[1], t))
        elif len(ws) == 3: self.emit(('c3x_dg' if dg else 'c3x', ws[0], ws[1], ws[2], t))
        else: raise ValueError('mcx>3')
        for w in neg: self.emit(('x', w))
    def key(self, lits):
        """product of lits (dict bit->val, <=3) on a scratch wire; cached."""
        k = frozenset(lits.items())
        if k in self.cache: return self.cache[k]
        if any(b in self.dirty for b in lits): self.fail = 'key needs dirty literal'; return None
        free = [s for s in self.scratch if s not in self.cache.values()]
        if not free:
            for kk, s in list(self.cache.items()):
                if all(b not in self.dirty for b, v in kk):
                    self.mcx(sorted(dict(kk).items()), s, dg=True); del self.cache[kk]; free = [s]; break
        if not free: self.fail = 'no scratch'; return None
        s = free[0]; self.mcx(sorted(lits.items()), s); self.cache[k] = s
        return s
    def cube_keys(self, lits, t):
        """split a cube into (key1 lits or None, key2 lits or None, raw ctrl list)."""
        dirty = {b: v for b, v in lits.items() if b in self.dirty or b == t}
        raw = sorted(((b, v) for b, v in lits.items() if b not in self.dirty and b != t), reverse=True)
        if len(dirty) > 3: return None
        k1 = dict(dirty)
        if len(lits) > 3 or k1:
            while len(k1) < 3 and raw and len(k1) + len(raw) > 3:
                k1[raw[0][0]] = raw[0][1]; raw = raw[1:]
        k2 = None
        if (1 if k1 else 0) + len(raw) > 3:
            k2 = dict(raw[:3]); raw = raw[3:]
        if (1 if k1 else 0) + (1 if k2 else 0) + len(raw) > 3: return None
        return (k1 or None), k2, raw
    def accumulate(self, f, t):
        """XOR f onto wire t (data or ancilla)."""
        const, pcs = cover(f)
        pcs = sorted(pcs, key=lambda l: -len(l))
        plan = []
        for lits in pcs:
            r = self.cube_keys(lits, t)
            if r is None: self.fail = 'cube too long'; return
            plan.append(r)
        # keys that contain the target literal must exist before t is dirtied
        if t < 6:
            for k1, k2, raw in plan:
                for k in (k1, k2):
                    if k and t in k and self.key(k) is None: return
        if const: self.emit(('x', t))
        if t < 6: self.dirty.add(t)
        for k1, k2, raw in plan:
            ctrls = []
            for k in (k1, k2):
                if k:
                    s = self.key(k)
                    if s is None: return
                    ctrls.append((s, 1))
            self.mcx(ctrls + list(raw), t)

def compile_side(fs, order, targets, scratch):
    """order: function indices in emission order; targets[i]: wire for f_i."""
    S = Side(scratch)
    markers = []
    for i in order:
        S.accumulate(fs[i], targets[i])
        if S.fail: return None, S.fail
        markers.append(i)
    body = list(S.ops)
    mirror = [(INV[op[0]],) + op[1:] for op in reversed(body)]
    return body, mirror

def ext(tab64):  # x-function table -> 4096-bit contents (index x + 64 y)
    return sum(tab64 << (64 * y) for y in range(64))

def check(fs, targets, body, mirror, n=9):
    c = list(RM9)
    for op in body: C.apply(c, op)
    ok = all(c[targets[i]] == (RM9[targets[i]] ^ ext(fs[i])) for i in range(len(fs)))
    for op in mirror: C.apply(c, op)
    return ok and all(c[w] == RM9[w] for w in range(n))

def loads(ops, n=9):
    L = [0] * n
    for op in ops:
        if op[0] == 'x': continue
        for w in op[1:]: L[w] += 1
    return L

def search(fs, iters, seed, nscratch=2, verbose=False):
    rng = random.Random(seed); best = None; fails = {}
    for it in range(iters):
        order = list(range(len(fs))); rng.shuffle(order)
        tg = list(range(9)); rng.shuffle(tg)
        targets = {i: tg[k] for k, i in enumerate(order)}
        scratch = [w for w in (6, 7, 8) if w not in tg[:len(fs)]]
        if not scratch: continue
        body, mirror = compile_side(fs, order, targets, scratch)
        if body is None: fails[mirror] = fails.get(mirror, 0) + 1; continue
        if body is None: continue
        ops = body + mirror
        d = model_depth(ops, n=9)
        ng = sum(1 for o in ops if o[0] in ('ccx', 'c3x', 'ccx_dg', 'c3x_dg'))
        if best is None or d < best[0]:
            ok = check(fs, targets, body, mirror)
            best = (d, ng, order, targets, ops, ok)
            if verbose: print('it', it, 'depth', d, 'mcx', ng, 'exact', ok, 'loads', loads(ops), flush=True)
    print('fails', fails)
    return best

if __name__ == '__main__':
    side = sys.argv[1]; iters = int(sys.argv[2]); nf = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    xf, yf = SY.basis_pair()
    fs = (xf if side == 'x' else yf)
    # cheapest nf functions first (step-1 sizing: 7 accumulators + 2 scratch)
    costs = [(sum(gcost(len(l)) for l in cover(f)[1]), i) for i, f in enumerate(fs)]
    costs.sort(); pick = [i for c, i in costs[:nf]]
    print(side, 'cover costs', costs, 'using', pick)
    b = search([fs[i] for i in pick], iters, 1, verbose=True)
    if b is None: print('no feasible layout')
    if b:
        d, ng, order, targets, ops, ok = b
        print('BEST depth', d, 'mcx', ng, 'exact', ok, 'loads', loads(ops), 'sum', sum(loads(ops)))
        pickle.dump(b, open('cpfm_%s.pkl' % side, 'wb'))
