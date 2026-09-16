"""CP-FG assembly-based window model (CryptoMiniSat).  Contents change only by
(a) an ASSEMBLY on a wire that is read this step: XOR in 1-2 source wires
(start-of-step contents), optionally undone after the Toffolis, (b) free X on
the const bit, (c) a node bit landing on a Toffoli target.  No free CX layers."""
import sys, time, collections
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfg_model as M
from cpfg_cms import CMS, Sol
from cpfg_step import in_span, MASK69

N, TERMS, NN, NW, BITS = M.N, M.TERMS, M.NN, M.NW, M.BITS
dur = M.dur
RAW = [1 << w if w < 12 else 0 for w in range(NW)]


def nid(k): return k[1] if isinstance(k, tuple) else k


def build(cont0, nodes, Tw, readers=3, nogoods=(), pending=None, final_terms=None, cxmax=None, allow_undo=True, span_ops=(), done_nodes=(), min_free=0, fire_steps=(), nsrc=2, n_remaining=10**6, span_at=None, min_fire0=0):
    pending = pending or {}
    m = CMS(); B = m.new
    T1 = Tw + 1                       # step Tw is the phase-assembly step (no Toffolis)
    c = [[[None] * BITS for w in range(NW)] for t in range(T1 + 1)]     # start-of-step contents
    r = [[[None] * BITS for w in range(NW)] for t in range(T1)]         # read view (after assembly)
    for w in range(NW):
        for b in range(BITS): c[0][w][b] = m.const((cont0[w] >> b) & 1)
    for t in range(1, T1 + 1):
        for w in range(NW):
            for b in range(BITS): c[t][w][b] = B()
    lock0 = set()
    for k, (tw, rs) in pending.items(): lock0.add(tw); lock0.update(rs)
    asm = {}; sel = {}; undo = {}; xf = {}; cxlits = []; cs = {}
    for t in range(T1):
        for w in range(NW):
            asm[t, w] = B(); undo[t, w] = B(); xf[t, w] = B()
            if t == 0 and w in lock0: m.clause([-asm[t, w]]); m.clause([-xf[t, w]])
            cs[t, w] = B(); m.xor([c[t][w][69], xf[t, w], cs[t, w]], False)
    for t in range(T1):
        for w in range(NW):
            S = [[B() for s in range(NW)] for j in range(nsrc)]
            def SB(s, b): return cs[t, s] if b == 69 else c[t][s][b]
            for j in range(nsrc):
                for s in range(NW):
                    sel[t, w, j, s] = S[j][s]
                    if s == w or (t == 0 and s in lock0): m.clause([-S[j][s]])
                    for j2 in range(j): m.clause([-S[j][s], -S[j2][s]])     # distinct sources
                    m.imp(S[j][s], asm[t, w]); cxlits.append(S[j][s])
                m.atmost(S[j], 1)
            m.clause([-asm[t, w]] + S[0])                    # asm -> some source 0
            m.clause([-undo[t, w], asm[t, w]])
            if not allow_undo: m.clause([-undo[t, w]])
            for b in range(BITS):
                Sb = []
                for j in range(nsrc):
                    sb = B(); Sb.append(sb)
                    for s in range(NW):
                        if s == w: continue
                        m.clause([-S[j][s], -sb, SB(s, b)]); m.clause([-S[j][s], sb, -SB(s, b)])
                    m.clause([-sb] + [S[j][s] for s in range(NW) if s != w])
                D = B(); m.xor(Sb + [D], False)                 # D = XOR of source bits
                rv = B()
                lits = [c[t][w][b], D, rv]
                if b == 69: lits.append(xf[t, w])
                m.xor(lits, False)                              # r = c ^ D (^ xf)
                K = B(); m.clause([-K, D]); m.clause([-K, undo[t, w]]); m.clause([K, -D, -undo[t, w]])
                r[t][w][b] = (rv, K)
    # source wires are not assembly targets in the same step (CX layer semantics)
    for t in range(T1):
        for w in range(NW):
            for s in range(NW):
                if s != w:
                    for j in range(nsrc): m.imp(sel[t, w, j, s], -asm[t, s])
    def RV(t, w, b): return r[t][w][b][0]
    fire = {}; tgt = {}; rd = {}; ft = {}; rdt = {}; skip = {}
    for k, (e, lst, optional) in nodes.items():
        n_ = nid(k)
        ts = list(range(max(0, e), min(Tw - dur[n_], lst) + 1))
        if not ts:
            if optional: continue
            return None
        for t in ts: fire[k, t] = B()
        skip[k] = B()
        if not optional: m.clause([-skip[k]])
        m.exactly_one([fire[k, t] for t in ts] + [skip[k]])
        for w in range(NW):
            tgt[k, w] = B()
            for i in range(len(N[n_])): rd[k, i, w] = B()
        m.exactly_one([tgt[k, w] for w in range(NW)] + [skip[k]])
        for i in range(len(N[n_])): m.exactly_one([rd[k, i, w] for w in range(NW)] + [skip[k]])
        for w in range(NW): m.atmost([tgt[k, w]] + [rd[k, i, w] for i in range(len(N[n_]))], 1)
        for t in ts:
            for w in range(NW):
                v = B(); ft[k, t, w] = v
                m.imp(v, fire[k, t]); m.imp(v, tgt[k, w]); m.clause([-fire[k, t], -tgt[k, w], v])
                if isinstance(k, tuple):            # uncompute: target must hold the bit
                    m.imp(v, RV(t, w, 12 + n_))
                for i in range(len(N[n_])):
                    rr = B(); rdt[k, i, t, w] = rr
                    m.imp(rr, fire[k, t]); m.imp(rr, rd[k, i, w]); m.clause([-fire[k, t], -rd[k, i, w], rr])
    pres = {}
    def P(o, w, t):
        key = (o, w, t)
        if key not in pres:
            v = B(); pres[key] = v
            for b in range(BITS): m.imp(v, RV(t, w, b) if (o >> b) & 1 else -RV(t, w, b))
        return pres[key]
    pw = {}
    if final_terms:
        for p, term in enumerate(final_terms):
            for i, o in enumerate(term):
                for w in range(NW):
                    pw[p, i, w] = B(); m.imp(pw[p, i, w], P(o, w, Tw))
                m.exactly_one([pw[p, i, w] for w in range(NW)])
            for w in range(NW): m.atmost([pw[p, i, w] for i in range(len(term))], 1)
    # participation: assembly / x only on a wire read this step
    part = collections.defaultdict(list)
    for (k, i, t, w), rr in rdt.items(): part[t, w].append(rr)
    for (p, i, w), v in pw.items(): part[Tw, w].append(v)
    for t in range(T1):
        for w in range(NW):
            m.clause([-asm[t, w]] + part.get((t, w), []))
            m.clause([-xf[t, w]] + part.get((t, w), []))
    # occupancy / reads
    for t in range(Tw):
        for w in range(NW):
            tl = [ft[k, t, w] for k in nodes if (k, t, w) in ft]
            tl += [ft[k, t - 1, w] for k in nodes if dur[nid(k)] == 2 and (k, t - 1, w) in ft]
            if t == 0 and w in lock0: tl.append(m.const(1))
            m.atmost(tl, 1)
            occ = B()
            for v in tl: m.imp(v, occ)
            m.clause([-occ] + tl) if tl else m.clause([-occ])
            rl = [rdt[k, i, t, w] for k in nodes for i in range(len(N[nid(k)])) if (k, i, t, w) in rdt]
            rl += [rdt[k, i, t - 1, w] for k in nodes if dur[nid(k)] == 2 for i in range(3) if (k, i, t - 1, w) in rdt]
            m.atmost(rl, readers)
            for rr in rl: m.imp(rr, -occ)
            m.imp(occ, -asm[t, w])                      # a target wire is not assembled this step
            for w2 in range(NW):                        # ... nor used as an assembly source (undo reads it after the Toffoli)
                if w2 != w:
                    for j in range(nsrc): m.imp(occ, -sel[t, w2, j, w])
    for (k, i, t, w), rr in rdt.items():
        m.imp(rr, P(N[nid(k)][i], w, t))
        if dur[nid(k)] == 2: m.imp(rr, P(N[nid(k)][i], w, t + 1))
    for (k, t, w), v in ft.items():
        if dur[nid(k)] == 2:
            m.imp(v, -asm[t + 1, w]); m.imp(v, -xf[t + 1, w])
            for s in range(NW):
                if s != w:
                    for j in range(nsrc): m.imp(v, -sel[t + 1, s, j, w])
    # step boundary: c[t+1] = r ^ K ^ nodebits
    for t in range(T1):
        for w in range(NW):
            for b in range(BITS):
                rv, K = r[t][w][b]; new = c[t + 1][w][b]
                lits = [rv, K, new]
                if 12 <= b < 12 + NN and t < Tw:
                    k = b - 12
                    if k in pending and t == 0 and pending[k][0] == w:
                        lits.append(m.const(1))
                    else:
                        tf = t if dur[k] == 1 else t - 1
                        if (k, tf, w) in ft: lits.append(ft[k, tf, w])
                        if (('u', k), tf, w) in ft: lits.append(ft[('u', k), tf, w])
                m.xor(lits, False)
    # SPAN INVARIANT: every future operand form must be a GF(2) combination of
    # the final contents (69 bits; const is free).  lambda_w per operand.
    done_nodes = set(done_nodes)
    for t_at in (span_at if span_at is not None else (T1,)):
        fin = c[t_at]
        # node bits landing exactly at/after t_at are not yet present: a bit of an
        # in-window node exists at c[t_at] iff it fired at a step < t_at (ccx) / < t_at-1 (c3x)
        for o in sorted(set(x & MASK69 for x in span_ops)):
            lam = [B() for w in range(NW)]
            for b in range(69):
                terms = []
                for w in range(NW):
                    a_ = B(); terms.append(a_)
                    m.clause([-a_, lam[w]]); m.clause([-a_, fin[w][b]]); m.clause([a_, -lam[w], -fin[w][b]])
                want = (o >> b) & 1
                if 12 <= b < 12 + NN and want:
                    k = b - 12
                    if k in skip:
                        early = [fire[k, t] for t in range(t_at - dur[k] + 1) if (k, t) in fire]
                        pres_k = B()
                        for f_ in early: m.imp(f_, pres_k)
                        m.clause([-pres_k] + early)
                        m.xor_cnf(terms + [pres_k], False); continue
                    if k not in done_nodes:
                        want = 0
                m.xor_cnf(terms, bool(want))
    fin = c[T1]
    # committed-step yield: at least min_fire0 compute nodes fire in step 0
    if min_fire0 > 0:
        lits0 = [fire[k, 0] for (k, t) in fire if t == 0 and not isinstance(k, tuple)]
        if len(lits0) < min_fire0: m.clause([-m.T])
        else: m.atleast(lits0, min_fire0)
    # LOOKAHEAD WITNESS: each listed step must fire at least one compute node,
    # unless every remaining compute node already fired in step 0
    if fire_steps:
        comp = [k for k in nodes if not isinstance(k, tuple)]
        alldone0 = B()
        for k in comp:
            m.imp(alldone0, fire[k, 0] if (k, 0) in fire else -alldone0)
        if len(comp) < n_remaining: m.clause([-alldone0])
        for ts_ in fire_steps:
            lits = [fire[k, t] for (k, t) in fire if t == ts_ and not isinstance(k, tuple)]
            m.clause(lits + [alldone0])
    # DEADLOCK GUARD: at least min_free wires must end REDUNDANT (content in the
    # span of the other 17 wires), so the next window has somewhere to fire.
    if min_free > 0:
        red = []
        for w in range(NW):
            rw = B(); red.append(rw)
            lam = {v: B() for v in range(NW) if v != w}
            for b in range(69):
                terms = []
                for v in range(NW):
                    if v == w: continue
                    x = B(); terms.append(x)
                    m.clause([-x, lam[v]]); m.clause([-x, fin[v][b]]); m.clause([x, -lam[v], -fin[v][b]])
                e = B()
                m.xor_cnf(terms + [fin[w][b], e], False)      # e = XOR(terms) ^ fin[w][b]
                m.clause([-rw, -e])                             # redundant -> e == 0
        m.atleast(red, min_free)
    for ng in nogoods:
        m.clause([-tgt[k, w] for (k, w) in ng if (k, w) in tgt])
    if cxmax is not None: m.atmost(cxlits + [undo[t, w] for t in range(T1) for w in range(NW)], cxmax)
    return m, dict(c=c, r=r, asm=asm, sel=sel, nsrc=nsrc, undo=undo, xf=xf, fire=fire, tgt=tgt, rd=rd,
                   pw=pw, skip=skip, Tw=Tw, nodes=nodes)


def decode(sol, V, commit=None):
    """emit ops step by step: assemblies (cx), x flips, toffolis, undo cx.
    commit=k: only the first k Toffoli steps are emitted; contents returned
    are those at the start of step k (sliding-window use)."""
    Tw = V['Tw']; body = []; fired = {}
    steps = range(Tw + 1) if commit is None else range(commit)
    for t in steps:
        pre = []; post = []
        for w in range(NW):
            if sol.Value(V['xf'][t, w]): pre.append(('x', w))
        for w in range(NW):
            if sol.Value(V['asm'][t, w]):
                srcs = [s for j in range(V['nsrc']) for s in range(NW) if sol.Value(V['sel'][t, w, j, s])]
                for s in srcs: pre.append(('cx', s, w))
                if sol.Value(V['undo'][t, w]):
                    for s in srcs: post.append(('cx', s, w))
        body += pre
        if t < Tw:
            for k in V['nodes']:
                n_ = nid(k)
                for tt in range(Tw):
                    if (k, tt) in V['fire'] and tt == t and sol.Value(V['fire'][k, tt]):
                        tw = [w for w in range(NW) if sol.Value(V['tgt'][k, w])][0]
                        rs = [[w for w in range(NW) if sol.Value(V['rd'][k, i, w])][0] for i in range(len(N[n_]))]
                        body.append((('ccx' if len(rs) == 2 else 'c3x'),) + tuple(rs) + (tw,))
                        fired[k] = (t, tw, rs)
        body += post
    tc = Tw + 1 if commit is None else commit
    cont = [sum(sol.Value(V['c'][tc][w][b]) << b for b in range(BITS)) for w in range(NW)]
    ph = []
    for p in range(len(TERMS)):
        if (p, 0, 0) in V['pw']:
            ws = [[w for w in range(NW) if sol.Value(V['pw'][p, i, w])][0] for i in range(len(TERMS[p]))]
            ph.append((('cz' if len(ws) == 2 else 'ccz'),) + tuple(ws))
    return body, fired, cont, ph


def solve_window(cont, nodes, Tw, tlimit=300, nogoods=(), pending=None, final_terms=None, cxmax=None, threads=4, allow_undo=True, span_ops=(), done_nodes=(), nsrc=2):
    rr = build(cont, nodes, Tw, nogoods=nogoods, pending=pending, final_terms=final_terms, cxmax=cxmax, allow_undo=allow_undo, span_ops=span_ops, done_nodes=done_nodes, nsrc=nsrc)
    if rr is None: return None, 'none'
    m, V = rr
    t0 = time.time(); sat, sol = m.solve(threads=threads, tlimit=tlimit)
    if sat is None: return None, 'timeout %.0fs' % (time.time() - t0)
    if not sat: return None, 'UNSAT %.1fs' % (time.time() - t0)
    return (Sol(sol), V), 'SAT %.1fs vars %d clauses %d xors %d' % (time.time() - t0, m.n, len(m.cl), len(m.xr))


if __name__ == '__main__':
    lvl0 = [k for k in range(57) if not M.preds[k]]; ccx0 = [k for k in lvl0 if dur[k] == 1]
    for name, nodes, Tw in [('6 ccx Tw=1', {k: (0, 0, False) for k in ccx0[:6]}, 1),
                            ('8 ccx Tw=2', {k: (0, 1, False) for k in ccx0[:8]}, 2),
                            ('8 ccx Tw=4', {k: (0, 3, False) for k in ccx0[:8]}, 4),
                            ('12 ccx Tw=3', {k: (0, 2, False) for k in ccx0[:12]}, 3),
                            ('lvl0 18 Tw=4', {k: (0, 4 - dur[k], False) for k in lvl0}, 4)]:
        res, msg = solve_window(list(RAW), nodes, Tw, tlimit=120, threads=4)
        extra = ''
        if res:
            sol, V = res; body, fired, cont, ph = decode(sol, V)
            # exact replay check
            cc = list(RAW); ok = True
            for op in body:
                if op[0] == 'x': cc[op[1]] ^= 1 << 69
                elif op[0] == 'cx': cc[op[2]] ^= cc[op[1]]
                else:
                    *rs, tw = op[1:]; forms = sorted(cc[q] for q in rs)
                    mt = [k for k in nodes if sorted(N[k]) == forms]
                    if not mt: ok = False
                    else: cc[tw] ^= 1 << (12 + mt[0])
            extra = ' fired %d cx %d replay %s contents-match %s' % (len(fired), sum(1 for o in body if o[0] == 'cx'), ok, cc == cont)
        print(name, '->', msg + extra, flush=True)
