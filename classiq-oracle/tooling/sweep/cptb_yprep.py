"""search a forward-only y prep (9 y wires: y0..y5, D1..D3) that leaves wires
holding  V3 (exact), W3 (exact), W2, W1, W0 (on valid rows), y5 (exact).
score = (#targets met, -ccx levels, -ccx, -len).  usage: iters seed K M"""
from cpri_io import out_path as _out
import sys, random, pickle
from cpta_deg import run
from cpta_setsearch2 import levels, rand_gate

ALL = (1 << 64) - 1
Wt = {}
for y, w in {11:2,12:4,13:6,14:6,15:7,16:7,17:8,18:8,19:8,20:8,21:8,22:7,23:7,24:6,25:6,26:4,27:2,
             35:2,36:4,37:5,38:5,39:6,40:6,41:6,42:6,43:6,44:5,45:5,46:4,47:2}.items():
    Wt[y] = w
valid = sum(1 << y for y in Wt)
def tab(f): return sum(1 << y for y in range(64) if f(y))
W3 = tab(lambda y: Wt.get(y) == 8)
V3 = tab(lambda y: y in Wt and Wt[y] != 8)
TG = [('V3', V3, ALL), ('W3', W3, ALL), ('y5', tab(lambda y: y >> 5 & 1), ALL)] + \
     [('W%d' % b, tab(lambda y, b=b: y in Wt and (Wt[y] >> b) & 1), V3) for b in (2, 1, 0)]   # care: V3 rows only

def met(wires):
    used = set(); n = 0
    # greedy distinct-wire matching (targets in order), either polarity
    for name, t, care in TG:
        for i, w in enumerate(wires):
            if i in used: continue
            if (w ^ t) & care == 0 or (w ^ t ^ ALL) & care == 0:
                used.add(i); n += 1; break
    return n

def score(g, K, M):
    if sum(1 for x in g if x[0] == 'ccx') > K or len(g) > M: return None
    return (met(run(g)), -levels(g), -sum(1 for x in g if x[0] == 'ccx'), -len(g))

def main():
    iters = int(sys.argv[1]); seed = int(sys.argv[2]); K = int(sys.argv[3]); M = int(sys.argv[4])
    rng = random.Random(seed)
    cur = []; cs = score(cur, K, M); best = (cs, [])
    for it in range(iters):
        T = 1.5 * (1 - it / iters) + 0.05
        g = list(cur); m = rng.random()
        if m < 0.35 or not g: g.insert(rng.randrange(len(g) + 1), rand_gate(rng, 0.5))
        elif m < 0.55: g.pop(rng.randrange(len(g)))
        elif m < 0.85: g[rng.randrange(len(g))] = rand_gate(rng, 0.5)
        else:
            i, j = rng.randrange(len(g)), rng.randrange(len(g)); g[i], g[j] = g[j], g[i]
        s = score(g, K, M)
        if s is None: continue
        d = (s[0] - cs[0]) * 4 + 1.0 * (s[1] - cs[1]) + 0.3 * (s[2] - cs[2]) + 0.02 * (s[3] - cs[3])
        if d >= 0 or rng.random() < pow(2.718, d / T):
            cur, cs = g, s
            if s > best[0]: best = (s, list(g))
    print('seed', seed, 'K', K, 'best (met/6, -levels, -ccx, -len)', best[0], flush=True)
    print(best[1], flush=True)
    pickle.dump(best, open(_out('cptb_yprep_K%d_s%d.pkl' % (K, seed)), 'wb'))

if __name__ == '__main__':
    main()
