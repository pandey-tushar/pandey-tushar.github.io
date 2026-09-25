"""Option 1 (last try): BQSKit block resynthesis of the 249 circuit.
compile(optimization_level=LVL, max_synthesis_size=BS, synthesis_epsilon=1e-12);
BQSKit logs its passes (INFO) as progress.  Result -> qiskit transpile(u3,cx,
lvl 2) -> depth/cx -> statevector check (error must stay < 1e-10).
Usage: python3 cptg_bqskit.py LVL BS
Output: ckpt/bqskit_L<LVL>_B<BS>.qasm (if exact), ckpt/bqskit_L<LVL>_B<BS>.json"""
import sys, json, time, logging
from bqskit import Circuit, compile
from bqskit.ext import bqskit_to_qiskit
from qiskit import transpile, qasm2
from cpae_core import sv_check_gp

LVL, BS = int(sys.argv[1]), int(sys.argv[2])
tag = 'bqskit_L%d_B%d' % (LVL, BS)
logging.basicConfig(level=logging.WARNING, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S'); logging.getLogger('bqskit').setLevel(logging.INFO)
t0 = time.time()
c = Circuit.from_file('../cpev_best.qasm')
print('[%s] source gates %d  depth(bqskit) %d' % (tag, c.num_operations, c.depth), flush=True)
out = compile(c, optimization_level=LVL, max_synthesis_size=BS, synthesis_epsilon=1e-12,
              error_threshold=1e-10, seed=1, num_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 1)
print('[%s] bqskit output gates %d  %s' % (tag, out.num_operations, dict(out.gate_counts)), flush=True)
qc = bqskit_to_qiskit(out)
t = transpile(qc, basis_gates=['u3', 'cx'], optimization_level=2)
d, cx = t.depth(), t.count_ops().get('cx', 0)
err, leak = sv_check_gp(t, 'LOGO')
ok = err < 1e-10 and leak < 1e-20
print('[%s] result depth %d cx %d  err %.2e leak %.2e  exact %s  %.0fs' % (tag, d, cx, err, leak, ok, time.time() - t0), flush=True)
if ok: qasm2.dump(t, 'ckpt/%s.qasm' % tag)
json.dump(dict(depth=d, cx=cx, err=err, leak=leak, exact=ok, sec=round(time.time() - t0)), open('ckpt/%s.json' % tag, 'w'))
