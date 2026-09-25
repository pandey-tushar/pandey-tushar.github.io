"""Stronger (offline) decoder for cpth_span genomes: distance from F to the
GF(2) span of the features.  (a) greedy pursuit (the in-loop bound);
(b) information-set decoding: random permutation, Gaussian elimination to
reduced form, codeword matching F on the information set, then greedy
polishing; best over NTRY tries.  Usage: [CZ=1] python3 cpth_decode.py NPZ... """
import sys, os, time
import numpy as np
import cpte_evo as E
import cpth_emit as EM
import cpth_span as S

NTRY = int(os.environ.get('NTRY', '200'))


def bits(v): return ((v[:, None] >> np.arange(64, dtype=np.uint64)) & np.uint64(1)).astype(np.uint8).reshape(-1)


def isd(rows, f, rng, ntry):
    A = np.array([bits(r) for r in rows], dtype=np.uint8)      # k x 4096
    fb = bits(f)
    best = int(fb.sum())
    for _ in range(ntry):
        perm = rng.permutation(4096)
        M = A[:, perm].copy(); t = fb[perm].copy()
        piv = []; r = 0
        for c in range(4096):
            if r == M.shape[0]: break
            nz = np.nonzero(M[r:, c])[0]
            if len(nz) == 0: continue
            p = r + nz[0]
            if p != r: M[[r, p]] = M[[p, r]]
            others = np.nonzero(M[:, c])[0]; others = others[others != r]
            M[others] ^= M[r]
            piv.append(c); r += 1
        M = M[:r]
        res = t.copy()
        for i, c in enumerate(piv):
            if res[c]: res ^= M[i]
        w = int(res.sum())
        imp = True
        while imp:                                  # greedy polish with basis rows
            imp = False
            ws = ((res[None, :] ^ M).sum(axis=1))
            i = int(np.argmin(ws))
            if ws[i] < w: res ^= M[i]; w = int(ws[i]); imp = True
        best = min(best, w)
    return best


if __name__ == '__main__':
    rng = np.random.default_rng(0)
    Fv = E.logo_bits()
    for f in sys.argv[1:]:
        d = np.load(f); cx, tf, L = d['cx'], d['tf'], int(d['L'])
        st = E.states(cx, tf, L)
        rows, lab = EM.features(st, tf, L * E.P, E.P, S.CZ)
        g, _ = EM.pursuit(rows, Fv)
        t0 = time.time()
        b = isd(rows, Fv, rng, NTRY)
        print('%-45s features %d  greedy dist %d  ISD(+polish, %d tries) dist %d  -> fitness %d  (%.0fs)' %
              (f, len(rows), g, NTRY, b, 4096 - min(g, b), time.time() - t0), flush=True)
