"""Budgeted builder: choose internal AND values level by level so that F lies
in the GF(2) span of {1, inputs, internal AND products, pair and triple
products of the values held at the turnaround}.
Wires: 12 data + 6 ancillas.  A level places up to 6 ANDs (Toffolis on
disjoint wires; target = a zero ancilla or a data wire that is hosted
in place).  Candidate products at a level: AND of two currently held wire
values (any polarity).  Selection per AND: the candidate that lowers the
GF(2) deficiency of F most, measured as the weight of F reduced against an
incremental basis of the features that WOULD exist at the turnaround (held
values' pairs/triples + all products so far) -- beam over levels.
Usage: python3 cptq_rank.py SEED LEVELS [BEAM]
Progress per AND; checkpoint ckpt/qrank_s<seed>.pkl"""
import os, sys, time, pickle, json
import numpy as np
import numba as nb
import cpte_evo as E
from cpte_evo import NW, NWORD, popc
from cptn_prefix import insert, member

ONES = np.uint64(0xFFFFFFFFFFFFFFFF)


@nb.njit(cache=True)
def turn_basis(S, prods, npr, basis, piv):
    """basis of: const, the 12 inputs (S0 rows 0..11 passed in prods[0:13]), products, pairs+triples of S"""
    nb_ = 0
    for i in range(npr): nb_ = insert(basis, piv, nb_, prods[i])
    tmp = np.empty(NWORD, dtype=np.uint64)
    n = S.shape[0]
    for a in range(n):
        for b in range(a + 1, n):
            for k in range(NWORD): tmp[k] = S[a, k] & S[b, k]
            nb_ = insert(basis, piv, nb_, tmp)
            for c in range(b + 1, n):
                for k in range(NWORD): tmp[k] = S[a, k] & S[b, k] & S[c, k]
                nb_ = insert(basis, piv, nb_, tmp)
    return nb_


def deficiency(S, prods, Fv, basis, piv):
    nb_ = turn_basis(S, np.array(prods), len(prods), basis, piv)
    return member(basis, piv, nb_, Fv), nb_


if __name__ == '__main__':
    seed, LV = int(sys.argv[1]), int(sys.argv[2]); BEAM = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    NC = int(os.environ.get('NC', '120'))          # candidates sampled per AND
    rng = np.random.default_rng(seed)
    Fv = E.logo_bits()
    S0 = E.init_state()
    prods0 = [np.full(NWORD, ONES)] + [S0[i].copy() for i in range(12)]
    basis = np.zeros((4096, NWORD), dtype=np.uint64); piv = np.zeros(4096, dtype=np.int64)
    d0, r0 = deficiency(S0, prods0, Fv, basis, piv)
    print('[qrank s%d] start deficiency weight %d  rank %d' % (seed, d0, r0), flush=True)
    beam = [(d0, S0.copy(), prods0, [])]
    t0 = time.time()
    for L in range(LV):
        nxt = []
        for (dcur, S, prods, gates) in beam:
            for trial in range(max(1, 8 // BEAM)):
                S2 = S.copy(); pr2 = list(prods); g2 = list(gates); used = set(); cur = dcur
                for slot in range(6):
                    best = None
                    for _ in range(NC):
                        free = [w for w in range(NW) if w not in used]
                        if len(free) < 3: break
                        a, b, t = rng.choice(free, 3, replace=False)
                        pa, pb = int(rng.integers(2)), int(rng.integers(2))
                        p = (S[a] ^ (ONES if pa else np.uint64(0))) & (S[b] ^ (ONES if pb else np.uint64(0)))
                        S3 = S2.copy(); S3[t] = S3[t] ^ p
                        d, _ = deficiency(S3, pr2 + [p], Fv, basis, piv)
                        if best is None or d < best[0]: best = (d, int(a), int(b), pa, pb, int(t), p)
                    if best is None or best[0] >= cur: break
                    d, a, b, pa, pb, t, p = best
                    S2[t] = S2[t] ^ p; pr2.append(p); g2.append((L, a, b, pa, pb, t)); used |= {a, b, t}; cur = d
                    print('   level %d slot %d: deficiency %d  (%.0fs)' % (L + 1, slot + 1, cur, time.time() - t0), flush=True)
                nxt.append((cur, S2, pr2, g2))
        nxt.sort(key=lambda z: z[0]); beam = nxt[:BEAM]
        print('[qrank s%d] level %d  best deficiency %d  beam %s  gates %d  %.0fs' %
              (seed, L + 1, beam[0][0], [z[0] for z in beam], len(beam[0][3]), time.time() - t0), flush=True)
        pickle.dump(dict(gates=beam[0][3], deficiency=beam[0][0]), open('ckpt/qrank_s%d.pkl' % seed, 'wb'))
        if beam[0][0] == 0:
            print('[qrank s%d] EXACT: F in span after %d levels' % (seed, L + 1), flush=True); break
