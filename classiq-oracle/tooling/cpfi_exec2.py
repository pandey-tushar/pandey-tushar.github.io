"""CP-FI: plan executor v2 -- plans as partial orders, per-episode ancilla
quotas, banker's rule against ancilla deadlock.

deps of a move (derived from the plan sequence):
  ('c', k): latest earlier move on k, latest earlier ('c', p) for preds p
  ('u', k): latest earlier ('c', k), latest ('c', p) for preds p, and every
            earlier move that read k since that compute (successor moves,
            phase moves)
  ('p', j): latest ('c', k) for the pair's nodes
A move is ready when its deps are done; the executor fires, across all
episodes, the ready move with the earliest start (rigid profiles).
"""
import sys, random, time, pickle
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfi_joint as J
import cpfi_plan as P
import cpfi_exec as E1
from cpfi_exec import finish, model_depth, ops_to_qc
from collections import Counter

N, preds, succ = J.N, J.preds, J.succ
NW = 18


def deps_of(plan, ep):
    pairs = P.phase_pairs(ep)
    last_c = {}; last_any = {}; readers = {}
    deps = []
    for j, (a, k) in enumerate(plan):
        d = set()
        if a == 'c':
            if k in last_any: d.add(last_any[k])
            for p in preds[k]:
                d.add(last_c[p]); readers.setdefault(p, []).append(j)
            last_c[k] = j; last_any[k] = j; readers[k] = []
        elif a == 'u':
            d.add(last_c[k])
            for p in preds[k]:
                d.add(last_c[p]); readers.setdefault(p, []).append(j)
            d.update(readers.get(k, []))
            last_any[k] = j
        else:
            for kind, v in pairs[k]:
                if kind == 'n':
                    d.add(last_c[v]); readers.setdefault(v, []).append(j)
        if a == 'c':
            d.update(i for i in range(j) if plan[i][0] == 'u')      # keep the plan's register discipline
        deps.append(sorted(d))
    return deps


class Exec2(J.Sched):
    def __init__(self, eps, plans, quota, rng, data_pref=True, jitter=0.0, lazy=True, prio=None):
        super().__init__(eps, rng, anc_pref=not data_pref, jitter=jitter)
        self.lazy = lazy; self.plans = plans; self.quota = quota
        self.deps = [deps_of(pl, ep) for pl, ep in zip(plans, eps)]
        self.done = [set() for _ in plans]
        self.hostable = [P.hostable(ep) for ep in eps]
        self.data_pref = data_pref
        self.prio = prio if prio is not None else list(range(len(eps)))
        self.blocked = set()
        self.rem = [sum(13 if len(N[m[1]]) == 3 else 7 for m in pl if m[0] != 'p') for pl in plans]

    def held(self, e):
        return sum(1 for k, w in self.host.items() if w >= 12 and self.nodes_of[k] == e)

    def admitted(self, e):
        """admission control: episodes are admitted in priority order while the
        sum of quotas of unfinished admitted episodes stays within 6."""
        tot = 0
        for b in self.prio:
            if len(self.done[b]) >= len(self.plans[b]): continue
            if tot + self.quota[b] <= 6:
                if b == e: return True
                tot += self.quota[b]
            elif b == e:
                return False
        return False

    def temporal_safe(self, e, i, k, w):
        """sequential execution: no move between plan index i and k's next
        uncompute reads x_w without n_k."""
        pl = self.plans[e]; nb = 1 << (12 + k)
        for j in range(i + 1, len(pl)):
            a, m = pl[j]
            if a == 'u' and m == k: return True
            if a == 'p': continue
            for f in N[m]:
                if (f >> w) & 1 and not (f & nb):
                    return False
        return True

    def ready(self, e):
        j = len(self.done[e])
        return [j] if j < len(self.plans[e]) else []

    def try_move(self, e, j, dry):
        a, k = self.plans[e][j]
        if a == 'p':
            return 0.0
        if a == 'u':
            return self.fire(k, uncompute=True, dry=dry)
        cands = [w for w in self.hostable[e].get(k, [])
                 if self.cont[w] == J.RAW[w] and self.temporal_safe(e, j, k, w)]
        anc = []
        if self.admitted(e) and (self.held(e) < self.quota[e] or (not cands and self.hostable[e].get(k))):
            anc = [w for w in range(12, NW) if self.cont[w] == 0]        # soft quota for hostable nodes
        order = (cands + anc) if self.data_pref else (anc + cands)
        if self.jitter and len(order) > 1:
            self.rng.shuffle(order)
        best = None
        for w in order:
            t = self.fire(k, dry=True, tgt=w)
            if t is None: continue
            if best is None or t < best[0]:
                best = (t, w)
            if not self.jitter: break
        if best is None:
            if not cands and not anc: self.blocked.add(e)
            return None
        if dry: return best[0]
        self.blocked.discard(e)
        return self.fire(k, tgt=best[1])

    def run(self):
        total = sum(len(p) for p in self.plans)
        ndone = 0
        while ndone < total:
            opts = []
            for e in range(len(self.eps)):
                for j in self.ready(e):
                    t = self.try_move(e, j, dry=True)
                    if t is None: continue
                    opts.append((t + self.rng.random() * self.jitter, -self.rem[e], e, j))
            if not opts:
                if self.verbose:
                    print('    DEADLOCK done %s host %s' % ([len(d) for d in self.done], self.host))
                return False
            opts.sort()
            _, _, e, j = opts[0]
            r = self.try_move(e, j, dry=False)
            if r is None: return False
            a, k = self.plans[e][j]
            if a != 'p': self.rem[e] -= 13 if len(N[k]) == 3 else 7
            self.done[e].add(j); ndone += 1
        self.restore()
        return True


def attempt(eps, plans, quota, seed, data_pref=True, jitter=0.0, verbose=False, prio=None):
    rng = random.Random(seed)
    x = Exec2(eps, plans, quota, rng, data_pref=data_pref, jitter=jitter, prio=prio)
    x.verbose = verbose
    if not x.run():
        return None
    ops = x.oplist()
    new, mism, dirty = finish(ops, eps, verbose)
    if new is None or mism or dirty:
        return ('BAD', mism, dirty)
    return (model_depth(new), new)


if __name__ == '__main__':
    eps_all = J.episodes()
    sel = sys.argv[1] if len(sys.argv) > 1 else '0123'
    A = [int(a) for a in (sys.argv[2] if len(sys.argv) > 2 else '6,6,6,6').split(',')]       # plan budgets
    Q = [int(a) for a in (sys.argv[3] if len(sys.argv) > 3 else sys.argv[2] if len(sys.argv) > 2 else '6,6,6,6').split(',')]  # runtime quotas
    iters = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    jitter = float(sys.argv[5]) if len(sys.argv) > 5 else 2.0
    eps = [eps_all[int(c)] for c in sel]
    plans = []
    for c, ep in zip(sel, eps):
        fn = 'cpfi_plan_%s_A%d.pkl' % (c, A[int(c)])
        plans.append(pickle.load(open(fn, 'rb')))
        print('episode %s plan A=%d: %s' % (c, A[int(c)], dict(Counter(m[0] for m in plans[-1]))))
    quota = [Q[int(c)] for c in sel]
    best = None; fails = bad = 0
    t0 = time.time()
    for seed in range(iters):
        for dp in (True, False):
            for prio in ([i for i in range(len(eps))], [i for i in reversed(range(len(eps)))]):
                r = attempt(eps, plans, quota, seed, data_pref=dp, jitter=jitter if seed else 0.0, verbose=(seed == 0), prio=prio)
                if r is None: fails += 1; continue
                if r[0] == 'BAD': bad += 1; print('  seed %d dp %s BAD mism %s dirty %s' % (seed, dp, r[1], r[2])); continue
                d, ops = r
                if best is None or d < best[0]:
                    best = (d, ops, seed, dp)
                    print('  seed %d dp %s prio %s model depth %d ops %d (%.0fs)' % (seed, dp, prio, d, len(ops), time.time() - t0), flush=True)
    print('episodes %s: fails %d bad %d' % (sel, fails, bad))
    if best:
        d, ops, seed, dp = best
        print('best model depth %d  ops %s' % (d, dict(Counter(o[0] for o in ops))))
        pickle.dump(ops, open('cpfi_exec2_%s.pkl' % sel, 'wb'))
        from cpae_core import extract, sim_exact, fvec, SHAPES
        from qiskit import transpile
        qc = ops_to_qc(ops, n=18)
        tq = transpile(qc, basis_gates=['u3', 'cx'], optimization_level=2, seed_transpiler=0)
        print('opt2 depth %d cx %d' % (tq.depth(), tq.count_ops().get('cx', 0)))
        if len(sel) == 4:
            gl, gp = extract(qc)
            err, mm = sim_exact(gl, gp, fvec(SHAPES['LOGO']))
            print('sim_exact err %.1e mism %d' % (err, mm))
