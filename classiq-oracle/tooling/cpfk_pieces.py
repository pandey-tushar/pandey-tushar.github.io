"""CP-FK step 1b: piece compiler for one side.

Term functions f_1..f_n (64-bit tables over one 6-bit coordinate v = (h,l),
h = v>>3, l = v&7) are ACCUMULATED on a result wire R inside groups:
R = f_1, cz, R ^= (f_2^f_1), cz, ...  and at the end of the group the
increments are undone in reverse.  Each increment is split by h-row into
pieces  A(h2,h1) * h0-literal * (product of l-literals)  where A is shared
by the two rows h0=0/1, and a product of >=2 l-literals is first formed on
a scratch wire V.  Everything is exact; polarities are X gates.
"""
import sys, pickle, itertools
sys.path.insert(0, '/home/user/classiq-challenge')
from cpfk_side import M64, ONE, LIN, COLS, ROWS, tab
from cpae_core import PROF

NWL = 9
R_W, A_W, V_W = 6, 7, 8          # local ancilla roles
LIT_PRODS = None


def lit_products():
    """all products of literals over 3 bits (l2,l1,l0) as 8-bit tables:
    returns dict value -> tuple of (bit, polarity) literals."""
    out = {}
    for pol in itertools.product((None, 0, 1), repeat=3):
        v = 0
        for l in range(8):
            ok = True
            for bit, p in enumerate(pol):
                if p is None: continue
                if ((l >> bit) & 1) != (1 - p): ok = False
            if ok: v |= 1 << l
        lits = tuple((bit, p) for bit, p in enumerate(pol) if p is not None)
        if v not in out or len(lits) < len(out[v]): out[v] = lits
    return out


def min_xor(P, prods):
    """min number of literal products whose XOR is P (8-bit); BFS."""
    if P == 0: return []
    items = list(prods.items())
    best = None
    for k in range(1, 5):
        for combo in itertools.combinations(items, k):
            v = 0
            for val, _ in combo: v ^= val
            if v == P:
                c = sum(len(l) for _, l in combo)
                if best is None or (k, c) < best[0]: best = ((k, c), [l for _, l in combo])
        if best: return best[1]
    return None


class Emitter:
    def __init__(self):
        self.ops = []; self.cont = list(LIN) + [0, 0, 0]; self.lay = [0] * NWL
        self.nand = 0; self.pol = [0] * NWL      # current X state of each wire
    def place(self, op):
        prof = PROF[op[0]]; qs = op[1:]
        st = 0
        for j, w in enumerate(qs): st = max(st, self.lay[w] - prof[j][0] + 2)
        for j, w in enumerate(qs): self.lay[w] = st + prof[j][-1] - 1
    def raw(self, op):
        k = op[0]
        if k == 'x': self.cont[op[1]] ^= ONE; self.pol[op[1]] ^= 1
        elif k == 'cx': self.cont[op[2]] ^= self.cont[op[1]]; self.place(op)
        elif k == 'ccx': self.cont[op[3]] ^= self.cont[op[1]] & self.cont[op[2]]; self.place(op); self.nand += 1
        elif k == 'c3x': self.cont[op[4]] ^= self.cont[op[1]] & self.cont[op[2]] & self.cont[op[3]]; self.place(op); self.nand += 1
        self.ops.append(op)
    def setpol(self, w, p):
        if self.pol[w] != p: self.raw(('x', w))
    def mcx(self, ctrls, t):
        """ctrls = [(wire, polarity)], polarity 1 = negated."""
        for w, p in ctrls: self.setpol(w, p)
        ws = [w for w, _ in ctrls]
        if len(ws) == 0: self.raw(('x', t))
        elif len(ws) == 1: self.raw(('cx', ws[0], t))
        elif len(ws) == 2: self.raw(('ccx', ws[0], ws[1], t))
        elif len(ws) == 3: self.raw(('c3x', ws[0], ws[1], ws[2], t))
        else: raise ValueError('too many controls')
    def marker(self, i):
        self.ops.append(('cz', R_W, i))


def hval(k):
    """literal list for h == k  ->  (A-literals for (h2,h1), h0-literal)."""
    return [(5, 1 - ((k >> 2) & 1)), (4, 1 - ((k >> 1) & 1))], (3, 1 - (k & 1))


def compile_increment(E, g, prods, cache):
    """emit pieces so that R ^= g.  cache: current V content descriptor."""
    rows = {k: (g >> (8 * k)) & 255 for k in range(8)}
    # group rows by (h2,h1)
    for hh in range(4):
        r0, r1 = rows[2 * hh], rows[2 * hh + 1]
        if not r0 and not r1: continue
        Alits, _ = hval(2 * hh)
        if cache[2] != Alits:
            if cache[2] is not None: E.mcx(cache[2], A_W)
            E.mcx(Alits, A_W); cache[2] = Alits
        if r0 == r1 == 255:
            E.mcx([(A_W, 0)], R_W)            # both rows full: linear piece
        else:
            for k, P in ((2 * hh, r0), (2 * hh + 1, r1)):
                if not P: continue
                _, h0lit = hval(k)
                if r0 == r1:
                    h0ctrl = []                # both rows equal: h0 free
                else:
                    h0ctrl = [h0lit]
                for lits in min_xor(P, prods):
                    lctrl = [(b, p) for b, p in lits]          # l bits are local wires 0..2
                    if len(lctrl) <= 1:
                        E.mcx([(A_W, 0)] + h0ctrl + lctrl, R_W)
                    else:
                        if cache[0] != lits:
                            if cache[0] is not None: E.mcx(cache[1], V_W)   # uncompute old V
                            E.mcx(lctrl, V_W); cache[0] = lits; cache[1] = lctrl
                        E.mcx([(A_W, 0)] + h0ctrl + [(V_W, 0)], R_W)
                if r0 == r1: break
    pass


def compile_side(groups, verbose=False):
    """groups: list of lists of 64-bit functions (each group accumulated on R)."""
    prods = lit_products()
    E = Emitter(); idx = 0
    for grp in groups:
        prev = 0; incs = []
        cache = [None, None, None]
        for f in grp:
            g = f ^ prev; prev = f
            n0 = len(E.ops); a0 = E.nand
            compile_increment(E, g, prods, cache)
            incs.append(E.ops[n0:])
            assert E.cont[R_W] == f, 'accumulation mismatch'
            E.marker(idx); idx += 1
            if verbose: print('  term %d: +%d ands (%d ops), total %d, depth %d' % (idx - 1, E.nand - a0, len(E.ops) - n0, E.nand, max(E.lay)))
        # close scratch, then undo the group in reverse
        n0 = len(E.ops)
        if cache[0] is not None: E.mcx(cache[1], V_W)
        if cache[2] is not None: E.mcx(cache[2], A_W)
        incs.append(E.ops[n0:])
        for inc in reversed(incs):
            for op in reversed(inc):
                E.raw(op)
        assert E.cont[R_W] == 0
    for w in range(NWL): E.setpol(w, 0)
    assert E.cont == list(LIN) + [0, 0, 0], 'not restored'
    return E


def x_groups():
    from cpfk_syn import basis_pair
    xf, yf = basis_pair()
    return xf, yf


if __name__ == '__main__':
    xf, yf = x_groups()
    # x groups: nest around 40 (c1..c5) and the rest (c6..c10); y pairs accordingly (cumulative)
    xg = [[xf[0], xf[1], xf[2], xf[3], xf[4]], [xf[5], xf[6], xf[7], xf[8], xf[9]]]
    # matching y functions: F = sum c_i b_i with c_i accumulated -> use differences on x:
    # R_x = c_i directly (accumulate increments c_i ^ c_{i-1}), pair with b_i.
    yg = [[yf[0], yf[1], yf[2], yf[3], yf[4]], [yf[5], yf[6], yf[7], yf[8], yf[9]]]
    for name, groups in (('x', xg), ('y', yg)):
        print('side', name)
        E = compile_side(groups, verbose=True)
        kinds = {}
        for op in E.ops: kinds[op[0]] = kinds.get(op[0], 0) + 1
        print('  TOTAL side %s: ands %d, ops %s, model depth %d' % (name, E.nand, kinds, max(E.lay)))
        pickle.dump(E.ops, open('cpfk_pieces_%s.pkl' % name, 'wb'))
