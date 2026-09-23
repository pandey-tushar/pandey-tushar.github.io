"""SA over in-place setup gate lists (9 wires: 6 data + 3 ancilla) maximising
how much of the side's function space V is degree <= 2 (then <= 3) in the
wire values after the setup.  usage: side iters seed maxccx"""
import sys, random
from cpta_deg import run, inside, Wspan
from cpri_round import logo_pairs

def rand_gate(rng):
    m = rng.random()
    if m < 0.45:
        a, b = rng.sample(range(9), 2); return ('cx', a, b)
    if m < 0.55:
        return ('x', rng.randrange(9))
    a, b, t = rng.sample(range(9), 3); return ('ccx', a, b, t)

def score(W, g, maxccx):
    n = sum(1 for x in g if x[0] == 'ccx')
    if n > maxccx: return (-1, -1, 0)
    st = run(g)
    return (inside(W, st, 2), inside(W, st, 3), -len(g))

def main():
    side = sys.argv[1]; iters = int(sys.argv[2]); seed = int(sys.argv[3]); maxccx = int(sys.argv[4])
    rng = random.Random(seed)
    W = [u for u, v in logo_pairs()] if side == 'x' else [v for u, v in logo_pairs()]
    cur = []; cs = score(W, cur, maxccx); best = (cs, list(cur))
    T = 1.0
    for it in range(iters):
        g = list(cur); m = rng.random()
        if m < 0.4 or not g: g.insert(rng.randrange(len(g) + 1), rand_gate(rng))
        elif m < 0.6: g.pop(rng.randrange(len(g)))
        elif m < 0.85: g[rng.randrange(len(g))] = rand_gate(rng)
        else:
            i, j = rng.randrange(len(g)), rng.randrange(len(g)); g[i], g[j] = g[j], g[i]
        s = score(W, g, maxccx)
        d = (s[0] - cs[0]) * 10 + (s[1] - cs[1]) + 0.01 * (s[2] - cs[2])
        if d >= 0 or rng.random() < pow(2.718, d / T):
            cur, cs = g, s
            if s > best[0]:
                best = (s, list(g))
        T = max(0.05, 1.0 * (1 - it / iters))
    print(side, 'seed', seed, 'maxccx', maxccx, 'score(deg2,deg3,-len)', best[0], 'dimV', len(Wspan(W)))
    print(best[1], flush=True)

if __name__ == '__main__':
    main()
