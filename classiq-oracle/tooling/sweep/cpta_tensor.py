"""CP-TA: tensor-span readout check for round schedules.

Relaxed readout rule: the phase f(x,y) only has to be a sum of cz products
between items the two sides hold in the same round:
    f  in  sum_r  A_r (x) B_r
Option A of round r: x items = wires at round start + x products + const,
                     y items = wires at round start + const.
Option B of round r: x items = wires after the x RCCX's + const,
                     y items = y products.
End state: x wires (x) y wires after the last round.
No fixed pair basis, no per-pair round, no item-count limit.
"""
from cpri_round import simulate, init_tables, NW
from cpae_core import fvec, SHAPES

ALL = (1 << 64) - 1
F = 0
for i, b in enumerate(fvec(SHAPES['LOGO'])):
    if b: F |= 1 << i                 # index x + 64*y


def tens(a, b):
    """a(x) b(y) as a 4096-bit vector"""
    v = 0
    for y in range(64):
        if (b >> y) & 1:
            v |= a << (64 * y)
    return v


class Span:
    def __init__(self):
        self.b = {}                   # pivot bit -> vector (fully reduced not needed)

    def reduce(self, v):
        while v:
            hb = v.bit_length() - 1
            if hb in self.b:
                v ^= self.b[hb]
            else:
                return v
        return 0

    def add(self, v):
        v = self.reduce(v)
        if v:
            self.b[v.bit_length() - 1] = v
            return True
        return False


def vocab(sched, xinit=None, yinit=None):
    """list of (x items, y items) blocks, one per option per round + end"""
    xl = sched.get('xlin') or [[] for _ in sched['x']]
    yl = sched.get('ylin') or [[] for _ in sched['y']]
    R = max(len(sched['x']), len(sched['y']))
    xg = sched['x'] + [[]] * (R - len(sched['x'])); xl = xl + [[]] * (R - len(xl))
    yg = sched['y'] + [[]] * (R - len(sched['y'])); yl = yl + [[]] * (R - len(yl))
    rx = simulate(xinit or init_tables(), xg, xl); ry = simulate(yinit or init_tables(), yg, yl)
    blocks = []
    for r in range(R):
        xs, xp = rx[r]; ys, yp = ry[r]
        xpost = list(xs)
        for (a, pa, b, pb, t), p in zip(xg[r], xp):
            xpost[t] ^= p
        blocks.append(('A%d' % r, xs + xp + [ALL], ys + [ALL]))
        if yp:
            blocks.append(('B%d' % r, xpost + [ALL], yp))
    # end state
    xe = list(rx[-1][0]); ye = list(ry[-1][0])
    for (a, pa, b, pb, t), p in zip(xg[-1], rx[-1][1]):
        xe[t] ^= p
    for (a, pa, b, pb, t), p in zip(yg[-1], ry[-1][1]):
        ye[t] ^= p
    blocks.append(('end', xe + [ALL], ye + [ALL]))
    return blocks


def check(sched, target=F, verbose=True, xinit=None, yinit=None):
    """returns (covered?, dim of span, residual rank proxy)"""
    S = Span()
    for name, xa, yb in vocab(sched, xinit, yinit):
        for a in set(xa):
            for b in set(yb):
                if a and b:
                    S.add(tens(a, b))
    res = S.reduce(target)
    rk = rank64(res)
    if verbose:
        print('span dim %d  covered %s  residual rank %d' % (len(S.b), res == 0, rk))
    return res == 0, len(S.b), rk


def rank64(v):
    """GF(2) rank of v viewed as a 64x64 matrix (rows = y)"""
    rows = [(v >> (64 * y)) & ALL for y in range(64)]
    S = Span(); r = 0
    for w in rows:
        r += S.add(w)
    return r


def side_cover(init_sched_side, lins, target_space):
    """one-sided: first round R at which span of all x items so far
    contains target_space (list of 64-bit tables)"""
    rx = simulate(init_tables(), init_sched_side, lins)
    S = Span(); S.add(ALL)
    out = []
    for r, (xs, xp) in enumerate(rx):
        for v in xs + xp:
            S.add(v)
        miss = sum(1 for t in target_space if S.reduce(t))
        out.append(miss)
    return out


if __name__ == '__main__':
    print('rank of F', rank64(F))
