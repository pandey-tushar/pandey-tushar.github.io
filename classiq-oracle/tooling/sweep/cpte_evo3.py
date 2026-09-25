"""cpte_evo with 3-control Toffolis (option 2).  Same skeleton, fitness,
restarts and progress as cpte_evo; a Toffoli-layer gate may now have 2 or 3
controls:  w ^= (a^pa)(b^pb)[(c^pc)]   (c = -1: 2 controls).
Genome: cx[l, w] = source;  tf[l, w] = (a, b, c, pa, pb, pc).
P3 = probability that a mutated Toffoli gets 3 controls (env, default 0.3).
Op-model cost of a level: LCX + 7 if it has only 2-control gates, LCX + 13
if it has a 3-control gate (printed as est_fwd for the best genome).
Usage: python3 cpte_evo3.py test|logo L SEED MINUTES
Progress: one line / PEVERY s; checkpoint ckpt/evo3_<mode>_L<L>_s<seed>[_c<LCX>][_k3].npz/.json"""
import os, sys, time, json
import numpy as np
import numba as nb
import cpte_evo as E
from cpte_evo import NW, NWORD, fit_k, init_state, logo_bits

PEVERY = float(os.environ.get('PEVERY', '10'))
LCX = E.LCX
P = E.P
P3 = float(os.environ.get('P3', '0.3'))


@nb.njit(cache=True)
def layer(src, dst, cx, tf, l, t):
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
                b = tf[l, w, 1]; c = tf[l, w, 2]
                ma = ONES if tf[l, w, 3] else np.uint64(0)
                mb = ONES if tf[l, w, 4] else np.uint64(0)
                if c < 0:
                    for k in range(NWORD):
                        dst[w, k] ^= (src[a, k] ^ ma) & (src[b, k] ^ mb)
                else:
                    mc = ONES if tf[l, w, 5] else np.uint64(0)
                    for k in range(NWORD):
                        dst[w, k] ^= (src[a, k] ^ ma) & (src[b, k] ^ mb) & (src[c, k] ^ mc)


@nb.njit(cache=True)
def evaluate_from(st, cx, tf, T, li, P):
    for j in range(li, T):
        layer(st[j], st[j + 1], cx, tf, j, 1 if j % P == P - 1 else 0)


@nb.njit(cache=True)
def clear_conflicts(cx, tf, l, t, wires):
    for u in range(NW):
        if t == 0:
            if cx[l, u] < 0: continue
            g1 = cx[l, u]; g2 = -2; g3 = -2
        else:
            if tf[l, u, 0] < 0: continue
            g1 = tf[l, u, 0]; g2 = tf[l, u, 1]; g3 = tf[l, u, 2]
        for v in wires:
            if v == u or v == g1 or v == g2 or (g3 >= 0 and v == g3):
                if t == 0: cx[l, u] = -1
                else: tf[l, u, 0] = -1
                break


@nb.njit(cache=True)
def run(cx, tf, T, F, st, tmp, iters, fit0, pnone, p3, seed, K, P):
    np.random.seed(seed)
    fit = fit0; acc = 0
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
            n = 3 if np.random.random() < p3 else 2
            pick = np.random.permutation(NW)
            cs = [0, 0, 0]; m = 0
            for u in pick:
                if u != w and m < n:
                    cs[m] = u; m += 1
            wires = [w, cs[0], cs[1]]
            if n == 3: wires.append(cs[2])
            clear_conflicts(ccx, ctf, l, 1, wires)
            ctf[l, w, 0] = cs[0]; ctf[l, w, 1] = cs[1]; ctf[l, w, 2] = cs[2] if n == 3 else -1
            ctf[l, w, 3] = np.random.randint(2); ctf[l, w, 4] = np.random.randint(2)
            ctf[l, w, 5] = np.random.randint(2)
        li = l
        tmp[li] = st[li]
        evaluate_from(tmp, ccx, ctf, T, li, P)
        f = fit_k(tmp[T], F, K)[0]
        if f >= fit:
            if f > fit: acc += 1
            fit = f
            cx[:] = ccx; tf[:] = ctf
            for j in range(li + 1, T + 1):
                st[j] = tmp[j]
        if fit == 4096:
            return fit, acc, it + 1
    return fit, acc, iters


def empty(L):
    return -np.ones((L * P, NW), dtype=np.int64), -np.ones((L * P, NW, 6), dtype=np.int64)


def states(cx, tf, L):
    st = np.zeros((L * P + 1, NW, NWORD), dtype=np.uint64); st[0] = init_state()
    evaluate_from(st, cx, tf, L * P, 0, P)
    return st


def est_fwd(tf, L):
    """op-model forward depth: per level LCX + 7 (2-control only) or + 13 (any 3-control)"""
    d = 0
    for l in range(L):
        g = tf[l * P + P - 1]
        on = g[:, 0] >= 0
        d += LCX + (13 if (on & (g[:, 2] >= 0)).any() else (7 if on.any() else 0))
    return d


if __name__ == '__main__':
    mode, L, seed, minutes = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
    rng = np.random.default_rng(seed)
    tag = 'evo3_%s_L%d_s%d' % (mode, L, seed) + ('_c%d' % LCX if LCX != 1 else '')
    os.makedirs('ckpt', exist_ok=True)
    if mode == 'test':
        # planted target: most nonlinear wire of a dense random 2-control circuit (cpte_evo test)
        tcx, ttf = E.random_genome(L, np.random.default_rng(1000 + seed))
        S = E.states(tcx, ttf, L)[-1]
        from cptd_rot import walsh
        def unpack(x): return ((x[:, None] >> np.arange(64, dtype=np.uint64)) & np.uint64(1)).astype(np.uint8).reshape(-1)
        nl = [2048 - int(np.abs(walsh(unpack(S[w]))).max()) // 2 for w in range(NW)]
        F = S[int(np.argmax(nl))].copy()
        print('planted target: nonlinearity %d' % max(nl), flush=True)
    else:
        F = logo_bits()
    K = int(os.environ.get('FITK', '2'))
    tag += '_k%d' % K if K != 2 else ''
    RESTART = float(os.environ.get('RESTART', '90'))
    def fresh():
        cx, tf = empty(L)
        st = states(cx, tf, L)
        return cx, tf, st, st.copy(), fit_k(st[-1], F, K)[0]
    cx, tf, st, tmp, fit = fresh()
    best = (fit, cx.copy(), tf.copy()); nrs = 0
    t0 = time.time(); total = 0; last = t0; chunk = 2000; t_imp = t0; fit_prev = fit
    print('[%s] start fitness %d / 4096  P3 %.2f  restart after %.0fs without gain' % (tag, fit, P3, RESTART), flush=True)
    while True:
        c0 = time.time()
        fit, acc, n = run(cx, tf, L * P, F, st, tmp, chunk, fit, 0.1, P3, int(rng.integers(1 << 30)), K, P)
        total += n; now = time.time()
        if now - c0 > 0: chunk = max(200, int(chunk * min(4.0, (PEVERY / 2) / (now - c0))))
        if fit > fit_prev: t_imp = now; fit_prev = fit
        if fit > best[0]: best = (fit, cx.copy(), tf.copy())
        done = best[0] == 4096 or now - t0 > minutes * 60
        if now - last >= PEVERY or done:
            last = now
            on = best[2][:, :, 0] >= 0
            g = int((best[1] >= 0).sum()), int(on.sum()), int((on & (best[2][:, :, 2] >= 0)).sum())
            rec = dict(tag=tag, best=int(best[0]), current=int(fit), restarts=nrs, iters=total,
                       elapsed_s=round(now - t0), evals_per_s=round(total / (now - t0)),
                       cx=g[0], tof=g[1], tof3=g[2], est_fwd=est_fwd(best[2], L),
                       utc=time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now)))
            print('[%s] %s  %5ds  best %4d/4096  current %4d  restarts %d  iters %d (%d/s)  best: cx %d tof %d (3-ctl %d) est_fwd %d' %
                  (rec['utc'], tag, rec['elapsed_s'], best[0], fit, nrs, total, rec['evals_per_s'], *g, rec['est_fwd']), flush=True)
            np.savez('ckpt/%s.npz' % tag, cx=best[1], tf=best[2], F=F, L=L)
            json.dump(rec, open('ckpt/%s.json' % tag, 'w'))
            if done: break
        if now - t_imp > RESTART:
            cx, tf, st, tmp, fit = fresh(); nrs += 1; t_imp = now; fit_prev = fit
    S = states(best[1], best[2], L)[-1]
    print('[%s] final best %d / 4096  readout %s  restarts %d' % (tag, best[0], fit_k(S, F, K)[1:], nrs), flush=True)
