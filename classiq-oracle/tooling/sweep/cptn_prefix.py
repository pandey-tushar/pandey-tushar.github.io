"""Shortest prefix of the 249 op list whose phase features span F.
Features after op t: inputs, constant, Toffoli products of ops[0..t], and
pair (PAIRS=1) / triple (TRIPLES=1) products of values held on the wires at
the same state (any state <= t).  Circuit if F is in the span:
prefix + phase gates (Z / CZ / CCZ at their states) + mirror(prefix).
Incremental GF(2) basis (numba), membership of F checked after every op.
Usage: [PAIRS=1] [TRIPLES=0] python3 cptn_prefix.py
Output: one line per 20 ops; ckpt/prefix_p<P>_t<T>.json"""
import os, sys, time, json, pickle
import numpy as np
import numba as nb
import cpte_evo as E
from cpte_evo import popc, NWORD

PAIRS = int(os.environ.get('PAIRS', '1'))
TRIPLES = int(os.environ.get('TRIPLES', '0'))
OPS = os.environ.get('CPEN_O1', '/home/user/classiq-challenge/cpen_o1.pkl')


@nb.njit(cache=True)
def insert(basis, piv, nb_, v):
    """reduce v against basis (pivot = lowest set bit); add if independent. returns new size"""
    r = v.copy()
    for j in range(nb_):
        w = piv[j] >> 6; b = piv[j] & 63
        if (r[w] >> np.uint64(b)) & np.uint64(1):
            for k in range(NWORD): r[k] ^= basis[j, k]
    for k in range(NWORD):
        if r[k] != 0:
            x = r[k]; b = 0
            while (x >> np.uint64(b)) & np.uint64(1) == 0: b += 1
            for kk in range(NWORD): basis[nb_, kk] = r[kk]
            piv[nb_] = k * 64 + b
            return nb_ + 1
    return nb_


@nb.njit(cache=True)
def member(basis, piv, nb_, v):
    r = v.copy()
    for j in range(nb_):
        w = piv[j] >> 6; b = piv[j] & 63
        if (r[w] >> np.uint64(b)) & np.uint64(1):
            for k in range(NWORD): r[k] ^= basis[j, k]
    s = 0
    for k in range(NWORD): s += popc(r[k])
    return s


@nb.njit(cache=True)
def add_state(basis, piv, nb_, S, pairs, triples):
    n = S.shape[0]
    tmp = np.empty(NWORD, dtype=np.uint64)
    if pairs:
        for a in range(n):
            for b in range(a + 1, n):
                for k in range(NWORD): tmp[k] = S[a, k] & S[b, k]
                nb_ = insert(basis, piv, nb_, tmp)
                if triples:
                    for c in range(b + 1, n):
                        for k in range(NWORD): tmp[k] = S[a, k] & S[b, k] & S[c, k]
                        nb_ = insert(basis, piv, nb_, tmp)
    return nb_


if __name__ == '__main__':
    ops = pickle.load(open(OPS, 'rb'))
    N = 4096; s = np.arange(N, dtype=np.int64)
    Fv = E.logo_bits()
    def wires(s): return np.array([E.pack(((s >> w) & 1).astype(np.uint8)) for w in range(18)])
    basis = np.zeros((4096, NWORD), dtype=np.uint64); piv = np.zeros(4096, dtype=np.int64); nb_ = 0
    nb_ = insert(basis, piv, nb_, np.full(NWORD, np.uint64(0xFFFFFFFFFFFFFFFF)))
    W0 = wires(s)
    for i in range(12): nb_ = insert(basis, piv, nb_, W0[i])
    nb_ = add_state(basis, piv, nb_, W0, PAIRS, TRIPLES)
    t0 = time.time(); hit = None; ntof = 0
    for t, op in enumerate(ops):
        k, q = op[0], list(op[1:])
        if k in ('cz', 'ccz'): continue            # 249's own readouts are NOT used
        if k == 'x': s = s ^ (1 << q[0])
        elif k == 'cx': s = s ^ (((s >> q[0]) & 1) << q[1])
        elif k[:3] in ('ccx', 'c3x'):
            p = np.ones(N, dtype=np.int64)
            for w in q[:-1]: p &= (s >> w) & 1
            nb_ = insert(basis, piv, nb_, E.pack(p.astype(np.uint8))); ntof += 1
            s = s ^ (p << q[-1])
        nb_ = add_state(basis, piv, nb_, wires(s), PAIRS, TRIPLES)
        d = member(basis, piv, nb_, Fv)
        if t % 20 == 0 or d == 0:
            print('op %3d/%d  toffolis %3d  rank %4d  residual weight after reduction %4d  %.0fs' %
                  (t, len(ops), ntof, nb_, d, time.time() - t0), flush=True)
        if d == 0:
            hit = t; break
    rec = dict(pairs=PAIRS, triples=TRIPLES, hit_op=hit, rank=int(nb_), ops=len(ops))
    if hit is not None:
        from cpae_core import ops_to_qc, real_depth
        pre = [o for o in ops[:hit + 1] if o[0] not in ('cz', 'ccz')]
        dep = real_depth(ops_to_qc(pre))
        rec['prefix_real_depth_cx'] = list(dep)
        print('F in span after op %d (of %d); prefix real depth/cx %s -> prefix + mirror ~ %d + phase layer' %
              (hit, len(ops), dep, 2 * dep[0]), flush=True)
    else:
        print('F not in span even for the full list (rank %d)' % nb_, flush=True)
    json.dump(rec, open('ckpt/prefix_p%d_t%d.json' % (PAIRS, TRIPLES), 'w'))
