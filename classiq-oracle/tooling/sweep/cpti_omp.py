"""Phase-polynomial readout size.  Given wire contents z(x) (18 functions of
x, e.g. the state of a forward stream at one or more instants), the phase
pi*F(x) is realised by Rz on parities of the wires:
    pi*F(x) = c + sum_T theta_T * (-1)^{T . z(x)}      (all x)
Each atom (instant, parity T) costs one Rz on a parity-network wire.
Orthogonal matching pursuit (correlations by a 2^18 Walsh-Hadamard transform
per instant, least squares on the chosen atoms) until the residual is 0
(exact) or KMAX atoms.  Reports K, the number of parities needed.
Usage: python3 cpti_omp.py base            (z = x only: plain Walsh, sanity)
       python3 cpti_omp.py npz FILE [final|all]   (evolved stream: final state or every Toffoli state)
Output: one line / 50 atoms; ckpt/omp_<tag>.json"""
import os, sys, time, json
import numpy as np
import cpte_evo as E
from cpae_core import SHAPES, fvec

KMAX = int(os.environ.get('KMAX', '4096'))
N = 4096


def unpack(v):
    return ((v[:, None] >> np.arange(64, dtype=np.uint64)) & np.uint64(1)).astype(np.int64).reshape(-1)


def fwht(a):
    a = a.copy(); h = 1; n = a.shape[0]
    while h < n:
        a = a.reshape(-1, 2, h); a = np.stack([a[:, 0] + a[:, 1], a[:, 0] - a[:, 1]], axis=1).reshape(-1); h *= 2
    return a


def zcode(Z):
    """Z: list of 18 0/1 arrays over x -> integer code z(x) in [0, 2^18)"""
    c = np.zeros(N, dtype=np.int64)
    for i, v in enumerate(Z): c |= v.astype(np.int64) << i
    return c


def omp(codes, target, tag):
    """codes: list of z-codes (one per instant); atoms (instant, T) with
    column chi_T(z(x)) = (-1)^popcount(T & z(x)); constant column included."""
    cols = [np.ones(N)]; names = [('const',)]
    r = target - target.mean()
    Q = np.ones((N, 1)) / np.sqrt(N)
    t0 = time.time(); last = t0
    pc = np.array([bin(i).count('1') & 1 for i in range(1 << 18)], dtype=np.int8) if len(codes) else None
    while True:
        res = float(np.abs(r).max())
        if res < 1e-9 or len(cols) - 1 >= KMAX: break
        best = (0, None)
        for s, c in enumerate(codes):
            R = np.zeros(1 << 18); np.add.at(R, c, r)
            W = np.abs(fwht(R))
            W[0] = 0
            for (_, s2, T2) in [n for n in names if n[0] == 'atom' and n[1] == s]: W[T2] = 0
            i = int(np.argmax(W))
            if W[i] > best[0]: best = (W[i], (s, i))
        if best[1] is None: break
        s, T = best[1]
        col = 1.0 - 2.0 * pc[T & codes[s]]
        cols.append(col); names.append(('atom', s, T))
        q = col - Q @ (Q.T @ col); q -= Q @ (Q.T @ q)
        nq = np.linalg.norm(q)
        if nq < 1e-9: continue
        Q = np.hstack([Q, (q / nq)[:, None]])
        r = target - Q @ (Q.T @ target)
        now = time.time()
        if len(cols) % 50 == 0 or now - last > 10:
            last = now
            print('[%s] atoms %d  max residual %.3e  rms %.3e  %.0fs' % (tag, len(cols) - 1, np.abs(r).max(),
                  np.sqrt((r ** 2).mean()), now - t0), flush=True)
    K = len(cols) - 1
    print('[%s] done: atoms %d  max residual %.3e  exact %s  %.0fs' % (tag, K, np.abs(r).max(), np.abs(r).max() < 1e-9,
          time.time() - t0), flush=True)
    json.dump(dict(tag=tag, atoms=K, max_res=float(np.abs(r).max()), exact=bool(np.abs(r).max() < 1e-9),
                   per_instant=[sum(1 for n in names if n[0] == 'atom' and n[1] == s) for s in range(len(codes))]),
              open('ckpt/omp_%s.json' % tag, 'w'))
    return K


if __name__ == '__main__':
    F = fvec(SHAPES['LOGO']).astype(np.float64)
    target = np.pi * F
    x = np.arange(N)
    X = [(x >> i) & 1 for i in range(12)] + [np.zeros(N, dtype=np.int64)] * 6
    if sys.argv[1] == 'base':
        omp([zcode(X)], target, 'base')
    else:
        f = sys.argv[2]; mode = sys.argv[3] if len(sys.argv) > 3 else 'final'
        d = np.load(f); cx, tf, L = d['cx'], d['tf'], int(d['L'])
        st = E.states(cx, tf, L)
        P = E.P
        idx = [L * P] if mode == 'final' else [0] + [j + 1 for j in range(L * P) if j % P == P - 1]
        codes = [zcode([unpack(st[j][w]) for w in range(18)]) for j in idx]
        omp(codes, target, os.path.basename(f).replace('.npz', '') + '_' + mode)
