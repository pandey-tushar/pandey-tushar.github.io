"""cpfo_join: pairing check and depth for two beam-search sides."""
import sys, itertools, pickle
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfo_beam as B
import cpfk_side as SD
from cpae_core import model_depth

M64 = (1 << 64) - 1
INV = {'ccx': 'ccx_dg', 'ccx_dg': 'ccx', 'c3x': 'c3x_dg', 'c3x_dg': 'c3x', 'cx': 'cx'}

def replay(hist):
    st = list(B.RAW + [0, 0, 0]); ops = []
    for act in hist:
        *ops_d, w = act
        vals = []
        for d in ops_d:
            v = 0
            for i in d: v ^= st[i]
            vals.append(v)
        p = vals[0]
        for v in vals[1:]: p &= v
        st[w] ^= p
        # gate list: assemble XOR operands onto their first wire, gate, undo
        pre = []
        ctrl = []
        for d in ops_d:
            if len(d) == 1: ctrl.append(d[0])
            else:
                pre.append(('cx', d[1], d[0])); ctrl.append(d[0])
        g = ('ccx',) + tuple(ctrl) + (w,) if len(ctrl) == 2 else ('c3x',) + tuple(ctrl) + (w,)
        ops += pre + [g] + list(reversed(pre))
    return st, ops

def basis(vecs):
    return list(B.reduce_basis(vecs).values())

def spans(st):
    L = basis([c for c in st if c] + [M64])
    S = basis(L + [a & b for a, b in itertools.combinations(L, 2)])
    return L, S

def tensor(a, b):
    """a(x) b(y) as 4096-bit int, index x + 64 y."""
    t = 0
    for y in range(64):
        if (b >> y) & 1: t |= a << (64 * y)
    return t

def pair_check(stx, sty):
    Lx, Sx = spans(stx); Ly, Sy = spans(sty)
    vecs = [tensor(a, b) for a in Lx for b in Sy] + [tensor(a, b) for a in Sx for b in Ly]
    piv = B.reduce_basis(vecs)
    miss = B.rank_with(piv, [SD.F])
    return miss == 0, len(Lx), len(Sx), len(Ly), len(Sy), len(piv)

def side_depth(ops, n=9):
    mirror = [(INV[o[0]],) + o[1:] for o in reversed(ops)]
    return model_depth(ops + mirror, n=n), model_depth(ops, n=n)

if __name__ == '__main__':
    rx = pickle.load(open(sys.argv[1], 'rb')); ry = pickle.load(open(sys.argv[2], 'rb'))
    stx, opsx = replay(rx[2]); sty, opsy = replay(ry[2])
    print('x ANDs', len(rx[2]), 'covered', rx[0], 'depth both/one dir', side_depth(opsx))
    print('y ANDs', len(ry[2]), 'covered', ry[0], 'depth both/one dir', side_depth(opsy))
    print('pairing: F in Lx*Sy + Sx*Ly ->', pair_check(stx, sty))
