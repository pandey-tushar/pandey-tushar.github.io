"""search short in-place y setups (<= K RCCX on 9 wires) after which each
y target is affine in the wires, or affine + ONE product of two wires, on its
care set.  score = (#targets affine, #targets 1-product, -levels, -len).
usage: iters seed K"""
import sys, random, pickle, itertools
from cpta_deg import run
from cpta_setsearch2 import levels, rand_gate
from cptb_yprep import TG, ALL
from cpri_io import out_path

TGS = [t for t in TG if t[0] != 'y5']

def in_span(vecs, t, care):
    rows = []
    for v in vecs:
        v &= care
        for r in rows:
            if v >> (r.bit_length() - 1) & 1: v ^= r
        if v: rows.append(v); rows.sort(reverse=True)
    t &= care
    for r in rows:
        if t >> (r.bit_length() - 1) & 1: t ^= r
    return t == 0

def classify(wires):
    base = [ALL] + [w for w in wires if w not in (0, ALL)]
    prods = [wires[i] & wires[j] for i, j in itertools.combinations(range(9), 2)]
    a = b = 0
    for name, t, care in TGS:
        if in_span(base, t, care): a += 1
        elif any(in_span(base + [p], t, care) for p in prods): b += 1
    return a, b

def score(g, K):
    if sum(1 for x in g if x[0] == 'ccx') > K or len(g) > 30: return None
    a, b = classify(run(g))
    return (a + b, a, -levels(g), -len(g))

def main():
    iters, seed, K = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    rng = random.Random(seed)
    cur = []; cs = score(cur, K); best = (cs, [])
    for it in range(iters):
        T = 1.2 * (1 - it / iters) + 0.05
        g = list(cur); m = rng.random()
        if m < 0.35 or not g: g.insert(rng.randrange(len(g) + 1), rand_gate(rng, 0.5))
        elif m < 0.55: g.pop(rng.randrange(len(g)))
        elif m < 0.85: g[rng.randrange(len(g))] = rand_gate(rng, 0.5)
        else:
            i, j = rng.randrange(len(g)), rng.randrange(len(g)); g[i], g[j] = g[j], g[i]
        s = score(g, K)
        if s is None: continue
        d = (s[0] - cs[0]) * 3 + (s[1] - cs[1]) + 0.5 * (s[2] - cs[2]) + 0.02 * (s[3] - cs[3])
        if d >= 0 or rng.random() < pow(2.718, d / T):
            cur, cs = g, s
            if s > best[0]: best = (s, list(g))
    print('seed', seed, 'K', K, 'best (reachable/5, affine, -levels, -len)', best[0], flush=True)
    print(best[1], flush=True)
    pickle.dump(best, open(out_path('cptb_setup1_K%d_s%d.pkl' % (K, seed)), 'wb'))

if __name__ == '__main__':
    main()
