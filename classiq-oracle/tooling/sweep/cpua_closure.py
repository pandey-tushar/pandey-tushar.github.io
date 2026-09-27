"""Closure diagnostic: for a sa2/sa3 checkpoint, deficiency of F against the span of
{Toffoli products, final wires, all monomials of degree <= d in the final wires}, d = 2,3,4.
Also the span rank.  Usage: python3 closure.py ckpt.pkl LV"""
import sys, pickle, itertools, time
import numpy as np
import cpte_evo as E
from cptw_mcts import Env
from cptn_prefix import insert, member
pk, LV = sys.argv[1], int(sys.argv[2])
d = pickle.load(open(pk, 'rb')); lv = d['levels']
lv = [list(l) for l in lv[:LV]] + [[] for _ in range(LV - len(lv))]
env = Env(E.logo_bits(), LV)
seq = []
for l in lv: seq += l + ['end']
S, prods = env.play(seq)
ntof = sum(len(l) for l in lv)
for deg in (2, 3, 4):
    basis = np.zeros((4096, 64), dtype=np.uint64); piv = np.zeros(4096, dtype=np.int64); nb = 0
    t0 = time.time()
    for p in prods: nb = insert(basis, piv, nb, p)
    for w in range(18): nb = insert(basis, piv, nb, S[w])
    for k in range(2, deg + 1):
        for c in itertools.combinations(range(18), k):
            v = S[c[0]].copy()
            for w in c[1:]: v = v & S[w]
            nb = insert(basis, piv, nb, v)
    print(f"{pk} tof {ntof} deg<={deg}: rank {nb} deficiency {int(member(basis, piv, nb, env.Fv))} ({time.time()-t0:.0f}s)", flush=True)
