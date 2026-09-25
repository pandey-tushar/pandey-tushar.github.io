"""Option 1 (last try): pytket optimisation passes on the 249 circuit.
Each pass sequence: qasm -> tket pass -> qasm -> qiskit transpile(u3,cx,lvl 2)
-> depth/cx (the challenge metric) -> statevector check (err, leak) with the
global phase divided out.  Iterates tket <-> qiskit while depth improves.
Output: one line per sequence/iteration; best exact circuit
ckpt/tket_best.qasm; ckpt/tket.json"""
import sys, json, time
from qiskit import QuantumCircuit, transpile, qasm2
from pytket.qasm import circuit_from_qasm_str, circuit_to_qasm_str
from pytket.passes import (FullPeepholeOptimise, PeepholeOptimise2Q, CliffordSimp, RemoveRedundancies,
                           CommuteThroughMultis, KAKDecomposition, SequencePass, AutoRebase,
                           ZXGraphlikeOptimisation, DecomposeBoxes)
from pytket.circuit import OpType
from cpae_core import sv_check_gp

SRC = sys.argv[1] if len(sys.argv) > 1 else '../cpev_best.qasm'
reb = AutoRebase({OpType.CX, OpType.U3})
SEQS = {
    'fullpeephole': lambda: SequencePass([FullPeepholeOptimise(target_2qb_gate=OpType.CX), reb]),
    'fullpeephole_noswap': lambda: SequencePass([FullPeepholeOptimise(allow_swaps=False, target_2qb_gate=OpType.CX), reb]),
    'peephole2q': lambda: SequencePass([PeepholeOptimise2Q(), reb]),
    'clifford_kak': lambda: SequencePass([CliffordSimp(), KAKDecomposition(), CommuteThroughMultis(), RemoveRedundancies(), reb]),
    'commute_red': lambda: SequencePass([CommuteThroughMultis(), RemoveRedundancies(), reb]),
    'zx': lambda: SequencePass([ZXGraphlikeOptimisation(), FullPeepholeOptimise(target_2qb_gate=OpType.CX), reb]),
}


def metric(qc):
    t = transpile(qc, basis_gates=['u3', 'cx'], optimization_level=2)
    return t, t.depth(), t.count_ops().get('cx', 0)


def tket_step(qc, name):
    c = circuit_from_qasm_str(qasm2.dumps(qc))
    SEQS[name]().apply(c)
    return QuantumCircuit.from_qasm_str(circuit_to_qasm_str(c, header='qelib1'))


if __name__ == '__main__':
    base = QuantumCircuit.from_qasm_file(SRC)
    _, d0, c0 = metric(base)
    print('source %s: depth %d cx %d' % (SRC, d0, c0), flush=True)
    best = (d0, c0, None, 'source'); log = []
    for name in SEQS:
        qc = base; prev = (d0, c0)
        for it in range(6):
            t0 = time.time()
            try:
                q2 = tket_step(qc, name)
            except Exception as e:
                print('%-20s it %d: failed %s' % (name, it, str(e)[:120]), flush=True); break
            t, d, c = metric(q2)
            err, leak = sv_check_gp(t, 'LOGO')
            ok = err < 1e-10 and leak < 1e-20
            rec = dict(seq=name, it=it, depth=d, cx=c, err=err, leak=leak, exact=ok, sec=round(time.time() - t0, 1))
            log.append(rec)
            print('%-20s it %d: depth %d cx %d  err %.1e leak %.1e  exact %s  (%.0fs)' %
                  (name, it, d, c, err, leak, ok, rec['sec']), flush=True)
            if ok and (d, c) < best[:2]:
                best = (d, c, t, '%s it %d' % (name, it))
                qasm2.dump(t, 'ckpt/tket_best.qasm')
            if not ok or (d, c) >= prev: break
            prev = (d, c); qc = t
        json.dump(dict(source=[d0, c0], best=[best[0], best[1], best[3]], runs=log), open('ckpt/tket.json', 'w'), indent=1)
    print('best: depth %d cx %d  (%s)' % (best[0], best[1], best[3]), flush=True)
