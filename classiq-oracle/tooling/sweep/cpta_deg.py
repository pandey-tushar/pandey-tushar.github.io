"""degree profile of a side's function space in terms of the wire values
after an in-place setup: dim(V  cap  span{products of <= d wire values})."""
import itertools
from cpta_tensor import Span
from cpri_round import logo_pairs, bit
ALL = (1 << 64) - 1

def run(gates, nw=9):
    w = [bit(k) for k in range(6)] + [0] * (nw - 6)
    for g in gates:
        if g[0] == 'cx': w[g[2]] ^= w[g[1]]
        elif g[0] == 'x': w[g[1]] ^= ALL
        elif g[0] == 'ccx': w[g[3]] ^= w[g[1]] & w[g[2]]
    return w

def profile(W, wires, dmax=4):
    wires = [v for v in set(wires) if v not in (0, ALL)]
    out = []
    for d in range(1, dmax + 1):
        S = Span(); S.add(ALL)
        for k in range(1, d + 1):
            for M in itertools.combinations(wires, k):
                p = ALL
                for m in M: p &= m
                S.add(p)
        base = len(S.b)
        out.append(sum(S.add(v) for v in W) and len(Wspan(W)) - sum(1 for _ in []) )
    return out

def Wspan(W):
    S = Span(); [S.add(v) for v in W]; return S.b

def inside(W, wires, d):
    wires = [v for v in set(wires) if v not in (0, ALL)]
    S = Span(); S.add(ALL)
    for k in range(1, d + 1):
        for M in itertools.combinations(wires, k):
            p = ALL
            for m in M: p &= m
            S.add(p)
    n0 = len(S.b)
    for v in W: S.add(v)
    return len(Wspan(W)) - (len(S.b) - n0)      # dims of V already inside

# x setup of cph_v1 (local: b0..b3 = 0..3, x4 = 4, x5 = 5, A1 = 6, A3 = 8)
XSET = [('cx',4,3),('cx',4,2),('cx',4,1),('cx',4,0),('x',3),('ccx',3,0,1),('ccx',1,0,6),
        ('cx',1,0),('cx',6,0),('ccx',3,0,2),('x',3),('ccx',5,4,8),('cx',8,5),('cx',8,4)]
# y setup (local: c0..c2 = 0..2, y3 = 3, y4 = 4, y5 = 5, D1 = 6, D2 = 7)
YSET = [('cx',4,2),('cx',4,3),('ccx',5,3,4),('ccx',1,0,6),('ccx',4,6,2),('x',0),('ccx',4,0,1),
        ('x',0),('cx',4,3),('x',3),('ccx',5,3,7),('x',3),('cx',5,3),('cx',7,3)]

if __name__ == '__main__':
    U = [u for u, v in logo_pairs()]; V = [v for u, v in logo_pairs()]
    for name, W, g in (('x', U, XSET), ('y', V, YSET)):
        raw = run([]); st = run(g)
        print(name, 'dim', len(Wspan(W)),
              '| raw bits: inside deg<=1..4', [inside(W, raw, d) for d in range(1, 5)],
              '| after setup (9 wires):', [inside(W, st, d) for d in range(1, 5)])
