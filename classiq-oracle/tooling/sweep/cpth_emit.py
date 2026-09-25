"""Emit + verify a cpth_span genome whose fitness is 4096.
Forward stream (CX / RCCX per layer) with phase gates on the chosen features:
  x_i            -> Z on data wire i at t = 0
  Toffoli (j, w) -> Z on w just before and just after that Toffoli
  pair (a, b)    -> CZ(a, b) at the turnaround
then the mirror of the forward stream (no phase gates).  Checks: classical
phase == F, identity, statevector (err, leak), real depth/cx.
Usage: [CZ=1] [LCX=1] python3 cpth_emit.py ckpt/span_....npz"""
import sys, os, pickle
import numpy as np
import cpte_evo as E
import cpth_span as S
from cpae_core import mirror, ops_to_qc, real_depth, sv_check_gp, SHAPES, fvec
from cptf_sched import classical

NW = 18


def features(st, tf, T, P, cz):
    """same order as cpth_span.fitness, with labels"""
    lab = [('const',)]
    rows = [np.full(64, np.uint64(0xFFFFFFFFFFFFFFFF))]
    for i in range(12): rows.append(st[0, i]); lab.append(('x', i))
    for j in range(T):
        if j % P != P - 1: continue
        for w in range(NW):
            if tf[j, w, 0] >= 0: rows.append(st[j + 1, w] ^ st[j, w]); lab.append(('tof', j, w))
    if cz:
        s0 = 0 if cz == 2 else T
        for s in range(s0, T + 1, P):
            for a in range(NW):
                for b in range(a + 1, NW): rows.append(st[s, a] & st[s, b]); lab.append(('cz', a, b, s))
    if cz == 3:
        for a in range(NW):
            for b in range(a + 1, NW):
                for c in range(b + 1, NW): rows.append(st[T, a] & st[T, b] & st[T, c]); lab.append(('ccz', a, b, c))
    return np.array(rows), lab


def solve_exact(rows, Fv):
    """exact GF(2) solve: F as XOR of feature rows (returns selected indices or None)"""
    bits = lambda v: ((v[:, None] >> np.arange(64, dtype=np.uint64)) & np.uint64(1)).astype(np.uint8).reshape(-1)
    A = np.array([bits(r) for r in rows], dtype=np.uint8).T          # 4096 x nf
    b = bits(Fv).copy(); nf = A.shape[1]
    M = np.concatenate([A, b[:, None], np.eye(4096, dtype=np.uint8)[:, :0]], axis=1)
    piv = []; r = 0
    for c in range(nf):
        nz = np.nonzero(M[r:, c])[0]
        if len(nz) == 0: continue
        p = r + nz[0]
        if p != r: M[[r, p]] = M[[p, r]]
        o = np.nonzero(M[:, c])[0]; o = o[o != r]; M[o] ^= M[r]
        piv.append(c); r += 1
        if r == 4096: break
    if M[r:, nf].any(): return None
    x = np.zeros(nf, dtype=np.uint8)
    for i, c in enumerate(piv): x[c] = M[i, nf]
    return [i for i in range(nf) if x[i]]


def pursuit(rows, Fv):
    res = Fv.copy(); pick = np.zeros(len(rows), dtype=np.int64)
    w = lambda v: int(sum(bin(int(t)).count('1') for t in v))
    cur = w(res)
    while cur:
        ws = [w(res ^ r) for r in rows]
        i = int(np.argmin(ws))
        if ws[i] >= cur: break
        res ^= rows[i]; pick[i] ^= 1; cur = ws[i]
    return cur, [i for i in range(len(rows)) if pick[i]]


def emit(cx, tf, L, sel, lab):
    P = E.P; T = L * P
    zt = {}
    for i in sel:
        if lab[i][0] == 'tof': zt[(lab[i][1], lab[i][2])] = 1
    turn = [('cz', lab[i][1], lab[i][2]) for i in sel if lab[i][0] == 'cz' and lab[i][3] == T]
    turn += [('ccz', lab[i][1], lab[i][2], lab[i][3]) for i in sel if lab[i][0] == 'ccz']
    mid = {}
    for i in sel:
        if lab[i][0] == 'cz' and lab[i][3] != T: mid.setdefault(lab[i][3], []).append(('cz', lab[i][1], lab[i][2]))
    fwd, pre = [], []
    for i in sel:
        if lab[i][0] == 'x': pre.append(('z', lab[i][1]))
    for j in range(T):
        fwd += mid.get(j, [])
        if j % P != P - 1:
            for w in range(NW):
                if cx[j, w] >= 0: fwd.append(('cx', int(cx[j, w]), w))
        else:
            for w in range(NW):
                a = tf[j, w, 0]
                if a < 0: continue
                b, pa, pb = tf[j, w, 1], tf[j, w, 2], tf[j, w, 3]
                if (j, w) in zt: fwd.append(('z', w))
                fl = [q for q, p in ((int(a), pa), (int(b), pb)) if p]
                fwd += [('x', q) for q in fl]
                fwd.append(('ccx', int(a), int(b), w))
                fwd += [('x', q) for q in fl]
                if (j, w) in zt: fwd.append(('z', w))
    perm = [o for o in fwd if o[0] not in ('z', 'cz')]
    return pre + fwd + turn + mirror(perm)


def replay(ops, F):
    s = np.arange(4096, dtype=np.int64); ph = np.zeros(4096, dtype=np.int64)
    b = lambda w: (s >> w) & 1
    for op in ops:
        k, q = op[0], op[1:]
        if k == 'z': ph ^= b(q[0])
        else:
            if k == 'x': s = s ^ (1 << q[0])
            elif k == 'cx': s = s ^ (b(q[0]) << q[1])
            elif k.startswith('ccx'): s = s ^ ((b(q[0]) & b(q[1])) << q[2])
            elif k == 'cz': ph ^= b(q[0]) & b(q[1])
            elif k == 'ccz': ph ^= b(q[0]) & b(q[1]) & b(q[2])
    return int((ph != F).sum()), bool((s == np.arange(4096)).all())


if __name__ == '__main__':
    d = np.load(sys.argv[1]); cx, tf, L = d['cx'], d['tf'], int(d['L'])
    P = E.P; T = L * P
    st = E.states(cx, tf, L)                      # natural bit order
    rows, lab = features(st, tf, T, P, S.CZ)
    Fv = E.logo_bits()
    sel = solve_exact(rows, Fv)
    if sel is None: print('F not in the feature span'); sys.exit(1)
    print('exact: features used %d' % len(sel))
    ops = emit(cx, tf, L, sel, lab)
    F = fvec(SHAPES['LOGO']).astype(np.int64)
    mism, ident = replay(ops, F)
    print('classical: phase mismatches %d  identity %s' % (mism, ident))
    qc = ops_to_qc([o if o[0] != 'z' else ('z', o[1]) for o in ops])
    print('real depth/cx', real_depth(qc))
    print('statevector (err, leak)', sv_check_gp(qc, 'LOGO'))
    pickle.dump(ops, open(sys.argv[1].replace('.npz', '_ops.pkl'), 'wb'))
