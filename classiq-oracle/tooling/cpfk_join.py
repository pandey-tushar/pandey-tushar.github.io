"""join two compiled sides (cpfk_affine op lists with ('cz', R, tag, i) markers)
into one oracle: x local 0-5 -> 0-5, 6-8 -> 12-14; y local 0-5 -> 6-11, 6-8 -> 15-17.
Markers with equal (group, i) are paired into one cz."""
import sys, pickle
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfh_core as C
from cpae_core import extract, sim_exact, fvec, SHAPES
from cpfi_exec import ops_to_qc, model_depth
XMAP = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 12, 7: 13, 8: 14}
YMAP = {0: 6, 1: 7, 2: 8, 3: 9, 4: 10, 5: 11, 6: 15, 7: 16, 8: 17}

def glob(op, mp):
    return (op[0],) + tuple(mp[q] for q in op[1:])

def join(xops, yops):
    out = []; i = j = 0
    while i < len(xops) or j < len(yops):
        # advance x until marker
        while i < len(xops) and xops[i][0] != 'cz':
            out.append(glob(xops[i], XMAP)); i += 1
        while j < len(yops) and yops[j][0] != 'cz':
            out.append(glob(yops[j], YMAP)); j += 1
        if i < len(xops) and j < len(yops):
            mx, my = xops[i], yops[j]
            assert mx[2][1:] == my[2][1:] and mx[3] == my[3], (mx, my)
            out.append(('cz', XMAP[mx[1]], YMAP[my[1]])); i += 1; j += 1
        elif i < len(xops) or j < len(yops):
            raise ValueError('unpaired marker')
    return out

def opt2(ops):
    from qiskit import transpile
    t = transpile(ops_to_qc(ops, n=18), basis_gates=['u3', 'cx'], optimization_level=2)
    return t.depth(), t.count_ops().get('cx', 0)

if __name__ == '__main__':
    xops = pickle.load(open(sys.argv[1], 'rb')); yops = pickle.load(open(sys.argv[2], 'rb'))
    ops = join(xops, yops)
    c, ph = C.replay(ops)
    print('replay: dirty %s, phase mismatch %d' % ([w for w in range(18) if c[w] != C.RM[w]], bin(ph ^ C.F).count('1')))
    print('ops %d, model depth %d, opt2 %s' % (len(ops), model_depth(ops), opt2(ops)), flush=True)
    gl, gp = extract(ops_to_qc(ops, n=18)); print('sim_exact', sim_exact(gl, gp, fvec(SHAPES['LOGO'])))
    pickle.dump(ops, open(sys.argv[3] if len(sys.argv) > 3 else 'cpfk_join.pkl', 'wb'))
