"""Merge idea, steps 1-2 (read-only analysis of the 249 op list cpen_o1.pkl).
1. exact value sequence of every wire + the values each cz/ccz readout reads
2. single-mirror floor: with unlimited wires and 249's own formulas, a
   forward stream U must produce every readout value; the mirror U^-1
   removes them again, so total >= max_r (2*ready(r) + dur(r)) (op model).
Checkpoint: ckpt/merge1.pkl"""
import os, sys, pickle
import numpy as np
from cpae_core import PROF, model_depth

OPS = os.environ.get('CPEN_O1', '/home/user/classiq-challenge/cpen_o1.pkl')
ops = pickle.load(open(OPS, 'rb'))
N = 4096
st = np.arange(N, dtype=np.int64)
def col(s, w): return np.packbits(((s >> w) & 1).astype(np.uint8)).tobytes()
def apply(op, s):
    k, q = op[0], op[1:]
    if k == 'x': return s ^ (1 << q[0])
    if k == 'cx': return s ^ (((s >> q[0]) & 1) << q[1])
    if k in ('ccx', 'ccx_dg'): return s ^ ((((s >> q[0]) & 1) & ((s >> q[1]) & 1)) << q[2])
    if k in ('c3x', 'c3x_dg'): return s ^ ((((s >> q[0]) & 1) & ((s >> q[1]) & 1) & ((s >> q[2]) & 1)) << q[3])
    return s
TGT = {'x': 0, 'cx': 1, 'ccx': 2, 'ccx_dg': 2, 'c3x': 3, 'c3x_dg': 3}

vid = {}                       # value bytes -> id
def V(b):
    if b not in vid: vid[b] = len(vid)
    return vid[b]
ZERO = V(col(np.zeros(N, dtype=np.int64), 0))
ONE = V(col(np.full(N, 1, dtype=np.int64), 0))
ready = {}
for w in range(18):
    v = V(col(st, w)); ready[v] = 0
ready[ZERO] = 0; ready[ONE] = 0
seq = {w: [(-1, V(col(st, w)))] for w in range(18)}
reads = []                     # (op idx, kind, value ids, start, dur)
for i, op in enumerate(ops):
    k, q = op[0], list(op[1:])
    vin = [V(col(st, w)) for w in q]
    if k == 'x':               # free: complement is ready when its source is
        st = apply(op, st); v = V(col(st, q[0]))
        ready[v] = min(ready.get(v, 1e9), ready[vin[0]]); seq[q[0]].append((i, v)); continue
    prof = PROF[k]
    S = max(ready[vin[j]] - prof[j][0] + 1 for j in range(len(q)))
    dur = max(p[-1] for p in prof.values())
    if k in ('cz', 'ccz'):
        reads.append((i, k, vin, S, dur)); continue
    st = apply(op, st)
    t = q[TGT[k]]; v = V(col(st, t))
    ready[v] = min(ready.get(v, 1e9), S + prof[TGT[k]][-1] - 1)
    seq[t].append((i, v))

print('ops %d  model_depth %d  distinct values %d' % (len(ops), model_depth(ops), len(vid)))
anc = range(12, 18)
for w in range(18):
    ch = [v for _, v in seq[w]]
    z = sum(1 for a, b in zip(ch, ch[1:]) if b == ch[0] and a != ch[0])
    print('wire %2d: %3d writes, %2d distinct values, returns-to-initial %d' % (w, len(ch) - 1, len(set(ch)), z))
lb = 0
for i, k, vin, S, dur in reads:
    r = max(ready[v] for v in vin)
    lb = max(lb, 2 * r + dur)
    print('readout op %3d %-3s values %s  ready %3d' % (i, k, vin, r))
T = max(max(ready[v] for v in vin) for _, _, vin, _, _ in reads)
print('max readout-value ready time T = %d (op model)' % T)
print('single-mirror floor (unlimited wires, 249 formulas): %d op-model layers' % lb)
print('calibration: 249 real vs op model %d' % model_depth(ops))
os.makedirs('ckpt', exist_ok=True)
pickle.dump(dict(seq=seq, reads=reads, ready=ready, T=T, lb=lb), open('ckpt/merge1.pkl', 'wb'))
