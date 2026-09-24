"""Evolutionary search for the forward stream U (then Z readout, then U^-1).
Skeleton: 18 wires (12 data + 6 zero ancillas), L levels, each level = one CX
layer + one Toffoli layer, gates in a layer on disjoint wires.
Genome: cx[l, w] = source (-1 none);  tf[l, w] = (a, b, pa, pb) (a = -1 none),
w ^= (a ^ pa)(b ^ pb).
Fitness: inputs (of 4096) where the target phase is matched by the best
readout on the final wires: one wire (Z) or a 2-wire product (CZ), any
polarities; the global sign is free.  4096 = exact.
Search: (1+1) with neutral drift, one gate mutated per step, conflicting gates
in that layer removed.  All inputs bit-parallel (64 x uint64), numba.
Usage:
  python3 cpte_evo.py test L SEED MINUTES     planted target from a random L-level circuit
  python3 cpte_evo.py logo L SEED MINUTES     the logo
Progress: one line / PEVERY s;  checkpoint ckpt/evo_<mode>_L<L>_s<seed>.npz (best genome)
+ ckpt/evo_<mode>_L<L>_s<seed>.json (progress)."""
import os, sys, time, json
import numpy as np
import numba as nb

NW, NWORD = 18, 64
PEVERY = float(os.environ.get('PEVERY', '10'))


def init_state():
    s = np.zeros((NW, NWORD), dtype=np.uint64)
    idx = np.arange(4096)
    for w in range(12):
        bits = ((idx >> w) & 1).astype(np.uint64).reshape(NWORD, 64)
        s[w] = (bits << np.arange(64, dtype=np.uint64)).sum(axis=1).astype(np.uint64)
    return s


def pack(v):
    bits = v.astype(np.uint64).reshape(NWORD, 64)
    return (bits << np.arange(64, dtype=np.uint64)).sum(axis=1).astype(np.uint64)


@nb.njit(cache=True)
def popc(x):
    x = x - ((x >> np.uint64(1)) & np.uint64(0x5555555555555555))
    x = (x & np.uint64(0x3333333333333333)) + ((x >> np.uint64(2)) & np.uint64(0x3333333333333333))
    x = (x + (x >> np.uint64(4))) & np.uint64(0x0F0F0F0F0F0F0F0F)
    return (x * np.uint64(0x0101010101010101)) >> np.uint64(56)


@nb.njit(cache=True)
def layer(src, dst, cx, tf, l, t):
    """state src -> dst through layer (l, t): t=0 CX layer, t=1 Toffoli layer"""
    ONES = np.uint64(0xFFFFFFFFFFFFFFFF)
    for w in range(NW):
        for k in range(NWORD):
            dst[w, k] = src[w, k]
    for w in range(NW):
        if t == 0:
            s = cx[l, w]
            if s >= 0:
                for k in range(NWORD):
                    dst[w, k] ^= src[s, k]
        else:
            a = tf[l, w, 0]
            if a >= 0:
                b = tf[l, w, 1]
                ma = ONES if tf[l, w, 2] else np.uint64(0)
                mb = ONES if tf[l, w, 3] else np.uint64(0)
                for k in range(NWORD):
                    dst[w, k] ^= (src[a, k] ^ ma) & (src[b, k] ^ mb)


@nb.njit(cache=True)
def fitness(S, F):
    """best readout agreement: single wire or 2-wire product, any polarity,
    global sign free.  returns (fit, a, b, pa, pb)  (b=-1 single)"""
    ONES = np.uint64(0xFFFFFFFFFFFFFFFF)
    best = 0; ba = 0; bb = -1; bpa = 0; bpb = 0
    for a in range(NW):
        m = 0
        for k in range(NWORD):
            m += popc(~(S[a, k] ^ F[k]))
        m = max(m, 4096 - m)
        if m > best:
            best = m; ba = a; bb = -1
    for a in range(NW):
        for b in range(a + 1, NW):
            for pa in range(2):
                ma = ONES if pa else np.uint64(0)
                for pb in range(2):
                    mb = ONES if pb else np.uint64(0)
                    m = 0
                    for k in range(NWORD):
                        m += popc(~(((S[a, k] ^ ma) & (S[b, k] ^ mb)) ^ F[k]))
                    m = max(m, 4096 - m)
                    if m > best:
                        best = m; ba = a; bb = b; bpa = pa; bpb = pb
    return best, ba, bb, bpa, bpb


@nb.njit(cache=True)
def fitness3(S, F):
    """best readout = ANY Boolean function of 3 final wires (a diagonal on 3
    wires); covers 1- and 2-wire readouts.  returns (fit, a, b, c, 0)"""
    ONES = np.uint64(0xFFFFFFFFFFFFFFFF)
    M = np.empty(NWORD, dtype=np.uint64)
    best = 0; ba = 0; bb = 1; bc = 2
    for a in range(NW):
        for b in range(a + 1, NW):
            for c in range(b + 1, NW):
                sc = 0
                for p in range(4):
                    ma = ONES if p & 1 else np.uint64(0)
                    mb = ONES if p & 2 else np.uint64(0)
                    nM = 0; nMF = 0; n1 = 0; n1F = 0
                    for k in range(NWORD):
                        m = (S[a, k] ^ ma) & (S[b, k] ^ mb)
                        mf = m & F[k]
                        nM += popc(m); nMF += popc(mf)
                        n1 += popc(m & S[c, k]); n1F += popc(mf & S[c, k])
                    n0 = nM - n1; n0F = nMF - n1F
                    sc += max(n1F, n1 - n1F) + max(n0F, n0 - n0F)
                if sc > best:
                    best = sc; ba = a; bb = b; bc = c
    return best, ba, bb, bc, 0


@nb.njit(cache=True)
def fit_k(S, F, K):
    if K == 3:
        return fitness3(S, F)
    return fitness(S, F)


@nb.njit(cache=True)
def evaluate_from(st, cx, tf, L, li):
    for j in range(li, 2 * L):
        layer(st[j], st[j + 1], cx, tf, j // 2, j % 2)


@nb.njit(cache=True)
def clear_conflicts(cx, tf, l, t, wires):
    """remove every gate of layer (l,t) that touches one of the wires"""
    for u in range(NW):
        if t == 0:
            if cx[l, u] < 0: continue
            g1 = cx[l, u]; g2 = -2
        else:
            if tf[l, u, 0] < 0: continue
            g1 = tf[l, u, 0]; g2 = tf[l, u, 1]
        for v in wires:
            if v == u or v == g1 or v == g2:
                if t == 0: cx[l, u] = -1
                else: tf[l, u, 0] = -1
                break


@nb.njit(cache=True)
def run(cx, tf, L, F, st, tmp, iters, fit0, pnone, seed, K=2):
    np.random.seed(seed)
    fit = fit0; acc = 0
    ccx = cx.copy(); ctf = tf.copy()
    for it in range(iters):
        ccx[:] = cx; ctf[:] = tf
        l = np.random.randint(L); t = np.random.randint(2); w = np.random.randint(NW)
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
        li = 2 * l + t
        tmp[li] = st[li]
        evaluate_from(tmp, ccx, ctf, L, li)
        f = fit_k(tmp[2 * L], F, K)[0]
        if f >= fit:
            if f > fit: acc += 1
            fit = f
            cx[:] = ccx; tf[:] = ctf
            for j in range(li + 1, 2 * L + 1):
                st[j] = tmp[j]
        if fit == 4096:
            return fit, acc, it + 1
    return fit, acc, iters


def random_genome(L, rng, dens=0.8):
    cx = -np.ones((L, NW), dtype=np.int64); tf = -np.ones((L, NW, 4), dtype=np.int64)
    for l in range(L):
        for t in range(2):
            perm = list(rng.permutation(NW)); used = set()
            for w in perm:
                if w in used or rng.random() > dens: continue
                free = [u for u in range(NW) if u not in used and u != w]
                need = 1 if t == 0 else 2
                if len(free) < need: continue
                pick = list(rng.choice(free, need, replace=False))
                if t == 0: cx[l, w] = pick[0]
                else: tf[l, w] = [pick[0], pick[1], rng.integers(2), rng.integers(2)]
                used |= {w, *pick}
    return cx, tf


def states(cx, tf, L):
    st = np.zeros((2 * L + 1, NW, NWORD), dtype=np.uint64); st[0] = init_state()
    evaluate_from(st, cx, tf, L, 0)
    return st


def logo_bits():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cpae_core import SHAPES, fvec
    return pack(fvec(SHAPES['LOGO']).astype(np.uint8))


if __name__ == '__main__':
    mode, L, seed, minutes = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
    rng = np.random.default_rng(seed)
    tag = 'evo_%s_L%d_s%d' % (mode, L, seed)
    os.makedirs('ckpt', exist_ok=True)
    if mode == 'test':
        # planted target: final value of a dense random L-level circuit, most balanced nonlinear wire
        tcx, ttf = random_genome(L, np.random.default_rng(1000 + seed))
        S = states(tcx, ttf, L)[-1]
        from cptd_rot import walsh
        def unpack(x): return ((x[:, None] >> np.arange(64, dtype=np.uint64)) & np.uint64(1)).astype(np.uint8).reshape(-1)
        nl = [2048 - int(np.abs(walsh(unpack(S[w]))).max()) // 2 for w in range(NW)]   # distance to nearest affine fn
        w = int(np.argmax(nl))
        F = S[w].copy()
        print('planted target: wire %d, ones %d, nonlinearity %d (logo %d)' % (
            w, int(unpack(F).sum()), nl[w], 2048 - int(np.abs(walsh(unpack(logo_bits()))).max()) // 2), flush=True)
    else:
        F = logo_bits()
    K = int(os.environ.get('FITK', '2'))                # 2: 1-2 wire readout, 3: any fn of 3 wires
    tag += '_k%d' % K if K != 2 else ''
    RESTART = float(os.environ.get('RESTART', '90'))    # s without improvement -> fresh start
    def fresh():
        cx = -np.ones((L, NW), dtype=np.int64); tf = -np.ones((L, NW, 4), dtype=np.int64)
        st = states(cx, tf, L)
        return cx, tf, st, st.copy(), fit_k(st[-1], F, K)[0]
    cx, tf, st, tmp, fit = fresh()
    best = (fit, cx.copy(), tf.copy()); nrs = 0
    t0 = time.time(); total = 0; last = t0; chunk = 2000; t_imp = t0; fit_prev = fit
    print('[%s] start fitness %d / 4096  restart after %.0fs without gain' % (tag, fit, RESTART), flush=True)
    while True:
        c0 = time.time()
        fit, acc, n = run(cx, tf, L, F, st, tmp, chunk, fit, 0.1, int(rng.integers(1 << 30)), K)
        total += n; now = time.time()
        if now - c0 > 0: chunk = max(200, int(chunk * min(4.0, (PEVERY / 2) / (now - c0))))
        if fit > fit_prev: t_imp = now; fit_prev = fit
        if fit > best[0]: best = (fit, cx.copy(), tf.copy())
        done = best[0] == 4096 or now - t0 > minutes * 60
        if now - last >= PEVERY or done:
            last = now
            gates = int((best[1] >= 0).sum()), int((best[2][:, :, 0] >= 0).sum())
            rec = dict(tag=tag, best=int(best[0]), current=int(fit), restarts=nrs, iters=total,
                       elapsed_s=round(now - t0), evals_per_s=round(total / (now - t0)),
                       cx=gates[0], tof=gates[1], utc=time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now)))
            print('[%s] %s  %5ds  best %4d/4096  current %4d  restarts %d  iters %d  (%d/s)  best gates cx %d tof %d' %
                  (rec['utc'], tag, rec['elapsed_s'], best[0], fit, nrs, total, rec['evals_per_s'], *gates), flush=True)
            np.savez('ckpt/%s.npz' % tag, cx=best[1], tf=best[2], F=F, L=L)
            json.dump(rec, open('ckpt/%s.json' % tag, 'w'))
            if done: break
        if now - t_imp > RESTART:
            cx, tf, st, tmp, fit = fresh(); nrs += 1; t_imp = now; fit_prev = fit
    S = states(best[1], best[2], L)[-1]
    print('[%s] final best %d / 4096  readout %s  restarts %d' % (tag, best[0], fit_k(S, F, K)[1:], nrs), flush=True)
