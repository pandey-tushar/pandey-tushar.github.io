"""CP-FI: bilinear pair sub-episodes + mode-aware exact planner + executor.

Sub-episode = one bilinear pair of a phase term: parts (node k | affine
form) x (node m | affine form); its phase is the product of the two part
functions and the XOR over all pairs of all terms is F.  Cones are small
(0..19 nodes) and independent, so many run concurrently on 2 ancillas each.

Planner: Dijkstra/A* over (live set, phase done, hosting modes).  A node
may be hosted on a data wire w (reader-compatible) and while it is, no move
of the plan may read x_w without n_k -- so the plan is physically
realisable as-is.  Ancillas in use = live - data-hosted <= A.

Executor: sequential per sub-episode, interleaved by earliest start;
per-episode ancilla quota with admission control (sum of quotas of
admitted unfinished episodes <= 6); phase gates by the temporal span
solver afterwards; exact replay + statevector + transpile.
"""
import sys, heapq, time, random, pickle, itertools
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfi_joint as J
import cpfi_plan as P
import cpfi_span as S
import cpfh_core as C
from cpfi_exec import model_depth, ops_to_qc
from collections import Counter

N, preds, succ, lev = J.N, J.preds, J.succ, J.lev
NW = 18
RAWB = (1 << 12) - 1


def pair_episodes():
    out = []
    for ti, ep in enumerate(J.episodes()):
        for pi, pr in enumerate(P.phase_pairs(ep)):
            term = []; top = []
            for kind, v in pr:
                if kind == 'n':
                    term.append(1 << (12 + v)); top.append(v)
                else:
                    term.append(v)
            seen = set(); st = list(top)
            while st:
                k = st.pop()
                if k in seen: continue
                seen.add(k); st.extend(preds[k])
            cone = sorted(seen)
            h = {}
            for k in sorted(cone, key=lambda k: -lev[k]):
                h[k] = (13 if len(N[k]) == 3 else 7) + max([h[s] for s in succ[k] if s in seen], default=2)
            out.append(dict(ti=ti, pi=pi, term=term, top=sorted(top), cone=cone, cset=seen, h=h,
                            name='%d.%d' % (ti, pi)))
    return out


def reads_pure(forms, w, k):
    nb = 1 << (12 + k)
    return any((f >> w) & 1 and not (f & nb) for f in forms)


def plan_modes(ep, A, cost_c3=13, cost_cc=7, cost_cz=2, limit=4_000_000, verbose=False):
    cone = ep['cone']; idx = {k: i for i, k in enumerate(cone)}; n = len(cone)
    host = P.hostable(ep)
    top = ep['top']
    pm = [0] * n
    for k in cone:
        m = 0
        for p in preds[k]: m |= 1 << idx[p]
        pm[idx[k]] = m
    gcost = [cost_c3 if len(N[k]) == 3 else cost_cc for k in cone]
    hw = [host.get(k, []) for k in cone]
    needm = 0
    for k in top: needm |= 1 << idx[k]
    # pure-read table: pure[i][w] = node i's forms read x_w without n_k -- depends on k, so compute lazily
    def blocked(i_or_forms, modes):
        forms = N[cone[i_or_forms]] if isinstance(i_or_forms, int) else i_or_forms
        for (k, w) in modes:
            if reads_pure(forms, w, k): return True
        return False
    term_forms = ep['term']
    allcone = 0
    for i in range(n): allcone |= 1 << i

    def heur(live, done):
        h = 0 if done else cost_cz
        m = live | (0 if done else (allcone & ~live))
        while m:
            i = (m & -m).bit_length() - 1; m &= m - 1; h += gcost[i]
        return h

    start = (0, 0, frozenset())
    dist = {start: 0}; prev = {}
    pq = [(heur(0, 0), 0, start)]
    pops = 0; t0 = time.time()
    while pq:
        fd, nm, st = heapq.heappop(pq)
        d = dist[st]; live, done, modes = st
        if fd > d + heur(live, done): continue
        pops += 1
        if pops > limit: return None
        if done and live == 0:
            seq = []; cur = st
            while cur in prev:
                p, mv = prev[cur]; seq.append(mv); cur = p
            seq.reverse()
            if verbose: print('  plan %s A=%d: cost %d moves %d states %d (%.1fs)' % (ep['name'], A, d, len(seq), len(dist), time.time() - t0))
            return d, seq
        moves = []
        nanc = bin(live).count('1') - len(modes)
        used_w = {w for _, w in modes}
        for i in range(n):
            if pm[i] & ~live: continue
            k = cone[i]
            if live >> i & 1:
                if blocked(i, modes - {(k, w) for (kk, w) in modes if kk == k}): continue
                nm2 = frozenset(m for m in modes if m[0] != k)
                moves.append((gcost[i], ('u', k), (live & ~(1 << i), done, nm2)))
            else:
                if blocked(i, modes): continue
                nl = live | (1 << i)
                if nanc < A:
                    moves.append((gcost[i], ('c', k, None), (nl, done, modes)))
                for w in hw[i]:
                    if w in used_w: continue
                    # hosting k on w: forbidden if any currently live node's later uncompute... handled by blocked() at move time
                    moves.append((gcost[i], ('c', k, w), (nl, done, modes | {(k, w)})))
        if not done and needm & ~live == 0 and not blocked(term_forms, modes):
            moves.append((cost_cz, ('p', 0), (live, 1, modes)))
        for c, mv, ns in moves:
            nd = d + c
            if nd < dist.get(ns, 1e18):
                dist[ns] = nd; prev[ns] = (st, mv)
                heapq.heappush(pq, (nd + heur(ns[0], ns[1]), nm + 1, ns))
    return None


class Exec3(J.Sched):
    def __init__(self, eps, plans, quota, rng, jitter=0.0, prio=None, cap=6):
        super().__init__(eps, rng, anc_pref=True, jitter=jitter)
        self.host_by_ep = True; self.lazy = True
        self.plans = plans; self.quota = quota; self.pos = [0] * len(eps)
        self.prio = prio if prio is not None else list(range(len(eps)))
        self.cap = cap
        self.rem = [sum(13 if len(N[m[1]]) == 3 else 7 for m in pl if m[0] != 'p') for pl in plans]

    def unassemble(self, w, dry):
        """return data wire w (affine content) to its raw bit by CX / X."""
        a = self.find_assembly(J.RAW[w], set(range(NW)) - {w}, set())
        if a is None or a[0] != w: return False
        if dry: return True
        for s in a[1]:
            self.place(('cx', s, w)); self.apply(('cx', s, w))
        if a[2]:
            self.place(('x', w)); self.apply(('x', w))
        return self.cont[w] == J.RAW[w]

    def held(self, e):
        return sum(1 for (ee, k), w in self.host.items() if w >= 12 and ee == e)

    def admitted(self, e):
        tot = 0
        for b in self.prio:
            if self.pos[b] >= len(self.plans[b]): continue
            if tot + self.quota[b] <= self.cap:
                if b == e: return True
                tot += self.quota[b]
            elif b == e:
                return False
        return False

    def next_action(self, e, dry):
        pl = self.plans[e]; i = self.pos[e]
        if i >= len(pl): return None
        mv = pl[i]
        if mv[0] == 'p': return 0.0
        if mv[0] == 'u': return self.fire(mv[1], uncompute=True, dry=dry, e=e)
        _, k, w = mv
        if w is not None:
            if self.cont[w] != J.RAW[w]:
                if (self.cont[w] & J.MASK69 & ~RAWB) or not self.unassemble(w, dry):
                    return None                     # hosted by someone else, or not restorable now
                if dry: return self.busy[w]
            return self.fire(k, dry=dry, tgt=w, e=e)
        if self.held(e) >= self.quota[e] or not self.admitted(e): return None
        anc = [w2 for w2 in range(12, NW) if self.cont[w2] == 0]
        if self.jitter: self.rng.shuffle(anc)
        best = None
        for w2 in anc:
            t = self.fire(k, dry=True, tgt=w2, e=e)
            if t is None: continue
            if best is None or t < best[0]: best = (t, w2)
            if not self.jitter: break
        if best is None: return None
        if dry: return best[0]
        return self.fire(k, tgt=best[1], e=e)

    def run(self):
        while True:
            if all(self.pos[e] >= len(self.plans[e]) for e in range(len(self.eps))):
                self.restore(); return True
            opts = []
            for e in range(len(self.eps)):
                t = self.next_action(e, dry=True)
                if t is None: continue
                opts.append((t + self.rng.random() * self.jitter, -self.rem[e], e))
            if not opts:
                if self.verbose:
                    print('    DEADLOCK pos %s host %s' % (self.pos, self.host))
                    for e in range(len(self.eps)):
                        if self.pos[e] >= len(self.plans[e]): continue
                        mv = self.plans[e][self.pos[e]]
                        if mv[0] == 'p': continue
                        k = mv[1]
                        print('      ep %d next %s held %d quota %d admitted %s free_anc %s' % (
                            e, mv, self.held(e), self.quota[e], self.admitted(e), [w for w in range(12, NW) if self.cont[w] == 0]))
                        for f in N[k]:
                            print('        form %s -> %s' % (J.bits(f), self.find_assembly(f, set(), set())))
                        if mv[0] == 'c' and mv[2] is not None:
                            print('        mode wire %d content %s' % (mv[2], J.bits(self.cont[mv[2]])))
                    print('      cont', [(w, J.bits(self.cont[w])) for w in range(NW) if self.cont[w] != J.RAW[w]])
                return False
            opts.sort(); e = opts[0][2]
            mv = self.plans[e][self.pos[e]]
            r = self.next_action(e, dry=False)
            if r is None: return False
            if mv[0] != 'p': self.rem[e] -= 13 if len(N[mv[1]]) == 3 else 7
            self.pos[e] += 1


def expected_phase(eps):
    ph = 0
    for ep in eps:
        m = C.FULL
        for v in ep['term']:
            m &= J.U.value(v, J._NM)
        ph ^= m
    return ph


def finish(ops, eps):
    want = expected_phase(eps)
    r, ins = S.solve(ops, target=want, deg=2)
    if r:
        tw = [(t, tuple(range(NW))) for t in range(0, len(ops) + 1, max(1, len(ops) // 300))]
        r, ins = S.solve(ops, target=want, deg=3, triple_wires=tw)
    if ins is None: return None, r, None
    new = S.insert(ops, ins)
    c, ph = C.replay(new)
    dirty = [w for w in range(NW) if c[w] != C.RM[w]]
    return new, bin(ph ^ want).count('1'), dirty


def attempt(eps, plans, quota, seed, jitter=0.0, verbose=False, prio=None, cap=6):
    rng = random.Random(seed)
    x = Exec3(eps, plans, quota, rng, jitter=jitter, prio=prio, cap=cap)
    x.verbose = verbose
    if not x.run(): return None
    ops = x.oplist()
    new, mism, dirty = finish(ops, eps)
    if new is None or mism or dirty: return ('BAD', mism, dirty)
    return (model_depth(new), new)


def get_plans(eps, A, verbose=True):
    """plan each sub-episode at the smallest feasible budget >= A; returns (plans, budgets)"""
    plans = []; budgets = []
    for ep in eps:
        for a in range(A, 7):
            fn = 'cpfi_pplan_%s_A%d.pkl' % (ep['name'], a)
            try:
                seq = pickle.load(open(fn, 'rb'))
            except FileNotFoundError:
                r = plan_modes(ep, a, verbose=verbose)
                if r is None:
                    if verbose: print('  %s: no plan at A=%d' % (ep['name'], a), flush=True)
                    continue
                seq = r[1]; pickle.dump(seq, open(fn, 'wb'))
            plans.append(seq); budgets.append(a); break
        else:
            raise RuntimeError('no plan for %s' % ep['name'])
    return plans, budgets


if __name__ == '__main__':
    eps_all = pair_episodes()
    names = [e['name'] for e in eps_all]
    sel = sys.argv[1] if len(sys.argv) > 1 else 'all'
    A = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    iters = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    jitter = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
    eps = eps_all if sel == 'all' else [e for e in eps_all if e['name'] in sel.split(',')]
    print('sub-episodes', [(e['name'], len(e['cone'])) for e in eps])
    plans, budgets = get_plans(eps, A)
    print('plans:', [(e['name'], len(p), b) for e, p, b in zip(eps, plans, budgets)])
    quota = [b if len(e['cone']) else 0 for e, b in zip(eps, budgets)]
    best = None; fails = bad = 0; t0 = time.time()
    for seed in range(iters):
        prios = [list(range(len(eps))), sorted(range(len(eps)), key=lambda i: -len(eps[i]['cone']))]
        if seed:
            p = list(range(len(eps))); random.Random(seed).shuffle(p); prios.append(p)
        for prio in prios:
            r = attempt(eps, plans, quota, seed, jitter=jitter if seed else 0.0, verbose=(seed == 0), prio=prio)
            if r is None: fails += 1; continue
            if r[0] == 'BAD': bad += 1; print('  seed %d BAD mism %s dirty %s' % (seed, r[1], r[2])); continue
            d, ops = r
            if best is None or d < best[0]:
                best = (d, ops, seed)
                print('  seed %d prio %s model depth %d ops %d (%.0fs)' % (seed, prio[:6], d, len(ops), time.time() - t0), flush=True)
    print('%s: fails %d bad %d' % (sel, fails, bad))
    if best:
        d, ops, seed = best
        print('best model depth %d ops %s' % (d, dict(Counter(o[0] for o in ops))))
        pickle.dump(ops, open('cpfi_pairs_%s_A%d.pkl' % (sel.replace(',', '_'), A), 'wb'))
        from cpae_core import extract, sim_exact, fvec, SHAPES
        from qiskit import transpile
        qc = ops_to_qc(ops, n=18)
        tq = transpile(qc, basis_gates=['u3', 'cx'], optimization_level=2, seed_transpiler=0)
        print('opt2 depth %d cx %d' % (tq.depth(), tq.count_ops().get('cx', 0)))
        if sel == 'all':
            gl, gp = extract(qc)
            err, mm = sim_exact(gl, gp, fvec(SHAPES['LOGO']))
            print('sim_exact err %.1e mism %d' % (err, mm))
