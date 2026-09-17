"""CP-FI: exact reversible pebbling plan for one phase-term episode.

State = (live node set, phase pairs done).  Moves: compute k (preds live),
uncompute k (preds live), phase pair (its nodes live).  Register check:
live nodes minus a matching of data-hostable nodes onto distinct data wires
must fit in the episode's ancilla share A.  Dijkstra on gate cost
(7 ccx / 13 c3x / 2 cz), ties by fewer moves.  The phase is split
bilinearly: for term forms f1, f2 the phase is XOR over pairs (a, b) with a
in the node-or-affine parts of f1 and b of f2, so only two nodes need to be
live at once (three for the arity-3 term).
"""
import sys, heapq, itertools, time
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfi_joint as J

N, preds, succ, lev = J.N, J.preds, J.succ, J.lev
MASK69 = J.MASK69


def hostable(ep):
    forms_all = list(ep['term']) + [f for k in ep['cone'] for f in N[k]]
    host = {}
    for k in ep['cone']:
        nb = 1 << (12 + k)
        readers = [f for f in forms_all if f & nb]
        ws = [w for w in range(12) if all((f >> w) & 1 for f in readers)
              and not any((f >> w) & 1 for f in N[k])]
        if ws: host[k] = ws
    return host


def phase_pairs(ep):
    """list of tuples of parts, one part per term form; a part is either
    ('n', k) for a top node or ('a', affine_form) for the raw/const remainder."""
    parts = []
    for f in ep['term']:
        ps = [('n', b - 12) for b in J.bits(f) if 12 <= b < 69]
        aff = f & ((1 << 12) - 1) | (f & (1 << 69))
        if aff: ps.append(('a', aff))
        parts.append(ps)
    return list(itertools.product(*parts))


def plan(ep, A, host=None, cost_c3=13, cost_cc=7, cost_cz=2, limit=3_000_000, verbose=False):
    cone = ep['cone']; idx = {k: i for i, k in enumerate(cone)}; n = len(cone)
    if host is None: host = hostable(ep)
    pairs = phase_pairs(ep)
    npair = len(pairs)
    need = []          # per pair: bitmask of nodes needed
    for pr in pairs:
        m = 0
        for kind, v in pr:
            if kind == 'n': m |= 1 << idx[v]
        need.append(m)
    pm = [0] * n
    for k in cone:
        m = 0
        for p in preds[k]: m |= 1 << idx[p]
        pm[idx[k]] = m
    gcost = [cost_c3 if len(N[k]) == 3 else cost_cc for k in cone]
    hw = [host.get(k, []) for k in cone]

    def fits(live):
        ks = [i for i in range(n) if live >> i & 1]
        free = [i for i in ks if not hw[i]]
        hs = [i for i in ks if hw[i]]
        if len(free) > A: return False
        # max matching of hostable live nodes onto distinct data wires (greedy + small brute force)
        best = 0
        if hs:
            wires = sorted({w for i in hs for w in hw[i]})
            # brute force over assignments for small sets
            def rec(i, used):
                nonlocal best
                if i == len(hs):
                    best = max(best, len(used)); return
                if len(used) + (len(hs) - i) <= best: return
                for w in hw[hs[i]]:
                    if w not in used:
                        rec(i + 1, used | {w})
                rec(i + 1, used)
            rec(0, frozenset())
        return len(ks) - best <= A

    start = (0, 0)
    goal_pairs = (1 << npair) - 1
    # A* heuristic: every live node must still be uncomputed; every node in the
    # cone of an undone pair that is not live must still be computed; 2 per undone pair
    pcone = []
    for j in range(npair):
        m = need[j]; st = [i for i in range(n) if m >> i & 1]; seen = 0
        while st:
            i = st.pop()
            if seen >> i & 1: continue
            seen |= 1 << i
            st.extend(q for q in range(n) if pm[i] >> q & 1)
        pcone.append(seen)
    def heur(live, done):
        needm = 0; cnt = 0
        for j in range(npair):
            if not (done >> j & 1):
                needm |= pcone[j]; cnt += 1
        h = cost_cz * cnt
        m = live | (needm & ~live)
        while m:
            i = (m & -m).bit_length() - 1; m &= m - 1
            h += gcost[i]
        return h
    dist = {start: 0}
    prev = {}
    pq = [(heur(0, 0), 0, start)]
    pops = 0
    t0 = time.time()
    while pq:
        fd, nm, st = heapq.heappop(pq)
        d = dist[st]
        live, done = st
        if fd > d + heur(live, done): continue
        pops += 1
        if pops > limit: return None
        if done == goal_pairs and live == 0:
            # reconstruct
            seq = []
            cur = st
            while cur in prev:
                p, mv = prev[cur]; seq.append(mv); cur = p
            seq.reverse()
            if verbose: print('  plan A=%d: cost %d moves %d states %d (%.1fs)' % (A, d, len(seq), len(dist), time.time() - t0))
            return d, seq
        moves = []
        for i in range(n):
            if pm[i] & ~live: continue
            if live >> i & 1:
                moves.append((gcost[i], ('u', cone[i]), (live & ~(1 << i), done)))
            elif done != goal_pairs:
                nl = live | (1 << i)
                if fits(nl):
                    moves.append((gcost[i], ('c', cone[i]), (nl, done)))
        if done != goal_pairs:
            for j in range(npair):
                if not (done >> j & 1) and need[j] & ~live == 0:
                    moves.append((cost_cz, ('p', j), (live, done | (1 << j))))
        for c, mv, ns in moves:
            nd = d + c
            if nd < dist.get(ns, 1e18):
                dist[ns] = nd; prev[ns] = (st, mv)
                heapq.heappush(pq, (nd + heur(ns[0], ns[1]), nm + 1, ns))
    return None


def plan_beam(ep, A, host=None, width=3000, cost_c3=13, cost_cc=7, cost_cz=2, verbose=False):
    """beam search on the same state space, ranked by g + h; returns (cost, seq)"""
    cone = ep['cone']; idx = {k: i for i, k in enumerate(cone)}; n = len(cone)
    if host is None: host = hostable(ep)
    pairs = phase_pairs(ep); npair = len(pairs)
    need = []
    for pr in pairs:
        m = 0
        for kind, v in pr:
            if kind == 'n': m |= 1 << idx[v]
        need.append(m)
    pm = [0] * n
    for k in cone:
        m = 0
        for p in preds[k]: m |= 1 << idx[p]
        pm[idx[k]] = m
    gcost = [cost_c3 if len(N[k]) == 3 else cost_cc for k in cone]
    hw = [host.get(k, []) for k in cone]
    def fits(live):
        ks = [i for i in range(n) if live >> i & 1]
        free = [i for i in ks if not hw[i]]
        if len(free) > A: return False
        hs = [i for i in ks if hw[i]]
        best = 0
        def rec(i, used):
            nonlocal best
            if i == len(hs):
                best = max(best, len(used)); return
            if len(used) + (len(hs) - i) <= best: return
            for w in hw[hs[i]]:
                if w not in used: rec(i + 1, used | {w})
            rec(i + 1, used)
        rec(0, frozenset())
        return len(ks) - best <= A
    pcone = []
    for j in range(npair):
        m = need[j]; st = [i for i in range(n) if m >> i & 1]; seen = 0
        while st:
            i = st.pop()
            if seen >> i & 1: continue
            seen |= 1 << i
            st.extend(q for q in range(n) if pm[i] >> q & 1)
        pcone.append(seen)
    def heur(live, done):
        needm = 0; cnt = 0
        for j in range(npair):
            if not (done >> j & 1):
                needm |= pcone[j]; cnt += 1
        h = cost_cz * cnt; m = live | (needm & ~live)
        while m:
            i = (m & -m).bit_length() - 1; m &= m - 1; h += gcost[i]
        return h
    goal = (1 << npair) - 1
    beam = {(0, 0): (0, [])}
    t0 = time.time()
    for depth in range(400):
        nxt = {}
        for (live, done), (g, seq) in beam.items():
            if done == goal and live == 0:
                if verbose: print('  beam A=%d: cost %d moves %d (%.1fs)' % (A, g, len(seq), time.time() - t0))
                return g, seq
            for i in range(n):
                if pm[i] & ~live: continue
                if live >> i & 1:
                    ns = (live & ~(1 << i), done); c = gcost[i]; mv = ('u', cone[i])
                elif done != goal:
                    nl = live | (1 << i)
                    if not fits(nl): continue
                    ns = (nl, done); c = gcost[i]; mv = ('c', cone[i])
                else:
                    continue
                if ns not in nxt or nxt[ns][0] > g + c:
                    nxt[ns] = (g + c, seq + [mv])
            if done != goal:
                for j in range(npair):
                    if not (done >> j & 1) and need[j] & ~live == 0:
                        ns = (live, done | (1 << j))
                        if ns not in nxt or nxt[ns][0] > g + cost_cz:
                            nxt[ns] = (g + cost_cz, seq + [('p', j)])
        if not nxt: return None
        ranked = sorted(nxt.items(), key=lambda kv: kv[1][0] + heur(*kv[0]))
        beam = dict(ranked[:width])
    return None


if __name__ == '__main__':
    eps = J.episodes()
    sel = sys.argv[1] if len(sys.argv) > 1 else '0123'
    for c in sel:
        ep = eps[int(c)]
        h = hostable(ep)
        print('episode %s cone %d hostable %d pairs %d' % (c, len(ep['cone']), len(h), len(phase_pairs(ep))))
        for A in [int(a) for a in (sys.argv[2] if len(sys.argv) > 2 else '2,3,4,6').split(',')]:
            r = plan(ep, A, h, verbose=True) if len(ep['cone']) <= 15 else plan_beam(ep, A, h, verbose=True)
            if r is None:
                print('  A=%d: no plan' % A)
            else:
                d, seq = r
                from collections import Counter
                print('  A=%d cost %d moves %s' % (A, d, dict(Counter(m[0] for m in seq))))
                import pickle; pickle.dump(seq, open('cpfi_plan_%s_A%d.pkl' % (c, A), 'wb'))
