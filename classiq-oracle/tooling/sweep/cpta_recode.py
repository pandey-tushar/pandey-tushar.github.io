"""search affine recodings z = L x + c of one 6-bit side that lower the degree
of that side's function space V.  Score = dims of V inside deg<=2, deg<=3."""
import itertools, random, sys
from cpta_tensor import Span
from cpri_round import logo_pairs

def table(fn): return sum(1 << x for x in range(64) if fn(x))
MON = {d: [S for k in range(d + 1) for S in itertools.combinations(range(6), k)] for d in (2, 3)}

def apply(L, c, x):
    z = 0
    for i in range(6):
        z |= ((bin(L[i] & x).count('1') + ((c >> i) & 1)) & 1) << i
    return z

def score(W, L, c):
    zs = [apply(L, c, x) for x in range(64)]
    out = []
    for d in (2, 3):
        S = Span()
        for M in MON[d]:
            S.add(sum(1 << x for x in range(64) if all((zs[x] >> i) & 1 for i in M)))
        n0 = len(S.b); k = sum(S.add(w) for w in W)
        out.append(len(W_dim(W)) - k)
    return tuple(out)

def W_dim(W):
    S = Span(); [S.add(w) for w in W]; return S.b

def invertible(L):
    S = Span(); return all(S.add(r) for r in L)

def search(W, iters, seed):
    rng = random.Random(seed)
    L = [1 << i for i in range(6)]; c = 0
    cur = score(W, L, c); best = (cur, list(L), c)
    for it in range(iters):
        L2 = list(L); c2 = c
        m = rng.random()
        if m < 0.7:
            i, j = rng.sample(range(6), 2); L2[i] ^= L2[j]
        elif m < 0.85:
            c2 ^= 1 << rng.randrange(6)
        else:
            i, j = rng.sample(range(6), 2); L2[i], L2[j] = L2[j], L2[i]
        s = score(W, L2, c2)
        if s >= cur or rng.random() < 0.05:
            L, c, cur = L2, c2, s
            if s > best[0]: best = (s, list(L2), c2)
    return best

if __name__ == '__main__':
    side = sys.argv[1]; iters = int(sys.argv[2]); seeds = int(sys.argv[3])
    W = [u for u, v in logo_pairs()] if side == 'x' else [v for u, v in logo_pairs()]
    print(side, 'dim', len(W_dim(W)), 'identity score', score(W, [1 << i for i in range(6)], 0))
    for s in range(seeds):
        b = search(W, iters, s)
        print('seed', s, 'deg2/deg3 dims', b[0], 'L', [bin(r) for r in b[1]], 'c', bin(b[2]), flush=True)
