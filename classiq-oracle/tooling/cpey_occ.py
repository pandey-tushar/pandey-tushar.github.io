"""CP-EY: per-wire slot occupancy of the real metric circuit.
Tests the claim: the empty 65% of the 18xD grid is on the DATA wires."""
import sys
sys.path.insert(0,'/home/user/classiq-challenge')
from qiskit import QuantumCircuit, transpile

def occ(path):
    qc = QuantumCircuit.from_qasm_file(path)
    t  = transpile(qc, basis_gates=['u3','cx'], optimization_level=2)
    n, D = t.num_qubits, t.depth()
    busy = [0]*n
    for inst in t.data:
        for q in inst.qubits:
            busy[t.find_bit(q).index] += 1
    return t, n, D, busy

for path in sys.argv[1:]:
    t,n,D,busy = occ(path)
    cx = t.count_ops().get('cx',0); u3 = t.count_ops().get('u3',0)
    tot = sum(busy)
    print('%s  width %d depth %d cx %d u3 %d' % (path,n,D,cx,u3))
    print('  occupied slots %d / %d  = density %.4f   perfect-pack floor %.1f'
          % (tot, n*D, tot/(n*D), tot/n))
    for w in range(n):
        tag = 'data' if w<12 else 'anc '
        print('   q%-2d %s busy %4d / %4d = %5.1f%%  %s'
              % (w, tag, busy[w], D, 100.0*busy[w]/D, '#'*int(40*busy[w]/D)))
    dat = sum(busy[:12]); anc = sum(busy[12:])
    print('  DATA q0-11 : %d / %d = %.1f%%' % (dat, 12*D, 100.0*dat/(12*D)))
    print('  ANC  q12-17: %d / %d = %.1f%%' % (anc, (n-12)*D, 100.0*anc/((n-12)*D)))
    print()
