"""Coordinate-transform synthesis.  In-place gates on the 12 data wires are
permutations sigma of {0,1}^12; the phase function in current wire
coordinates is G = F o sigma^-1 (exact, 4096-entry table).  Goal: a short
gate sequence after which deg G <= 3; a cubic phase layer then finishes the
oracle exactly and the mirror restores the wires.
Gates: CX (t ^= a), Toffoli (t ^= (a^pa)(b^pb)).  Cost of G = number of ANF
monomials of degree >= 4 (weighted by degree-3 with W=1).
Greedy/beam: each step tries every gate, keeps the BEAM best tables.
Usage: python3 cptl_deg.py SEED STEPS [BASIS_PKL]
Progress one line per step; checkpoint ckpt/deg_s<seed>.pkl (gate list, cost)"""
import os, sys, time, pickle
import numpy as np
from cpae_core import SHAPES, fvec

N = 4096
IDX = np.arange(N, dtype=np.int64)
DEG = np.array([bin(i).count('1') for i in range(N)], dtype=np.int64)
W = int(os.environ.get('W', '1'))
BEAM = int(os.environ.get('BEAM', '8'))
HI = DEG >= 4
WT = np.where(HI, (DEG - 3) if W else 1, 0)


def anf(t):
    a = t.copy(); h = 1
    while h < N:
        a = a.reshape(-1, 2 * h); a[:, h:] ^= a[:, :h]; a = a.reshape(-1); h *= 2
    return a


def cost(t):
    a = anf(t)
    return int((a * WT).sum()), int(a.sum()), int(DEG[a == 1].max()) if a.any() else 0


def gates():
    g = []
    for t in range(12):
        for a in range(12):
            if a != t: g.append(('cx', a, t, 0, 0, -1))
        for a in range(12):
            for b in range(a + 1, 12):
                if t in (a, b): continue
                for pa in range(2):
                    for pb in range(2): g.append(('tof', a, b, pa, pb, t))
    return g


def apply(tbl, g):
    """new table in the new coordinates: G'(z') = G(sigma^-1 z'); sigma is an involution"""
    k, a, b, pa, pb, t = g
    if k == 'cx': src = IDX ^ (((IDX >> a) & 1) << b)          # here b holds the target
    else: src = IDX ^ (((((IDX >> a) & 1) ^ pa) & (((IDX >> b) & 1) ^ pb)) << t)
    return tbl[src]


if __name__ == '__main__':
    seed, steps = int(sys.argv[1]), int(sys.argv[2])
    F = fvec(SHAPES['LOGO']).astype(np.uint8)
    if len(sys.argv) > 3:
        from cptk_basis import fprime
        bd = pickle.load(open(sys.argv[3], 'rb')); F = fprime(bd['cols'], bd['c']).astype(np.uint8)
    G = gates(); rng = np.random.default_rng(seed)
    c0 = cost(F)
    print('start: weighted high-degree cost %d  monomials %d  max degree %d  (gates per step %d, BEAM %d)' %
          (c0[0], c0[1], c0[2], len(G), BEAM), flush=True)
    if os.environ.get('LAYER'):               # layer mode: each step = one layer of disjoint gates
        LB = int(os.environ.get('LBEAM', '6'))
        beam = [(c0, F, [])]; t0 = time.time()
        for s in range(steps):
            cand = []
            for (c, tbl, seq) in beam:
                for trial in range(LB):
                    used = set(); t2 = tbl; cur = c; lay = []
                    while True:
                        opts = [g for g in G if not ({g[1], g[2], g[5]} - {-1}) & used and not (g[0] == 'cx' and {g[1], g[2]} & used)]
                        if not opts: break
                        sc = []
                        for g in opts:
                            nt = apply(t2, g); sc.append((cost(nt), rng.random(), g, nt))
                        sc.sort(key=lambda z: (z[0], z[1]))
                        k = min(len(sc) - 1, int(rng.integers(3)) if trial else 0)
                        cc, _, g, nt = sc[k]
                        if cc >= cur: break
                        t2, cur = nt, cc; lay.append(g)
                        used |= ({g[1], g[2], g[5]} - {-1}) if g[0] == 'tof' else {g[1], g[2]}
                    cand.append((cur, rng.random(), t2, seq + [lay]))
            cand.sort(key=lambda z: (z[0], z[1]))
            nb, seen = [], set()
            for c, _, nt, seq in cand:
                key = nt.tobytes()
                if key in seen: continue
                seen.add(key); nb.append((c, nt, seq))
                if len(nb) == BEAM: break
            beam = nb
            print('layer %2d  best cost %s  gates in layer %d  beam %s  %.0fs' % (s + 1, beam[0][0], len(beam[0][2][-1]),
                  [b[0][0] for b in beam[:5]], time.time() - t0), flush=True)
            pickle.dump(dict(layers=beam[0][2], cost=beam[0][0]), open('ckpt/degL_s%d.pkl' % seed, 'wb'))
            np.save('ckpt/degL_s%d_target.npy' % seed, beam[0][1])
        sys.exit(0)
    beam = [(c0, F, [])]; t0 = time.time(); best = beam[0]
    for s in range(steps):
        cand = []
        for (c, tbl, seq) in beam:
            for g in G:
                nt = apply(tbl, g)
                cand.append((cost(nt), rng.random(), nt, seq + [g]))
        cand.sort(key=lambda z: (z[0], z[1]))
        nb, seen = [], set()
        for c, _, nt, seq in cand:
            key = nt.tobytes()
            if key in seen: continue
            seen.add(key); nb.append((c, nt, seq))
            if len(nb) == BEAM: break
        beam = nb
        if beam[0][0] < best[0]: best = beam[0]
        print('step %2d  best cost %s  beam costs %s  %.0fs' % (s + 1, beam[0][0], [b[0][0] for b in beam[:5]], time.time() - t0), flush=True)
        pickle.dump(dict(seq=beam[0][2], cost=beam[0][0]), open('ckpt/deg_s%d.pkl' % seed, 'wb'))
        if beam[0][0][0] == 0:
            print('degree <= 3 reached at step %d' % (s + 1), flush=True); break
