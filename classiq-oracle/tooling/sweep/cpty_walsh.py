"""Arbitrary-angle phase stage after a Toffoli prefix.  Wire state g(x) (18 bits,
injective).  Exact iff pi*F(x) = sum_S theta_S * (S.g(x) mod 2) (real, no 2pi
wrap used here) -- equivalently F = c0 + sum_S c_S (-1)^{S.g(x)}.  K = number of
parity terms: greedy OMP; each step scores all 2^18 parities at once with one
18-bit Walsh transform of the residual placed on the image points.
Modes: ident | rand L | plant L (target = product of 4 prefix wire values).
Usage: python3 cpty_walsh.py MODE L SEED BUDGET"""
import sys, time, random
import numpy as np
import cpte_evo as E
from cptw_mcts import Env, rand_action, unpack

NW = 18; NS = 1 << NW


def fwht(a):
    a = a.copy(); h = 1
    while h < len(a):
        a = a.reshape(-1, 2 * h); x = a[:, :h].copy(); y = a[:, h:]; a[:, :h] += y; a[:, h:] = x - y; a = a.reshape(-1); h *= 2
    return a


def omp(idx, y, budget, marks=(25, 50, 100, 200, 400, 800, 1600, 3200)):
    n = len(y); Q = np.zeros((n, budget + 1)); k = 0
    q = np.ones(n) / np.sqrt(n); Q[:, 0] = q; k = 1
    r = y - q * (q @ y); chosen = {0}; out = {}
    pc = np.array([bin(i).count('1') & 1 for i in range(1 << 9)], dtype=np.int8)
    def col(S):
        v = idx & S
        par = pc[v & 511] ^ pc[(v >> 9) & 511]
        return 1.0 - 2.0 * par
    t0 = time.time()
    while k <= budget:
        z = np.zeros(NS); z[idx] = r
        c = np.abs(fwht(z)); c[list(chosen)] = -1
        S = int(np.argmax(c)); chosen.add(S)
        v = col(S)
        for _ in range(2): v = v - Q[:, :k] @ (Q[:, :k].T @ v)
        nv = np.linalg.norm(v)
        if nv < 1e-9: continue
        v /= nv; Q[:, k] = v; k += 1
        r = r - v * (v @ r)
        res = np.linalg.norm(r)
        if (k - 1) in marks: out[k - 1] = res
        if res < 1e-7: out['exact'] = k - 1; break
    return out, time.time() - t0


if __name__ == '__main__':
    mode, L, seed, budget = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    rng = random.Random(seed)
    F = unpack(E.logo_bits()).astype(float)
    seq = []
    if mode in ('rand', 'plant'):
        for l in range(L):
            used = set()
            for _ in range(6):
                a = rand_action(used, rng)
                if a is None: break
                seq.append(a); used |= {a[0], a[1], a[4]}
            seq.append('end')
    env = Env(E.logo_bits(), max(L, 1)); S, _ = env.play(seq)
    W = np.array([unpack(S[w]) for w in range(NW)]).astype(np.int64)
    idx = (W << np.arange(NW)[:, None]).sum(0)
    assert len(set(idx.tolist())) == 4096
    if mode == 'plant':
        nz = [w for w in range(NW) if W[w].any() and not W[w].all()]
        pick = rng.sample(nz, 4)
        F = np.prod(W[pick], axis=0).astype(float)
        print('planted: product of wires %s, weight %d (true K <= 16)' % (pick, F.sum()))
    out, dt = omp(idx, F, budget)
    print('%s L%d s%d: residual norm by K %s  (%.0fs)' % (mode, L, seed,
          {k: ('%.3g' % v if k != 'exact' else v) for k, v in out.items()}, dt), flush=True)
