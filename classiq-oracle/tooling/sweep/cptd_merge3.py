"""Merge idea, step 3: single forward stream (then one mirror) on 18 wires
built only from the 249 op list's own values and Toffoli products.

Values are taken up to complement (X is free).  Class set C = every wire
value the 249 list ever holds.  Rounds r=1..R, each = LCX CX layers + one
Toffoli layer:
  CX layer   : w ^= s  (s not a target), result must stay in C
  Tof layer  : w ^= p  for a product p of the 249 list (any control
               polarity), controls held on wires not written this layer,
               result must stay in C
Readouts   : the 6 non-cancelling cz/ccz of the 249 list; each needs its
               classes present at some state.
Relaxation : control fanout inside a Toffoli layer is not limited, readouts
               take no wires -> UNSAT at R is a floor for this value set.
Usage: LCX=2 python3 cptd_merge3.py R1 R2 ...   (no timeout; kill externally)
Checkpoint: ckpt/merge3_ledger.json, ckpt/merge3_R<R>.pkl"""
import os, sys, json, time, pickle
import numpy as np
from pysat.card import CardEnc, EncType
from cpri_round import Enc, solve

OPS = os.environ.get('CPEN_O1', '/home/user/classiq-challenge/cpen_o1.pkl')
NW, N = 18, 4096
LEDGER = 'ckpt/merge3_ledger.json'   # keys R:LCX


def canon(v):
    return v ^ 1 if v[0] else v


def key(v):
    return np.packbits(canon(v)).tobytes()


def extract():
    ops = pickle.load(open(OPS, 'rb'))
    s = np.arange(N, dtype=np.int64)
    bit = lambda w: ((s >> w) & 1).astype(np.uint8)
    C, vals = {}, []
    def cid(v):
        k = key(v)
        if k not in C: C[k] = len(vals); vals.append(canon(v).copy())
        return C[k]
    for w in range(NW): cid(bit(w))
    prods, reads = {}, []
    for i, op in enumerate(ops):
        k, q = op[0], list(op[1:])
        if k in ('cz', 'ccz'):
            reads.append((i, tuple(bit(w).copy() for w in q))); continue
        if k[:3] in ('ccx', 'c3x'):
            cs = [cid(bit(w)) for w in q[:-1]]
            if len(set(cs)) == len(cs):
                prods[tuple(sorted(cs))] = 1
            p = np.ones(N, dtype=np.uint8)
            for w in q[:-1]: p &= bit(w)
            s = s ^ (p.astype(np.int64) << q[-1])
        elif k == 'cx':
            s = s ^ (((s >> q[0]) & 1) << q[1])
        elif k == 'x':
            s = s ^ (1 << q[0])
        for w in range(NW): cid(bit(w))
    # drop readouts that cancel pairwise (identical value tuples)
    rk = {}
    for i, vs in reads:
        t = tuple(np.packbits(v).tobytes() for v in vs)
        rk.setdefault(t, []).append((i, vs))
    reads = [lst[0] for t, lst in rk.items() if len(lst) % 2 == 1]
    return ops, C, vals, list(prods), reads


def tables(C, vals, prods):
    nc = len(vals)
    xor = np.full((nc, nc), -1, dtype=np.int32)
    for a in range(nc):
        for b in range(nc):
            xor[a, b] = C.get(key(vals[a] ^ vals[b]), -1)
    P = []                     # (control classes, polarities, product value)
    for cs in prods:
        for pol in range(1 << len(cs)):
            p = np.ones(N, dtype=np.uint8)
            for j, c in enumerate(cs): p &= vals[c] ^ ((pol >> j) & 1)
            P.append((cs, pol, p))
    pt = np.full((len(P), nc), -1, dtype=np.int32)
    for j, (_, _, p) in enumerate(P):
        for a in range(nc):
            pt[j, a] = C.get(key(vals[a] ^ p), -1)
    keep = [j for j in range(len(P)) if (pt[j] >= 0).any() and (pt[j] != np.arange(nc)).any()]
    return xor, [P[j] for j in keep], pt[keep]


LCX = int(os.environ.get('LCX', '2'))      # CX layers per round


def encode(R, C, vals, P, pt, xor, reads):
    e = Enc(); nc = len(vals); K = LCX + 1; S = K * R + 1
    a = lambda s, w, c: e.v('a', s, w, c)
    def exactly1(lits):
        c = CardEnc.equals(lits=lits, bound=1, vpool=e.pool, encoding=EncType.seqcounter)
        e.cl.extend(c.clauses)
    def atmost1(lits):
        if len(lits) > 1:
            c = CardEnc.atmost(lits=lits, bound=1, vpool=e.pool, encoding=EncType.seqcounter)
            e.cl.extend(c.clauses)
    for s in range(S):
        for w in range(NW): exactly1([a(s, w, c) for c in range(nc)])
    for w in range(NW):      # init: data wires hold x/y bits, ancillas zero
        init = C[key(((np.arange(N) >> w) & 1).astype(np.uint8))]
        e.cl.append([a(0, w, init)])
    for rr in range(R * LCX):
        r, l = divmod(rr, LCX)
        s0, s1 = K * r + l, K * r + l + 1
        # ---- CX layer s0 -> s1   (key r = round*LCX + layer)
        r = rr
        cx = {(sw, tw): e.v('cx', r, sw, tw) for sw in range(NW) for tw in range(NW) if sw != tw}
        for tw in range(NW):
            atmost1([cx[sw, tw] for sw in range(NW) if sw != tw])
        for sw in range(NW):   # a wire is in at most one cx: source once, never also a target
            atmost1([cx[sw, tw] for tw in range(NW) if tw != sw])
            for tw in range(NW):
                if tw == sw: continue
                for t2 in range(NW):
                    if t2 != sw: e.cl.append([-cx[sw, tw], -cx[t2, sw]])
        for tw in range(NW):
            tg = e.v('tg', r, tw)
            lits = [cx[sw, tw] for sw in range(NW) if sw != tw]
            e.cl.append([-tg] + lits); e.cl.extend([[tg, -l] for l in lits])
            for sw in range(NW):
                if sw == tw: continue
                for d in range(nc):
                    e.cl.append([-cx[sw, tw], -a(s0, sw, d), e.v('rv', r, tw, d)])
            for c in range(nc):
                e.cl.append([tg, -a(s0, tw, c), a(s1, tw, c)])
                for d in range(nc):
                    n = xor[c, d]
                    rv = e.v('rv', r, tw, d)
                    e.cl.append([-rv, -a(s0, tw, c)] + ([a(s1, tw, n)] if n >= 0 else []))
    for r in range(R):
        s1, s2 = K * r + LCX, K * r + K
        # ---- Toffoli layer s1 -> s2
        wr = {}
        for w in range(NW):
            us = [e.v('tu', r, w, j) for j in range(len(P))]
            atmost1(us)
            wr[w] = e.v('wr', r, w)
            e.cl.append([-wr[w]] + us); e.cl.extend([[wr[w], -u] for u in us])
            for c in range(nc):
                e.cl.append([wr[w], -a(s1, w, c), a(s2, w, c)])
            for j in range(len(P)):
                u = us[j]
                for c in range(nc):
                    n = pt[j, c]
                    e.cl.append([-u, -a(s1, w, c)] + ([a(s2, w, n)] if n >= 0 else []))
                for c in P[j][0]:
                    e.cl.append([-u, e.v('h', r, c)])
        for c in range(nc):     # control held on some wire not written this layer
            z = [e.v('z', r, w, c) for w in range(NW)]
            e.cl.append([-e.v('h', r, c)] + z)
            for w in range(NW):
                e.cl.append([-z[w], a(s1, w, c)]); e.cl.append([-z[w], -wr[w]])
    # ---- readouts
    for k, (i, vs) in enumerate(reads):
        cs = [C[key(v)] for v in vs]
        rd = [e.v('rd', k, s) for s in range(S)]
        e.cl.append(rd)
        for s in range(S):
            for c in cs:
                e.cl.append([-rd[s], e.v('pr', s, c)])
    for s in range(S):
        for c in range(nc):
            e.cl.append([-e.v('pr', s, c)] + [a(s, w, c) for w in range(NW)])
    return e


def decode(R, e, model, nc, P, reads, C):
    m = set(l for l in model if l > 0)
    on = lambda *k: e.pool.obj2id.get(k) in m if k in e.pool.obj2id else False
    K = LCX + 1; S = K * R + 1
    state = [[next(c for c in range(nc) if on('a', s, w, c)) for w in range(NW)] for s in range(S)]
    layers = []
    for r in range(R):
        cxs = [[(sw, tw) for sw in range(NW) for tw in range(NW) if sw != tw and on('cx', r * LCX + l, sw, tw)]
               for l in range(LCX)]
        tfs = [(w, j) for w in range(NW) for j in range(len(P)) if on('tu', r, w, j)]
        layers.append((cxs, tfs))
    rds = [[s for s in range(S) if on('rd', k, s)] for k in range(len(reads))]
    return dict(state=state, layers=layers, rds=rds, lcx=LCX)


def ledger_set(k, v):
    d = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {}
    d[k] = v; tmp = LEDGER + '.tmp'
    json.dump(d, open(tmp, 'w'), indent=1); os.replace(tmp, LEDGER)


if __name__ == '__main__':
    os.makedirs('ckpt', exist_ok=True)
    ops, C, vals, prods, reads = extract()
    xor, P, pt = tables(C, vals, prods)
    print('classes %d  products(with polarity, useful) %d  readouts %d' % (len(vals), len(P), len(reads)), flush=True)
    done = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {}
    for R in map(int, sys.argv[1:]):
        kk = '%d:%d' % (R, LCX)
        if kk in done and done[kk]['res'] in ('SAT', 'UNSAT'):
            print('R=%d cached %s' % (R, done[str(R)]['res']), flush=True); continue
        e = encode(R, C, vals, P, pt, xor, reads)
        print('R=%d vars %d clauses %d' % (R, e.pool.top, len(e.cl)), flush=True)
        t0 = time.time(); res = solve(e.cl, None); dt = time.time() - t0
        tag = 'SAT' if isinstance(res, list) else ('UNSAT' if res is None or res is False else str(res))
        print('R=%d -> %s  %.0fs' % (R, tag, dt), flush=True)
        ledger_set(kk, dict(res=tag, sec=round(dt)))
        if tag == 'SAT':
            sol = decode(R, e, res, len(vals), P, reads, C)
            pickle.dump(dict(sol=sol, P=[(cs, pol) for cs, pol, _ in P], vals=vals, reads=reads),
                        open('ckpt/merge3_R%d_L%d.pkl' % (R, LCX), 'wb'))
            break
