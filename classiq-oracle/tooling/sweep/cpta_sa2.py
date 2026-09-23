"""SA over readout rounds after fixed setups, scored by the tensor rule.
score = (residual rank, -(dims of Vx in x-vocab + dims of Vy in y-vocab))
usage: xsetup.pkl ysetup.pkl R iters seed [G] [L]"""
from cpri_io import out_path as _out
import sys, random, pickle, time
from cpta_tensor import vocab, tens, Span, F, rank64, ALL
from cpta_deg import run, Wspan
from cpri_round import logo_pairs, NW
from cpta_sa import mutate

U = [u for u, v in logo_pairs()]; V = [v for u, v in logo_pairs()]
dU = len(Wspan(U)); dV = len(Wspan(V))

def evaluate(s, xi, yi):
    S = Span(); SX = Span(); SY = Span()
    for name, xa, yb in vocab(s, xi, yi):
        for a in xa: SX.add(a)
        for b in yb: SY.add(b)
        for a in set(xa):
            for b in set(yb):
                if a and b: S.add(tens(a, b))
    rk = rank64(S.reduce(F))
    cx = dU - sum(SX.add(u) for u in U); cy = dV - sum(SY.add(v) for v in V)
    return rk, -(cx + cy)

def main():
    xs = pickle.load(open(sys.argv[1], 'rb'))[1]; ys = pickle.load(open(sys.argv[2], 'rb'))[1]
    R = int(sys.argv[3]); iters = int(sys.argv[4]); seed = int(sys.argv[5])
    G = int(sys.argv[6]) if len(sys.argv) > 6 else 3; L = int(sys.argv[7]) if len(sys.argv) > 7 else 2
    xi = run(xs); yi = run(ys)
    rng = random.Random(seed)
    s = {'x': [[] for _ in range(R)], 'y': [[] for _ in range(R)], 'xlin': [[] for _ in range(R)], 'ylin': [[] for _ in range(R)]}
    cur = evaluate(s, xi, yi); best = (cur, s); t0 = time.time()
    print('start', cur, flush=True)
    for it in range(iters):
        T = 2.0 * (1 - it / iters) + 0.03
        s2 = mutate(s, rng, G, L)
        if s2 is None: continue
        sc = evaluate(s2, xi, yi)
        d = (cur[0] - sc[0]) * 3 + (cur[1] - sc[1]) * 1.0
        if d >= 0 or rng.random() < pow(2.718, d / T):
            s, cur = s2, sc
            if sc < best[0]:
                best = (sc, s2)
                if sc[0] == 0: print('FEASIBLE it', it, flush=True); break
        if it % 5000 == 0: print('it %d cur %s best %s %.0fs' % (it, cur, best[0], time.time() - t0), flush=True)
    print('BEST', best[0], flush=True)
    pickle.dump((best, xs, ys), open(_out('cpta_sa2_R%d_s%d.pkl' % (R, seed)), 'wb'))

if __name__ == '__main__':
    main()
