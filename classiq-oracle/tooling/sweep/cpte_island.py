"""Island search for the forward stream U (same skeleton/fitness as cpte_evo).
NI islands, each a (1+1) neutral-drift climber, run round-robin (CHUNK_S
seconds each turn).  Every MIG seconds: the worst island is replaced by a
level crossover of the best island and itself (never a plain copy), and
islands that are exact duplicates of another are restarted fresh.  An island
without gain for RESTART s restarts fresh.  Global best kept throughout.
Usage: python3 cpte_island.py L SEED MINUTES
Progress: one line / PEVERY s; checkpoint ckpt/isl_L<L>_s<seed>.npz/.json"""
import os, sys, time, json
import numpy as np
import cpte_evo as E

PEVERY = float(os.environ.get('PEVERY', '10'))
NI = int(os.environ.get('NI', '6'))
MIG = float(os.environ.get('MIG', '60'))
RESTART = float(os.environ.get('RESTART', '150'))
CHUNK_S = float(os.environ.get('CHUNK_S', '1.0'))


class Island:
    def __init__(self, L, F, rng, cx=None, tf=None):
        self.L, self.F = L, F
        if cx is None: cx, tf = E.empty(L)
        self.cx, self.tf = cx, tf
        self.st = E.states(cx, tf, L); self.tmp = self.st.copy()
        self.fit = E.fit_k(self.st[-1], F, 2)[0]
        self.t_imp = time.time(); self.chunk = 2000

    def step(self, rng):
        c0 = time.time(); f0 = self.fit
        self.fit, _, n = E.run(self.cx, self.tf, self.L * E.P, self.F, self.st, self.tmp, self.chunk,
                               self.fit, 0.1, int(rng.integers(1 << 30)), 2, E.P)
        dt = time.time() - c0
        if dt > 0: self.chunk = max(200, int(self.chunk * min(4.0, CHUNK_S / dt)))
        if self.fit > f0: self.t_imp = time.time()
        return n


def cross(a, b, L, rng):
    cx, tf = E.empty(L)
    for l in range(L):
        p = a if rng.random() < 0.5 else b
        sl = slice(l * E.P, (l + 1) * E.P)
        cx[sl] = p.cx[sl]; tf[sl] = p.tf[sl]
    return cx, tf


if __name__ == '__main__':
    L, seed, minutes = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
    rng = np.random.default_rng(seed)
    tag = 'isl_L%d_s%d' % (L, seed)
    os.makedirs('ckpt', exist_ok=True)
    F = E.logo_bits()
    isl = [Island(L, F, rng) for _ in range(NI)]
    best = (0, None, None)
    t0 = time.time(); last = t0; last_mig = t0; total = 0; nmig = 0; nrs = 0
    print('[%s] %d islands, migrate every %.0fs, restart after %.0fs' % (tag, NI, MIG, RESTART), flush=True)
    while True:
        for i in range(NI):
            total += isl[i].step(rng)
            if isl[i].fit > best[0]: best = (isl[i].fit, isl[i].cx.copy(), isl[i].tf.copy())
            if time.time() - isl[i].t_imp > RESTART:
                isl[i] = Island(L, F, rng); nrs += 1
        now = time.time()
        if now - last_mig > MIG:
            last_mig = now; nmig += 1
            order = sorted(range(NI), key=lambda i: isl[i].fit)
            w, b = order[0], order[-1]
            cx, tf = cross(isl[b], isl[w], L, rng)
            isl[w] = Island(L, F, rng, cx, tf)
            for i in range(NI):                  # restart exact duplicates
                for j in range(i):
                    if np.array_equal(isl[i].cx, isl[j].cx) and np.array_equal(isl[i].tf, isl[j].tf):
                        isl[i] = Island(L, F, rng); nrs += 1; break
        done = best[0] == 4096 or now - t0 > minutes * 60
        if now - last >= PEVERY or done:
            last = now
            fits = sorted((int(x.fit) for x in isl), reverse=True)
            rec = dict(tag=tag, best=int(best[0]), islands=fits, migrations=nmig, restarts=nrs, iters=total,
                       elapsed_s=round(now - t0), utc=time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now)))
            print('[%s] %s  %5ds  best %4d/4096  islands %s  migr %d  restarts %d  iters %d' %
                  (rec['utc'], tag, rec['elapsed_s'], best[0], fits, nmig, nrs, total), flush=True)
            np.savez('ckpt/%s.npz' % tag, cx=best[1], tf=best[2], F=F, L=L)
            json.dump(rec, open('ckpt/%s.json' % tag, 'w'))
            if done: break
    S = E.states(best[1], best[2], L)[-1]
    print('[%s] final best %d / 4096  readout %s' % (tag, best[0], E.fit_k(S, F, 2)[1:]), flush=True)
