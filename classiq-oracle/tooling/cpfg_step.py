"""CP-FG step-wise constructive solver.  Exact wire semantics (70-bit content
per wire), one small CP-SAT per step: <=L CX layers (+free X) to assemble
operands, then the step's Toffolis fire on distinct targets reading operands
EXACTLY.  Nodes that cannot be placed defer to the next step.  Body only;
circuit = body ; phase ; mirror(body)."""
import sys, pickle, time, random, collections
sys.path.insert(0, '/home/user/classiq-challenge')
from ortools.sat.python import cp_model
import cpfg_model as M

N, TERMS, NN, NW, BITS = M.N, M.TERMS, M.NN, M.NW, M.BITS
dur, preds, succ, lev = M.dur, M.preds, M.succ, M.lev
RAW = [1 << w if w < 12 else 0 for w in range(NW)]
_, H = M.windows(10**6)
height = [10**6 - h for h in H]


def step_solve(cont, S, locked, remaining_ops, L=2, readers=3, tlimit=10.0, seed=0,
               phase_reads=None, uncomp=(), demand=(), nogoods=(), future=None):
    """cont: list of 18 ints.  S: nodes to fire this step.  locked: wires that
    may not be modified (c3x in flight).  remaining_ops: operand forms still to
    be read later (for the raw-bit penalty).  Returns None or a dict."""
    m = cp_model.CpModel(); B = m.NewBoolVar
    cl = [[[None] * BITS for w in range(NW)] for l in range(L + 1)]
    for w in range(NW):
        for b in range(BITS):
            cl[0][w][b] = m.NewConstant((cont[w] >> b) & 1)
    cx = {}; xf = {}
    for l in range(1, L + 1):
        for w in range(NW):
            for b in range(BITS):
                cl[l][w][b] = B('cl%d_%d_%d' % (l, w, b))
        for s in range(NW):
            for w in range(NW):
                if s != w:
                    cx[l, s, w] = B('cx%d_%d_%d' % (l, s, w))
                    if s in locked or w in locked:
                        m.Add(cx[l, s, w] == 0)
        for w in range(NW):
            xf[l, w] = B('xf%d_%d' % (l, w))
            if w in locked: m.Add(xf[l, w] == 0)
            inb = [cx[l, s, w] for s in range(NW) if s != w]
            outb = [cx[l, w, d] for d in range(NW) if d != w]
            m.Add(sum(inb) + sum(outb) <= 1)
            has = B('has%d_%d' % (l, w)); m.Add(sum(inb) == has)
            for b in range(BITS):
                inc = B('inc%d_%d_%d' % (l, w, b))
                m.AddImplication(inc, has)
                for s in range(NW):
                    if s == w: continue
                    m.AddBoolOr([cx[l, s, w].Not(), inc.Not(), cl[l - 1][s][b]])
                    m.AddBoolOr([cx[l, s, w].Not(), inc, cl[l - 1][s][b].Not()])
                lits = [cl[l - 1][w][b], inc, cl[l][w][b].Not()]
                if b == 69: lits.append(xf[l, w])
                m.AddBoolXOr(lits)
    def present(o, w):
        v = B('p_%d_%d' % (o & ((1 << 70) - 1), w))
        for b in range(BITS):
            if (o >> b) & 1: m.AddImplication(v, cl[L][w][b])
            else: m.AddImplication(v, cl[L][w][b].Not())
        return v
    tgt = {}; rd = {}
    reads = collections.defaultdict(list); tg = collections.defaultdict(list)
    MASK = (1 << 69) - 1
    incompat = []; unsafe = []
    for k in S:
        for w in range(NW):
            tgt[k, w] = B('t%d_%d' % (k, w))
            if w in locked: m.Add(tgt[k, w] == 0)
            tg[w].append(tgt[k, w])
            after = (cont[w] & MASK) | (1 << (12 + k))
            ok = any(((o >> (12 + k)) & 1) and (after & ~o & MASK) == 0 for o in remaining_ops)
            if not ok:
                incompat.append(tgt[k, w])
            if future is not None:
                others = [cont[v] for v in range(NW) if v != w] + [cont[w] ^ (1 << (12 + k))]
                if in_span(others, future):
                    unsafe.append(tgt[k, w])
            for i in range(len(N[k])):
                rd[k, i, w] = B('r%d_%d_%d' % (k, i, w))
                m.AddImplication(rd[k, i, w], present(N[k][i], w))
                reads[w].append(rd[k, i, w])
        m.AddExactlyOne([tgt[k, w] for w in range(NW)])
        for i in range(len(N[k])):
            m.AddExactlyOne([rd[k, i, w] for w in range(NW)])
        for w in range(NW):
            m.Add(tgt[k, w] + sum(rd[k, i, w] for i in range(len(N[k]))) <= 1)
    # optional in-body uncompute of consumed nodes: fire the node again on a
    # wire that holds its bit (removes it there); rewarded, since it frees a wire
    utg = {}; urd = {}; ufire = {}
    for u in uncomp:
        ufire[u] = B('uf%d' % u)
        for w in range(NW):
            utg[u, w] = B('ut%d_%d' % (u, w))
            if w in locked: m.Add(utg[u, w] == 0)
            m.AddImplication(utg[u, w], cl[L][w][12 + u])
            m.AddImplication(utg[u, w], ufire[u])
            tg[w].append(utg[u, w])
            for i in range(len(N[u])):
                urd[u, i, w] = B('ur%d_%d_%d' % (u, i, w))
                m.AddImplication(urd[u, i, w], present(N[u][i], w))
                m.AddImplication(urd[u, i, w], ufire[u])
                reads[w].append(urd[u, i, w])
        m.Add(sum(utg[u, w] for w in range(NW)) == ufire[u])
        for i in range(len(N[u])):
            m.Add(sum(urd[u, i, w] for w in range(NW)) == ufire[u])
        for w in range(NW):
            m.Add(utg[u, w] + sum(urd[u, i, w] for i in range(len(N[u]))) <= 1)
    pw = {}
    if phase_reads:
        for p, term in enumerate(phase_reads):
            for i, o in enumerate(term):
                for w in range(NW):
                    pw[p, i, w] = B('pw%d_%d_%d' % (p, i, w))
                    m.AddImplication(pw[p, i, w], present(o, w))
                    reads[w].append(pw[p, i, w])
                m.AddExactlyOne([pw[p, i, w] for w in range(NW)])
            for w in range(NW):
                m.Add(sum(pw[p, i, w] for i in range(len(term))) <= 1)
    for w in range(NW):
        m.Add(sum(tg[w]) <= 1)
        m.Add(sum(reads[w]) <= readers)
        for r in reads[w]:
            for t in tg[w]: m.AddImplication(r, t.Not())
    # INVARIANT: every raw bit still demanded later must end the step PURE on
    # some wire (content == x_j up to const, and that wire not a target now).
    for j in demand:
        pures = []
        for w in range(NW):
            pv = B('pure%d_%d' % (j, w))
            for b in range(69):
                if b == j: m.AddImplication(pv, cl[L][w][b])
                else: m.AddImplication(pv, cl[L][w][b].Not())
            for t in tg[w]: m.AddImplication(pv, t.Not())
            pures.append(pv)
        m.AddBoolOr(pures)
    for ng in nogoods:
        m.AddBoolOr([tgt[k, w].Not() for (k, w) in ng if (k, w) in tgt])
    # penalty: destroying a pure raw data wire that later operands still want
    want = collections.Counter()
    for o in remaining_ops:
        for w in range(12):
            if (o >> w) & 1: want[w] += 1
    pen = []
    for w in range(12):
        if cont[w] == RAW[w] and want[w]:
            mod = B('mod%d' % w)
            for l in range(1, L + 1):
                for s in range(NW):
                    if s != w: m.AddImplication(cx[l, s, w], mod)
                m.AddImplication(xf[l, w], mod)
            for t in tg[w]: m.AddImplication(t, mod)
            pen.append(want[w] * mod)
    m.Minimize(2 * sum(cx.values()) + sum(pen) + 12 * sum(incompat) + 20 * sum(unsafe) - 8 * sum(ufire.values()))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = tlimit
    s.parameters.num_workers = 4
    s.parameters.random_seed = seed
    st = s.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    ops = []
    for l in range(1, L + 1):
        for (ll, a, b), v in cx.items():
            if ll == l and s.Value(v): ops.append(('cx', a, b))
        for (ll, w), v in xf.items():
            if ll == l and s.Value(v): ops.append(('x', w))
    newc = [sum(s.Value(cl[L][w][b]) << b for b in range(BITS)) for w in range(NW)]
    fired = {}
    for k in S:
        tw = [w for w in range(NW) if s.Value(tgt[k, w])][0]
        rs = [[w for w in range(NW) if s.Value(rd[k, i, w])][0] for i in range(len(N[k]))]
        ops.append((('ccx' if len(rs) == 2 else 'c3x'),) + tuple(rs) + (tw,))
        fired[k] = (tw, rs)
    unc = {}
    for u in uncomp:
        if s.Value(ufire[u]):
            tw = [w for w in range(NW) if s.Value(utg[u, w])][0]
            rs = [[w for w in range(NW) if s.Value(urd[u, i, w])][0] for i in range(len(N[u]))]
            ops.append((('ccx' if len(rs) == 2 else 'c3x'),) + tuple(rs) + (tw,))
            unc[u] = (tw, rs)
    ph = []
    for p, term in enumerate(phase_reads or []):
        ws = [[w for w in range(NW) if s.Value(pw[p, i, w])][0] for i in range(len(term))]
        ph.append((('cz' if len(ws) == 2 else 'ccz'),) + tuple(ws))
    return dict(ops=ops, cont=newc, fired=fired, unc=unc, ph=ph, cx=sum(1 for o in ops if o[0] == 'cx'))


MASK69 = (1 << 69) - 1


def in_span(vectors, targets):
    """GF(2): are all `targets` in the span of `vectors` (69-bit ints)?"""
    basis = {}
    for v in vectors:
        v &= MASK69
        while v:
            h = v.bit_length() - 1
            if h in basis: v ^= basis[h]
            else: basis[h] = v; break
    bad = []
    for o in targets:
        v = o & MASK69
        while v:
            h = v.bit_length() - 1
            if h in basis: v ^= basis[h]
            else: break
        if v: bad.append(o)
    return bad


def assembly_cost(contents, o, maxw=3):
    """min number of wires whose XOR (up to const) equals o; maxw+1 if deeper, 99 if not in span."""
    o &= MASK69
    vs = [c & MASK69 for c in contents]
    if o in vs: return 1
    pairs = {}
    for i in range(len(vs)):
        for j in range(i + 1, len(vs)):
            pairs.setdefault(vs[i] ^ vs[j], (i, j))
    if o in pairs: return 2
    if maxw >= 3:
        for i in range(len(vs)):
            if (o ^ vs[i]) in pairs: return 3
    return (maxw + 1) if not in_span(vs, [o]) else 99


def lookahead(contents, done, S, pending):
    """weighted future assembly cost: operands of nodes whose preds are all done
    weigh 1, others 0.3; not-yet-computed node bits are masked out."""
    notyet = 0
    for j in range(NN):
        if j not in done and j not in S: notyet |= 1 << (12 + j)
    tot = 0.0
    for j in range(NN):
        if j in done or j in S: continue
        soon = all(p in done or p in S for p in preds[j])
        for o in N[j]:
            tot += (1.0 if soon else 0.3) * (assembly_cost(contents, o & ~notyet) - 1)
    for tm in TERMS:
        for o in tm: tot += 0.3 * (assembly_cost(contents, o & ~notyet) - 1)
    return tot


def construct(cap=7, seed=0, tlimit=4.0, L=3, verbose=True, jitter=0.0, purity=False, span=True, pool=5):
    rng = random.Random(seed)
    cont = list(RAW)
    done = {}            # node -> step fired
    pending = {}         # c3x fired last step: node -> (tw, rs)
    body = []; t = 0
    prio = {k: height[k] + jitter * rng.random() for k in range(NN)}
    while len(done) < NN:
        locked = set()
        for k, (tw, rs) in pending.items():
            locked.add(tw); locked.update(rs)
        avail = set(k for k in done if done[k] + dur[k] <= t)
        ready = [k for k in range(NN) if k not in done and all(j in avail for j in preds[k])]
        ready.sort(key=lambda k: -prio[k])
        phfeed = set(M.A['phfeed'])
        def attempt(S, extra_nogoods=()):
            rem_ops = [o for k in range(NN) if k not in done and k not in S for o in N[k]] + [o for tm in TERMS for o in tm]
            demand = set(w for o in rem_ops for w in range(12) if (o >> w) & 1)
            cands = [u for u in done if u not in pending and u not in phfeed and dur[u] == 1
                     and all(v in done and v not in S for v in succ[u])
                     and any((cont[w] >> (12 + u)) & 1 for w in range(NW))]
            nogoods = list(extra_nogoods)
            notyet = 0
            for j in range(NN):
                if j not in done and j not in S: notyet |= 1 << (12 + j)
            fut = [o & ~notyet for o in rem_ops]
            for _ in range(4):
                sol = step_solve(cont, S, locked, rem_ops, L=L, tlimit=tlimit, seed=seed,
                                 uncomp=cands, demand=(demand if purity else ()), nogoods=nogoods,
                                 future=(fut if span else None))
                if sol is None or not span: return sol
                after = list(sol['cont'])
                for k, (tw, rs) in sol['fired'].items(): after[tw] ^= 1 << (12 + k)
                for k, (tw, rs) in pending.items(): after[tw] ^= 1 << (12 + k)
                for u, (tw, rs) in sol['unc'].items(): after[tw] ^= 1 << (12 + u)
                # future operands must stay assemblable: in the span of the contents
                # (node bits of nodes not yet computed are ignored -- they will be added)
                bad = in_span(after, fut)
                if not bad: return sol
                nogoods.append([(k, tw) for k, (tw, rs) in sol['fired'].items()])
            return None
        # greedy-add: keep a node only if the step stays feasible with it
        S = []; sol = attempt([])
        for k in ready:
            if len(S) >= cap: break
            r = attempt(S + [k])
            if r is not None: S = S + [k]; sol = r
        # solution pool for the chosen S: K alternatives, pick by lookahead
        if sol is not None and S:
            def after_of(r):
                a = list(r['cont'])
                for k, (tw, rs) in r['fired'].items(): a[tw] ^= 1 << (12 + k)
                for k, (tw, rs) in pending.items(): a[tw] ^= 1 << (12 + k)
                for u, (tw, rs) in r['unc'].items(): a[tw] ^= 1 << (12 + u)
                return a
            best = (lookahead(after_of(sol), done, S, pending) + 0.5 * sol['cx'], sol)
            pool_ng = [[(k, tw) for k, (tw, rs) in sol['fired'].items()]]
            for _ in range(pool - 1):
                r = attempt(S, extra_nogoods=pool_ng)
                if r is None: break
                pool_ng.append([(k, tw) for k, (tw, rs) in r['fired'].items()])
                sc = lookahead(after_of(r), done, S, pending) + 0.5 * r['cx']
                if sc < best[0]: best = (sc, r)
            sol = best[1]
            if verbose: print('    pool: best lookahead %.1f' % best[0], flush=True)
        if sol is None or (not sol['fired'] and not sol['unc']):
            if verbose: print('  step %d: nothing placeable (ready %d) -> idle step' % (t, len(ready)), flush=True)
            pickle.dump(dict(cont=cont, done=done, pending=pending, t=t, ready=ready), open('cpfg_stall.pkl', 'wb'))
            if not pending: return None
            for k, (tw, rs) in pending.items(): cont[tw] ^= 1 << (12 + k)
            t += 1; pending = {}; continue
        body += sol['ops']
        newc = sol['cont']          # contents after the CX phase
        for k, (tw, rs) in sol['fired'].items():
            done[k] = t
            if dur[k] == 1: newc[tw] ^= 1 << (12 + k)      # ccx bit lands now
        for k, (tw, rs) in pending.items():
            newc[tw] ^= 1 << (12 + k)                      # c3x from t-1 lands now
        for u, (tw, rs) in sol['unc'].items():
            newc[tw] ^= 1 << (12 + u)                      # uncomputed: bit removed
        cont = newc
        pending = {k: v for k, v in sol['fired'].items() if dur[k] == 2}
        pickle.dump(dict(cont=cont, done=dict(done), pending=dict(pending), t=t + 1), open('cpfg_state_%d.pkl' % t, 'wb'))
        if verbose:
            free = sum(1 for w in range(NW) if cont[w] in (RAW[w], RAW[w] | (1 << 69)))
            print('  step %2d: fired %d (%s) unc %s cx %d  ready %d  pure/clean wires %d' % (t, len(sol['fired']),
                  ','.join('%d%s' % (k, '*' if dur[k] == 2 else '') for k in sol['fired']),
                  list(sol['unc']), sol['cx'], len(ready), free), flush=True)
        t += 1
    # c3x fired in the last step need one more step to land
    if pending:
        locked = set()
        for k, (tw, rs) in pending.items(): locked.add(tw); locked.update(rs)
        for k, (tw, rs) in pending.items(): cont[tw] ^= 1 << (12 + k)
        t += 1
    # phase assembly
    sol = step_solve(cont, [], set(), [], L=L, tlimit=tlimit, seed=seed, phase_reads=TERMS)
    if sol is None:
        # try with more layers
        sol = step_solve(cont, [], set(), [], L=4, tlimit=tlimit, seed=seed, phase_reads=TERMS)
        if sol is None:
            print('  phase assembly infeasible'); return None
    body += sol['ops']
    if verbose: print('  steps %d  body ops %d  cx %d' % (t, len(body), sum(1 for o in body if o[0] == 'cx')))
    return body, sol['ph'], t


if __name__ == '__main__':
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    t0 = time.time()
    r = construct(cap=cap, seed=seed)
    print('construct time %.0fs' % (time.time() - t0))
    if r:
        body, ph, T = r
        pickle.dump((body, ph), open('cpfg_step_c%d_s%d.pkl' % (cap, seed), 'wb'))
        import cpfg_eval as E
        E.evaluate(body, ph, sv=True)
