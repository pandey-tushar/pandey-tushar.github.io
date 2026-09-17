"""term-level episodes through the mode-aware planner + Exec3 (terms 0,1,2; term 3 is too big for exact planning)."""
import sys, time, random, pickle
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfi_joint as J, cpfi_pairs as Q
from collections import Counter
sel = sys.argv[1] if len(sys.argv) > 1 else '012'
A0 = int(sys.argv[2]) if len(sys.argv) > 2 else 2
iters = int(sys.argv[3]) if len(sys.argv) > 3 else 6
eps = []
for c in sel:
    ep = J.episodes()[int(c)]; ep['name'] = 't%s' % c; eps.append(ep)
plans, budgets = Q.get_plans(eps, A0)
print('plans:', [(e['name'], len(p), b) for e, p, b in zip(eps, plans, budgets)], flush=True)
best = None; fails = bad = 0; t0 = time.time()
for seed in range(iters):
    prios = [list(range(len(eps))), list(reversed(range(len(eps))))]
    if seed:
        p = list(range(len(eps))); random.Random(seed).shuffle(p); prios.append(p)
    for prio in prios:
        r = Q.attempt(eps, plans, budgets, seed, jitter=2.0 if seed else 0.0, verbose=(seed == 0), prio=prio)
        if r is None: fails += 1; continue
        if r[0] == 'BAD': bad += 1; print('  BAD', r[1:]); continue
        d, ops = r
        if best is None or d < best[0]:
            best = (d, ops); print('  seed %d prio %s model depth %d ops %d (%.0fs)' % (seed, prio, d, len(ops), time.time() - t0), flush=True)
print('fails %d bad %d' % (fails, bad))
if best:
    d, ops = best
    pickle.dump(ops, open('cpfi_terms_%s.pkl' % sel, 'wb'))
    from qiskit import transpile
    tq = transpile(Q.ops_to_qc(ops, 18), basis_gates=['u3', 'cx'], optimization_level=2, seed_transpiler=0)
    print('best model depth %d  opt2 depth %d cx %d  ops %s' % (d, tq.depth(), tq.count_ops().get('cx', 0), dict(Counter(o[0] for o in ops))))
