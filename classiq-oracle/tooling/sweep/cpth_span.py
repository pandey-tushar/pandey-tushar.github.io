"""Phase-along-the-way fitness for the forward stream U (then one mirror).

Readout features (all are phase gates that cost ~0 depth, or one CZ layer):
  - constant and the 12 input bits (Z on data wires at t=0; parities free),
  - every Toffoli product p = new(target) ^ old(target)   (Z before + Z after),
  - every pairwise AND of two wires at the turnaround      (CZ layer, optional).
F is realisable exactly iff F is in the GF(2) span of the features.
Fitness = 4096 - (upper bound on the distance from F to that span):
greedy pursuit: repeatedly XOR the feature row that lowers the residual
weight most (bound only; exact when it reaches 0).
Skeleton / genome / mutation as cpte_evo (L levels x (LCX CX layers + 1
Toffoli layer), 18 wires), (1+1) neutral drift with restarts.
Usage: [CZ=1] [LCX=1] python3 cpth_span.py check NPZ...   (score old genomes)
       [CZ=1] [LCX=1] python3 cpth_span.py logo L SEED MINUTES
Progress: one line / PEVERY s;  ckpt/span_L<L>_s<seed>_c<LCX>_z<CZ>.npz/.json"""
import os, sys, time, json
import numpy as np
import numba as nb
import cpte_evo as E
from cpte_evo import NW, NWORD, popc, evaluate_from, clear_conflicts, init_state, logo_bits

PEVERY = float(os.environ.get('PEVERY', '10'))
CZ = int(os.environ.get('CZ', '1'))
P = E.P
RESTART = float(os.environ.get('RESTART', '150'))
PERM = np.random.default_rng(12345).permutation(4096)     # fixed bit order for pivots


def permute_bits(v):
    """uint64[64] -> same vector with positions permuted by PERM (numpy, setup only)"""
    b = ((v[:, None] >> np.arange(64, dtype=np.uint64)) & np.uint64(1)).astype(np.uint8).reshape(-1)
    return E.pack(b[PERM])


@nb.njit(cache=True)
def lowbit(r):
    for k in range(NWORD):
        if r[k] != 0:
            x = r[k]; b = 0
            while (x >> np.uint64(b)) & np.uint64(1) == 0: b += 1
            return k, b
    return -1, -1


@nb.njit(cache=True)
def weight(r):
    s = 0
    for k in range(NWORD): s += popc(r[k])
    return s


@nb.njit(cache=True)
def span_dist(feats, nf, Fv, basis, pw, pb):
    """upper bound on dist(F, span(feats)): greedy pursuit over the original
    feature rows (XOR the row that lowers the residual weight most, repeat)"""
    res = Fv.copy()
    cur = weight(res)
    while True:
        bi = -1; bw = cur
        for i in range(nf):
            s = 0
            for k in range(NWORD): s += popc(res[k] ^ feats[i, k])
            if s < bw: bw = s; bi = i
        if bi < 0: break
        for k in range(NWORD): res[k] ^= feats[bi, k]
        cur = bw
    return cur


@nb.njit(cache=True)
def fitness(st, tf, T, P, Fv, cz, feats, basis, pw, pb):
    """st: states in PERMUTED bit order.  returns 4096 - dist bound"""
    ONES = np.uint64(0xFFFFFFFFFFFFFFFF)
    nf = 0
    for k in range(NWORD): feats[nf, k] = ONES
    nf += 1
    for i in range(12):
        for k in range(NWORD): feats[nf, k] = st[0, i, k]
        nf += 1
    for j in range(T):
        if j % P != P - 1: continue
        for w in range(NW):
            if tf[j, w, 0] >= 0:
                for k in range(NWORD): feats[nf, k] = st[j + 1, w, k] ^ st[j, w, k]
                nf += 1
    if cz:
        for a in range(NW):
            for b in range(a + 1, NW):
                for k in range(NWORD): feats[nf, k] = st[T, a, k] & st[T, b, k]
                nf += 1
    return 4096 - span_dist(feats, nf, Fv, basis, pw, pb)


@nb.njit(cache=True)
def run(cx, tf, T, Fv, st, tmp, iters, fit0, pnone, seed, P, cz, feats, basis, pw, pb):
    np.random.seed(seed)
    fit = fit0
    ccx = cx.copy(); ctf = tf.copy()
    for it in range(iters):
        ccx[:] = cx; ctf[:] = tf
        l = np.random.randint(T); t = 1 if l % P == P - 1 else 0; w = np.random.randint(NW)
        if np.random.random() < pnone:
            if t == 0: ccx[l, w] = -1
            else: ctf[l, w, 0] = -1
        elif t == 0:
            s = np.random.randint(NW - 1); s = s + 1 if s >= w else s
            wires = [w, s]
            clear_conflicts(ccx, ctf, l, 0, wires)
            ccx[l, w] = s
        else:
            a = np.random.randint(NW - 1); a = a + 1 if a >= w else a
            b = np.random.randint(NW - 2)
            lo = min(a, w); hi = max(a, w)
            if b >= lo: b += 1
            if b >= hi: b += 1
            wires = [w, a, b]
            clear_conflicts(ccx, ctf, l, 1, wires)
            ctf[l, w, 0] = a; ctf[l, w, 1] = b
            ctf[l, w, 2] = np.random.randint(2); ctf[l, w, 3] = np.random.randint(2)
        tmp[l] = st[l]
        evaluate_from(tmp, ccx, ctf, T, l, P)
        f = fitness(tmp, ctf, T, P, Fv, cz, feats, basis, pw, pb)
        if f >= fit:
            fit = f
            cx[:] = ccx; tf[:] = ctf
            for j in range(l + 1, T + 1):
                st[j] = tmp[j]
        if fit == 4096:
            return fit, it + 1
    return fit, iters


def pinit():
    s = init_state()
    return np.array([permute_bits(s[w]) for w in range(NW)])


def states(cx, tf, L):
    st = np.zeros((L * P + 1, NW, NWORD), dtype=np.uint64); st[0] = pinit()
    evaluate_from(st, cx, tf, L * P, 0, P)
    return st


def workspace(L):
    nmax = 1 + 12 + L * NW + NW * NW
    return (np.zeros((nmax, NWORD), dtype=np.uint64), np.zeros((nmax, NWORD), dtype=np.uint64),
            np.zeros(nmax, dtype=np.int64), np.zeros(nmax, dtype=np.int64))


if __name__ == '__main__':
    Fv = permute_bits(logo_bits())
    if sys.argv[1] == 'check':
        for f in sys.argv[2:]:
            d = np.load(f); cx, tf, L = d['cx'], d['tf'], int(d['L'])
            if tf.shape[2] != 4 or cx.shape[0] != L * P: print(f, 'skip (other skeleton)'); continue
            st = states(cx, tf, L); ws = workspace(L)
            f0 = fitness(st, tf, L * P, P, Fv, 0, *ws); f1 = fitness(st, tf, L * P, P, Fv, 1, *ws)
            ntof = int((tf[:, :, 0] >= 0).sum())
            print('%-40s L %d tof %2d   span fitness: no CZ %d   with CZ layer %d' % (f, L, ntof, f0, f1))
        sys.exit(0)
    L, seed, minutes = int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
    rng = np.random.default_rng(seed)
    tag = 'span_L%d_s%d_c%d_z%d' % (L, seed, E.LCX, CZ)
    os.makedirs('ckpt', exist_ok=True)
    ws = workspace(L); T = L * P
    def fresh():
        cx, tf = E.empty(L)
        st = states(cx, tf, L)
        return cx, tf, st, st.copy(), fitness(st, tf, T, P, Fv, CZ, *ws)
    cx, tf, st, tmp, fit = fresh()
    if os.environ.get('INIT'):
        d = np.load(os.environ['INIT']); cx, tf = d['cx'].copy(), d['tf'].copy()
        st = states(cx, tf, L); tmp = st.copy(); fit = fitness(st, tf, T, P, Fv, CZ, *ws)
    best = (fit, cx.copy(), tf.copy()); nrs = 0
    t0 = time.time(); last = t0; total = 0; chunk = 200; t_imp = t0; fit_prev = fit
    print('[%s] start fitness %d / 4096  (CZ layer %d, LCX %d)' % (tag, fit, CZ, E.LCX), flush=True)
    while True:
        c0 = time.time()
        fit, n = run(cx, tf, T, Fv, st, tmp, chunk, fit, 0.1, int(rng.integers(1 << 30)), P, CZ, *ws)
        total += n; now = time.time()
        if now - c0 > 0: chunk = max(20, int(chunk * min(4.0, (PEVERY / 2) / (now - c0))))
        if fit > fit_prev: t_imp = now; fit_prev = fit
        if fit > best[0]: best = (fit, cx.copy(), tf.copy())
        done = best[0] == 4096 or now - t0 > minutes * 60
        if now - last >= PEVERY or done:
            last = now
            g = int((best[1] >= 0).sum()), int((best[2][:, :, 0] >= 0).sum())
            rec = dict(tag=tag, best=int(best[0]), current=int(fit), restarts=nrs, iters=total,
                       elapsed_s=round(now - t0), cx=g[0], tof=g[1], utc=time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now)))
            print('[%s] %s  %5ds  best %4d/4096  current %4d  restarts %d  iters %d (%d/s)  best: cx %d tof %d' %
                  (rec['utc'], tag, rec['elapsed_s'], best[0], fit, nrs, total, total / max(now - t0, 1e-9), *g), flush=True)
            np.savez('ckpt/%s.npz' % tag, cx=best[1], tf=best[2], L=L)
            json.dump(rec, open('ckpt/%s.json' % tag, 'w'))
            if done: break
        if now - t_imp > RESTART:
            cx, tf, st, tmp, fit = fresh(); nrs += 1; t_imp = now; fit_prev = fit
    print('[%s] final best %d / 4096' % (tag, best[0]), flush=True)
