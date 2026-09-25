"""Mixed phase stage: F' = F xor (GF(2) features: Toffoli products of a prefix,
pairs of final wire values -- Z-around / CZ, free in depth) and the rest by the
arbitrary-angle parity stage over the 18 final wire values.  Greedy: each step
XORs in the feature that most lowers the OMP residual at K = KP (NC sampled
features per step).  Prefix: the best cpty_greedy prefix (INIT) or empty.
Usage: python3 cptz_mixed.py SEED STEPS NC KP [INIT.pkl]
Checkpoint ckpt/wmixed_s<seed>.pkl"""
import sys, time, random, pickle
import numpy as np
import cpte_evo as E
from cptw_mcts import Env, unpack
from cpty_walsh import omp, NW
seed, STEPS, NC, KP = map(int, sys.argv[1:5]); rng = random.Random(seed)
seq = pickle.load(open(sys.argv[5], 'rb'))['seq'] if len(sys.argv) > 5 else []
env = Env(E.logo_bits(), 8); S, prods = env.play(seq)
W = np.array([unpack(S[w]) for w in range(NW)]).astype(np.int64)
idx = (W << np.arange(NW)[:, None]).sum(0)
feats = [unpack(p) for p in prods[13:]] + [(W[a] & W[b]).astype(np.uint8) for a in range(NW) for b in range(a + 1, NW)]
feats = [f for f in feats if f.any() and not f.all()]
F = unpack(E.logo_bits()).astype(np.uint8)
def res(Fc):
    out, _ = omp(idx, Fc.astype(float), KP, marks=(KP,)); return out.get(KP, 0.0)
cur = F.copy(); best = res(cur); used = []; t0 = time.time()
print('[mixed s%d] prefix %d Toffolis, %d features, start residual@%d %.3f' % (seed, sum(x != 'end' for x in seq), len(feats), KP, best), flush=True)
for step in range(STEPS):
    cand = rng.sample(range(len(feats)), min(NC, len(feats)))
    sc = [(res(cur ^ feats[j]), j) for j in cand if j not in used]
    r, j = min(sc)
    if r >= best - 1e-9: print('[mixed s%d] no improving feature at step %d' % (seed, step + 1), flush=True); continue
    cur ^= feats[j]; best = r; used.append(j)
    print('[mixed s%d] step %d: residual@%d %.3f  features used %d  %.0fs' % (seed, step + 1, KP, best, len(used), time.time() - t0), flush=True)
    pickle.dump(dict(seq=seq, used=used, res=best), open('ckpt/wmixed_s%d.pkl' % seed, 'wb'))
out, _ = omp(idx, cur.astype(float), 4096)
print('[mixed s%d] final: residual by K %s' % (seed, {k: ('%.3g' % v if k != 'exact' else v) for k, v in out.items()}), flush=True)
