"""Emit + verify a cptd_merge3 solution: forward stream with readouts, then
one mirror.  Reports control-fanout conflicts (relaxed in the SAT model),
exact classical phase check, statevector check, real depth.
Usage: python3 cptd_emit3.py ckpt/merge3_R<R>.pkl"""
import sys, pickle
import numpy as np
from cpae_core import mirror, ops_to_qc, real_depth, sv_check_gp, SHAPES, fvec

NW, N = 18, 4096


def emit(d):
    sol, P, vals, reads = d['sol'], d['P'], d['vals'], d['reads']
    s = np.arange(N, dtype=np.int64)
    bit = lambda w: ((s >> w) & 1).astype(np.uint8)
    same = lambda u, v: np.array_equal(u, v)
    def find(v, excl=()):       # wire holding v or its complement -> (wire, needs x)
        for w in range(NW):
            if w in excl: continue
            b = bit(w)
            if same(b, v): return w, False
            if same(b, v ^ 1): return w, True
        raise RuntimeError('value not held')
    stream, conflicts = [], 0
    def readouts(st):
        for k, sts in enumerate(sol['rds']):
            if sts and sts[0] == st:
                ws = []
                for v in reads[k][1]:
                    w, fl = find(v, ws); ws.append(w)
                    if fl: stream.append(('x', w))
                stream.append(('cz' if len(ws) == 2 else 'ccz',) + tuple(ws))
                for w, v in zip(ws, reads[k][1]):
                    if not same(bit(w), v): stream.append(('x', w))
    K = sol['lcx'] + 1
    for r, (cxl, tfs) in enumerate(sol['layers']):
        for l, cxs in enumerate(cxl):
            readouts(K * r + l)
            for sw, tw in cxs:
                stream.append(('cx', sw, tw)); s = s ^ (((s >> sw) & 1) << tw)
        readouts(K * r + K - 1)
        written = set(w for w, _ in tfs); used = {}
        plan = []
        for w, j in tfs:
            cs, pol = P[j]
            ctl = []
            for i, c in enumerate(cs):
                need = vals[c] ^ ((pol >> i) & 1)
                cw, fl = find(need, set(written) | set(ctl))
                used[cw] = used.get(cw, 0) + 1
                ctl.append(cw)
            plan.append((w, ctl, cs, pol))
        conflicts += sum(v - 1 for v in used.values() if v > 1)
        for w, ctl, cs, pol in plan:
            need = [vals[c] ^ ((pol >> i) & 1) for i, c in enumerate(cs)]
            fl = [cw for cw, v in zip(ctl, need) if not same(bit(cw), v)]
            p = np.ones(N, dtype=np.uint8)
            for v in need: p &= v
            stream += [('x', cw) for cw in fl]
            stream.append(('ccx' if len(ctl) == 2 else 'c3x',) + tuple(ctl) + (w,))
            stream += [('x', cw) for cw in fl]
            s = s ^ (p.astype(np.int64) << w)
    readouts(K * len(sol['layers']))
    fwd = [o for o in stream if o[0] not in ('cz', 'ccz')]
    return stream + mirror(fwd), conflicts


def classical(ops):
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
    return int((ph != fvec(SHAPES['LOGO'])).sum()), bool((s == np.arange(N)).all())


if __name__ == '__main__':
    d = pickle.load(open(sys.argv[1], 'rb'))
    full, conf = emit(d)
    mism, ident = classical(full)
    print('ops %d  fanout conflicts %d  classical mism %d  identity %s' % (len(full), conf, mism, ident))
    qc = ops_to_qc(full)
    print('real depth/cx', real_depth(qc))
    print('statevector (err, leak)', sv_check_gp(qc, 'LOGO'))
    pickle.dump(full, open(sys.argv[1].replace('.pkl', '_ops.pkl'), 'wb'))
