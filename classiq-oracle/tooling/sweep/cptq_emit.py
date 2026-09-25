"""Emit + verify a cptq_rank gate list.
Gates (L, a, b, pa, pb, t): level L Toffoli t ^= (a^pa)(b^pb) (same-level
gates on disjoint wires).  Features: const, x_i (Z at t=0), each Toffoli
product (Z before + after its target), pairs / triples of the turnaround
values (CZ / CCZ).  Exact GF(2) solve (prefers cheap features: pivots taken
in the order const, inputs, products, pairs, triples), then forward +
phase gates + mirror.  Checks: classical phase, identity, statevector, real
depth/cx.  Usage: python3 cptq_emit.py ckpt/qrank_s<k>.pkl"""
import sys, pickle
import numpy as np
import cpte_evo as E
from cpae_core import mirror, ops_to_qc, real_depth, sv_check_gp, SHAPES, fvec
from cpth_emit import replay

ONES = np.uint64(0xFFFFFFFFFFFFFFFF)


def bits(v): return ((v[:, None] >> np.arange(64, dtype=np.uint64)) & np.uint64(1)).astype(np.uint8).reshape(-1)


def solve(rows, Fv):
    A = np.array([bits(r) for r in rows], dtype=np.uint8).T.copy()      # 4096 x nf
    b = bits(Fv).copy(); nf = A.shape[1]
    M = np.concatenate([A, b[:, None]], axis=1)
    piv = []; r = 0
    for c in range(nf):
        nz = np.nonzero(M[r:, c])[0]
        if len(nz) == 0: continue
        p = r + nz[0]
        if p != r: M[[r, p]] = M[[p, r]]
        o = np.nonzero(M[:, c])[0]; o = o[o != r]; M[o] ^= M[r]
        piv.append(c); r += 1
        if r == M.shape[0]: break
    if M[r:, nf].any(): return None
    x = np.zeros(nf, dtype=np.uint8)
    for i, c in enumerate(piv): x[c] = M[i, nf]
    return [i for i in range(nf) if x[i]]


if __name__ == '__main__':
    d = pickle.load(open(sys.argv[1], 'rb')); gates = d['gates']
    S = E.init_state().copy()
    rows = [np.full(64, ONES)] + [S[i].copy() for i in range(12)]
    lab = [('const',)] + [('x', i) for i in range(12)]
    fwd = []
    levels = sorted(set(g[0] for g in gates))
    for L in levels:
        S0 = S.copy()
        for gi, (l, a, b, pa, pb, t) in enumerate(gates):
            if l != L: continue
            p = (S0[a] ^ (ONES if pa else np.uint64(0))) & (S0[b] ^ (ONES if pb else np.uint64(0)))
            S[t] = S[t] ^ p; rows.append(p); lab.append(('tof', gi))
    for a in range(18):
        for b in range(a + 1, 18):
            rows.append(S[a] & S[b]); lab.append(('cz', a, b))
    for a in range(18):
        for b in range(a + 1, 18):
            for c in range(b + 1, 18):
                rows.append(S[a] & S[b] & S[c]); lab.append(('ccz', a, b, c))
    sel = solve(rows, E.logo_bits())
    if sel is None: print('F not in span'); sys.exit(1)
    kinds = {}
    for i in sel: kinds[lab[i][0]] = kinds.get(lab[i][0], 0) + 1
    print('exact solve: features used %d  %s' % (len(sel), kinds))
    ztof = set(lab[i][1] for i in sel if lab[i][0] == 'tof')
    ops = [('z', lab[i][1]) for i in sel if lab[i][0] == 'x']
    for L in levels:
        for gi, (l, a, b, pa, pb, t) in enumerate(gates):
            if l != L: continue
            fl = [q for q, pq in ((a, pa), (b, pb)) if pq]
            if gi in ztof: ops.append(('z', t))
            ops += [('x', q) for q in fl]; ops.append(('ccx', a, b, t)); ops += [('x', q) for q in fl]
            if gi in ztof: ops.append(('z', t))
    perm = [o for o in ops if o[0] != 'z']
    turn = [('cz', lab[i][1], lab[i][2]) for i in sel if lab[i][0] == 'cz'] + \
           [('ccz', lab[i][1], lab[i][2], lab[i][3]) for i in sel if lab[i][0] == 'ccz']
    full = ops + turn + mirror(perm)
    F = fvec(SHAPES['LOGO']).astype(np.int64)
    print('classical (mismatches, identity):', replay(full, F))
    qc = ops_to_qc(full)
    print('real depth/cx:', real_depth(qc), '  forward-only real depth/cx:', real_depth(ops_to_qc(perm)))
    print('statevector (err, leak):', sv_check_gp(qc, 'LOGO'))
    pickle.dump(full, open(sys.argv[1].replace('.pkl', '_ops.pkl'), 'wb'))
