"""CP-H v1: hand-ordered circuit for the logo phase oracle.

x wires: X5=5 X4=4 B3=3 B2=2 B1=1 B0=0, ancillas A1=12 A2=13 A3=14
y wires: Y5=11 Y4=10 Y3=9 C2=8 C1=7 C0=6, ancillas D1=15 D2=16 D3=17

x side: fan-out x4 into the low nibble, then the |s| map (b3 ? low3 : 8-low3)
        so the ring functions are thresholds on |s| = (b2',b1',b0).
y side: c2 ^= y4; K = y4 ^ y5(y4^y3) on Y4; map s3 -> 6-s3 on blocks {2,3,5,7}
        so the D and C row-rings are G3*[k] and B10*[k], k in {3},{4},{5,6}.
"""
from cph_build import Builder, lift_x, lift_y, inp
from cph_terms import rng, setof, NOT

X5, X4, B3, B2, B1, B0, A1, A2, A3 = 5, 4, 3, 2, 1, 0, 12, 13, 14
Y5, Y4, Y3, C2, C1, C0, D1, D2, D3 = 11, 10, 9, 8, 7, 6, 15, 16, 17


def xs(s):        # x-side set -> full table
    return lift_x(s)


def ys(s):
    return lift_y(s)


def build():
    b = Builder()
    # ------------------------------------------------------------ x setup
    for t in (B3, B2, B1, B0):
        b.cx(X4, t)
    b.x(B3)
    b.ccx(B3, B0, B1)            # b1' = b1 ^ ~b3 b0
    b.ccx(B1, B0, A1)            # m10' = b1' b0
    b.cx(B1, B0)
    b.cx(A1, B0)                 # B0 = b1' | b0
    b.ccx(B3, B0, B2)            # b2' = b2 ^ ~b3 (b0|b1')
    b.x(B3)
    b.ccx(X5, X4, A3)            # m54
    b.cx(A3, X5)                 # X5 = x5 ~x4
    b.cx(A3, X4)                 # X4 = ~x5 x4
    b.is_(X5, xs(rng(32, 47)), 'x5~x4')
    b.is_(X4, xs(rng(16, 31)), '~x5x4')
    b.is_(A3, xs(rng(48, 63)), 'm54')
    # ------------------------------------------------------------ y setup
    b.cx(Y4, C2)                 # c2 ^= y4
    b.cx(Y4, Y3)                 # Y3 = d = y4 ^ y3
    b.ccx(Y5, Y3, Y4)            # Y4 = K = y4 ^ y5 d
    b.ccx(C1, C0, D1)            # p10
    b.ccx(Y4, D1, C2)            # c2 ^= K p10
    b.x(C0)
    b.ccx(Y4, C0, C1)            # c1 ^= K ~c0
    b.x(C0)
    b.cx(Y4, Y3)                 # Y3 = K ^ d
    b.x(Y3)
    b.ccx(Y5, Y3, D2)            # D2 = B10 = y5 ~(K^d)
    b.x(Y3)
    b.cx(Y5, Y3)
    b.cx(D2, Y3)                 # Y3 = G3 = ~y5 (K^d)
    b.is_(D2, ys(rng(32, 47)), 'B10')
    b.is_(Y3, ys(rng(8, 15) | rng(24, 31)), 'G3')
    # low-set functions of the mapped (c2,c1,c0); expected tables
    S3 = ys(setof(11, 27, 35, 47) | setof(3, 19, 51, 59))   # not used directly
    return b


if __name__ == '__main__':
    b = build()
    print('setup depth', b.depth())
