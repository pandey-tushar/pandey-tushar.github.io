"""CP-FG: turn a (body, phase) solution into the full circuit, verify exactly,
and score with the real metric."""
import sys, pickle, time
sys.path.insert(0, '/home/user/classiq-challenge')
from cpae_core import ops_to_qc, mirror, extract, sim_exact, fvec, SHAPES, real_depth
import cpet_wide as W
import cpdh_core as DH

def full_ops(body, ph):
    return list(body) + list(ph) + mirror(body)

def evaluate(body, ph, sv=True, obj=False):
    ops = full_ops(body, ph)
    phm, dirty = W.replay(ops, 18)
    mism = bin(phm ^ DH.want_mask('LOGO')).count('1')
    print('ops %d | mask replay: mismatch %d dirty %s' % (len(ops), mism, dirty))
    qc = ops_to_qc(ops, n=18)
    if sv:
        gl, gp = extract(qc)
        err, mm = sim_exact(gl, gp, fvec(SHAPES['LOGO']))
        print('sim_exact: phase err %.2e  perm mismatches %d' % (err, mm))
    for lvl in (2, 3):
        t0 = time.time()
        from qiskit import transpile
        tq = transpile(qc, basis_gates=['u3', 'cx'], optimization_level=lvl, seed_transpiler=0)
        c = tq.count_ops()
        print('opt%d: depth %d  cx %d  u3 %d  (%.0fs)' % (lvl, tq.depth(), c.get('cx', 0), c.get('u3', 0), time.time() - t0))
    if obj:
        import cpew_obj
        s = cpew_obj.obj(ops)
        print('pipeline obj:', {k: s[k] for k in ('depth', 'cx', 'u3', 'width', 'density')})
    return ops

if __name__ == '__main__':
    body, ph = pickle.load(open(sys.argv[1], 'rb'))
    evaluate(body, ph, sv=True, obj=('--obj' in sys.argv))
