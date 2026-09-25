"""Affine input basis minimising the ANF monomial count of f'(u) = F(A u ^ c).
Simulated annealing over elementary column operations of A (col_i ^= col_j)
and bit flips of c.  Same objective as the earlier record (216 best).
Usage: python3 cptk_basis.py SEED ITERS
Progress every 10 s; checkpoint ckpt/basis_s<seed>.pkl (cols, c, n)"""
import sys, time, pickle, math
import numpy as np
from cpae_core import SHAPES, fvec

IDX = np.arange(4096, dtype=np.int64)
BITS = np.stack([(IDX >> j) & 1 for j in range(12)])
F = fvec(SHAPES['LOGO']).astype(np.uint8)


def anf_count(f):
    a = f.copy(); h = 1
    while h < 4096:
        a = a.reshape(-1, 2 * h); a[:, h:] ^= a[:, :h]; a = a.reshape(-1); h *= 2
    return int(a.sum())


def fprime(cols, c):
    idx = np.zeros(4096, dtype=np.int64)
    for j in range(12): idx ^= BITS[j] * cols[j]
    return F[idx ^ c]


if __name__ == '__main__':
    seed, iters = int(sys.argv[1]), int(sys.argv[2])
    rng = np.random.default_rng(seed)
    cols = [1 << j for j in range(12)]; c = 0
    cur = anf_count(fprime(cols, c)); best = (cur, list(cols), c)
    t0 = time.time(); last = t0
    for it in range(iters):
        T = 3.0 * (1 - it / iters) + 0.05
        nc, ncc = list(cols), c
        if rng.random() < 0.8:
            i, j = rng.choice(12, 2, replace=False); nc[i] ^= nc[j]
        else:
            ncc ^= 1 << int(rng.integers(12))
        n = anf_count(fprime(nc, ncc))
        if n <= cur or rng.random() < math.exp((cur - n) / T):
            cols, c, cur = nc, ncc, n
            if n < best[0]:
                best = (n, list(nc), ncc)
                pickle.dump(dict(cols=best[1], c=best[2], n=best[0]), open('ckpt/basis_s%d.pkl' % seed, 'wb'))
        if time.time() - last > 10:
            last = time.time()
            print('[basis s%d] it %d  cur %d  best %d  %.0fs' % (seed, it, cur, best[0], last - t0), flush=True)
    print('[basis s%d] final best %d monomials  cols %s c %d' % (seed, best[0], best[1], best[2]), flush=True)
