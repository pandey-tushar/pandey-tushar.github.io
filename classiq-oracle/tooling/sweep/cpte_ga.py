"""Population search (memetic GA) for the forward stream U, same skeleton and
fitness as cpte_evo (FITK=2: 1-2 wire readout, FITK=3: any function of 3
wires).  Steady state: pick 2 parents (tournament of 3), child = each level
(CX layer + Toffoli layer together) taken from one parent, then a short (1+1)
local climb (LOCAL steps); child replaces the worst member if it is better
and not a duplicate.  IMM: fraction of children that are fresh random climbs.
Usage: FITK=2 python3 cpte_ga.py L SEED MINUTES
Progress: one line / PEVERY s; checkpoint ckpt/ga_L<L>_s<seed>_k<K>.npz/.json"""
import os, sys, time, json
import numpy as np
import cpte_evo as E

PEVERY = float(os.environ.get('PEVERY', '10'))
POP = int(os.environ.get('POP', '24'))
TOUR = 3
IMM = float(os.environ.get('IMM', '0.1'))


def climb(cx, tf, L, F, K, steps, rng):
    st = E.states(cx, tf, L); tmp = st.copy()
    f0 = E.fit_k(st[-1], F, K)[0]
    f, _, _ = E.run(cx, tf, L * E.P, F, st, tmp, steps, f0, 0.1, int(rng.integers(1 << 30)), K, E.P)
    return f


empty = E.empty


if __name__ == '__main__':
    L, seed, minutes = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
    K = int(os.environ.get('FITK', '2'))
    LOCAL = int(os.environ.get('LOCAL', '4000' if K == 2 else '400'))
    rng = np.random.default_rng(seed)
    tag = 'ga_L%d_s%d_k%d' % (L, seed, K)
    os.makedirs('ckpt', exist_ok=True)
    F = E.logo_bits()
    t0 = time.time()
    pop = []
    for i in range(POP):                       # initial population: fresh climbs
        cx, tf = empty(L)
        f = climb(cx, tf, L, F, K, LOCAL * 5, rng)
        pop.append([f, cx, tf])
    print('[%s] init pop %d  fits %s  %.0fs  (LOCAL %d)' % (tag, POP, sorted(p[0] for p in pop)[::-1][:8],
                                                         time.time() - t0, LOCAL), flush=True)
    last = t0; nchild = 0; nrepl = 0
    while True:
        if rng.random() < IMM:
            cx, tf = empty(L)
            f = climb(cx, tf, L, F, K, LOCAL * 5, rng)
        else:
            par = []
            for _ in range(2):
                cand = rng.choice(len(pop), TOUR, replace=False)
                par.append(pop[max(cand, key=lambda i: pop[i][0])])
            cx, tf = empty(L)
            for l in range(L):
                p = par[rng.integers(2)]
                sl = slice(l * E.P, (l + 1) * E.P)
                cx[sl] = p[1][sl]; tf[sl] = p[2][sl]
            f = climb(cx, tf, L, F, K, LOCAL, rng)
        nchild += 1
        worst = min(range(POP), key=lambda i: pop[i][0])
        dup = any(f == p[0] and np.array_equal(cx, p[1]) and np.array_equal(tf, p[2]) for p in pop)
        if f > pop[worst][0] and not dup:
            pop[worst] = [f, cx, tf]; nrepl += 1
        best = max(pop, key=lambda p: p[0])
        now = time.time()
        done = best[0] == 4096 or now - t0 > minutes * 60
        if now - last >= PEVERY or done:
            last = now
            fits = sorted((p[0] for p in pop), reverse=True)
            rec = dict(tag=tag, best=int(best[0]), median=int(fits[POP // 2]), worst=int(fits[-1]),
                       children=nchild, replaced=nrepl, elapsed_s=round(now - t0),
                       utc=time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now)))
            print('[%s] %s  %5ds  best %4d/4096  median %4d  worst %4d  children %d  replaced %d' %
                  (rec['utc'], tag, rec['elapsed_s'], best[0], rec['median'], rec['worst'], nchild, nrepl), flush=True)
            np.savez('ckpt/%s.npz' % tag, cx=best[1], tf=best[2], F=F, L=L, K=K)
            json.dump(rec, open('ckpt/%s.json' % tag, 'w'))
            if done: break
    S = E.states(best[1], best[2], L)[-1]
    print('[%s] final best %d / 4096  readout %s' % (tag, best[0], E.fit_k(S, F, K)[1:]), flush=True)
