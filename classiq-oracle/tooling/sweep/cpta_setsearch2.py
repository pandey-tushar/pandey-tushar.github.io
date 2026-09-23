"""SA over compact setups: <= K ccx, <= M total gates on 9 wires.
score = (dims of V at deg<=2, dims at deg<=3, -ccx levels, -len).
usage: side iters seed K M"""
from cpri_io import out_path as _out
import sys, random, pickle
from cpta_deg import run, inside, Wspan
from cpri_round import logo_pairs

def levels(g):
    lv = [0] * 9; top = 0
    for x in g:
        if x[0] == 'ccx':
            l = max(lv[x[1]], lv[x[2]], lv[x[3]]) + 1
            for q in x[1:]: lv[q] = l
            top = max(top, l)
        elif x[0] == 'cx':
            l = max(lv[x[1]], lv[x[2]])
            lv[x[1]] = lv[x[2]] = l
    return top

def rand_gate(rng, pcx):
    m = rng.random()
    if m < pcx:
        a, b = rng.sample(range(9), 2); return ('cx', a, b)
    if m < pcx + 0.08: return ('x', rng.randrange(9))
    a, b, t = rng.sample(range(9), 3); return ('ccx', a, b, t)

def score(W, g, K, M):
    n = sum(1 for x in g if x[0] == 'ccx')
    if n > K or len(g) > M: return None
    st = run(g)
    return (inside(W, st, 2), inside(W, st, 3), -levels(g), -len(g))

def main():
    side = sys.argv[1]; iters = int(sys.argv[2]); seed = int(sys.argv[3])
    K = int(sys.argv[4]); M = int(sys.argv[5])
    rng = random.Random(seed)
    W = [u for u, v in logo_pairs()] if side == 'x' else [v for u, v in logo_pairs()]
    cur = []; cs = score(W, cur, K, M); best = (cs, [])
    for it in range(iters):
        T = 1.5 * (1 - it / iters) + 0.05
        g = list(cur); m = rng.random()
        if m < 0.35 or not g: g.insert(rng.randrange(len(g) + 1), rand_gate(rng, 0.5))
        elif m < 0.55: g.pop(rng.randrange(len(g)))
        elif m < 0.85: g[rng.randrange(len(g))] = rand_gate(rng, 0.5)
        else:
            i, j = rng.randrange(len(g)), rng.randrange(len(g)); g[i], g[j] = g[j], g[i]
        s = score(W, g, K, M)
        if s is None: continue
        d = (s[0] - cs[0]) * 4 + (s[1] - cs[1]) + 0.5 * (s[2] - cs[2]) + 0.02 * (s[3] - cs[3])
        if d >= 0 or rng.random() < pow(2.718, d / T):
            cur, cs = g, s
            if s > best[0]: best = (s, list(g))
    print(side, 'seed', seed, 'K', K, 'M', M, 'best (deg2, deg3, -levels, -len)', best[0], 'dimV', len(Wspan(W)), flush=True)
    print(best[1], flush=True)
    pickle.dump(best, open(_out('cpta_set_%s_K%d_s%d.pkl' % (side, K, seed)), 'wb'))

if __name__ == '__main__':
    main()
