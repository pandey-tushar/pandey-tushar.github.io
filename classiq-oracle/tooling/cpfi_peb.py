"""CP-FI: parallel reversible pebbling of one phase-term episode under a
register budget, recomputation allowed.

A step is a set of simultaneous Toffolis (computes / uncomputes of distinct
cone nodes) whose read set and write set are disjoint; the episode ends when
the term's phase gate has fired and no node is live.  Registers needed in a
step = live before + computes in the step.  Randomised greedy with restarts;
returns the best (cost, steps) where cost = sum over steps of the slowest
gate in the step (7 ccx / 13 c3x) + 2 for the phase step.
"""
import sys, random
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfg_model as M

N, TERMS, lev, preds, succ = M.N, M.TERMS, M.lev, M.preds, M.succ
def bits(v): return [i for i in range(70) if v >> i & 1]


def term_info(ti):
    t = TERMS[ti]
    top = set()
    for v in t:
        top |= {b - 12 for b in bits(v) if 12 <= b < 69}
    seen = set(); st = list(top)
    while st:
        k = st.pop()
        if k in seen: continue
        seen.add(k); st.extend(preds[k])
    return sorted(top), sorted(seen)


def height(cone):
    h = {}
    for k in sorted(cone, key=lambda k: -lev[k]):
        h[k] = (13 if len(N[k]) == 3 else 7) + max([h[s] for s in succ[k] if s in h], default=0)
    return h


def pebble(ti, budget, iters=200, seed=0, verbose=False):
    top, cone = term_info(ti)
    cone_set = set(cone); top_set = set(top)
    h = height(cone)
    cost_of = {k: (13 if len(N[k]) == 3 else 7) for k in cone}
    rng = random.Random(seed)
    best = None
    for it in range(iters):
        live = set(); phased = False; steps = []; cost = 0
        # future need: node k is needed while (phase not done and k in cone of not-yet-phased term)
        stuck = 0
        while not (phased and not live):
            if len(steps) > 400: break
            reads = set(); writes = set(); moves = []
            if not phased and top_set <= live:
                phased = True; steps.append([('phase', tuple(top))]); cost += 2
                continue
            # ready computes: preds live, not live; useful = phase not done
            comps = [k for k in cone if k not in live and all(p in live for p in preds[k])
                     and not phased]
            # ready uncomputes: live, preds live
            uncs = [k for k in live if all(p in live for p in preds[k])]
            if not phased:
                # keep nodes with a live successor or with unfired successors only if
                # they will be needed; greedy: uncompute only nodes whose successors
                # are all live (their job is done until uncompute time) when budget is tight
                uncs = [k for k in uncs if k not in top_set and succ[k] and all(s in live for s in succ[k] if s in cone_set)]
            else:
                # after the phase: uncompute nodes with no live successors first
                uncs = [k for k in uncs if not any(s in live for s in succ[k] if s in cone_set)]
            comps.sort(key=lambda k: (-h[k], rng.random()))
            uncs.sort(key=lambda k: (rng.random(),))
            free = budget - len(live)
            chosen = []
            # computes first (bounded by free registers), then uncomputes
            for k in comps:
                if free <= 0: break
                rd = set(preds[k])
                if rd & writes or k in reads: continue
                if rng.random() < 0.15: continue          # randomisation
                chosen.append(('c', k)); writes.add(k); reads |= rd; free -= 1
            for k in uncs:
                rd = set(preds[k])
                if rd & writes or k in reads or k in writes: continue
                if not phased and rng.random() < 0.5: continue
                # do not uncompute a node needed by an unfired successor
                if not phased and any(s not in live for s in succ[k] if s in cone_set): continue
                chosen.append(('u', k)); writes.add(k); reads |= rd
            if not chosen:
                # tight budget: must free registers by uncomputing something with live preds
                cand = [k for k in live if all(p in live for p in preds[k]) and k not in top_set]
                if not cand:
                    stuck = 1; break
                k = max(cand, key=lambda k: (lev[k], rng.random()))
                chosen = [('u', k)]
            for m, k in chosen:
                if m == 'c': live.add(k)
                else: live.discard(k)
            steps.append(chosen); cost += max(cost_of[k] for _, k in chosen)
        if stuck or not (phased and not live):
            continue
        if best is None or cost < best[0]:
            best = (cost, steps)
            if verbose:
                print('  iter %d cost %d steps %d gates %d' % (it, cost, len(steps), sum(len(s) for s in steps)))
    return best


if __name__ == '__main__':
    for ti in range(4):
        top, cone = term_info(ti)
        row = []
        for b in (3, 4, 5, 6, 8, 10, 12, 25):
            r = pebble(ti, b, iters=300, seed=1)
            row.append('b%d:%s' % (b, 'X' if r is None else '%d/%d' % (r[0], sum(len(s) for s in r[1]))))
        print('term %d cone %d  ' % (ti, len(cone)) + '  '.join(row), flush=True)
