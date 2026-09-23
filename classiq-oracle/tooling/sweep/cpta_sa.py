"""SA over joint round schedules (x and y, R rounds, <=G RCCX and <=L CX per
side per round), scored by the tensor-span readout rule.
score = (residual rank, -dim(S cap Vx(x)Vy))   lower is better; 0 rank = feasible.
usage: cpta_sa.py R iters seed [G] [L]"""
from cpri_io import out_path as _out
import sys, random, pickle, time
from cpta_tensor import vocab, tens, Span, F, rank64, ALL
from cpri_round import logo_pairs, NW

U = [u for u, v in logo_pairs()]; V = [v for u, v in logo_pairs()]
VV = Span()
for u in U:
    for v in V:
        VV.add(tens(u, v))
VVb = list(VV.b.values())


def evaluate(s):
    S = Span()
    for name, xa, yb in vocab(s):
        for a in set(xa):
            for b in set(yb):
                if a and b:
                    S.add(tens(a, b))
    res = S.reduce(F)
    rk = rank64(res)
    # graded: how much of Vx(x)Vy is inside S
    n0 = len(S.b); inside = sum(1 for w in VVb if not S.reduce(w))
    return rk, -inside


def rand_gate(rng, used):
    for _ in range(20):
        a, b, t = rng.sample(range(NW), 3)
        if t in used['t'] or t in used['c'] or a in used['t'] or b in used['t']:
            continue
        return (min(a, b), rng.random() < .5, max(a, b), rng.random() < .5, t)
    return None


def valid_row(row):
    ts = [g[4] for g in row]
    if len(set(ts)) != len(ts): return False
    cs = set(c for g in row for c in (g[0], g[2]))
    return not (cs & set(ts))


def mutate(s, rng, G, L):
    s = {k: [list(r) for r in v] for k, v in s.items()}
    side = rng.choice('xy'); R = len(s[side]); r = rng.randrange(R)
    row = s[side][r]; lin = s[side + 'lin'][r]
    m = rng.random()
    if m < 0.55:
        used = {'t': set(g[4] for g in row), 'c': set(c for g in row for c in (g[0], g[2]))}
        if row and (len(row) >= G or rng.random() < 0.5):
            i = rng.randrange(len(row)); old = row.pop(i)
            used = {'t': set(g[4] for g in row), 'c': set(c for g in row for c in (g[0], g[2]))}
        g = rand_gate(rng, used)
        if g and len(row) < G: row.append(g)
    elif m < 0.7 and row:
        i = rng.randrange(len(row)); a, pa, b, pb, t = row[i]
        if rng.random() < .5: pa = not pa
        else: pb = not pb
        row[i] = (a, pa, b, pb, t)
    elif m < 0.85 and L:
        if lin and (len(lin) >= L or rng.random() < 0.5):
            lin.pop(rng.randrange(len(lin)))
        else:
            a, b = rng.sample(range(NW), 2); lin.append((a, b))
    else:
        r2 = rng.randrange(R)
        s[side][r], s[side][r2] = s[side][r2], s[side][r]
        s[side + 'lin'][r], s[side + 'lin'][r2] = s[side + 'lin'][r2], s[side + 'lin'][r]
    if not valid_row(s[side][r]): return None
    return s


def main():
    R = int(sys.argv[1]); iters = int(sys.argv[2]); seed = int(sys.argv[3])
    G = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    L = int(sys.argv[5]) if len(sys.argv) > 5 else 2
    rng = random.Random(seed)
    s = {'x': [[] for _ in range(R)], 'y': [[] for _ in range(R)],
         'xlin': [[] for _ in range(R)], 'ylin': [[] for _ in range(R)]}
    cur = evaluate(s); best = (cur, s); t0 = time.time()
    T0 = 2.0
    for it in range(iters):
        T = T0 * (1 - it / iters) + 0.02
        s2 = mutate(s, rng, G, L)
        if s2 is None: continue
        sc = evaluate(s2)
        d = (cur[0] - sc[0]) * 3 + (cur[1] - sc[1]) * 0.2
        if d >= 0 or rng.random() < pow(2.718, d / T):
            s, cur = s2, sc
            if sc < best[0]:
                best = (sc, s2)
                if sc[0] == 0:
                    print('FEASIBLE at it', it, flush=True)
                    break
        if it % 5000 == 0:
            print('it %d cur %s best %s  %.0fs' % (it, cur, best[0], time.time() - t0), flush=True)
    print('BEST', best[0])
    pickle.dump(best[1], open(_out('cpta_sa_R%d_s%d.pkl' % (R, seed)), 'wb'))


if __name__ == '__main__':
    main()
