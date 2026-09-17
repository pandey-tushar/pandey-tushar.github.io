"""cpfn: offline gate count for the fold/hold piece model.

Side function f (64-bit table over 6 bits) = XOR of affine-subspace pieces.
A piece A of codim k is emitted either
  folded : CCZ(key, form, partner-wire) with key = a codim k-1 superset of A
           held on an ancilla (k<=2: CCZ/CZ on forms, no key);  cost = keycost + 1
  held   : accumulated onto the function's wire: rccx(key(k-1), form) or
           rc3x(key(k-2), form, form);  cost = keycost + 1  (k<=2: 1, k<=1: 0)
keycost(S) = codim(S)-2 fresh, or codim(S)-codim(K) for an existing key K > S
(chain of one-form extensions); intermediate chain keys become shared keys.
Units = Toffoli-type gates per direction; the mirror doubles keys and held
pieces, folded CCZs are not mirrored.
"""
import sys, itertools, random, pickle
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfk_syn as SY
import cpfk_side as SD
from cpfk_affine import all_affine

M64 = (1 << 64) - 1
AFF = all_affine()                       # mask -> forms
AFF[M64] = ()
DIM = {m: 6 - len(f) for m, f in AFF.items()}
CODIM = {m: len(f) for m, f in AFF.items()}
_SUP = {}
def shift(mask, v):
    return sum(1 << (a ^ v) for a in range(64) if (mask >> a) & 1)
def supersets(A):
    """affine supersets of dimension dim(A)+1."""
    if A in _SUP: return _SUP[A]
    out = set()
    for v in range(1, 64):
        S = A | shift(A, v)
        if S != A and S in AFF and DIM[S] == DIM[A] + 1: out.add(S)
    _SUP[A] = sorted(out); return _SUP[A]

class Keys:
    def __init__(self): self.keys = set()
    def cost(self, S):
        """(cost, chain) to have product S on an ancilla given current keys."""
        k = CODIM[S]
        if S in self.keys: return 0, []
        best = (k - 2, [S]) if k >= 3 else (0, [])
        if k >= 4:
            for P in supersets(S):
                c, ch = self.cost(P)
                if c + 1 < best[0]: best = (c + 1, ch + [S])
        return best
    def add(self, chain):
        for S in chain: self.keys.add(S)

def piece_cost(A, keys, mode):
    k = CODIM[A]
    if mode == 'fold':
        if k <= 2: return 1, []
        best = None
        for S in supersets(A):
            c, ch = keys.cost(S)
            if best is None or c < best[0]: best = (c, ch)
        return best[0] + 1, best[1]
    else:
        if k <= 1: return 0, []
        if k == 2: return 1, []
        best = None
        for S in supersets(A):
            c, ch = keys.cost(S)
            if best is None or c < best[0]: best = (c, ch)
            if k >= 4:
                for S2 in supersets(S):
                    c2, ch2 = keys.cost(S2)
                    if c2 < best[0]: best = (c2, ch2)
        return best[0] + 1, best[1]

ITEMS = list(AFF.items())
def cover(f, keys, mode, maxp=12):
    """greedy XOR cover of f (or its complement) by affine pieces, cost-aware."""
    best = None
    for const in (0, 1):
        rem = f ^ (M64 if const else 0); pcs = []; K = Keys(); K.keys = set(keys.keys); tot = 0
        while rem and len(pcs) < maxp:
            b = None; w0 = bin(rem).count('1')
            for mask, forms in ITEMS:
                g = w0 - bin(rem ^ mask).count('1')
                if g <= 0: continue
                c, ch = piece_cost(mask, K, mode)
                sc = g / (c + 0.3)
                if b is None or sc > b[0]: b = (sc, mask, c, ch)
            rem ^= b[1]; pcs.append((b[1], b[2])); K.add(b[3]); tot += b[2]
        if rem: continue
        if best is None or tot < best[0]: best = (tot, const, pcs, K)
    return best

def side_cost(fs, mode, order=None):
    keys = Keys(); tot = 0; detail = []
    for i in (order or range(len(fs))):
        r = cover(fs[i], keys, mode)
        if r is None: return None
        tot += r[0]; keys = r[3]; detail.append((i, r[0], [(CODIM[m], c) for m, c in r[2]], r[1]))
    return tot, len(keys.keys), detail

def corner_basis():
    F = SD.F
    def px(x, y): return (F >> (x + 64 * y)) & 1 if 0 <= x < 64 and 0 <= y < 64 else 0
    corners = [(p, q) for p in range(64) for q in range(64)
               if (px(p, q) ^ px(p - 1, q) ^ px(p, q - 1) ^ px(p - 1, q - 1))]
    xs = sorted(set(p for p, q in corners)); ys = sorted(set(q for p, q in corners))
    thr = lambda p: sum(1 << v for v in range(64) if v >= p)
    xf = [thr(p) for p in xs]
    yf = [sum(thr(q) for q in ys if (p, q) in corners) & 0 for p in xs]
    yf = []
    for p in xs:
        t = 0
        for q in ys:
            if (p, q) in corners: t ^= thr(q)
        yf.append(t)
    # transposed: y thresholds folded, x partners held
    yf2 = [thr(q) for q in ys]; xf2 = []
    for q in ys:
        t = 0
        for p in xs:
            if (p, q) in corners: t ^= thr(p)
        xf2.append(t)
    return (xf, yf), (xf2, yf2), len(corners)

if __name__ == '__main__':
    xf, yf = SY.basis_pair(); dx, dy = SY.basis_diff()
    (cx1, cy1), (cx2, cy2), nc = corner_basis()
    print('corners', nc, 'x thresholds', len(cx1), 'y thresholds', len(cy2), flush=True)
    bases = {'pair': (xf, yf), 'diff': (dx, dy), 'corner-x': (cx1, cy1), 'corner-y': (cx2, cy2)}
    res = {}
    for name, (fx, fy) in bases.items():
        for mode_x, mode_y in (('fold', 'hold'), ('hold', 'fold')):
            rx = side_cost(fx, mode_x); ry = side_cost(fy, mode_y)
            if rx is None or ry is None: print(name, mode_x, mode_y, 'cover failed'); continue
            # units per direction; both-direction load: keys and held pieces doubled, folded CCZ once
            ux = rx[0]; uy = ry[0]
            print('%-9s x:%s y:%s  units/dir x %3d (keys %2d)  y %3d (keys %2d)   total %3d' % (name, mode_x, mode_y, ux, rx[1], uy, ry[1], ux + uy), flush=True)
            res[(name, mode_x, mode_y)] = (rx, ry)
            for i, c, pcs, const in rx[2]: print('    x f%d cost %2d pieces(codim,cost) %s const %d' % (i, c, pcs, const))
            for i, c, pcs, const in ry[2]: print('    y f%d cost %2d pieces(codim,cost) %s const %d' % (i, c, pcs, const))
    pickle.dump(res, open('cpfn_count.pkl', 'wb'))
