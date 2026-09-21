"""Verify a QASM file the way the challenge checker does.

Prints the transpiled depth and CX count, the statevector error with the
global phase divided out, and the ancilla leakage.

usage: cpri_verify.py circuit.qasm
"""
import sys
from qiskit import QuantumCircuit
from cpae_core import real_depth, sv_check_gp


def main():
    qc = QuantumCircuit.from_qasm_file(sys.argv[1])
    d, cx = real_depth(qc)
    err, leak = sv_check_gp(qc, 'LOGO')
    print('depth %d  cx %d  err %.3g  leak %.3g  %s'
          % (d, cx, err, leak, 'PASS' if err < 1e-10 and leak < 1e-12
             else 'FAIL'))


if __name__ == '__main__':
    main()
