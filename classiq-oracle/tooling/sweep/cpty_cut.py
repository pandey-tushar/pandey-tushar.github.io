"""Cut a whole-F XAG low: keep a dependency-closed set of 6 AND nodes on the 6
ancillas (data wires keep x), synthesize the rest in the arbitrary-angle phase
stage.  Score = OMP residual norm at K = KP parity terms over the 18 values
(x, n_1..n_6).  Random dependency-closed sets from several XAGs; best sets get a
full OMP.  Usage: python3 cpty_cut.py SEED MINUTES KP XAG.v [XAG.v ...]"""
import sys, time, random, pickle
import numpy as np
from cptr_map import parse
from cpty_walsh import omp
import cpte_evo as E
from cptw_mcts import unpack
F = unpack(E.logo_bits()).astype(float)
IDX = np.arange(4096)
def signals(ands):
    sig = {0: np.ones(4096, np.uint8)}
    for i in range(12): sig[1 + i] = ((IDX >> i) & 1).astype(np.uint8)
    def ev(L):
        v = np.zeros(4096, np.uint8); b = 0
        while L:
            if L & 1: v ^= sig[b]
            L >>= 1; b += 1
        return v
    vals = []
    for k, (bit, A, B) in enumerate(ands):
        v = ev(A) & ev(B); sig[13 + k] = v; vals.append(v)
    return vals
def deps(ands, k):
    m = (ands[k][1] | ands[k][2]) >> 13
    return [j for j in range(len(ands)) if m >> j & 1]
seed, minutes, KP = int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]); rng = random.Random(seed)
X = []
for p in sys.argv[4:]:
    ands, Fo = parse(p); X.append((p, ands, signals(ands)))
best = None; t0 = time.time(); last = t0; n = 0
while time.time() - t0 < minutes * 60:
    p, ands, vals = rng.choice(X)
    chosen = []
    while len(chosen) < 6:
        ready = [k for k in range(len(ands)) if k not in chosen and all(j in chosen for j in deps(ands, k))]
        if not ready: break
        chosen.append(rng.choice(ready))
    idx = IDX.copy()
    for i, k in enumerate(chosen): idx = idx | (vals[k].astype(np.int64) << (12 + i))
    out, _ = omp(idx, F, KP, marks=(KP,)); r = out.get(KP, 0.0); n += 1
    if best is None or r < best[0]:
        best = (r, p, chosen); pickle.dump(dict(xag=p, chosen=chosen, res=r), open('ckpt/wcut_s%d.pkl' % seed, 'wb'))
        print('   new best residual@%d %.3f  %s ANDs %s' % (KP, r, p, chosen), flush=True)
    if time.time() - last > 10:
        last = time.time(); print('[cut s%d] %4.0fs tried %d best %.3f' % (seed, last - t0, n, best[0]), flush=True)
r, p, chosen = best
ands, _ = parse(p); vals = signals(ands); idx = IDX.copy()
for i, k in enumerate(chosen): idx = idx | (vals[k].astype(np.int64) << (12 + i))
out, _ = omp(idx, F, 4096)
print('[cut s%d] final best %s %s: residual by K %s' % (seed, p, chosen, {k: ('%.3g' % v if k != 'exact' else v) for k, v in out.items()}), flush=True)
