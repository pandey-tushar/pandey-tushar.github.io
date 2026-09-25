"""Check B: how many products F needs as an XOR of products (ESOP-type
forms of the whole truth table), and how many literals each has.
1. FPRM: for every input polarity (4096), the algebraic normal form of F with
   those inputs negated; best term count.
2. PSDKRO: per variable choose Shannon / positive Davio / negative Davio,
   exact minimum by memoized recursion for a given variable order; several
   orders.  (PSDKRO and FPRM are upper bounds on the minimum ESOP.)
Output: term counts, literal histogram.  Checkpoint: ckpt/esop.json"""
import os, sys, json, time
from functools import lru_cache
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpae_core import SHAPES, fvec

N, n = 4096, 12


def anf(t):
    a = t.astype(np.uint8).copy(); h = 1
    while h < len(a):
        a = a.reshape(-1, 2 * h); a[:, h:] ^= a[:, :h]; a = a.reshape(-1); h *= 2
    return a


def fprm(f):
    idx = np.arange(N); best = None
    for pol in range(N):
        a = anf(f[idx ^ pol])
        c = int(a.sum())
        if best is None or c < best[0]: best = (c, pol, a)
    c, pol, a = best
    lits = [bin(m).count('1') for m in np.nonzero(a)[0]]
    return c, pol, np.bincount(lits, minlength=n + 1).tolist()


def psdkro(f, order):
    """f as tuple-of-bits truth table; recursion splits variable order[i].
    returns (terms, literal histogram)"""
    sys.setrecursionlimit(10000)
    memo = {}
    def rec(t, i):
        # t: bytes of a 2^(n-i) table over remaining variables order[i:], var order[i] = top bit
        key = (t, i)
        if key in memo: return memo[key]
        arr = np.frombuffer(t, dtype=np.uint8)
        if not arr.any(): r = (0, (0,) * (n + 1))
        elif i == n: r = (1, (1,) + (0,) * n)
        else:
            h = len(arr) // 2
            f0, f1 = arr[:h], arr[h:]; f2 = f0 ^ f1
            opts = []
            for a, b, la, lb in ((f0, f1, 1, 1), (f0, f2, 0, 1), (f1, f2, 0, 1)):
                ca, ha = rec(a.tobytes(), i + 1); cb, hb = rec(b.tobytes(), i + 1)
                hist = [0] * (n + 1)
                for k in range(n + 1):
                    if ha[k] and k + la <= n: hist[k + la] += ha[k]
                    if hb[k] and k + lb <= n: hist[k + lb] += hb[k]
                opts.append((ca + cb, tuple(hist)))
            r = min(opts, key=lambda o: (o[0], sum(k * v for k, v in enumerate(o[1]))))
        memo[key] = r
        return r
    # reorder truth table so that order[0] is the top (most significant) bit
    idx = np.zeros(N, dtype=np.int64)
    for j in range(N):
        x = 0
        for pos, v in enumerate(order):
            x |= ((j >> (n - 1 - pos)) & 1) << v
        idx[j] = x
    return rec(f[idx].astype(np.uint8).tobytes(), 0), len(memo)


if __name__ == '__main__':
    f = fvec(SHAPES['LOGO']).astype(np.uint8)
    out = {}
    t0 = time.time()
    c, pol, hist = fprm(f)
    out['fprm'] = dict(terms=c, polarity=pol, literal_hist=hist)
    print('FPRM best over 4096 polarities: %d terms (polarity %s), literals per term %s  %.0fs' %
          (c, format(pol, '012b'), hist, time.time() - t0), flush=True)
    json.dump(out, open('ckpt/esop.json', 'w'), indent=1)
    rng = np.random.default_rng(0)
    orders = [list(range(12)), list(range(11, -1, -1)),
              [0, 6, 1, 7, 2, 8, 3, 9, 4, 10, 5, 11], [5, 11, 4, 10, 3, 9, 2, 8, 1, 7, 0, 6]]
    orders += [list(rng.permutation(12)) for _ in range(12)]
    best = None
    for o in orders:
        t1 = time.time()
        (c, hist), nm = psdkro(f, o)
        if best is None or c < best[0]: best = (c, o, hist)
        print('PSDKRO order %s: %d terms, literals %s  (memo %d, %.0fs)' % (o, c, list(hist), nm, time.time() - t1), flush=True)
        out['psdkro_best'] = dict(terms=best[0], order=[int(v) for v in best[1]], literal_hist=list(best[2]))
        json.dump(out, open('ckpt/esop.json', 'w'), indent=1)
    print('best PSDKRO: %d terms, order %s, literals %s' % (best[0], best[1], list(best[2])), flush=True)
