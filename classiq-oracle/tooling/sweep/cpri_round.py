"""CP-RI: round-schedule SAT for the logo phase oracle.

R rounds.  Each round, on each side (x: 9 wires, y: 9 wires), up to G RCCX
gates on distinct targets; controls are other wires of the round, read as they
are (polarity by X only, no CX hosting).  Everything a wire holds is allowed
(garbage); nothing is uncomputed inside the stream (the mirror does it).

Terms read out by cz pairs: within round r the x-side vocabulary is
span{wire values at the start of r} + span{products of r}; same on y.
Coverage: for each pair k (u_k, v_k) of the fixed rank decomposition there is
a round rho_k with u_k in the x-vocabulary of rho_k and v_k in the y one.

usage: cpri_round.py R [timeout_s] [G] [tag]
"""
import sys, time, multiprocessing as mp
from pysat.formula import IDPool
from pysat.card import CardEnc, EncType
from pysat.solvers import Cadical153

from cph_terms import x_side, y_side, PAIRS, ev, bit
from cpri_io import out_path as _out

NW = 9          # wires per side: 6 data + 3 ancilla
ALL64 = (1 << 64) - 1


def _worker(cl, q):
    s = Cadical153(bootstrap_with=cl)
    q.put(s.get_model() if s.solve() else None)


def solve(cl, timeout):
    q = mp.Queue(); pr = mp.Process(target=_worker, args=(cl, q)); pr.start()
    try:
        res = q.get(timeout=timeout)
    except Exception:
        res = 'timeout'
    if pr.is_alive():
        pr.terminate()
    pr.join()
    return res


class Enc:
    def __init__(self):
        self.pool = IDPool(); self.cl = []
        self.T = self.v('true'); self.cl.append([self.T])

    def v(self, *a):
        return self.pool.id(a)

    def const(self, b):
        return self.T if b else -self.T

    def xor2(self, a, b, key):
        n = self.v('xor', key)
        self.cl.extend([[-n, a, b], [-n, -a, -b], [n, -a, b], [n, a, -b]])
        return n

    def and2(self, a, b, key):
        n = self.v('and', key)
        self.cl.extend([[-n, a], [-n, b], [n, -a, -b]])
        return n

    def exactly_one(self, lits):
        self.cl.append(list(lits))
        for i in range(len(lits)):
            for j in range(i + 1, len(lits)):
                self.cl.append([-lits[i], -lits[j]])

    def atmost(self, lits, bound):
        cnf = CardEnc.atmost(lits=lits, bound=bound, top_id=self.pool.top, encoding=EncType.seqcounter)
        self.cl.extend(cnf.clauses)
        if cnf.nv > self.pool.top:
            self.pool.occupy(self.pool.top + 1, cnf.nv)

    def xor_chain(self, lits, key):
        cur = lits[0]
        for j, l in enumerate(lits[1:]):
            cur = self.xor2(cur, l, (key, j))
        return cur


def encode(R, G, pairs, xinit, yinit, e, maxsel=3, L=0, only=None):
    """pairs: list of (u_table, v_table); xinit/yinit: list of 9 init tables.
    L: CX gates per round per side, applied before the RCCX's (permanent).
    only: 'x' or 'y' -> encode that side only (other side's tables ignored)."""
    sides = {}
    for side, init in (('x', xinit), ('y', yinit)):
        if only and side != only:
            continue
        W = {}                                  # W[r][w] -> 64 literals
        for w in range(NW):
            W[(0, w)] = [e.const((init[w] >> i) & 1) for i in range(64)]
        P = {}
        act = {}
        for r in range(R):
            # linear gates: CX(src -> dst), distinct dsts, sources read the
            # round-start values; W becomes the post-CX state used below
            if L:
                lsrc = {}; ldst = {}; lact = {}
                for l in range(L):
                    lact[l] = e.v(side, 'lact', r, l)
                    lsrc[l] = [e.v(side, 'lsrc', r, l, w) for w in range(NW)]
                    ldst[l] = [e.v(side, 'ldst', r, l, w) for w in range(NW)]
                    e.exactly_one(lsrc[l]); e.exactly_one(ldst[l])
                    for w in range(NW):
                        e.cl.append([-lsrc[l][w], -ldst[l][w]])
                        for l2 in range(l):
                            e.cl.append([-lact[l], -ldst[l][w], -ldst[l2][w]])
                    if l:
                        e.cl.append([-lact[l], lact[l - 1]])
                Wn = {}
                for w in range(NW):
                    Wn[w] = []
                    for i in range(64):
                        adds = []
                        for l in range(L):
                            S = e.v(side, 'LS', r, l, i)
                            if w == 0:
                                for w2 in range(NW):
                                    e.cl.append([-lsrc[l][w2], -S, W[(r, w2)][i]])
                                    e.cl.append([-lsrc[l][w2], S, -W[(r, w2)][i]])
                            h = e.v(side, 'LH', r, l, w, i)
                            e.cl.extend([[-h, lact[l]], [-h, ldst[l][w]], [-h, S], [h, -lact[l], -ldst[l][w], -S]])
                            adds.append(h)
                        flip = e.v(side, 'lflip', r, w, i)
                        e.cl.append([-flip] + adds)
                        for h in adds:
                            e.cl.append([flip, -h])
                        Wn[w].append(e.xor2(W[(r, w)][i], flip, (side, 'WL', r, w, i)))
                for w in range(NW):
                    W[(r, w)] = Wn[w]
            tg = {}; ca = {}; cb = {}; pa = {}; pb = {}
            for g in range(G):
                act[(r, g)] = e.v(side, 'act', r, g)
                tg[g] = [e.v(side, 't', r, g, w) for w in range(NW)]
                ca[g] = [e.v(side, 'a', r, g, w) for w in range(NW)]
                cb[g] = [e.v(side, 'b', r, g, w) for w in range(NW)]
                pa[g] = e.v(side, 'pa', r, g); pb[g] = e.v(side, 'pb', r, g)
                e.exactly_one(tg[g]); e.exactly_one(ca[g]); e.exactly_one(cb[g])
            for g in range(G):
                # controls differ from every target of the round, a < b
                for w in range(NW):
                    for g2 in range(G):
                        e.cl.append([-act[(r, g2)], -ca[g][w], -tg[g2][w]])
                        e.cl.append([-act[(r, g2)], -cb[g][w], -tg[g2][w]])
                for w1 in range(NW):
                    for w2 in range(w1 + 1):
                        e.cl.append([-ca[g][w1], -cb[g][w2]])
                # targets distinct and increasing; inactive gates last
                if g > 0:
                    for w1 in range(NW):
                        for w2 in range(w1 + 1):
                            e.cl.append([-act[(r, g)], -tg[g - 1][w1], -tg[g][w2]])
                    e.cl.append([-act[(r, g)], act[(r, g - 1)]])
            # products
            for g in range(G):
                P[(r, g)] = []
                for i in range(64):
                    A = e.v(side, 'A', r, g, i); B = e.v(side, 'B', r, g, i)
                    for w in range(NW):
                        e.cl.append([-ca[g][w], -A, W[(r, w)][i]])
                        e.cl.append([-ca[g][w], A, -W[(r, w)][i]])
                        e.cl.append([-cb[g][w], -B, W[(r, w)][i]])
                        e.cl.append([-cb[g][w], B, -W[(r, w)][i]])
                    Ap = e.xor2(A, pa[g], (side, 'Ap', r, g, i))
                    Bp = e.xor2(B, pb[g], (side, 'Bp', r, g, i))
                    p = e.v(side, 'P', r, g, i)
                    e.cl.extend([[-p, Ap], [-p, Bp], [-p, act[(r, g)]],
                                 [p, -Ap, -Bp, -act[(r, g)]]])
                    P[(r, g)].append(p)
            # state update
            for w in range(NW):
                W[(r + 1, w)] = []
                for i in range(64):
                    hits = [e.and2(tg[g][w], P[(r, g)][i], (side, 'hit', r, g, w, i))
                            for g in range(G)]
                    flip = e.v(side, 'flip', r, w, i)
                    e.cl.append([-flip] + hits)
                    for h in hits:
                        e.cl.append([flip, -h])
                    W[(r + 1, w)].append(e.xor2(W[(r, w)][i], flip, (side, 'W', r + 1, w, i)))
        sides[side] = (W, P, act)
    # coverage with shared round assignment
    rho = {}
    for k, (u, vv) in enumerate(pairs):
        rho[k] = [e.v('rho', k, r) for r in range(R)]
        e.exactly_one(rho[k])
        for side, tab in (('x', u), ('y', vv)):
            if side not in sides:
                continue
            W, P, act = sides[side]
            sel = {}
            for r in range(R):
                for w in range(NW):
                    sel[(r, 'w', w)] = e.v(side, 'sel', k, r, 'w', w)
                    e.cl.append([-sel[(r, 'w', w)], rho[k][r]])
                for g in range(G):
                    sel[(r, 'g', g)] = e.v(side, 'sel', k, r, 'g', g)
                    e.cl.append([-sel[(r, 'g', g)], rho[k][r]])
                    e.cl.append([-sel[(r, 'g', g)], act[(r, g)]])
            e.atmost(list(sel.values()), maxsel)
            for i in range(64):
                terms = []
                for r in range(R):
                    for w in range(NW):
                        terms.append(e.and2(sel[(r, 'w', w)], W[(r, w)][i], (side, 'ct', k, r, w, i)))
                    for g in range(G):
                        terms.append(e.and2(sel[(r, 'g', g)], P[(r, g)][i], (side, 'cg', k, r, g, i)))
                out = e.xor_chain(terms, (side, 'cov', k, i))
                e.cl.append([out] if (tab >> i) & 1 else [-out])
    return sides, rho


def decode(model, R, G, e, L=0, only=None):
    m = set(l for l in model if l > 0)
    sched = {}
    for side in ('x', 'y'):
        if only and side != only:
            sched[side] = [[] for _ in range(R)]; sched[side + 'lin'] = [[] for _ in range(R)]
            continue
        gates = []; lins = []
        for r in range(R):
            lrow = []
            for l in range(L):
                if e.v(side, 'lact', r, l) not in m:
                    continue
                s_ = [w for w in range(NW) if e.v(side, 'lsrc', r, l, w) in m][0]
                d_ = [w for w in range(NW) if e.v(side, 'ldst', r, l, w) in m][0]
                lrow.append((s_, d_))
            lins.append(lrow)
            row = []
            for g in range(G):
                if e.v(side, 'act', r, g) not in m:
                    continue
                t = [w for w in range(NW) if e.v(side, 't', r, g, w) in m][0]
                a = [w for w in range(NW) if e.v(side, 'a', r, g, w) in m][0]
                b = [w for w in range(NW) if e.v(side, 'b', r, g, w) in m][0]
                row.append((a, e.v(side, 'pa', r, g) in m, b, e.v(side, 'pb', r, g) in m, t))
            gates.append(row)
        sched[side] = gates; sched[side + 'lin'] = lins
    return sched


def simulate(init, gates, lins=None):
    """returns list of (start-state, products) per round; states are tables.
    start-state = after that round's CX gates."""
    st = list(init); rounds = []
    for ri, row in enumerate(gates):
        if lins:
            for s_, d_ in lins[ri]:
                st[d_] ^= st[s_]
        prods = []
        start = list(st)
        for a, pa, b, pb, t in row:
            p = (st[a] ^ (ALL64 if pa else 0)) & (st[b] ^ (ALL64 if pb else 0))
            prods.append(p)
        for (a, pa, b, pb, t), p in zip(row, prods):
            st[t] ^= p
        rounds.append((start, prods))
    return rounds


def in_span(vecs, target):
    basis = {}
    for v in vecs:
        for hb in sorted(basis, reverse=True):
            if (v >> hb) & 1:
                v ^= basis[hb]
        if v:
            basis[v.bit_length() - 1] = v
    for hb in sorted(basis, reverse=True):
        if (target >> hb) & 1:
            target ^= basis[hb]
    return target == 0


def check(sched, pairs, xinit, yinit):
    rx = simulate(xinit, sched['x'], sched.get('xlin')); ry = simulate(yinit, sched['y'], sched.get('ylin'))
    ok = True
    for k, (u, vv) in enumerate(pairs):
        found = [r for r in range(len(rx))
                 if in_span(rx[r][0] + rx[r][1], u) and in_span(ry[r][0] + ry[r][1], vv)]
        if not found:
            ok = False
        print('  pair', k, 'rounds', found)
    return ok


def logo_pairs():
    FX, _ = x_side(); FY, _ = y_side()
    return [(ev(FX, xe), ev(FY, ye)) for xe, ye in PAIRS]


def init_tables():
    return [bit(k) for k in range(6)] + [0, 0, 0]


def main():
    R = int(sys.argv[1]); timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 600
    G = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    tag = sys.argv[4] if len(sys.argv) > 4 else ''
    maxsel = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    pairs = logo_pairs(); xinit = init_tables(); yinit = init_tables()
    e = Enc(); t0 = time.time()
    encode(R, G, pairs, xinit, yinit, e, maxsel=maxsel)
    print(f'R={R} G={G} maxsel={maxsel} vars={e.pool.top} clauses={len(e.cl)} enc {time.time()-t0:.1f}s', flush=True)
    t0 = time.time(); res = solve(e.cl, timeout)
    print(f'solve {time.time()-t0:.1f}s ->', 'timeout' if res == 'timeout' else ('UNSAT' if res is None else 'SAT'), flush=True)
    if res not in (None, 'timeout'):
        sched = decode(res, R, G, e)
        for side in ('x', 'y'):
            print(side, sched[side])
        print('check', check(sched, pairs, xinit, yinit))
        import pickle
        pickle.dump(sched, open(_out(f'cpri_sched_R{R}{tag}.pkl'), 'wb'))


if __name__ == '__main__':
    main()
