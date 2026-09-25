"""Signal test for learned guidance: planted L-level targets; for every data
input pair (a,b) compute truth-table statistics; label = pair used as the
controls of a level-1 Toffoli in the planted circuit.  Reports per-feature AUC
and a logistic-regression AUC on held-out targets.
Usage: python3 cptx_signal.py LV NTARGETS"""
import sys, random
import numpy as np, torch
import cpte_evo as E
from cptw_mcts import Env, rand_action

def unpack(v): return ((v[:, None] >> np.arange(64, dtype=np.uint64)) & np.uint64(1)).astype(np.uint8).reshape(-1)
N = 4096; IDX = np.arange(N); DEG = np.array([bin(i).count('1') for i in range(N)])
def anf(t):
    a = t.copy(); h = 1
    while h < N:
        a = a.reshape(-1, 2 * h); a[:, h:] ^= a[:, :h]; a = a.reshape(-1); h *= 2
    return a
def walsh(t):
    w = (1 - 2 * t.astype(np.int64)); h = 1
    while h < N:
        w = w.reshape(-1, 2 * h); x = w[:, :h].copy(); y = w[:, h:].copy(); w[:, :h] = x + y; w[:, h:] = x - y; w = w.reshape(-1); h *= 2
    return w
def feats(F):
    A = anf(F); mon = IDX[A == 1]; W = np.abs(walsh(F)).astype(float)
    out = {}
    for a in range(12):
        for b in range(a + 1, 12):
            m = 1 << a | 1 << b
            has = (mon & m) == m
            d2 = F ^ F[IDX ^ (1 << a)] ^ F[IDX ^ (1 << b)] ^ F[IDX ^ m]
            sel = (IDX & m) == m
            out[(a, b)] = [has.sum() / max(1, len(mon)), (DEG[mon][has].mean() if has.any() else 0) / 12,
                           d2.mean(), anf(d2).sum() / 4096, W[sel].mean() / 64, W[(IDX & m) == 0].mean() / 64]
    return out
if __name__ == '__main__':
    LV, NT = int(sys.argv[1]), int(sys.argv[2])
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
        F = unpack(Fv)
        lvl1 = seq[:seq.index('end')]
        pos = {tuple(sorted((x[0], x[1]))) for x in lvl1 if x[0] < 12 and x[1] < 12}
        for pr, f in feats(F).items():
            X.append(f); Y.append(1 if pr in pos else 0); G.append(s)
    X = np.array(X); Y = np.array(Y); G = np.array(G)
    def auc(sc, y):
        o = np.argsort(sc); r = np.empty(len(sc)); r[o] = np.arange(len(sc))
        p = y == 1; return (r[p].mean() - (p.sum() - 1) / 2) / (~p).sum()
    names = ['frac monomials with a,b', 'mean degree of those', 'weight D_aD_bF', 'ANF size D_aD_bF', 'mean |W| S>=ab', 'mean |W| S&ab=0']
    print('pairs %d  positives %d' % (len(Y), Y.sum()))
    for i, n in enumerate(names): print('  AUC %-26s %.3f' % (n, auc(X[:, i], Y)))
    tr = G < NT * 0.7
    Xt = torch.tensor((X - X.mean(0)) / (X.std(0) + 1e-9), dtype=torch.float32); Yt = torch.tensor(Y, dtype=torch.float32)
    w = torch.zeros(X.shape[1], requires_grad=True); b0 = torch.zeros(1, requires_grad=True)
    opt = torch.optim.Adam([w, b0], lr=0.05)
    for _ in range(500):
        opt.zero_grad(); l = torch.nn.functional.binary_cross_entropy_with_logits(Xt[tr] @ w + b0, Yt[tr]); l.backward(); opt.step()
    sc = (Xt[~tr] @ w + b0).detach().numpy()
    print('logistic regression held-out AUC %.3f  (0.5 = no signal)' % auc(sc, Y[~tr]))
    