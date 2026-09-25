"""Rotation-phase model: Rz(pi*a/2^(J-1)) on any wire at any time contributes
(pi*a/2^(J-1)) * w(t)(x); exact oracle iff  sum_k a_k p_k == 2^(J-1) F  (mod 2^J)
over the distinct wire values p_k seen during the forward pass (plus const).
Solver: unit-pivot elimination mod 2^J, then halve the remainder and recurse.
Test: random L-level circuits (Toffoli layers + CX layers) -> solvable or not,
residual = inconsistent rows at the failing stage.
Usage: python3 cpts_z8.py J L LCX TRIALS"""
import sys, time
import numpy as np
import numba as nb


@nb.njit(cache=True)
def solve_mod(A, b, J):
    """A: int64 [n, m] 0..2^J-1, b: [n].  returns (ok, residual rows, stage, pivots)"""
    n, m = A.shape
    M = (1 << J) - 1
    A = A.copy(); b = b.copy()
    active_c = np.ones(m, dtype=np.bool_)
    active_r = np.ones(n, dtype=np.bool_)
    npiv = 0
    for stage in range(J):
        mod = (1 << (J - stage)) - 1
        # unit pivots
        for c in range(m):
            if not active_c[c]: continue
            r = -1
            for i in range(n):
                if active_r[i] and (A[i, c] & 1): r = i; break
            if r < 0: continue
            # inverse of odd u mod 2^(J-stage)
            u = A[r, c] & mod; inv = 1
            for _ in range(6): inv = (inv * (2 - u * inv)) & mod
            for k in range(m): A[r, k] = (A[r, k] * inv) & mod
            b[r] = (b[r] * inv) & mod
            for i in range(n):
                if i != r and active_r[i]:
                    f = A[i, c] & mod
                    if f:
                        for k in range(m): A[i, k] = (A[i, k] - f * A[r, k]) & mod
                        b[i] = (b[i] - f * b[r]) & mod
            active_r[r] = False; active_c[c] = False; npiv += 1
        # remaining rows: all active entries even
        bad = 0
        for i in range(n):
            if active_r[i] and (b[i] & 1): bad += 1
        if bad: return False, bad, stage, npiv
        if stage == J - 1: return True, 0, stage, npiv
        for i in range(n):
            if active_r[i]:
                b[i] >>= 1
                for k in range(m):
                    if active_c[k]: A[i, k] >>= 1
    return True, 0, J, npiv


def unpack(v):
    return ((v[:, None] >> np.arange(64, dtype=np.uint64)) & np.uint64(1)).astype(np.int64).reshape(-1)


def forms_of(ops, nw=18):
    """distinct wire values over time for an op list (cx a t / ccx a b t with pol) on 12 data + ancillas"""
    idx = np.arange(4096)
    w = [((idx >> i) & 1).astype(np.uint8) for i in range(12)] + [np.zeros(4096, np.uint8)] * (nw - 12)
    seen = {}
    def add(v):
        if v.any(): seen.setdefault(v.tobytes(), v.copy())
    for v in w: add(v)
    for op in ops:
        if op[0] == 'cx': w[op[2]] = w[op[2]] ^ w[op[1]]; add(w[op[2]])
        elif op[0] == 'ccx':
            a, b, pa, pb, t = op[1:]
            w[t] = w[t] ^ ((w[a] ^ pa) & (w[b] ^ pb)); add(w[t])
    return list(seen.values()), w


def check(forms, F, J):
    A = np.array([np.ones(4096, np.int64)] + [f.astype(np.int64) for f in forms]).T.copy()
    b = (F.astype(np.int64) << (J - 1))
    return solve_mod(A, b, J)


def random_ops(L, lcx, rng, nw=18):
    ops = []
    for l in range(L):
        for _ in range(lcx):
            perm = rng.permutation(nw)
            for i in range(0, nw - 1, 2): ops.append(('cx', int(perm[i]), int(perm[i + 1])))
        perm = rng.permutation(nw)
        for i in range(0, nw - 2, 3):
            ops.append(('ccx', int(perm[i]), int(perm[i + 1]), int(rng.integers(2)), int(rng.integers(2)), int(perm[i + 2])))
    return ops


if __name__ == '__main__':
    J, L, lcx, trials = map(int, sys.argv[1:5])
    from cpae_core import SHAPES, fvec
    F = fvec(SHAPES['LOGO']).astype(np.int64)
    rng = np.random.default_rng(1)
    for tr in range(trials):
        ops = random_ops(L, lcx, rng)
        forms, _ = forms_of(ops)
        t0 = time.time()
        ok, bad, st, npiv = check(forms, F, J)
        # GF(2)-only comparison (J=1)
        ok1, bad1, _, np1 = check(forms, F, 1)
        print('trial %d: forms %d  Z%d: ok %s residual %d (stage %d, pivots %d)  | GF2: ok %s residual %d rank %d  %.1fs' %
              (tr, len(forms), 1 << J, ok, bad, st, npiv, ok1, bad1, np1, time.time() - t0), flush=True)
