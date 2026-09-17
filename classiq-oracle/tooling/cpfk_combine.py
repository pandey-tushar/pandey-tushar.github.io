"""CP-FK: combine an x-side walk and a y-side walk into a full oracle.
x side local wires 0-5 -> 0-5, 6-8 -> 12-14; y side 0-5 -> 6-11, 6-8 -> 15-17.
body = interleaved walks; ops = body + mirror(body); the temporal span
solver (deg 2, all wire pairs at all times) inserts z / cz so that the phase
is exactly F.  Verified by exact replay and statevector.
"""
import sys, pickle, time, itertools
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfh_core as C
import cpfi_span as S
from cpae_core import mirror, extract, sim_exact, fvec, SHAPES
from cpfi_exec import ops_to_qc, model_depth

XMAP = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 12, 7: 13, 8: 14}
YMAP = {0: 6, 1: 7, 2: 8, 3: 9, 4: 10, 5: 11, 6: 15, 7: 16, 8: 17}


def glob(ops, mp):
    return [(op[0],) + tuple(mp[q] for q in op[1:]) for op in ops]


def interleave(a, b):
    out = []; i = j = 0
    while i < len(a) or j < len(b):
        if i < len(a): out.append(a[i]); i += 1
        if j < len(b): out.append(b[j]); j += 1
    return out


def build(xops, yops, deg=2):
    body = interleave(glob(xops, XMAP), glob(yops, YMAP))
    ops = body + mirror(body)
    r, ins = S.solve(ops, target=C.F, deg=deg)
    if r:
        return r, None
    full = S.insert(ops, ins)
    return 0, full


def opt2(ops):
    from qiskit import transpile
    t = transpile(ops_to_qc(ops, n=18), basis_gates=['u3', 'cx'], optimization_level=2)
    return t.depth(), t.count_ops().get('cx', 0)


def verify(ops):
    gl, gp = extract(ops_to_qc(ops, n=18))
    return sim_exact(gl, gp, fvec(SHAPES['LOGO']))


if __name__ == '__main__':
    xops = pickle.load(open(sys.argv[1], 'rb'))
    yops = pickle.load(open(sys.argv[2], 'rb'))
    r, full = build(xops, yops)
    print('residual', r)
    if full:
        kinds = {}
        for op in full: kinds[op[0]] = kinds.get(op[0], 0) + 1
        print('ops', kinds, 'model depth', model_depth(full), 'opt2', opt2(full), 'verify', verify(full))
        pickle.dump(full, open(sys.argv[3] if len(sys.argv) > 3 else 'cpfk_full.pkl', 'wb'))
