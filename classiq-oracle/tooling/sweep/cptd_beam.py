"""Merge idea, fast heuristic for step 3: randomized beam search over the
cptd_merge3 model (249 value classes and products, 18 wires, rounds of LCX
CX layers + one Toffoli layer, readouts fire when their classes are held),
then one mirror.  Each wire is in at most one gate per layer (no control
fanout), so the emitted circuit is physical.
Score of a state = sum over pending readouts of the relaxed round-distance
(unlimited wires) of their classes.
Usage: python3 cptd_beam.py BEAM EXPAND SEED [NBEST]
Checkpoint: ckpt/beam_<seed>_R<rounds>.pkl (best solution per seed)"""
import os, sys, time, pickle, random
import numpy as np
import cptd_merge3 as M

NW, LCX, CXC = 18, 2, 0.3
HADD = int(os.environ.get('HADD', '1'))   # 1 = additive score, 0 = max-distance
ZW = float(os.environ.get('ZW', '0.1'))   # reward per free (zero) wire


def setup():
    ops, C, vals, prods, reads = M.extract()
    xor, P, pt = M.tables(C, vals, prods)
    rcls = [tuple(C[M.key(v)] for v in vs) for _, vs in reads]
    init = [C[M.key(((np.arange(4096) >> w) & 1).astype(np.uint8))] for w in range(NW)]
    return C, vals, P, pt, xor, reads, rcls, init


class Model:
    def __init__(self):
        (self.C, self.vals, self.P, self.pt, self.xor, self.reads,
         self.rcls, self.init) = setup()
        self.nc = len(self.vals)
        nP = len(self.P)
        # padded control table; pad index nc = sentinel class with distance -1
        self.ctl = np.full((nP, 3), self.nc, dtype=np.int64)
        for j, (cs, _, _) in enumerate(self.P): self.ctl[j, :len(cs)] = cs
        self.tj, self.to = np.nonzero(self.pt >= 0)
        self.tr = self.pt[self.tj, self.to]
        self.co, self.cd = np.nonzero(self.xor >= 0)
        self.cr = self.xor[self.co, self.cd]

    def dist(self, held):
        d = np.full(self.nc + 1, 99.0); d[list(held)] = 0; d[self.nc] = -1
        for _ in range(40):
            old = d.copy()
            cd = d[self.ctl].max(axis=1)
            np.minimum.at(d, self.tr, np.maximum(cd[self.tj], d[self.to]) + 1)
            np.minimum.at(d, self.cr, np.maximum(d[self.co], d[self.cd]) + CXC)
            if np.array_equal(old, d): break
        return d

    def cost(self, held):
        """additive relaxed cost (h_add): partial progress lowers it"""
        d = np.full(self.nc + 1, 999.0); d[list(held)] = 0; d[self.nc] = 0
        for _ in range(60):
            old = d.copy()
            cd = d[self.ctl].sum(axis=1)
            np.minimum.at(d, self.tr, cd[self.tj] + d[self.to] + 1)
            np.minimum.at(d, self.cr, d[self.co] + d[self.cd] + CXC)
            if np.array_equal(old, d): break
        return d

    def score(self, st, pend):
        d = self.cost(set(st)) if HADD else self.dist(set(st))
        z = self.init[NW - 1]          # zero class (ancilla start)
        agg = sum if HADD else max
        return sum(agg(d[c] for c in self.rcls[k]) for k in pend) - ZW * sum(1 for c in st if c == z)


def fire(m, st, pend, s, rds):
    held = set(st)
    for k in list(pend):
        if all(c in held for c in m.rcls[k]):
            pend.discard(k); rds[k] = [s]


def cx_layer(m, st, pend, rng, topk):
    """greedy randomized CX layer; returns (moves, new state)"""
    st = list(st); busy = set(); moves = []
    base = m.score(st, pend)
    while True:
        cands = []
        for tw in range(NW):
            if tw in busy: continue
            for sw in range(NW):
                if sw == tw or sw in busy: continue
                r = m.xor[st[tw], st[sw]]
                if r < 0 or r == st[tw]: continue
                s2 = list(st); s2[tw] = r
                sc = m.score(s2, pend)
                if sc < base: cands.append((sc, sw, tw, r))
        if not cands: return moves, st
        cands.sort(); sc, sw, tw, r = rng.choice(cands[:topk])
        moves.append((sw, tw)); busy |= {sw, tw}; st[tw] = r; base = sc


def tof_layer(m, st, pend, rng, topk, explore):
    st0 = list(st); st = list(st); busy = set(); written = set(); moves = []
    base = m.score(st, pend)
    while True:
        cands = []
        for w in range(NW):
            if w in busy: continue
            for j, (cs, pol, _) in enumerate(m.P):
                r = m.pt[j, st0[w]]
                if r < 0 or r == st0[w]: continue
                cw = []
                for c in cs:
                    ok = [u for u in range(NW) if st0[u] == c and u != w and u not in busy
                          and u not in written and u not in cw]
                    if not ok: break
                    cw.append(ok[0])
                if len(cw) != len(cs): continue
                s2 = list(st); s2[w] = r
                sc = m.score(s2, pend)
                if sc < base or (explore and rng.random() < explore):
                    cands.append((sc, w, j, r, tuple(cw)))
        if not cands: return moves, st
        cands.sort(); sc, w, j, r, cw = rng.choice(cands[:topk])
        moves.append((w, j)); busy |= {w} | set(cw); written.add(w); st[w] = r
        base = min(base, sc)


def run(beam, expand, seed, maxr=24):
    m = Model(); rng = random.Random(seed)
    K = LCX + 1
    start = dict(st=list(m.init), pend=set(range(len(m.rcls))), layers=[], rds={})
    fire(m, start['st'], start['pend'], 0, start['rds'])
    front = [start]
    for R in range(1, maxr + 1):
        nxt = []
        for node in front:
            for _ in range(expand):
                st, pend, rds = list(node['st']), set(node['pend']), dict(node['rds'])
                cxl = []
                for l in range(LCX):
                    mv, st = cx_layer(m, st, pend, rng, 3)
                    cxl.append(mv); fire(m, st, pend, K * (R - 1) + l + 1, rds)
                mv, st = tof_layer(m, st, pend, rng, 3, 0.02)
                fire(m, st, pend, K * R, rds)
                nxt.append(dict(st=st, pend=pend, layers=node['layers'] + [(cxl, mv)], rds=rds,
                                sc=m.score(st, pend)))
        done = [n for n in nxt if not n['pend']]
        if done:
            return R, done, m
        uniq = {}
        for n in sorted(nxt, key=lambda n: (n['sc'], len(n['pend']))):
            uniq.setdefault(tuple(n['st']), n)
        front = list(uniq.values())[:beam]
        print('round %d  best score %.1f  pending %d' % (R, front[0]['sc'], len(front[0]['pend'])), flush=True)
    return None, [], m


def to_sol(n, m):
    rds = [n['rds'][k] for k in range(len(m.rcls))]
    return dict(sol=dict(layers=n['layers'], rds=rds, lcx=LCX),
                P=[(cs, pol) for cs, pol, _ in m.P], vals=m.vals, reads=m.reads)


if __name__ == '__main__':
    import cptd_emit3 as E
    from cpae_core import ops_to_qc, real_depth
    beam, expand, seed = map(int, sys.argv[1:4]); nbest = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    t0 = time.time()
    R, done, m = run(beam, expand, seed)
    print('rounds %s  solutions %d  %.0fs' % (R, len(done), time.time() - t0), flush=True)
    best = None
    for n in done[:nbest]:
        d = to_sol(n, m)
        full, conf = E.emit(d)
        mism, ident = E.classical(full)
        dep = real_depth(ops_to_qc(full))
        print('  emit: conflicts %d  classical mism %d  identity %s  real depth/cx %s' % (conf, mism, ident, dep), flush=True)
        if mism == 0 and ident and (best is None or dep < best[0]):
            best = (dep, d, full)
    if best:
        os.makedirs('ckpt', exist_ok=True)
        pickle.dump(dict(depth=best[0], sol=best[1], ops=best[2]),
                    open('ckpt/beam_%d_R%d.pkl' % (seed, R), 'wb'))
        print('saved ckpt/beam_%d_R%d.pkl depth %s' % (seed, R, best[0]))
