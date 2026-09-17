"""CP-FK: rank-10 factorisation of the logo.  F(x,y) = sum_i a_i(x) b_i(y)
over GF(2) with only 10 terms; the column space (functions of x) and row
space (functions of y) are 10-dim and spanned by interval indicators, i.e.
XORs of threshold functions [v >= p].  One side = 6 raw wires + 3 zero
ancillas; this module searches a short Toffoli/CX walk whose contents over
time span the side's space (mod affine).  Guidance: coverage of the space
spanned by threshold prefix intermediates, which gives credit to in-place
variants automatically (the objective is linear).  64-bit truth tables.
"""
import sys, random, itertools, time, pickle
sys.path.insert(0, '/home/user/classiq-challenge')
import cpdh_core as DH
from cpae_core import PROF

M64 = (1 << 64) - 1
F = DH.want_mask('LOGO')
COLS = [(F >> (64 * y)) & M64 for y in range(64)]                                  # functions of x
ROWS = [sum(((F >> (x + 64 * y)) & 1) << y for y in range(64)) for x in range(64)]  # functions of y
LIN = [sum(((v >> i) & 1) << v for v in range(64)) for i in range(6)]
ONE = M64
def tab(f): return sum(f(v) << v for v in range(64))
THR = [tab(lambda v, p=p: v >= p) for p in range(65)]


class Span64:
    def __init__(self, vs=()):
        self.piv = {}
        for v in vs: self.add(v)
    def reduce(self, v):
        while v:
            p = v & -v
            e = self.piv.get(p)
            if e is None: return v
            v ^= e
        return 0
    def add(self, v):
        v = self.reduce(v)
        if v: self.piv[v & -v] = v; return True
        return False
    def copy(self):
        s = Span64(); s.piv = dict(self.piv); return s
    def plus(self, other):
        s = self.copy()
        for v in other.piv.values(): s.add(v)
        return s
    def __len__(self): return len(self.piv)


def thresholds_of(base):
    """threshold points p such that the space is spanned by [v>=p] differences."""
    ps = set()
    for v in base:
        prev = 0
        for i in range(64):
            b = (v >> i) & 1
            if b != prev: ps.add(i)
            prev = b
        if prev: ps.add(64)
    return sorted(ps)


def intermediates(ps):
    """MSB-first comparator prefixes for [v>=p]: g_k = bits above k fixed... as
    functions: for each p and each k, the function [v>>k >= p>>k] and [v>>k > p>>k]."""
    out = set()
    for p in ps:
        for k in range(0, 6):
            out.add(tab(lambda v, p=p, k=k: (v >> k) >= (p >> k)))
            out.add(tab(lambda v, p=p, k=k: (v >> k) > (p >> k)))
            out.add(tab(lambda v, p=p, k=k: (v >> k) == (p >> k)))
        # 3+3 split pieces
        hi, lo = p >> 3, p & 7
        out.add(tab(lambda v, hi=hi: (v >> 3) > hi)); out.add(tab(lambda v, hi=hi: (v >> 3) == hi))
        out.add(tab(lambda v, lo=lo: (v & 7) >= lo))
    return [v for v in out if v not in (0, ONE)]


class Side:
    def __init__(self, side):
        base = COLS if side == 'x' else ROWS
        self.name = side
        self.C = Span64(base + LIN + [ONE])
        self.ps = thresholds_of(base)
        self.I = Span64(intermediates(self.ps) + [THR[p] for p in self.ps] + LIN + [ONE])
        self.IC = self.I.plus(self.C)


class Walk:
    """9 local wires: 0-5 raw, 6-8 zero ancillas."""
    def __init__(self, S):
        self.S = S
        self.cont = list(LIN) + [0, 0, 0]
        self.lay = [0] * 9
        self.ops = []
        self.U = Span64(LIN + [ONE])
        self.UC = self.U.plus(S.C); self.UI = self.U.plus(S.IC)
        self.cov = len(self.U) + len(S.C) - len(self.UC)
        self.covI = len(self.U) + len(S.IC) - len(self.UI)
    def clone(self):
        w = Walk.__new__(Walk)
        w.S = self.S; w.cont = list(self.cont); w.lay = list(self.lay); w.ops = list(self.ops)
        w.U = self.U.copy(); w.UC = self.UC.copy(); w.UI = self.UI.copy(); w.cov = self.cov; w.covI = self.covI
        return w
    def value(self, op):
        if op[0] == 'ccx':
            a, b, t = op[1:]; return self.cont[t] ^ (self.cont[a] & self.cont[b])
        a, t = op[1:]; return self.cont[t] ^ self.cont[a]
    def gains(self, op):
        v = self.value(op)
        r = self.U.reduce(v)
        if not r: return 0, 0
        return (1 if self.UC.reduce(r) == 0 else 0), (1 if self.UI.reduce(r) == 0 else 0)
    def apply(self, op):
        v = self.value(op)
        self.cont[op[-1]] = v
        prof = PROF[op[0]]; qs = op[1:]
        st = 0
        for j, w in enumerate(qs): st = max(st, self.lay[w] - prof[j][0] + 2)
        for j, w in enumerate(qs): self.lay[w] = st + prof[j][-1] - 1
        self.ops.append(op)
        if self.U.add(v):
            self.UC.add(v); self.UI.add(v)
            self.cov = len(self.U) + len(self.S.C) - len(self.UC)
            self.covI = len(self.U) + len(self.S.IC) - len(self.UI)
    def depth(self): return max(self.lay)
    def moves(self):
        for t in range(9):
            for a in range(9):
                if a == t: continue
                yield ('cx', a, t)
                for b in range(a + 1, 9):
                    if b != t: yield ('ccx', a, b, t)


def closure_cov(w, k=2):
    """dim(A_j cap C) for j=1..k where A_j = span of products of <= j current contents (+U)."""
    S = w.S
    A = w.U.copy(); AC = w.UC.copy()
    for v in w.cont: A.add(v); AC.add(v)
    out = [len(A) + len(S.C) - len(AC)]
    cs = [v for v in w.cont if v not in (0, ONE)]
    prods = [cs[i] & cs[j] for i in range(len(cs)) for j in range(i + 1, len(cs))]
    for v in prods: A.add(v); AC.add(v)
    out.append(len(A) + len(S.C) - len(AC))
    if k >= 3:
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                for l in range(j + 1, len(cs)):
                    v = cs[i] & cs[j] & cs[l]; A.add(v); AC.add(v)
        out.append(len(A) + len(S.C) - len(AC))
    return out


def search(S, beam=8, maxsteps=60, seed=0, verbose=False, wdepth=0.0, allow_cx=True, k=3):
    rng = random.Random(seed)
    front = [Walk(S)]
    goal = len(S.C)
    seen = set()
    for step in range(maxsteps):
        cand = []
        for w in front:
            for op in w.moves():
                if op[0] == 'cx' and not allow_cx: continue
                v = w.value(op)
                if w.U.reduce(v) == 0 and op[0] == 'cx': continue
                w2 = w.clone(); w2.apply(op)
                key = tuple(sorted(w2.cont))
                if key in seen: continue
                seen.add(key)
                cc = closure_cov(w2, k)
                score = (w2.cov, cc[0], cc[1], (cc[2] if k >= 3 else 0) - wdepth * w2.depth() / 7.0, -len(w2.ops), rng.random())
                cand.append((score, w2))
        if not cand: break
        cand.sort(key=lambda c: c[0], reverse=True)
        front = [c[1] for c in cand[:beam]]
        top = front[0]
        if verbose:
            print('  step %d: cov %d/%d next %s depth %d ops %d' % (step + 1, top.cov, goal, closure_cov(top, k), top.depth(), len(top.ops)), flush=True)
        done = [w for w in front if w.cov >= goal]
        if done:
            return min(done, key=lambda w: (w.depth(), len(w.ops)))
    return None


if __name__ == '__main__':
    side = sys.argv[1] if len(sys.argv) > 1 else 'x'
    beam = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    S = Side(side)
    print('side %s: thresholds %s  dim C %d  dim I+C %d' % (side, S.ps, len(S.C), len(S.IC)), flush=True)
    t0 = time.time()
    k = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    best = search(S, beam=beam, seed=seed, verbose=True, k=k)
    if best:
        nt = sum(o[0] == 'ccx' for o in best.ops)
        print('FOUND: %d ops (%d toffoli, %d cx) depth %d  %.0fs' % (len(best.ops), nt, len(best.ops) - nt, best.depth(), time.time() - t0))
        print(best.ops)
        pickle.dump(best.ops, open('cpfk_side_%s_b%d_s%d.pkl' % (side, beam, seed), 'wb'))
    else:
        print('not found', time.time() - t0)
