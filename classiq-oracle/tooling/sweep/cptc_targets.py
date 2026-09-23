"""targets for the merged-disk rank idea.
x side (after the 4-CX fold, as functions of x): ring/threshold functions
  T_w = [d <= w] restricted to x5=1 (d = c + ~s), gated per region.
y side: merged width classes / nested thresholds of W(y), plus U, B rows."""
from cptb_yprep import Wt
ALL = (1 << 64) - 1
def tab(f): return sum(1 << v for v in range(64) if f(v))
def dx(x):
    x3 = (x >> 3) & 1; x4 = (x >> 4) & 1; c = (x & 7) ^ (0 if x3 else 7); s = x3 ^ x4
    return c + (1 - s)
X = {}
for w in (1, 2, 3, 4, 5, 6, 7):
    X['T%d' % w] = tab(lambda x, w=w: (x >> 5) & 1 and dx(x) <= w)            # [d<=w], x5=1 (both regions)
    X['R%d' % w] = tab(lambda x, w=w: (x >> 5) & 1 and dx(x) == w)            # ring d == w
X['P'] = tab(lambda x: 2 <= x <= 26); X['M'] = tab(lambda x: 27 <= x <= 48)
X['D48'] = tab(lambda x: 32 <= x <= 48)
Y = {}
for w in (2, 4, 5, 6, 7, 8):
    Y['G%d' % w] = tab(lambda y, w=w: Wt.get(y, -1) >= w)                     # nested, halves merged
    Y['E%d' % w] = tab(lambda y, w=w: Wt.get(y, -1) == w)                     # width class
Y['U'] = tab(lambda y: 29 <= y <= 53); Y['B'] = tab(lambda y: 39 <= y <= 43)
