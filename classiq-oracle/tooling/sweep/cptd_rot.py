"""Rotation-readout checks (TETRIS idea: read products by parity rotations
instead of computing them with Toffolis).
Check 1: nonzero Walsh coefficients of F  ->  pure CX+Rz oracle needs every
         such parity on some wire once: rotation layers >= count / 18.
Check 2: on the 249 op list's value DAG, unfold each readout's operands into
         the values they were computed from (while <= KMAX variables).  A phase
         pi*g(V) on k held values = parity rotations on <= 2^k-1 parities, so
         the readout no longer waits for the unfolded Toffoli levels.
         Reports per readout: ready time (op model) before/after, k, parities
         (nonzero Walsh coefficients of g over V), and the single-mirror floor
         max_r 2*ready_r (unlimited wires, parity formation not counted).
Checkpoint: ckpt/rot_checks.json"""
import os, json, pickle
import numpy as np
from cpae_core import PROF, SHAPES, fvec

OPS = os.environ.get('CPEN_O1', '/home/user/classiq-challenge/cpen_o1.pkl')
N = 4096


def walsh(f):          # f: 0/1 vector length 2^n -> Walsh spectrum of (-1)^f
    w = (1 - 2 * f.astype(np.int64)).copy(); h = 1
    while h < len(w):
        w = w.reshape(-1, 2 * h); a, b = w[:, :h].copy(), w[:, h:].copy()
        w[:, :h], w[:, h:] = a + b, a - b; w = w.reshape(-1); h *= 2
    return w


def check1():
    f = fvec(SHAPES['LOGO'])
    w = walsh(f)
    nz = int((w[1:] != 0).sum())
    return dict(nonzero_walsh=nz, rot_layers_floor=int(np.ceil(nz / 18)))


def dag():
    ops = pickle.load(open(OPS, 'rb'))
    s = np.arange(N, dtype=np.int64)
    col = lambda w: ((s >> w) & 1).astype(np.uint8)
    vid, vals = {}, []
    def V(v):
        k = np.packbits(v).tobytes()
        if k not in vid: vid[k] = len(vals); vals.append(v.copy())
        return vid[k]
    ready, recipe = {}, {}
    for w in range(18): ready[V(col(w))] = 0
    zero, one = V(np.zeros(N, np.uint8)), V(np.ones(N, np.uint8))
    ready[zero] = ready[one] = 0
    TGT = {'x': 0, 'cx': 1, 'ccx': 2, 'ccx_dg': 2, 'c3x': 3, 'c3x_dg': 3}
    reads = []
    for op in ops:
        k, q = op[0], list(op[1:])
        vin = [V(col(w)) for w in q]
        if k == 'x':
            s = s ^ (1 << q[0]); v = V(col(q[0]))
            if ready[vin[0]] < ready.get(v, 1e9): ready[v] = ready[vin[0]]; recipe[v] = [vin[0]]
            continue
        prof = PROF[k]
        S = max(ready[vin[j]] - prof[j][0] + 1 for j in range(len(q)))
        if k in ('cz', 'ccz'):
            reads.append(vin); continue
        t = q[TGT[k]]
        if k == 'cx': s = s ^ (((s >> q[0]) & 1) << t)
        else:
            p = np.ones(N, dtype=np.int64)
            for w in q[:-1]: p &= (s >> w) & 1
            s = s ^ (p << t)
        v = V(col(t)); r = S + prof[TGT[k]][-1] - 1
        if r < ready.get(v, 1e9):
            ready[v] = r; recipe[v] = [vin[TGT[k]]] + [x for i, x in enumerate(vin) if i != TGT[k]]
    return vals, ready, recipe, reads, {zero, one}


def nparities(g, V, vals):
    """nonzero Walsh coeffs of g as a function of the k values in V
    (unseen patterns set to 0)"""
    V = list(V); k = len(V)
    idx = np.zeros(N, dtype=np.int64)
    for i, v in enumerate(V): idx |= vals[v].astype(np.int64) << i
    t = np.zeros(1 << k, dtype=np.uint8); t[idx] = g
    return int((walsh(t)[1:] != 0).sum())


def check2(kmax):
    vals, ready, recipe, reads, const = dag()
    # drop pairwise-cancelling readouts
    key = lambda r: tuple(sorted(r))
    cnt = {}
    for r in reads: cnt[key(r)] = cnt.get(key(r), 0) + 1
    reads = [list(k) for k, c in cnt.items() if c % 2]
    out = []
    for r in reads:
        g = np.ones(N, dtype=np.uint8)
        for v in r: g &= vals[v]
        Vs = set(r) - const
        t0 = max(ready[v] for v in Vs)
        best = (t0, len(Vs), set(Vs))
        while True:     # unfold the latest unfoldable value while <= kmax variables
            cand = sorted((v for v in Vs if v in recipe), key=lambda v: -ready[v])
            if not cand: break
            v = cand[0]
            V2 = (Vs - {v}) | (set(recipe[v]) - const)
            if len(V2) > kmax: break
            Vs = V2; t = max(ready[u] for u in Vs)
            if (t, len(Vs)) < best[:2]: best = (t, len(Vs), set(Vs))
        t, _, Vs = best
        out.append(dict(read=r, ready_before=t0, ready_after=t,
                        k=len(Vs), parities=nparities(g, Vs, vals)))
    floor_b = max(2 * o['ready_before'] for o in out)
    floor_a = max(2 * o['ready_after'] for o in out)
    return dict(kmax=kmax, readouts=out, floor_before=floor_b, floor_after=floor_a,
                total_parities=sum(o['parities'] for o in out))


if __name__ == '__main__':
    res = dict(check1=check1())
    print('check 1:', res['check1'], flush=True)
    for kmax in (3, 4, 5, 6, 7, 8):
        c = check2(kmax); res['k%d' % kmax] = c
        print('check 2 kmax=%d: floor %d -> %d (op model x2), total parities %d' %
              (kmax, c['floor_before'], c['floor_after'], c['total_parities']), flush=True)
        for o in c['readouts']:
            print('   ready %3d -> %3d  k=%d  parities %d' % (o['ready_before'], o['ready_after'], o['k'], o['parities']))
    os.makedirs('ckpt', exist_ok=True)
    json.dump(res, open('ckpt/rot_checks.json', 'w'), indent=1, default=int)
