"""CP-H step 1: hand-derived term list for the logo, checked against pixels.

x side (columns): after CX(x4 -> x3,x2,x1,x0) the low nibble t' = t ^ 15*x4.
y side (rows):  after the controlled map on (c2,c1) with K = B01 ^ B5:
                c2 ^= K*c1*c0 ^ B01 ;  c1 ^= K*(1^c0)
Every product below is one RCCX in the circuit; everything else is CX/X.
"""
import numpy as np

from cpae_core import SHAPES

ALL = (1 << 64) - 1


def bit(k):
    """truth table (64-bit int) of input bit k over v = 0..63."""
    return sum(1 << v for v in range(64) if (v >> k) & 1)


def tt(pred):
    return sum(1 << v for v in range(64) if pred(v))


def rng(a, b):
    return tt(lambda v: a <= v <= b)


def setof(*vals):
    return tt(lambda v: v in vals)


def NOT(a):
    return a ^ ALL


# ----------------------------------------------------------------- x side
def x_side():
    x0, x1, x2, x3, x4, x5 = (bit(k) for k in range(6))
    b0, b1, b2, b3 = x0 ^ x4, x1 ^ x4, x2 ^ x4, x3 ^ x4       # fan-out
    P = {}                                                     # products
    P['m10'] = m10 = b1 & b0
    P['m32'] = m32 = b3 & b2
    n10 = NOT(b1 ^ b0 ^ m10)
    n32 = NOT(b3 ^ b2 ^ m32)
    P['E15'] = E15 = m32 & m10
    P['Z'] = Z = n32 & n10
    P['u1'] = u1 = n32 & NOT(b1)
    P['u2'] = u2 = n32 & NOT(m10)
    P['v14'] = v14 = m32 & b1
    P['v13'] = v13 = m32 & n10
    P['m21'] = m21 = b2 & b1
    P['w'] = w = b3 & m10
    P['p'] = p = b2 & n10
    G1 = NOT(Z)
    G2 = NOT(u1)
    I2 = NOT(u1 ^ E15)
    I3 = NOT(u2 ^ v14)
    I4 = b3 ^ b2 ^ v13
    I6 = m21 ^ v14 ^ b3 ^ m32 ^ w ^ E15
    G5 = b3 ^ b2 ^ m32 ^ p ^ v13
    P['m54'] = m54 = x5 & x4
    x5n4 = x5 ^ m54            # x5 & ~x4
    x4n5 = x4 ^ m54            # x4 & ~x5
    P['g2'] = g2 = x5 & I2
    P['g2c'] = g2c = m54 & I2
    P['g4'] = g4 = x5 & I4
    P['g4c'] = g4c = m54 & I4
    P['g6'] = g6 = x5 & I6
    P['g6c'] = g6c = m54 & I6
    P['g3'] = g3 = m54 & I3
    P['g1'] = g1 = x5n4 & G1
    P['e48'] = e48 = m54 & E15
    g0 = x5n4 ^ e48
    P['r'] = r = x4 & (G2 ^ G5)
    P['gA'] = gA = NOT(x5) & (G2 ^ r)
    P['bq'] = bq = x4n5 & NOT(G5)
    gB = g0 ^ bq
    F = dict(g2=g2, g2c=g2c, g4=g4, g4c=g4c, g6=g6, g6c=g6c, g3=g3,
             g1=g1, g0=g0, gA=gA, gB=gB)
    want = dict(g2=rng(34, 46) | rng(49, 61), g2c=rng(49, 61),
                g4=rng(36, 44) | rng(51, 59), g4c=rng(51, 59),
                g6=rng(38, 42) | rng(53, 57), g6c=rng(53, 57),
                g3=rng(50, 60), g1=rng(33, 47), g0=rng(32, 48),
                gA=rng(2, 26), gB=rng(27, 48))
    for k in want:
        assert F[k] == want[k], ('x', k)
    return F, P


# ----------------------------------------------------------------- y side
def y_side():
    c0, c1, c2, c3, y4, y5 = (bit(k) for k in range(6))
    P = {}
    P['m54'] = m54 = y5 & y4
    B01, B10, B11 = y4 ^ m54, y5 ^ m54, m54
    B00 = NOT(y5 ^ y4 ^ m54)
    P['B5'] = B5 = B10 & c3
    K = B01 ^ B5
    P['p10'] = p10 = c1 & c0
    P['mp'] = mp = K & p10
    c2 = c2 ^ mp ^ B01                       # map, part 1
    P['mc'] = mc = K & NOT(c0)
    c1 = c1 ^ mc                             # map, part 2
    P['S7'] = S7 = c2 & p10
    S3 = p10 ^ S7
    n10 = NOT(c1 ^ c0 ^ p10)
    P['S4'] = S4 = c2 & n10
    P['S56'] = S56 = c2 & (c1 ^ c0)
    P['c21'] = c21 = c2 & c1
    P['G3'] = G3 = NOT(y5) & c3
    P['Y11r'] = Y11r = G3 & S3
    P['Y12r'] = Y12r = G3 & S4
    P['Y13r'] = Y13r = G3 & S56
    P['B00y3'] = B00y3 = B00 & c3
    P['B01y3'] = B01y3 = B01 & c3
    P['h15'] = h15 = B00y3 & S7
    Y1523 = h15 ^ B01 ^ B01y3
    P['Y1721'] = Y1721 = (B01 ^ B01y3) & NOT(n10 ^ S4 ^ c21)
    P['Y35r'] = Y35r = B10 & S3
    P['Y36r'] = Y36r = B10 & S4
    P['Y37r'] = Y37r = B10 & S56
    P['q1'] = q1 = (B10 ^ B5) & S7
    P['q2'] = q2 = B5 & NOT(c2 ^ S3 ^ S7)
    Q = q1 ^ q2
    P['B11c3'] = B11c3 = B11 & c3
    P['p1'] = p1 = B01y3 & NOT(c2 ^ c1 ^ c21 ^ S7)
    P['p2'] = p2 = (B11 ^ B11c3) & NOT(c21)
    Pf = p1 ^ B10 ^ p2
    F = dict(Y11r=Y11r, Y12r=Y12r, Y13r=Y13r, Y1523=Y1523, Y1721=Y1721,
             Y35r=Y35r, Y36r=Y36r, Y37r=Y37r, Q=Q, P=Pf)
    want = dict(Y11r=setof(11, 27), Y12r=setof(12, 26),
                Y13r=setof(13, 14, 24, 25), Y1523=rng(15, 23),
                Y1721=rng(17, 21), Y35r=setof(35, 47), Y36r=setof(36, 46),
                Y37r=setof(37, 38, 44, 45), Q=rng(39, 43), P=rng(29, 53))
    for k in want:
        assert F[k] == want[k], ('y', k)
    return F, P


# pairs (x function, y function); f = XOR of products
PAIRS = [('gA', 'P'), ('gB', 'Q'),
         ('g0^g1', 'Y1721'), ('g1', 'Y1523'),
         ('g2^g2c', 'Y13r'), ('g2c', 'Q'),
         ('g4^g4c', 'Y12r'), ('g4c', 'Y36r'),
         ('g6^g6c', 'Y11r'), ('g6c', 'Y35r'),
         ('g3', 'Y37r')]


def ev(F, expr):
    v = 0
    for name in expr.split('^'):
        v ^= F[name]
    return v


def main():
    FX, PX = x_side()
    FY, PY = y_side()
    img = np.zeros((64, 64), dtype=int)          # img[x, y]
    for xe, ye in PAIRS:
        u, v = ev(FX, xe), ev(FY, ye)
        for x in range(64):
            if (u >> x) & 1:
                for y in range(64):
                    img[x, y] ^= (v >> y) & 1
    diff = int((img != SHAPES['LOGO']).sum())
    print('x products', len(PX), ' y products', len(PY), ' cz pairs',
          len(PAIRS), ' pixel mismatches', diff)
    assert diff == 0


if __name__ == '__main__':
    main()
