"""CP-FG driver: pinned list schedule solved W steps at a time with the
assembly-based SAT window model (cpfg_asm).  Body ; phase ; mirror(body)."""
import sys, pickle, time
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfg_model as M, cpfg_asm as A
from cpfg_step import in_span
from cpfg_cms import CMS

N, TERMS, NN, NW = M.N, M.TERMS, M.NN, M.NW
dur = M.dur
RAW = [1 << w if w < 12 else 0 for w in range(NW)]


def solve_with_skips(cont, nodes, W, pending, final_terms, nogoods, maxskip, tlimit, cxmax=None, span_ops=(), done_nodes=(), min_free=0, fire_steps=(), n_remaining=10**6, span_at=None, min_fire0=0):
    """add 'at most maxskip skips' to the window model and solve."""
    r = A.build(cont, nodes, W, nogoods=nogoods, pending=pending, final_terms=final_terms, cxmax=cxmax, span_ops=span_ops, done_nodes=done_nodes, min_free=min_free, fire_steps=fire_steps, n_remaining=n_remaining, span_at=span_at, min_fire0=min_fire0)
    if r is None: return None, 'none'
    m, V = r
    sk = [V['skip'][k] for k in V['skip']]
    if sk: m.atmost(sk, maxskip)
    t0 = time.time(); sat, sol = m.solve(tlimit=tlimit)
    if sat is None: return None, 'timeout %.0fs' % (time.time() - t0)
    if not sat: return None, 'UNSAT %.1fs' % (time.time() - t0)
    return (A.Sol(sol), V), 'SAT %.1fs' % (time.time() - t0)


def run(cap=6, W=2, slack=1, tlimit=240, tighten=2, verbose=True, min_free=0, ckpt=True, slide=1):
    center, Tls = M.list_schedule(cap)
    if verbose: print('list schedule cap %d -> %d steps; W %d slack %d' % (cap, Tls, W, slack), flush=True)
    cont = list(RAW); done = set(); body = []; pending = {}; t0 = 0
    import os
    ck = 'cpfg_drive_ckpt_c%d_w%d_s%d_f%d.pkl' % (cap, W, slack, min_free)
    if ckpt and os.path.exists(ck):
        st = pickle.load(open(ck, 'rb'))
        cont, done, body, pending, t0, center = st['cont'], st['done'], st['body'], st['pending'], st['t0'], st['center']
        if verbose: print('resumed from checkpoint: t0=%d done %d/%d' % (t0, len(done), NN), flush=True)
    while len(done) < NN:
        nodes = {}
        for k in range(NN):
            if k in done: continue
            e, l = max(center[k] - slack, 0), center[k] + slack
            e = max(e, t0)
            if e <= t0 + W - dur[k]:
                optional = l > t0 + W - dur[k]
                nodes[k] = (e - t0, min(l, t0 + W - dur[k]) - t0, optional)
        if not nodes:
            t0 += 1; continue
        phfeed = {j for tm in TERMS for o in tm for j in range(NN) if (o >> (12 + j)) & 1}
        for u in sorted(done):
            if u in phfeed or dur[u] == 2: continue
            if all(v in done for v in M.succ[u]) and any((cont[w] >> (12 + u)) & 1 for w in range(NW)):
                nodes[('u', u)] = (0, W - 1, True)
        rem_ops = [o for k in range(NN) if k not in done for o in N[k]] + [o for tm in TERMS for o in tm]
        final = None

        def attempt(maxskip, cxmax=None, tl=tlimit, min_fire0=0):
            # lookahead witness: the uncommitted steps must each fire something if
            # more nodes than this step can hold remain
            nrem = sum(1 for k in range(NN) if k not in done)
            fs = tuple(range(0, W))          # committed step AND lookahead steps must each fire
            return solve_with_skips(cont, nodes, W, pending, final, [], maxskip, tl, cxmax=cxmax,
                                    span_ops=rem_ops, done_nodes=done, min_free=min_free, fire_steps=fs, n_remaining=nrem, span_at=(slide, W + 1), min_fire0=min_fire0)
        # EASY -> HARD on the COMMITTED step: all nodes optional, then require
        # >= F fires in step 0 for F = 1, 2, ... until UNSAT/timeout
        for k in list(nodes): nodes[k] = (nodes[k][0], nodes[k][1], True)
        nopt = len(nodes); maxskip = nopt; best = None; F = 1
        while True:
            res, msg = attempt(maxskip, min_fire0=F)
            if verbose: print('  window t0=%d nodes %d min_fire0 %d -> %s' % (t0, len(nodes), F, msg), flush=True)
            if res is None: break
            best = (res, F); F += 1
            if F > 9: break
        if best is None: print('window failed'); return None
        (s, V), F = best; F -= 0
        wb, fired, newc, ph = A.decode(s, V, commit=slide)
        fired_all = dict(fired)
        ncx = sum(1 for o in wb if o[0] == 'cx')
        for _ in range(tighten):
            if ncx <= 1: break
            res2, msg2 = attempt(maxskip, cxmax=ncx - max(1, ncx // 5), tl=min(tlimit, 60), min_fire0=F)
            if res2 is None: break
            s2, V2 = res2; wb2, fired2, newc2, ph2 = A.decode(s2, V2, commit=slide)
            ncx2 = sum(1 for o in wb2 if o[0] == 'cx')
            if verbose: print('    tighten cx %d -> %d' % (ncx, ncx2), flush=True)
            wb, fired, newc, ph, ncx = wb2, fired2, newc2, ph2, ncx2
            fired_all = dict(fired)
        notyet = 0
        for j in range(NN):
            if j not in done and (j not in fired or (dur[j] == 2 and fired[j][0] == slide - 1)): notyet |= 1 << (12 + j)
        bad = in_span(newc, [o & ~notyet for o in rem_ops])
        if bad: print('  WARNING: span check failed on %d operands after solve' % len(bad), flush=True)
        unc = [k[1] for k in fired if isinstance(k, tuple)]
        fired = {k: v for k, v in fired.items() if not isinstance(k, tuple)}
        if not fired and not unc:
            pickle.dump(dict(cont=cont, done=done, pending=pending, t0=t0, center=center, nodes=nodes), open('cpfg_stall_state.pkl', 'wb'))
            print('  STALL: no node placeable at t0=%d (state dumped)' % t0, flush=True); return None
        for k in fired: done.add(k)
        for k in nodes:
            if not isinstance(k, tuple) and k not in fired: center[k] = max(center[k], t0 + slide)
        body += wb; cont = newc
        pending = {k: (tw, rs) for k, (tt, tw, rs) in fired.items() if dur[k] == 2 and tt == slide - 1}
        if verbose:
            print('  window t0=%2d: fired %2d %s unc %s cx %d  done %d/%d' % (t0, len(fired), sorted(fired), unc, ncx, len(done), NN), flush=True)
        t0 += slide
        if ckpt: pickle.dump(dict(cont=cont, done=done, body=body, pending=pending, t0=t0, center=center), open(ck, 'wb'))
    # all nodes computed: one assembly step for the phase terms (no Toffolis)
    if pending:
        for k, (tw, rs) in pending.items(): cont[tw] ^= 1 << (12 + k)
        pending = {}
    for ns, tl in ((2, tlimit), (4, tlimit), (6, 3 * tlimit)):
        r = A.build(cont, {}, 0, pending=None, final_terms=TERMS, nsrc=ns, allow_undo=False)
        m, V = r; sat, sol = m.solve(tlimit=tl)
        if verbose: print('  phase assembly nsrc %d -> %s' % (ns, sat), flush=True)
        if sat: break
    if not sat:
        pickle.dump(dict(cont=cont, done=done), open('cpfg_phase_fail.pkl', 'wb'))
        print('phase assembly failed (state dumped)'); return None
    wb, fired, newc, ph = A.decode(A.Sol(sol), V)
    body += wb
    if verbose: print('  phase assembly: cx %d  %s' % (sum(1 for o in wb if o[0] == 'cx'), ph), flush=True)
    return body, ph, t0


if __name__ == '__main__':
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    W = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    slack = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    tl = float(sys.argv[4]) if len(sys.argv) > 4 else 240
    t0 = time.time(); r = run(cap, W, slack, tl)
    print('total %.0fs' % (time.time() - t0), flush=True)
    if r:
        body, ph, T = r
        pickle.dump((body, ph), open('cpfg_drive_c%d_w%d_s%d.pkl' % (cap, W, slack), 'wb'))
        import cpfg_eval as E
        E.evaluate(body, ph, sv=True)
