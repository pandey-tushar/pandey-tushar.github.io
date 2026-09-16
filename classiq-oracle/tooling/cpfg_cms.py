"""CP-FG window model, solver-agnostic build (CryptoMiniSat with native XOR, or
CP-SAT), same semantics as cpfg_window.build_window."""
import sys, time, collections
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfg_model as M
from cpfg_step import in_span, MASK69
from pysat.card import CardEnc, EncType

N, TERMS, NN, NW, BITS = M.N, M.TERMS, M.NN, M.NW, M.BITS
dur = M.dur
RAW = [1 << w if w < 12 else 0 for w in range(NW)]


def _child_solve(clauses, q):
    from pysat.solvers import Solver as PS
    s = PS(name='cadical195', bootstrap_with=clauses)
    r = s.solve()
    q.put((r, s.get_model() if r else None))
    s.delete()


class CMS:
    """clause/xor sink for pycryptosat; literals are nonzero ints."""
    def __init__(self):
        self.n = 1; self.cl = []; self.xr = []
        self.T = 1                     # var 1 is TRUE
        self.cl.append([1])
    def new(self):
        self.n += 1; return self.n
    def const(self, b): return self.T if b else -self.T
    def clause(self, lits): self.cl.append(list(lits))
    def xor(self, lits, rhs):          # XOR(lits) == rhs
        # pycryptosat xor clauses take positive vars; fold signs into rhs
        vs = []
        for l in lits:
            if l < 0: rhs = not rhs; vs.append(-l)
            else: vs.append(l)
        # keep xors short: chain with auxiliaries (long xors blow up inside CMS)
        while len(vs) > 3:
            a = self.new()
            self.xr.append(([vs[0], vs[1], a], False))     # a = vs0 ^ vs1
            vs = [a] + vs[2:]
        self.xr.append((vs, bool(rhs)))
    def imp(self, a, b): self.clause([-a, b])
    def xor_cnf(self, lits, rhs):      # XOR(lits) == rhs as plain clauses (no Gauss matrices)
        vs = list(lits)
        while len(vs) > 3:
            a = self.new()
            self._xor3_cnf([vs[0], vs[1], -a])           # a = vs0 ^ vs1
            vs = [a] + vs[2:]
        if not rhs: vs[0] = -vs[0]                       # XOR(vs)==False  <=>  XOR(-vs0, ...) == True
        self._xor3_cnf(vs)
    def _xor3_cnf(self, vs):            # XOR(vs) == True, len(vs) <= 3
        import itertools
        n = len(vs)
        for signs in itertools.product([1, -1], repeat=n):
            # forbid assignments with even parity of true literals
            if sum(1 for sg in signs if sg == 1) % 2 == 0:
                self.clause([-sg * v for sg, v in zip(signs, vs)])
    def atmost(self, lits, k):
        lits = [l for l in lits if l != -self.T]
        if k < 0: self.clause([-self.T]); return
        if len(lits) <= k: return
        if k == 1:
            for i in range(len(lits)):
                for j in range(i + 1, len(lits)): self.clause([-lits[i], -lits[j]])
            return
        enc = CardEnc.atmost(lits=lits, bound=k, top_id=self.n, encoding=EncType.seqcounter)
        self.n = max(self.n, enc.nv)
        for c in enc.clauses: self.clause(c)
    def atleast(self, lits, k):
        if k <= 0: return
        enc = CardEnc.atleast(lits=lits, bound=k, top_id=self.n, encoding=EncType.seqcounter)
        self.n = max(self.n, enc.nv)
        for cl in enc.clauses: self.clause(cl)
    def exactly_one(self, lits):
        self.clause(lits); self.atmost(lits, 1)
    def equal(self, a, b): self.clause([-a, b]); self.clause([a, -b])
    def solve(self, threads=4, tlimit=300, backend='cadical'):
        if backend == 'cms':
            import pycryptosat
            s = pycryptosat.Solver(threads=threads, time_limit=tlimit)
            for c in self.cl: s.add_clause(c)
            for vs, rhs in self.xr: s.add_xor_clause(vs, rhs)
            sat, sol = s.solve()
            return sat, sol
        # CaDiCaL (pysat) in a child process; hard wall-clock kill = the interrupt
        import multiprocessing as mp
        ncl = len(self.cl)
        for vs, rhs in self.xr: self.xor_cnf(vs, rhs)
        extra = self.cl[ncl:]; del self.cl[ncl:]
        ctx = mp.get_context('fork')
        q = ctx.Queue()
        p = ctx.Process(target=_child_solve, args=(self.cl + extra, q))
        p.start()
        try:
            r, model = q.get(timeout=tlimit)
        except Exception:
            p.terminate(); p.join()
            return None, None
        p.join()
        if not r: return False, None
        sol = [False] * (self.n + 1)
        for lit in model:
            if lit > 0 and lit <= self.n: sol[lit] = True
        return True, sol


def build(cont0, nodes, Tw, L=2, readers=3, nogoods=(), pending=None, final_terms=None, cxmax=None):
    pending = pending or {}
    m = CMS(); B = m.new
    cl = [[[[None] * BITS for w in range(NW)] for l in range(L + 1)] for t in range(Tw + 1)]
    for w in range(NW):
        for b in range(BITS): cl[0][0][w][b] = m.const((cont0[w] >> b) & 1)
    cx = {}; xf = {}
    lock0 = set()
    for k, (tw, rs) in pending.items(): lock0.add(tw); lock0.update(rs)
    for t in range(Tw + 1):
        if t > 0:
            for w in range(NW):
                for b in range(BITS): cl[t][0][w][b] = B()
        for l in range(1, L + 1):
            for w in range(NW):
                for b in range(BITS): cl[t][l][w][b] = B()
            for s in range(NW):
                for w in range(NW):
                    if s != w:
                        cx[t, l, s, w] = B()
                        if t == 0 and (s in lock0 or w in lock0): m.clause([-cx[t, l, s, w]])
            for w in range(NW):
                xf[t, l, w] = B()
                if t == 0 and w in lock0: m.clause([-xf[t, l, w]])
                inb = [cx[t, l, s, w] for s in range(NW) if s != w]
                outb = [cx[t, l, w, d] for d in range(NW) if d != w]
                m.atmost(inb + outb, 1)
                has = B()
                for v in inb: m.imp(v, has)
                m.clause([-has] + inb)
                for b in range(BITS):
                    inc = B(); m.imp(inc, has)
                    for s in range(NW):
                        if s == w: continue
                        m.clause([-cx[t, l, s, w], -inc, cl[t][l - 1][s][b]])
                        m.clause([-cx[t, l, s, w], inc, -cl[t][l - 1][s][b]])
                    lits = [cl[t][l - 1][w][b], inc, cl[t][l][w][b]]
                    if b == 69: lits.append(xf[t, l, w])
                    m.xor(lits, False)
    fire = {}; tgt = {}; rd = {}; ft = {}; rdt = {}; skip = {}
    for k, (e, lst, optional) in nodes.items():
        ts = list(range(max(0, e), min(Tw - dur[k], lst) + 1))
        if not ts:
            if optional: continue
            return None
        for t in ts: fire[k, t] = B()
        skip[k] = B()
        if not optional: m.clause([-skip[k]])
        m.exactly_one([fire[k, t] for t in ts] + [skip[k]])
        for w in range(NW):
            tgt[k, w] = B()
            for i in range(len(N[k])): rd[k, i, w] = B()
        m.exactly_one([tgt[k, w] for w in range(NW)] + [skip[k]])
        for i in range(len(N[k])): m.exactly_one([rd[k, i, w] for w in range(NW)] + [skip[k]])
        for w in range(NW): m.atmost([tgt[k, w]] + [rd[k, i, w] for i in range(len(N[k]))], 1)
        for t in ts:
            for w in range(NW):
                v = B(); ft[k, t, w] = v
                m.imp(v, fire[k, t]); m.imp(v, tgt[k, w]); m.clause([-fire[k, t], -tgt[k, w], v])
                for i in range(len(N[k])):
                    r = B(); rdt[k, i, t, w] = r
                    m.imp(r, fire[k, t]); m.imp(r, rd[k, i, w]); m.clause([-fire[k, t], -rd[k, i, w], r])
    pres = {}
    def P(o, w, t):
        key = (o, w, t)
        if key not in pres:
            v = B(); pres[key] = v
            for b in range(BITS):
                m.imp(v, cl[t][L][w][b] if (o >> b) & 1 else -cl[t][L][w][b])
        return pres[key]
    for t in range(Tw):
        for w in range(NW):
            tl = [ft[k, t, w] for k in nodes if (k, t, w) in ft]
            tl += [ft[k, t - 1, w] for k in nodes if dur[k] == 2 and (k, t - 1, w) in ft]
            if t == 0 and w in lock0: tl.append(m.const(1))
            m.atmost(tl, 1)
            occ = B()
            for v in tl: m.imp(v, occ)
            m.clause([-occ] + tl) if tl else m.clause([-occ])
            rl = [rdt[k, i, t, w] for k in nodes for i in range(len(N[k])) if (k, i, t, w) in rdt]
            rl += [rdt[k, i, t - 1, w] for k in nodes if dur[k] == 2 for i in range(3) if (k, i, t - 1, w) in rdt]
            m.atmost(rl, readers)
            for r in rl: m.imp(r, -occ)
    pw = {}
    if final_terms:
        for p, term in enumerate(final_terms):
            for i, o in enumerate(term):
                for w in range(NW):
                    pw[p, i, w] = B(); m.imp(pw[p, i, w], P(o, w, Tw))
                m.exactly_one([pw[p, i, w] for w in range(NW)])
            for w in range(NW): m.atmost([pw[p, i, w] for i in range(len(term))], 1)
    part = collections.defaultdict(list)
    for (k, i, t, w), r in rdt.items(): part[t, w].append(r)
    for (k, t, w), v in ft.items(): part[t, w].append(v)
    for (p, i, w), v in pw.items(): part[Tw, w].append(v)
    for t in range(Tw + 1):
        for w in range(NW):
            lits = part.get((t, w), [])
            for l in range(1, L + 1):
                for s in range(NW):
                    if s != w: m.clause([-cx[t, l, s, w]] + lits)
                m.clause([-xf[t, l, w]] + lits)
    for (k, i, t, w), r in rdt.items():
        m.imp(r, P(N[k][i], w, t))
        if dur[k] == 2: m.imp(r, P(N[k][i], w, t + 1))
    for (k, t, w), v in ft.items():
        if dur[k] == 2:
            for l in range(1, L + 1):
                m.imp(v, -xf[t + 1, l, w])
                for s in range(NW):
                    if s != w: m.imp(v, -cx[t + 1, l, s, w]); m.imp(v, -cx[t + 1, l, w, s])
    for t in range(Tw):
        for w in range(NW):
            for b in range(BITS):
                new, old = cl[t + 1][0][w][b], cl[t][L][w][b]
                if 12 <= b < 12 + NN:
                    k = b - 12
                    if k in pending and t == 0 and pending[k][0] == w:
                        m.equal(new, -old); continue
                    if k in nodes:
                        tf = t if dur[k] == 1 else t - 1
                        if (k, tf, w) in ft:
                            m.xor([old, ft[k, tf, w], new], False); continue
                m.equal(new, old)
    for ng in nogoods:
        m.clause([-tgt[k, w] for (k, w) in ng if (k, w) in tgt])
    if cxmax is not None: m.atmost(list(cx.values()), cxmax)
    return m, dict(cl=cl, cx=cx, xf=xf, fire=fire, tgt=tgt, rd=rd, pw=pw, skip=skip, Tw=Tw, L=L, nodes=nodes)


class Sol:
    def __init__(self, sol): self.s = sol
    def Value(self, lit): return int(self.s[lit]) if lit > 0 else int(not self.s[-lit])


def solve_window(cont, nodes, Tw, L=2, tlimit=300, nogoods=(), pending=None, final_terms=None, cxmax=None, threads=4):
    r = build(cont, nodes, Tw, L=L, nogoods=nogoods, pending=pending, final_terms=final_terms, cxmax=cxmax)
    if r is None: return None, 'none'
    m, V = r
    t0 = time.time(); sat, sol = m.solve(threads=threads, tlimit=tlimit)
    if sat is None: return None, 'timeout %.0fs' % (time.time() - t0)
    if not sat: return None, 'UNSAT %.1fs' % (time.time() - t0)
    return (Sol(sol), V), 'SAT %.1fs vars %d clauses %d xors %d' % (time.time() - t0, m.n, len(m.cl), len(m.xr))


if __name__ == '__main__':
    # smoke test: the same bisection cases
    center, T = M.list_schedule(6)
    lvl0 = [k for k in range(57) if not M.preds[k]]
    ccx0 = [k for k in lvl0 if dur[k] == 1]
    for name, nodes, Tw in [('6 ccx Tw=1', {k: (0, 0, False) for k in ccx0[:6]}, 1),
                            ('12 ccx Tw=3 free', {k: (0, 2, False) for k in ccx0[:12]}, 3),
                            ('lvl0 18 Tw=4', {k: (0, 4 - dur[k], False) for k in lvl0}, 4)]:
        r, msg = solve_window(list(RAW), nodes, Tw, tlimit=120, threads=2)
        print(name, '->', msg, flush=True)
