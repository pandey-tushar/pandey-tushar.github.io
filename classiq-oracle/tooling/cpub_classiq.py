"""CP-UB: hand the WHOLE truth table of F to Classiq's synthesis engine and let it
do the width-18 synthesis (ancilla allocation, uncomputation, depth optimisation).
Run LOCALLY with an authenticated classiq SDK (this container has neither).

Variants (each synthesized with Constraints(max_width=18, optimization_parameter=depth)):
  kick   : aux in |->, aux ^= ESOP(x)   (phase kickback; 59 cubes, 519 literals)
  phase  : phase(ESOP(x), pi)           (arithmetic phase statement, if the SDK accepts a bitwise expression)
For every variant: export QASM2, transpile with qiskit to u3/cx (opt 3), print depth and CX,
verify the phase on all 4096 inputs by statevector (data = qubits 0-11 or, if not, the last 12).

usage: python3 cpub_classiq.py [kick|phase|all]      (default all)
Needs: classiq (authenticated), qiskit, sweep/eda/logo_cubes.txt, cpae_core.py (same folder).
Paste the printed lines back; every number is a measurement."""
import os, sys, time, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
CUBES = os.path.join(HERE, 'sweep', 'eda', 'logo_cubes.txt')


def load_cubes():
    """59 cubes; char i = input i: '1' literal x_i, '0' literal ~x_i, '-' absent"""
    cubes = []
    for ln in open(CUBES):
        ln = ln.strip()
        if len(ln) == 12 and set(ln) <= set('01-'): cubes.append(ln)
    assert len(cubes) == 59, len(cubes)
    return cubes


def cubes_truth(cubes):
    f = np.zeros(4096, dtype=np.uint8)
    for i in range(4096):
        v = 0
        for c in cubes:
            ok = all((ch == '-') or (int(ch) == ((i >> k) & 1)) for k, ch in enumerate(c))
            v ^= int(ok)
        f[i] = v
    return f


def esop_expr(x, cubes):
    """symbolic ESOP over the quantum bits x[0..11]"""
    terms = []
    for c in cubes:
        lits = [x[k] if ch == '1' else ~x[k] for k, ch in enumerate(c) if ch != '-']
        t = lits[0]
        for l in lits[1:]: t = t & l
        terms.append(t)
    e = terms[0]
    for t in terms[1:]: e = e ^ t
    return e


def build(variant, cubes):
    from classiq import (Constraints, Output, QArray, QBit, QNum, X, H, allocate,
                         create_model, qfunc, within_apply)
    if variant == 'kick':
        @qfunc
        def flip_f(x: QArray[QBit, 12], aux: QBit) -> None:
            aux ^= esop_expr(x, cubes)

        @qfunc
        def minus(aux: QBit) -> None:
            X(aux); H(aux)

        @qfunc
        def main(x: Output[QArray[QBit, 12]]) -> None:
            allocate(x)
            aux = QBit('aux'); allocate(aux)
            within_apply(lambda: minus(aux), lambda: flip_f(x, aux))
    elif variant == 'phase':
        from classiq import phase
        @qfunc
        def main(x: Output[QArray[QBit, 12]]) -> None:
            allocate(x)
            phase(esop_expr(x, cubes), math.pi)
    else:
        raise ValueError(variant)
    cons = Constraints(max_width=18, optimization_parameter='depth')
    return create_model(main, constraints=cons)


def measure(qasm, f):
    from qiskit import QuantumCircuit, transpile
    from qiskit.quantum_info import Statevector
    qc = QuantumCircuit.from_qasm_str(qasm)
    t = transpile(qc, basis_gates=['u3', 'cx'], optimization_level=3)
    d, cx, w = t.depth(), t.count_ops().get('cx', 0), t.num_qubits
    want = np.where(f == 1, -1.0, 1.0)
    res = {}
    for name, data in (('q0-11', list(range(12))), ('last12', list(range(w - 12, w)))):
        if w < 12: break
        pre = QuantumCircuit(w)
        for q in data: pre.h(q)
        sv = np.asarray(Statevector(pre.compose(t)))
        # amplitude of basis state with data bits = i, all other qubits 0
        idx = np.zeros(4096, dtype=np.int64)
        for k, q in enumerate(data): idx |= ((np.arange(4096) >> k) & 1) << q
        a = sv[idx] * 64.0
        ph = a[0] / abs(a[0]) if abs(a[0]) > 1e-9 else 1.0
        leak = float(1.0 - np.sum(np.abs(sv[idx]) ** 2))
        res[name] = (float(np.max(np.abs(a / ph - want))), leak)
    return w, d, cx, res


def run(variant, cubes, f):
    from classiq import TargetLanguage, export, synthesize, write_qmod
    print('== variant %s' % variant, flush=True)
    t0 = time.time()
    try:
        model = build(variant, cubes)
    except Exception as e:
        print('  build FAILED: %s: %s' % (type(e).__name__, str(e)[:300])); return
    try:
        write_qmod(model, 'cpub_%s' % variant, directory=HERE)
    except Exception as e:
        print('  write_qmod failed (non-fatal): %s' % str(e)[:200])
    try:
        qprog = synthesize(model)
    except Exception as e:
        print('  synthesize FAILED after %.0fs: %s: %s' % (time.time() - t0, type(e).__name__, str(e)[:400])); return
    print('  synthesize %.0fs' % (time.time() - t0), flush=True)
    try:
        info = qprog.data if hasattr(qprog, 'data') else None
        if info is not None: print('  classiq width %s depth %s' % (getattr(info, 'width', '?'), getattr(info, 'depth', '?')))
    except Exception: pass
    qasm = export(qprog, TargetLanguage.QASM2)
    fn = os.path.join(HERE, 'cpub_%s.qasm' % variant); open(fn, 'w').write(qasm)
    w, d, cx, res = measure(qasm, f)
    print('  qiskit u3/cx opt3: width %d depth %d cx %d   %s' % (w, d, cx, fn))
    for k, (err, leak) in res.items():
        print('  verify data=%s: max phase err %.2e, leak %.2e -> %s' % (k, err, leak, 'PASS' if err < 1e-8 and leak < 1e-10 else 'no'))


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    cubes = load_cubes(); f = cubes_truth(cubes)
    from cpae_core import SHAPES, fvec
    assert np.array_equal(f, fvec(SHAPES['LOGO'])), 'cube file does not reproduce F'
    print('F: 59 cubes reproduce the logo truth table (1097 ones)')
    for v in (['kick', 'phase'] if which == 'all' else [which]): run(v, cubes, f)
