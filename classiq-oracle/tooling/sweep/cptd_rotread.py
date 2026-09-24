"""Rotation-readout rewrite of the 249 op list (cpen_o1.pkl).
A readout reads a phase on a product of wire values.  If one factor v sits on
wire w only because a Toffoli computed it from a constant (w ^= a.b.., later
undone by the matching inverse op, w untouched in between except by
readouts), drop that compute/uncompute pair and read the product of its
controls directly: cz -> ccz -> c3z (-> c4z ...), a multi-controlled Z.
The new readout is placed at the earliest op position where all its factor
values are held on distinct wires (complements fixed by X pairs).
Greedy: one rewrite at a time, keep it if the real transpile depth drops.
Usage: python3 cptd_rotread.py [KMAX]
Checkpoint: ckpt/rotread.pkl (best op list, depth, log)"""
import os, sys, time, pickle
import numpy as np
from qiskit.circuit.library import ZGate
from cpae_core import ops_to_qc, real_depth, sv_check_gp, SHAPES, fvec

OPS = os.environ.get('CPEN_O1', '/home/user/classiq-challenge/cpen_o1.pkl')
N, NW = 4096, 18
READ = ('z', 'cz', 'ccz', 'mcz')
AND = ('ccx', 'ccx_dg', 'c3x', 'c3x_dg')


def states(ops):
    """st[p] = int64 state array before op p (p = 0..len)"""
    s = np.arange(N, dtype=np.int64); out = [s]
    b = lambda w: (s >> w) & 1
    for op in ops:
        k, q = op[0], op[1:]
        if k == 'x': s = s ^ (1 << q[0])
        elif k == 'cx': s = s ^ (b(q[0]) << q[1])
        elif k in AND:
            p = np.ones(N, dtype=np.int64)
            for w in q[:-1]: p &= b(w)
            s = s ^ (p << q[-1])
        out.append(s)
    return out


def bit(s, w): return ((s >> w) & 1).astype(np.uint8)


def classical(ops):
    s = np.arange(N, dtype=np.int64); ph = np.zeros(N, dtype=np.int64)
    sts = states(ops)
    for p, op in enumerate(ops):
        if op[0] in READ:
            t = np.ones(N, dtype=np.int64)
            for w in op[1:]: t &= (sts[p] >> w) & 1
            ph ^= t
    return int((ph != fvec(SHAPES['LOGO'])).sum()), bool((sts[-1] == np.arange(N)).all())


def to_qc(ops):
    base = [o for o in ops if o[0] != 'mcz']
    if len(base) == len(ops): return ops_to_qc(ops)
    qc = ops_to_qc([])
    for o in ops:
        if o[0] == 'mcz': qc.append(ZGate().control(len(o) - 2), list(o[1:]))
        else: qc.compose(ops_to_qc([o]), inplace=True)
    return qc


def find(st, v, excl):
    for w in range(NW):
        if w in excl: continue
        b = bit(st, w)
        if np.array_equal(b, v): return w, False
        if np.array_equal(b, v ^ 1): return w, True
    return None


def place(sts, facs, r, excl):
    """position nearest to r where all factor values are held on distinct
    wires (not in excl) -> ops for that readout (X-fixed) or None"""
    L = len(sts) - 1
    for p in sorted(range(L + 1), key=lambda p: (abs(p - r), p)):
        ws, fl = [], []
        for f in facs:
            h = find(sts[p], f, ws + list(excl.get(p, ())))
            if h is None: break
            ws.append(h[0]); fl.append(h[1])
        if len(ws) == len(facs):
            g = [('x', u) for u, f in zip(ws, fl) if f]
            name = 'cz' if len(ws) == 2 else ('ccz' if len(ws) == 3 else ('z' if len(ws) == 1 else 'mcz'))
            return p, g + [(name,) + tuple(ws)] + g
    return None


def norm(facs):
    """dedupe factors; None if the product is 0; [] if it is 1"""
    out = []
    for f in facs:
        if f.min() == 1: continue
        if f.max() == 0: return None
        if any(np.array_equal(f, g) for g in out): continue
        if any(np.array_equal(f ^ 1, g) for g in out): return None
        out.append(f)
    return out


def candidates(ops, kmax):
    """yield (new ops, description) for every single legal unfold:
    op j: w ^= prod(ctl) (w held u), op k: its inverse, only readouts touch w
    in between.  Each readout prod(v, rest), v = u ^ prod(ctl), becomes
    prod(u, rest) + prod(ctl, rest)."""
    sts = states(ops)
    for i, op in enumerate(ops):
        if op[0] not in READ: continue
        for w in op[1:]:
            j = next((p for p in range(i - 1, -1, -1) if w in ops[p][1:]), None)
            if j is None or ops[j][0] not in AND or ops[j][-1] != w: continue
            ks = [p for p in range(j + 1, len(ops)) if w in ops[p][1:]]
            k = next((p for p in ks if ops[p][0] not in READ), None)
            if k is None or ops[k][0] not in AND or ops[k][-1] != w: continue
            if sorted(ops[k][1:-1]) != sorted(ops[j][1:-1]): continue
            if not all(np.array_equal(bit(sts[k], c), bit(sts[j], c)) for c in ops[j][1:-1]): continue
            if not np.array_equal(bit(sts[k + 1], w), bit(sts[j], w)): continue
            reads = [p for p in ks if p < k]
            u = bit(sts[j], w)
            ctl = [bit(sts[j], c) for c in ops[j][1:-1]]
            excl = {p: (w,) for p in range(j + 1, k + 1)}       # w no longer holds v there
            ins, deg, ok = [], 0, True
            for r in reads:
                rest = [bit(sts[r], x) for x in ops[r][1:] if x != w]
                for facs in (norm([u] + rest), norm(ctl + rest)):
                    if facs is None: continue
                    if not facs: ok = False; break          # global phase -1: not a readout
                    if len(facs) > kmax: ok = False; break
                    deg = max(deg, len(facs))
                    pl = place(sts, facs, r, excl)
                    if pl is None: ok = False; break
                    ins.append(pl)
                if not ok: break
            if not ok: continue
            out = []
            for p, o in enumerate(ops):
                for pp, seq in ins:
                    if pp == p: out += seq
                if p in (j, k) or p in reads: continue
                out.append(o)
            for pp, seq in ins:
                if pp == len(ops): out += seq
            yield out, 'read@%d wire %d: drop ops %d,%d, %d reads -> %d, max degree %d' % (
                i, w, j, k, len(reads), len(ins), deg)


def measure(ops):
    return real_depth(to_qc(ops))


if __name__ == '__main__':
    kmax = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    ops = pickle.load(open(OPS, 'rb'))
    t0 = time.time()
    base = measure(ops); log = [('o1', base)]
    print('o1 real depth/cx %s  classical %s' % (base, classical(ops)), flush=True)
    best = (base, ops)
    os.makedirs('ckpt', exist_ok=True)
    while True:
        tried = []
        for cand, desc in candidates(best[1], kmax):
            mism, ident = classical(cand)
            if mism or not ident:
                print('  %s  INVALID mism %d ident %s' % (desc, mism, ident), flush=True); continue
            d = measure(cand); tried.append((d, desc, cand))
            print('  %s  -> real %s  (%.0fs)' % (desc, d, time.time() - t0), flush=True)
        if not tried: break
        d, desc, cand = min(tried, key=lambda t: t[0])
        if d >= best[0]: break
        best = (d, cand); log.append((desc, d))
        print('KEEP %s  depth/cx %s' % (desc, d), flush=True)
        pickle.dump(dict(depth=d, ops=cand, log=log), open('ckpt/rotread.pkl', 'wb'))
    print('final depth/cx %s  sv %s  %.0fs' % (best[0], sv_check_gp(to_qc(best[1]), 'LOGO'), time.time() - t0), flush=True)
