"""Exact GF(2) test: is F in the span of {1, inputs, Toffoli products, and
pair + triple products of the wires at EVERY Toffoli state} of a genome?
Reports feature count, GF(2) rank of the features, rank with F appended.
Usage: python3 cptm_rank.py NPZ... [BASIS=pkl]"""
import sys, os, time, pickle
import numpy as np
import cpte_evo as E

def bits(v): return ((v[:, None] >> np.arange(64, dtype=np.uint64)) & np.uint64(1)).astype(np.uint8).reshape(-1)

def gf2_rank(M):
    """M: rows x 4096 uint8 -> rank (packed elimination)"""
    A = np.packbits(M, axis=1).view(np.uint64) if M.shape[1] % 64 == 0 else None
    A = np.packbits(M, axis=1)
    A = A.view(np.uint8).copy()
    rows, cols = M.shape; r = 0
    Mb = M.copy()
    for c in range(cols):
        if r == rows: break
        nz = np.nonzero(Mb[r:, c])[0]
        if len(nz) == 0: continue
        p = r + nz[0]
        if p != r: Mb[[r, p]] = Mb[[p, r]]
        o = np.nonzero(Mb[:, c])[0]; o = o[o != r]
        Mb[o] ^= Mb[r]; r += 1
    return r

if __name__ == '__main__':
    Fv = E.logo_bits()
    if os.environ.get('BASIS'):
        from cptk_basis import fprime
        bd = pickle.load(open(os.environ['BASIS'], 'rb')); Fv = E.pack(fprime(bd['cols'], bd['c']))
    for f in sys.argv[1:]:
        d = np.load(f); cx, tf, L = d['cx'], d['tf'], int(d['L']); P = E.P; T = L * P
        st = E.states(cx, tf, L)
        rows = [np.full(64, np.uint64(0xFFFFFFFFFFFFFFFF))] + [st[0, i] for i in range(12)]
        for j in range(T):
            if j % P == P - 1:
                for w in range(18):
                    if tf[j, w, 0] >= 0: rows.append(st[j + 1, w] ^ st[j, w])
        for s in range(0, T + 1, P):
            for a in range(18):
                for b in range(a + 1, 18):
                    rows.append(st[s, a] & st[s, b])
                    for c in range(b + 1, 18): rows.append(st[s, a] & st[s, b] & st[s, c])
        M = np.array([bits(r) for r in rows], dtype=np.uint8)
        t0 = time.time()
        r1 = gf2_rank(M); r2 = gf2_rank(np.vstack([M, bits(Fv)[None, :]]))
        print('%-45s L %d  states %d  features %d  rank %d  rank+F %d  -> F in span: %s  (%.0fs)' %
              (f, L, L + 1, len(rows), r1, r2, r1 == r2, time.time() - t0), flush=True)
