"""Option 1: one forward stream + one mirror built from the 249 list's own
value classes (cptd_merge3 model), found by evolution instead of SAT/beam.

Genome g[T, NW] (T = R*(LCX+1) layers; layer j is a Toffoli layer iff
j % K == K-1):  CX layer: g = source wire (w ^= s);  Toffoli layer: g = product
index (w ^= product, control wires picked at decode time among wires holding
the control classes).  Decode keeps every gate physical (each wire in at most
one gate per layer) and every value inside the class set; a gate that would
break this is inactive.  Mutations are drawn only from moves legal at that
layer, so most proposals are active.
Readouts fire at the first state holding all their classes.
Score (minimised):  complete   -> op-model forward depth + 0.01*gates
                    incomplete -> 1000 + 100*pending + h_add cost of the
                                  pending classes (min over Toffoli states)
                                  - ZW*zero wires at the end
(1+1) neutral drift, restart after RESTART s without gain.  Every new best
complete genome is emitted (forward + readouts + mirror), checked classically
(phase == F, identity) and measured with the real transpile.
Usage: [READS=0,5] [LCX=2] python3 cptf_sched.py R SEED MINUTES
Progress: one line / PEVERY s;  checkpoint ckpt/sched_R<R>_L<LCX>_s<seed>[_r<reads>].npz/.json,
best exact circuit ckpt/sched_..._best.pkl (ops, depth)"""
import os, sys, time, json, pickle
import numpy as np
import numba as nb
import cptd_merge3 as M
from cpae_core import mirror, ops_to_qc, real_depth, model_depth, SHAPES, fvec

NW, N = 18, 4096
LCX = int(os.environ.get('LCX', '2')); K = LCX + 1
PEVERY = float(os.environ.get('PEVERY', '10'))
RESTART = float(os.environ.get('RESTART', '120'))
ZW = float(os.environ.get('ZW', '0.1'))
CXC = 0.3
PNONE = float(os.environ.get('PNONE', '0.15'))
TEMP = float(os.environ.get('TEMP', '0.3'))


def setup():
    ops, C, vals, prods, reads = M.extract()
    xor, P, pt = M.tables(C, vals, prods)
    if os.environ.get('READS'):
        reads = [reads[int(k)] for k in os.environ['READS'].split(',')]
    nc = len(vals)
    rc = -np.ones((len(reads), 3), dtype=np.int64)
    for k, (_, vs) in enumerate(reads):
        for i, v in enumerate(vs): rc[k, i] = C[M.key(v)]
    init = np.array([C[M.key(((np.arange(N) >> w) & 1).astype(np.uint8))] for w in range(NW)], dtype=np.int64)
    ctl = -np.ones((len(P), 3), dtype=np.int64); ncl = np.zeros(len(P), dtype=np.int64)
    for j, (cs, _, _) in enumerate(P):
        ctl[j, :len(cs)] = cs; ncl[j] = len(cs)
    tj, to = np.nonzero(pt >= 0); tr = pt[tj, to]
    co, cd = np.nonzero(xor >= 0); cr = xor[co, cd]
    D = dict(xor=xor.astype(np.int64), pt=pt.astype(np.int64), ctl=ctl, ncl=ncl, rc=rc, init=init,
             tj=tj.astype(np.int64), to=to.astype(np.int64), tr=tr.astype(np.int64),
             co=co.astype(np.int64), cd=cd.astype(np.int64), cr=cr.astype(np.int64))
    return D, (C, vals, P, reads)


@nb.njit(cache=True)
def hadd(st, nc, ctl, tj, to, tr, co, cd, cr):
    d = np.full(nc, 999.0)
    for w in range(NW): d[st[w]] = 0.0
    for _ in range(60):
        ch = False
        for i in range(len(tj)):
            j = tj[i]; s = d[to[i]] + 1.0
            for q in range(3):
                c = ctl[j, q]
                if c >= 0: s += d[c]
            if s < d[tr[i]]: d[tr[i]] = s; ch = True
        for i in range(len(co)):
            s = d[co[i]] + d[cd[i]] + CXC
            if s < d[cr[i]]: d[cr[i]] = s; ch = True
        if not ch: break
    return d


@nb.njit(cache=True)
def decode_layer(src, dst, g, j, K, xor, pt, ctl, ncl, cw):
    """src -> dst through layer j; cw[j, w, :] = control wires of the active Toffoli
    targeting w (-1 inactive).  returns number of active gates"""
    for w in range(NW): dst[w] = src[w]
    used = np.zeros(NW, dtype=np.bool_)
    n = 0
    tof = j % K == K - 1
    for w in range(NW):
        cw[j, w, 0] = -1; cw[j, w, 1] = -1; cw[j, w, 2] = -1
        x = g[j, w]
        if x < 0 or used[w]: continue
        if not tof:
            if used[x]: continue
            r = xor[src[w], src[x]]
            if r < 0 or r == src[w]: continue
            dst[w] = r; used[w] = True; used[x] = True; cw[j, w, 0] = x; n += 1
        else:
            r = pt[x, src[w]]
            if r < 0 or r == src[w]: continue
            ok = True; pick = np.full(3, -1, dtype=np.int64)
            for q in range(ncl[x]):
                c = ctl[x, q]; f = -1
                for u in range(NW):
                    if u != w and not used[u] and src[u] == c and u != pick[0] and u != pick[1]:
                        f = u; break
                if f < 0: ok = False; break
                pick[q] = f
            if not ok: continue
            used[w] = True
            for q in range(ncl[x]):
                used[pick[q]] = True; cw[j, w, q] = pick[q]
            dst[w] = r; n += 1
    return n


@nb.njit(cache=True)
def score(st, g, T, K, nc, rc, ctl, tj, to, tr, co, cd, cr, zc, ncl, cw, LCX, fired):
    """fired[k] = first state index holding readout k (-1 none)"""
    nr = rc.shape[0]
    pend = 0
    for k in range(nr):
        fired[k] = -1
        for s in range(T + 1):
            ok = True
            for q in range(3):
                c = rc[k, q]
                if c < 0: continue
                h = False
                for w in range(NW):
                    if st[s, w] == c: h = True; break
                if not h: ok = False; break
            if ok: fired[k] = s; break
        if fired[k] < 0: pend += 1
    ngate = 0; fwd = 0.0
    R = T // K
    for r in range(R):
        for l in range(K):
            j = r * K + l; a = 0; big = False
            for w in range(NW):
                if cw[j, w, 0] >= 0:
                    a += 1
                    if l == K - 1 and cw[j, w, 2] >= 0: big = True
            ngate += a
            if a > 0:
                if l < K - 1: fwd += 1.0
                else: fwd += 13.0 if big else 7.0
    if pend == 0:
        return fwd + 0.01 * ngate
    tot = 1000.0 + 100.0 * pend
    pk = np.full(nr, 1e9)                    # per pending readout: min over states of its class cost
    for s in range(0, T + 1, K):              # start, every Toffoli state, the final state
        d = hadd(st[s], nc, ctl, tj, to, tr, co, cd, cr)
        for k in range(nr):
            if fired[k] >= 0: continue
            c = 0.0
            for q in range(3):
                if rc[k, q] >= 0: c += d[rc[k, q]]
            if c < pk[k]: pk[k] = c
    best = 0.0
    for k in range(nr):
        if fired[k] < 0: best += pk[k]
    z = 0
    for w in range(NW):
        if st[T, w] == zc: z += 1
    return tot + best - ZW * z + 0.001 * ngate


@nb.njit(cache=True)
def run(g, st, cw, T, K, nc, xor, pt, ctl, ncl, rc, tj, to, tr, co, cd, cr, zc, LCX, iters, sc0, seed, pnone,
        temp, bg, bsc):
    """annealing at fixed temperature temp; best genome kept in bg, returns (score, best score)"""
    np.random.seed(seed)
    fired = np.zeros(rc.shape[0], dtype=np.int64)
    sc = sc0
    g2 = g.copy(); st2 = st.copy(); cw2 = cw.copy()
    cand = np.empty(max(NW, pt.shape[0]), dtype=np.int64)
    for it in range(iters):
        j = np.random.randint(T); w = np.random.randint(NW)
        tof = j % K == K - 1
        g2[:] = g
        if np.random.random() < pnone:
            if g2[j, w] < 0: continue
            g2[j, w] = -1
        else:
            c = st[j, w]; m = 0
            if not tof:
                for s in range(NW):
                    if s != w:
                        r = xor[c, st[j, s]]
                        if r >= 0 and r != c: cand[m] = s; m += 1
            else:
                for x in range(pt.shape[0]):
                    r = pt[x, c]
                    if r < 0 or r == c: continue
                    ok = True
                    for q in range(ncl[x]):
                        h = False
                        for u in range(NW):
                            if u != w and st[j, u] == ctl[x, q]: h = True; break
                        if not h: ok = False; break
                    if ok: cand[m] = x; m += 1
            if m == 0: continue
            x = cand[np.random.randint(m)]
            g2[j, w] = x
            # clear gates of this layer that share a wire with the new one (CX: w, x)
            if not tof:
                for u in range(NW):
                    if u != w and (u == x or g2[j, u] == w or g2[j, u] == x): g2[j, u] = -1
            else:
                g2[j, w] = x
        st2[:j + 1] = st[:j + 1]; cw2[:j] = cw[:j]
        for jj in range(j, T):
            decode_layer(st2[jj], st2[jj + 1], g2, jj, K, xor, pt, ctl, ncl, cw2)
        s2 = score(st2, g2, T, K, nc, rc, ctl, tj, to, tr, co, cd, cr, zc, ncl, cw2, LCX, fired)
        if s2 <= sc or (temp > 0 and np.random.random() < np.exp(-(s2 - sc) / temp)):
            sc = s2; g[:] = g2; st[:] = st2; cw[:] = cw2
            if sc < bsc:
                bsc = sc; bg[:] = g
    return sc, bsc


def decode_all(g, T, D):
    st = np.zeros((T + 1, NW), dtype=np.int64); st[0] = D['init']
    cw = -np.ones((T, NW, 3), dtype=np.int64)
    for j in range(T):
        decode_layer(st[j], st[j + 1], g, j, K, D['xor'], D['pt'], D['ctl'], D['ncl'], cw)
    return st, cw


def full_score(g, st, cw, T, D, nc):
    fired = np.zeros(D['rc'].shape[0], dtype=np.int64)
    s = score(st, g, T, K, nc, D['rc'], D['ctl'], D['tj'], D['to'], D['tr'], D['co'], D['cd'], D['cr'],
              int(D['init'][NW - 1]), D['ncl'], cw, LCX, fired)
    return s, fired


def emit(g, st, cw, T, D, M_, fired):
    """forward stream with readouts at their firing states, then the mirror"""
    C, vals, P, reads = M_
    s = np.arange(N, dtype=np.int64)
    bit = lambda w: ((s >> w) & 1).astype(np.uint8)
    stream = []
    def readouts(si):
        for k in range(len(reads)):
            if fired[k] != si: continue
            ws = []
            for v in reads[k][1]:
                c = C[M.key(v)]
                w = next(u for u in range(NW) if st[si, u] == c and u not in ws)
                ws.append(w)
                if not np.array_equal(bit(w), v): stream.append(('x', w))
            stream.append(('cz' if len(ws) == 2 else 'ccz',) + tuple(ws))
            for w, v in zip(ws, reads[k][1]):
                if not np.array_equal(bit(w), v): stream.append(('x', w))
    for j in range(T):
        readouts(j)
        tof = j % K == K - 1
        for w in range(NW):
            if cw[j, w, 0] < 0: continue
            if not tof:
                sw = int(cw[j, w, 0]); stream.append(('cx', sw, w))
        if not tof:
            for w in range(NW):
                if cw[j, w, 0] >= 0: s = s ^ (((s >> int(cw[j, w, 0])) & 1) << w)
            continue
        new = s.copy()
        for w in range(NW):
            if cw[j, w, 0] < 0: continue
            cs, pol, _ = P[g[j, w]]
            ctlw = [int(cw[j, w, q]) for q in range(len(cs))]
            need = [vals[c] ^ ((pol >> i) & 1) for i, c in enumerate(cs)]
            fl = [u for u, v in zip(ctlw, need) if not np.array_equal(bit(u), v)]
            p = np.ones(N, dtype=np.uint8)
            for v in need: p &= v
            stream += [('x', u) for u in fl]
            stream.append(('ccx' if len(ctlw) == 2 else 'c3x',) + tuple(ctlw) + (w,))
            stream += [('x', u) for u in fl]
            new = new ^ (p.astype(np.int64) << w)
        s = new
    readouts(T)
    fwd = [o for o in stream if o[0] not in ('cz', 'ccz')]
    return stream + mirror(fwd)


def classical(ops, target):
    s = np.arange(N, dtype=np.int64); ph = np.zeros(N, dtype=np.int64)
    b = lambda w: (s >> w) & 1
    for op in ops:
        k, q = op[0], op[1:]
        if k == 'x': s = s ^ (1 << q[0])
        elif k == 'cx': s = s ^ (b(q[0]) << q[1])
        elif k.startswith('ccx'): s = s ^ ((b(q[0]) & b(q[1])) << q[2])
        elif k.startswith('c3x'): s = s ^ ((b(q[0]) & b(q[1]) & b(q[2])) << q[3])
        elif k == 'cz': ph ^= b(q[0]) & b(q[1])
        elif k == 'ccz': ph ^= b(q[0]) & b(q[1]) & b(q[2])
    return int((ph != target).sum()), bool((s == np.arange(N)).all())


def remap(g, perm):
    """relabel ancilla wires 12..17 by perm (data wires fixed); CX sources remapped too"""
    K_ = K; h = -np.ones_like(g)
    mp = list(range(12)) + [12 + p for p in perm]
    for j in range(g.shape[0]):
        for w in range(NW):
            x = g[j, w]
            if x < 0: continue
            h[j, mp[w]] = mp[x] if j % K_ != K_ - 1 else x
    return h


def seed_genome(spec, T, D, nc):
    """SEEDS='a.pkl:off,b.pkl:off' (off in rounds): overlay single-readout genomes.
    Tries every ancilla relabelling of each later seed and both overlay orders,
    keeps the combination with the best score (fired readouts first)."""
    import itertools
    parts = []
    for item in spec.split(','):
        f, off = item.split(':')
        d = pickle.load(open(f, 'rb')); assert d['LCX'] == LCX
        gg = -np.ones((T, NW), dtype=np.int64); o = int(off) * K
        n = min(d['g'].shape[0], T - o); gg[o:o + n] = d['g'][:n]
        parts.append(gg)
    best = None
    perms = list(itertools.permutations(range(6)))
    cands = [parts[0]]
    for p in parts[1:]:
        nxt = []
        for base in cands:
            scored = []
            for perm in perms:
                q = remap(p, perm)
                for top, bot in ((q, base), (base, q)):
                    g = np.where(top >= 0, top, bot)
                    st, cw = decode_all(g, T, D)
                    sc, fired = full_score(g, st, cw, T, D, nc)
                    scored.append((sc, int((fired >= 0).sum()), g))
            scored.sort(key=lambda t: t[0])
            nxt += [t[2] for t in scored[:3]]
            if best is None or scored[0][0] < best[0]: best = scored[0][:2]
        cands = nxt
    st, cw = decode_all(cands[0], T, D)
    sc, fired = full_score(cands[0], st, cw, T, D, nc)
    print('seed: score %.2f  fired %s' % (sc, [int(f) for f in fired]), flush=True)
    return cands[0]


if __name__ == '__main__':
    R, seed, minutes = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
    T = R * K
    D, M_ = setup(); nc = len(M_[1]); reads = M_[3]
    # target phase = XOR of the selected readouts (== F when all 6 are used)
    tgt = np.zeros(N, dtype=np.int64)
    for _, vs in reads:
        p = np.ones(N, dtype=np.int64)
        for v in vs: p &= v
        tgt ^= p
    full_F = not os.environ.get('READS')
    if full_F:
        assert np.array_equal(tgt, fvec(SHAPES['LOGO']).astype(np.int64)), 'readouts do not give F'
    rtag = ('_r' + os.environ['READS'].replace(',', '')) if os.environ.get('READS') else ''
    tag = 'sched_R%d_L%d_s%d%s' % (R, LCX, seed, rtag) + ('_seeded' if os.environ.get('SEEDS') else '')
    os.makedirs('ckpt', exist_ok=True)
    rng = np.random.default_rng(seed)
    zc = int(D['init'][NW - 1])
    args = (T, K, nc, D['xor'], D['pt'], D['ctl'], D['ncl'], D['rc'], D['tj'], D['to'], D['tr'],
            D['co'], D['cd'], D['cr'], zc, LCX)
    seed_g = seed_genome(os.environ['SEEDS'], T, D, nc) if os.environ.get('SEEDS') else None
    def fresh():                               # restarts go back to the seed when one is given
        g = -np.ones((T, NW), dtype=np.int64) if seed_g is None else seed_g.copy()
        st, cw = decode_all(g, T, D)
        return g, st, cw, full_score(g, st, cw, T, D, nc)[0]
    g, st, cw, sc = fresh()
    best = (sc, g.copy()); best_exact = None; nrs = 0
    t0 = time.time(); last = t0; t_imp = t0; sc_prev = sc; total = 0; chunk = 200
    print('[%s] classes %d products %d readouts %d  R %d LCX %d  start score %.1f' %
          (tag, nc, len(M_[2]), len(reads), R, LCX, sc), flush=True)
    while True:
        c0 = time.time()
        bg = best[1].copy()
        sc, bsc = run(g, st, cw, *args, chunk, sc, int(rng.integers(1 << 30)), PNONE, TEMP, bg, best[0])
        total += chunk; now = time.time()
        if now - c0 > 0: chunk = max(20, int(chunk * min(4.0, (PEVERY / 2) / (now - c0))))
        if bsc < sc_prev - 1e-9: t_imp = now; sc_prev = bsc
        if bsc < best[0] - 1e-9:
            best = (bsc, bg.copy()); sc_b = bsc
            if sc_b < 1000:                      # complete: emit + verify + real depth
                bst, bcw = decode_all(best[1], T, D)
                _, fired = full_score(best[1], bst, bcw, T, D, nc)
                ops = emit(best[1], bst, bcw, T, D, M_, fired)
                mism, ident = classical(ops, tgt)
                dep = real_depth(ops_to_qc(ops)) if mism == 0 and ident else None
                mdep = model_depth(ops)
                print('   complete: score %.2f  model depth %s  classical mism %d identity %s  real depth/cx %s' %
                      (sc_b, mdep, mism, ident, dep), flush=True)
                if dep and (best_exact is None or dep < best_exact[0]):
                    best_exact = (dep, ops)
                    pickle.dump(dict(depth=dep, ops=ops, g=best[1], R=R, LCX=LCX, reads=os.environ.get('READS')),
                                open('ckpt/%s_best.pkl' % tag, 'wb'))
        done = now - t0 > minutes * 60
        if now - last >= PEVERY or done:
            last = now
            bst, bcw = decode_all(best[1], T, D)
            _, fired = full_score(best[1], bst, bcw, T, D, nc)
            rec = dict(tag=tag, best_score=round(float(best[0]), 3), current=round(float(sc), 3),
                       fired=[int(f) for f in fired], restarts=nrs, iters=total,
                       best_real=None if best_exact is None else list(best_exact[0]),
                       elapsed_s=round(now - t0), utc=time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now)))
            print('[%s] %s %5ds  best %.2f  fired %d/%d %s  current %.2f  restarts %d  iters %d  exact %s' %
                  (rec['utc'], tag, rec['elapsed_s'], best[0], int((fired >= 0).sum()), len(reads), rec['fired'],
                   sc, nrs, total, rec['best_real']), flush=True)
            np.savez('ckpt/%s.npz' % tag, g=best[1], R=R, LCX=LCX)
            json.dump(rec, open('ckpt/%s.json' % tag, 'w'))
            if done: break
        if now - t_imp > RESTART:
            g, st, cw, sc = fresh(); nrs += 1; t_imp = now; sc_prev = best[0]
    print('[%s] final best score %.2f  exact real depth/cx %s' %
          (tag, best[0], None if best_exact is None else best_exact[0]), flush=True)
