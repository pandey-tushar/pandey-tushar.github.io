"""Level-l signal test: given the planted prefix (levels < l), score each
candidate product p = (w_a^pa)(w_b^pb) of current wire values by ANF-divisibility
statistics against the target's ANF; label = candidate is a level-l Toffoli of
the planted circuit.  Usage: python3 cptx_signal2.py LV LEVEL NTARGETS"""
import sys, random
import numpy as np, torch
import cpte_evo as E
from cptw_mcts import Env, rand_action
from cptx_signal import unpack, anf, DEG, IDX
def auc(sc, y):
    o = np.argsort(sc); r = np.empty(len(sc)); r[o] = np.arange(len(sc))
    p = y == 1; return (r[p].mean() - (p.sum() - 1) / 2) / (~p).sum()
LV, LEV, NT = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
import os
RES = int(os.environ.get('RES', '0'))
X, Y, G = [], [], []
for s in range(NT):
    prng = random.Random(5000 + s); seq = []
    for l in range(LV):
        used = set()
        for _ in range(6):
            a = rand_action(used, prng)
            if a is None: break
            seq.append(a); used |= {a[0], a[1], a[4]}
        seq.append('end')
    env = Env(E.logo_bits(), LV); S, prods = env.play(seq)
    Fv = np.zeros(64, dtype=np.uint64)
    for p in prods[13:]:
        if prng.random() < 0.5: Fv ^= p
    for _ in range(20):
        a, b = prng.sample(range(18), 2); Fv ^= S[a] & S[b]
    FA = anf(unpack(Fv)); mon = IDX[FA == 1]
    ends = [i for i, x in enumerate(seq) if x == 'end']
    pre = seq[:ends[LEV - 2] + 1] if LEV > 1 else []
    lev = seq[(ends[LEV - 2] + 1 if LEV > 1 else 0):ends[LEV - 1]]
    Sp, pp = env.play(pre)
    if RES:
        from cptq_rank import turn_basis_anf, ORDER
        from cpth_span import moebius
        basis = np.zeros((4096, 64), dtype=np.uint64); piv = np.zeros(4096, dtype=np.int64)
        nb_ = turn_basis_anf(Sp[:0], np.array(pp), len(pp), basis, piv, ORDER)
        r = Fv.copy(); moebius(r)
        for j in range(nb_):
            if (r[piv[j] >> 6] >> np.uint64(piv[j] & 63)) & np.uint64(1): r ^= basis[j]
        mon = IDX[unpack(r) == 1]
    W = [unpack(Sp[w]) for w in range(18)]
    pos = {(min(x[0], x[1]), max(x[0], x[1])) for x in lev}
    for a in range(18):
        for b in range(a + 1, 18):
            if not W[a].any() or not W[b].any(): continue
            best = None
            for pa in range(2):
                for pb in range(2):
                    p = (W[a] ^ pa) & (W[b] ^ pb)
                    if not p.any(): continue
                    PA = anf(p); pm = IDX[PA == 1]; lead = pm[DEG[pm].argmax()]
                    sup = ((mon & lead) == lead).mean()
                    supall = np.mean([((mon & m) == m).mean() for m in pm[np.argsort(-DEG[pm])[:8]]])
                    f = [sup, supall, DEG[lead] / 12, len(pm) / 4096]
                    if best is None or f[0] > best[0]: best = f
            if best is None: continue
            X.append(best); Y.append(1 if (a, b) in pos else 0); G.append(s)
X = np.array(X); Y = np.array(Y); G = np.array(G)
print('level %d: candidates %d positives %d' % (LEV, len(Y), Y.sum()))
for i, n in enumerate(['frac R monomials above lead(p)', 'same, top-8 monomials of p', 'deg lead', 'ANF size p']):
    print('  AUC %-32s %.3f' % (n, auc(X[:, i], Y)))
tr = G < NT * 0.7
Xt = torch.tensor((X - X.mean(0)) / (X.std(0) + 1e-9), dtype=torch.float32); Yt = torch.tensor(Y, dtype=torch.float32)
w = torch.zeros(X.shape[1], requires_grad=True); b0 = torch.zeros(1, requires_grad=True); opt = torch.optim.Adam([w, b0], lr=0.05)
for _ in range(500):
    opt.zero_grad(); l = torch.nn.functional.binary_cross_entropy_with_logits(Xt[tr] @ w + b0, Yt[tr]); l.backward(); opt.step()
print('logistic held-out AUC %.3f' % auc((Xt[~tr] @ w + b0).detach().numpy(), Y[~tr]))
