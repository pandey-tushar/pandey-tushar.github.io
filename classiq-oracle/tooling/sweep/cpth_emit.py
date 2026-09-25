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
        for a in range(NW):
            for b in range(a + 1, NW): rows.append(st[T, a] & st[T, b]); lab.append(('cz', a, b))
    return np.array(rows), lab


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
    fwd, pre = [], []
    for i in sel:
        if lab[i][0] == 'x': pre.append(('z', lab[i][1]))
    for j in range(T):
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
    turn = [('cz', lab[i][1], lab[i][2]) for i in sel if lab[i][0] == 'cz']
    perm = [o for o in fwd if o[0] != 'z']
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
    return int((ph != F).sum()), bool((s == np.arange(4096)).all())


if __name__ == '__main__':
    d = np.load(sys.argv[1]); cx, tf, L = d['cx'], d['tf'], int(d['L'])
    P = E.P; T = L * P
    st = E.states(cx, tf, L)                      # natural bit order
    rows, lab = features(st, tf, T, P, S.CZ)
    Fv = E.logo_bits()
    dist, sel = pursuit(rows, Fv)
    print('pursuit distance %d  features used %d' % (dist, len(sel)))
    if dist: sys.exit(1)
    ops = emit(cx, tf, L, sel, lab)
    F = fvec(SHAPES['LOGO']).astype(np.int64)
    mism, ident = replay(ops, F)
    print('classical: phase mismatches %d  identity %s' % (mism, ident))
    qc = ops_to_qc([o if o[0] != 'z' else ('z', o[1]) for o in ops])
    print('real depth/cx', real_depth(qc))
    print('statevector (err, leak)', sv_check_gp(qc, 'LOGO'))
    pickle.dump(ops, open(sys.argv[1].replace('.npz', '_ops.pkl'), 'wb'))
