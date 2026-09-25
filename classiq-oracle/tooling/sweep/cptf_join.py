"""Mid-stream uncompute measurement: join the six exact single-readout
segments (each = forward + readout + its own mirror, from cptf_sched) in
sequence.  The phases XOR to F, every segment returns the wires, so the
joined circuit is exact.  Orders: all 720, ranked by op-model depth; the best
TOP are measured with the real transpile.
Usage: python3 cptf_join.py [TOP]
Output: ckpt/join.json, best joined op list ckpt/join_best.pkl"""
import sys, glob, pickle, json, itertools, time
import numpy as np
from cpae_core import ops_to_qc, real_depth, model_depth, SHAPES, fvec
from cptf_sched import classical

TOP = int(sys.argv[1]) if len(sys.argv) > 1 else 12
F = fvec(SHAPES['LOGO']).astype(np.int64)
seg = {}
for f in glob.glob('ckpt/sched_*_best.pkl'):
    d = pickle.load(open(f, 'rb'))
    r = d.get('reads')
    if r is None or ',' in str(r): continue
    k = int(r)
    if k not in seg or tuple(d['depth']) < seg[k][0]: seg[k] = (tuple(d['depth']), d['ops'], f)
for k in sorted(seg): print('readout %d: real depth/cx %s  (%s)' % (k, seg[k][0], seg[k][2]), flush=True)
missing = [k for k in range(6) if k not in seg]
if missing: print('missing segments', missing); sys.exit(1)
print('sum of segment depths: %d' % sum(seg[k][0][0] for k in range(6)), flush=True)
t0 = time.time()
cands = []
for order in itertools.permutations(range(6)):
    ops = [o for k in order for o in seg[k][1]]
    cands.append((model_depth(ops), order))
cands.sort()
print('model depth over 720 orders: best %s  worst %s  (%.0fs)' % (cands[0][0], cands[-1][0], time.time() - t0), flush=True)
res = []
for md, order in cands[:TOP]:
    ops = [o for k in order for o in seg[k][1]]
    mism, ident = classical(ops, F)
    dep = real_depth(ops_to_qc(ops))
    res.append(dict(order=list(order), model=md, real=list(dep), mism=mism, identity=ident))
    print('order %s  model %s  real depth/cx %s  phase mism %d  identity %s' % (order, md, dep, mism, ident), flush=True)
best = min((r for r in res if r['mism'] == 0 and r['identity']), key=lambda r: tuple(r['real']))
json.dump(dict(segments={k: list(seg[k][0]) for k in seg}, results=res, best=best), open('ckpt/join.json', 'w'), indent=1)
pickle.dump([o for k in best['order'] for o in seg[k][1]], open('ckpt/join_best.pkl', 'wb'))
print('best joined: order %s  real depth/cx %s' % (best['order'], best['real']), flush=True)
