"""Option 2 on the 249 circuit: per-u3 atom split mode search.
cpev pipeline splits every u3 into Rz/Rx atoms with one fixed rule (fewest
atoms); the split decides which atoms commute through CX controls (Rz) or
targets (Rx), i.e. the scheduling freedom.  Here the mode vector is searched:
change the mode of K random u3s, split, schedule (greedy + reverse polish),
keep if depth (then CX) does not get worse.  Best result is rebuilt,
transpiled to u3/cx and statevector-checked.
Usage: python3 cpto_mode.py SEED MINUTES [QASM]
Progress every 10 s; best exact circuit ckpt/mode_best_s<seed>.qasm"""
import sys, time, json
import numpy as np
from cpae_core import sv_check_gp          # sweep copy (has the global-phase check)
sys.path.insert(0, '/home/user/classiq-challenge')
from qiskit import QuantumCircuit, transpile, qasm2
import cpej_atoms as A, cpej_ir as R
from cpej_rand import minatom_mode
from cpev_pipe import to_gates, sched_atoms

seed, minutes = int(sys.argv[1]), float(sys.argv[2])
src = sys.argv[3] if len(sys.argv) > 3 else '../cpev_best.qasm'
rng = np.random.default_rng(seed)
qc = QuantumCircuit.from_qasm_file(src)
g = to_gates(qc)
uidx = [i for i, x in enumerate(g) if x[0] == 'u']
mode = np.array(minatom_mode(g))


def evaluate(mode):
    at, ph = A.split(g, mode)
    d, c, o = sched_atoms(at, 6, 18)
    return d, c, o


d0, c0, o0 = evaluate(mode)
best = (d0, c0, mode.copy(), o0)
print('[mode s%d] source %s: u3 %d  baseline (min-atom modes) depth %d cx %d' % (seed, src, len(uidx), d0, c0), flush=True)
t0 = time.time(); last = t0; it = 0; acc = 0
cur = (d0, c0, mode.copy())
while time.time() - t0 < minutes * 60:
    it += 1
    m = cur[2].copy()
    K = 1 + int(rng.integers(8))
    for k in rng.choice(len(mode), K, replace=False):
        m[k] = int(rng.integers(4))
    d, c, o = evaluate(m)
    if (d, c) <= (cur[0], cur[1]):
        cur = (d, c, m); acc += 1
        if (d, c) < (best[0], best[1]):
            best = (d, c, m.copy(), o)
            print('   new best depth %d cx %d (it %d)' % (d, c, it), flush=True)
    if time.time() - last > 10:
        last = time.time()
        print('[mode s%d] %5ds  it %d  accepted %d  current %d/%d  best %d/%d' %
              (seed, last - t0, it, acc, cur[0], cur[1], best[0], best[1]), flush=True)
gm = A.merge_runs(best[3], 18)
out = R.to_qc(gm, 18, fixphase=False)
t = transpile(out, basis_gates=['u3', 'cx'], optimization_level=0)
err, leak = sv_check_gp(t, 'LOGO')
print('[mode s%d] final best depth %d cx %d (sched)  rebuilt u3/cx depth %d cx %d  err %.2e leak %.2e' %
      (seed, best[0], best[1], t.depth(), t.count_ops().get('cx', 0), err, leak), flush=True)
if err < 1e-10 and leak < 1e-20:
    qasm2.dump(t, 'ckpt/mode_best_s%d.qasm' % seed)
json.dump(dict(baseline=[d0, c0], best=[best[0], best[1]], rebuilt=[t.depth(), t.count_ops().get('cx', 0)], err=err, leak=leak),
          open('ckpt/mode_s%d.json' % seed, 'w'))
