"""CP-FH: in-place contents model.

State = the 18 wire contents as 4096-bit truth tables (bit idx = x + 64*y,
same layout as cpdh_core.want_mask).  A Toffoli ADDS a product to whatever
its target already holds, so values never need a wire of their own; the
mirror restores everything.  Goal test: F lies in the GF(2) span of the
single / pairwise / triple products of the final contents, i.e. the phase
step is a set of z / cz / ccz gates on wires.  Everything here is exact.
"""
import sys
sys.path.insert(0, '/home/user/classiq-challenge')
import cpet_vdag as V
import cpdh_core as DH
from cpae_core import model_depth, mirror

NIN = 4096
FULL = (1 << NIN) - 1
NW = 18
RM = V.raw_masks(NW)
F = DH.want_mask('LOGO')
NLK = {'ccx': 2, 'ccx_dg': 2, 'c3x': 3, 'c3x_dg': 3}


def init():
    return list(RM)


def apply(c, op):
    """apply one op to the contents (in place).  cz/ccz return their phase
    contribution, everything else returns 0."""
    k, q = op[0], op[1:]
    if k == 'x':
        c[q[0]] ^= FULL
    elif k == 'cx':
        c[q[1]] ^= c[q[0]]
    elif k in NLK:
        nc = NLK[k]
        m = FULL
        for w in q[:nc]:
            m &= c[w]
        c[q[nc]] ^= m
    elif k == 'cz':
        return c[q[0]] & c[q[1]]
    elif k == 'ccz':
        return c[q[0]] & c[q[1]] & c[q[2]]
    elif k == 'z':
        return c[q[0]]
    else:
        raise ValueError(k)
    return 0


def replay(ops):
    c = init(); ph = 0
    for op in ops:
        ph ^= apply(c, op)
    return c, ph


class Span:
    """incremental GF(2) basis of 4096-bit vectors with combination tracking."""
    def __init__(self):
        self.piv = {}       # pivot bit -> (vec, combo)
        self.n = 0
    def reduce(self, v, combo=0):
        while v:
            p = v & -v
            e = self.piv.get(p)
            if e is None:
                return v, combo
            v ^= e[0]; combo ^= e[1]
        return 0, combo
    def add(self, v, tag):
        v, combo = self.reduce(v, 1 << tag)
        if v:
            self.piv[v & -v] = (v, combo)
            return True
        return False


def phase_span(c, deg=3, target=F, wires=None):
    """Is `target` a GF(2) sum of products of <= deg contents?  Returns
    (residual_weight, terms) with terms a list of wire tuples (len 1..deg)
    when residual_weight == 0, else (weight, None).  Cheap terms are inserted
    first so the witness prefers z/cz over ccz."""
    ws = list(range(NW)) if wires is None else list(wires)
    terms = []
    for i in ws:
        terms.append((i,))
    for a in range(len(ws)):
        for b in range(a + 1, len(ws)):
            terms.append((ws[a], ws[b]))
    if deg >= 3:
        for a in range(len(ws)):
            for b in range(a + 1, len(ws)):
                for d in range(b + 1, len(ws)):
                    terms.append((ws[a], ws[b], ws[d]))
    S = Span()
    for t, term in enumerate(terms):
        m = FULL
        for w in term:
            m &= c[w]
        if m:
            S.add(m, t)
    r, combo = S.reduce(target)
    if r:
        return bin(r).count('1'), None
    return 0, [terms[t] for t in range(len(terms)) if (combo >> t) & 1]


def phase_ops(terms):
    return [(('z', 'cz', 'ccz')[len(t) - 1],) + tuple(t) for t in terms]


def full_ops(body, terms):
    return list(body) + phase_ops(terms) + mirror(body)


def depth_est(ops):
    """occupancy depth estimate (per-wire ASAP, cpae_core profiles)."""
    return model_depth([op for op in ops if op[0] != 'z'])


if __name__ == '__main__':
    import pickle, time
    ops = pickle.load(open('cpen_search_11.pkl', 'rb'))[1]
    first = next(i for i, op in enumerate(ops) if op[0] in ('cz', 'ccz'))
    last = max(i for i, op in enumerate(ops) if op[0] in ('cz', 'ccz'))
    body = ops[:first]
    c, ph = replay(ops)
    print('best list: %d ops, body %d, phase ops %d, F mismatch %d, dirty %s'
          % (len(ops), len(body), last - first + 1,
             bin(ph ^ F).count('1'), [w for w in range(NW) if c[w] != RM[w]]))
    cb, _ = replay(body)
    for deg in (2, 3):
        t0 = time.time()
        r, terms = phase_span(cb, deg)
        print('phase_span deg %d: residual %d terms %s  (%.1fs)'
              % (deg, r, terms, time.time() - t0))
    r, terms = phase_span(cb, 3)
    ops2 = full_ops(body, terms)
    c2, ph2 = replay(ops2)
    print('re-emitted: F mismatch %d dirty %s depth_est %d (orig est %d)'
          % (bin(ph2 ^ F).count('1'), [w for w in range(NW) if c2[w] != RM[w]],
             depth_est(ops2), depth_est(ops)))
