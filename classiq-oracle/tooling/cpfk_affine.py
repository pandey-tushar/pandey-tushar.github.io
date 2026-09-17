"""CP-FK step 1c: affine-piece compiler for one side.

A function of one 6-bit coordinate is written as an XOR of indicators of
affine subspaces of GF(2)^6 (greedy cover, ~26k candidate subspaces).  A
subspace of dimension k is the product of 6-k affine forms; each form is
CX-assembled in place on one of its raw wires, and the product is one
multi-controlled X (<= 3 controls; larger products go through a scratch
wire V, and a group-wide pair of forms can be held on a scratch wire A).
Accumulation on a result wire R; groups undone in reverse.  Exact.
"""
import sys, pickle, itertools
sys.path.insert(0, '/home/user/classiq-challenge')
from cpfk_side import M64, ONE, LIN, COLS, ROWS, tab
from cpae_core import PROF

NWL = 9
R_W, A_W, V_W, V2_W = 6, 7, 8, None


def all_affine():
    """list of (mask, forms) for every affine subspace of GF(2)^6 with dim<=5;
    forms = tuple of (linear mask over 6 bits, const) equations."""
    out = {}
    # enumerate linear subspaces by their annihilator basis in reduced echelon form
    for m in range(1, 7):                      # number of equations
        for pivots in itertools.combinations(range(6), m):
            free = [j for j in range(6) if j not in pivots]
            # each equation: pivot bit + any subset of free bits with index > pivot? (echelon: free cols)
            choices = []
            for p in pivots:
                fs = [j for j in free]
                choices.append([(1 << p) | sum(1 << j for j in sub) for r in range(len(fs) + 1) for sub in itertools.combinations(fs, r)])
            for eqs in itertools.product(*choices):
                for consts in itertools.product((0, 1), repeat=m):
                    mask = 0
                    for v in range(64):
                        ok = True
                        for e, c in zip(eqs, consts):
                            if bin(v & e).count('1') % 2 != c: ok = False; break
                        if ok: mask |= 1 << v
                    if mask and mask not in out:
                        out[mask] = tuple(zip(eqs, consts))
    return out


def wl_forms(forms):
    return sum(4 * (bin(eq).count('1') - 1) for eq, c in forms)


def piece_cost(forms, A, wl=True):
    if not wl: return piece_cost0(forms, A)
    m = len(forms)
    if A is not None and all(f in forms for f in A):
        rest = [f for f in forms if f not in A]
        r = len(rest)
        if r <= 1: return 10 + wl_forms(rest)
        if r == 2: return 19 + wl_forms(rest)
        if r <= 4: return 19 + 19 + 2 * wl_forms(rest)      # V + mcx + unV
        return 999
    if m <= 2: return 10 + wl_forms(forms)
    if m == 3: return 19 + wl_forms(forms)
    if m <= 5: return 2 * 19 + 10 + 2 * wl_forms(forms)
    if A is None: return 3 * 19 + 2 * 10 + 2 * wl_forms(forms)
    return 999


def piece_cost0(forms, A):
    """gate count of one piece given the group's A forms (set of (eq,c)) or None.
    scratch wires: V_W always; A_W too when the group has no A."""
    m = len(forms)
    if A is not None and all(f in forms for f in A):
        r = m - 2
        if r <= 2: return 1
        if r <= 4: return 3          # V(<=3) + mcx(A,rest,V) + unV
        return 99
    if m <= 3: return 1
    if m <= 5: return 3              # V + mcx + unV
    if A is None: return 5           # V1(3) + V2(2) + c3x(V1,V2,f) + unV2 + unV1
    return 99


def cover(target, AFF, A=None, maxpieces=12):
    """greedy XOR cover of `target` (64-bit) by affine subspaces; returns list of forms."""
    rem = target; pieces = []
    items = list(AFF.items())
    while rem and len(pieces) < maxpieces:
        best = None
        w0 = bin(rem).count('1')
        for mask, forms in items:
            gain = w0 - bin(rem ^ mask).count('1')
            if gain <= 0: continue
            c = piece_cost(forms, A)
            if c >= 99 and c != 999 or c >= 999: continue
            score = gain / c
            if best is None or score > best[0]: best = (score, mask, forms)
        if best is None: return None
        rem ^= best[1]; pieces.append(best[2])
    return pieces if rem == 0 else None


class Emitter:
    def __init__(self):
        self.ops = []; self.cont = list(LIN) + [0, 0, 0]; self.lay = [0] * NWL
        self.nand = 0
    def place(self, op):
        prof = PROF[op[0]]; qs = op[1:]
        st = 0
        for j, w in enumerate(qs): st = max(st, self.lay[w] - prof[j][0] + 2)
        for j, w in enumerate(qs): self.lay[w] = st + prof[j][-1] - 1
    def raw(self, op):
        k = op[0]
        if k == 'x': self.cont[op[1]] ^= ONE
        elif k == 'cx': self.cont[op[2]] ^= self.cont[op[1]]; self.place(op)
        elif k in ('ccx', 'ccx_dg'): self.cont[op[3]] ^= self.cont[op[1]] & self.cont[op[2]]; self.place(op); self.nand += 1
        elif k in ('c3x', 'c3x_dg'): self.cont[op[4]] ^= self.cont[op[1]] & self.cont[op[2]] & self.cont[op[3]]; self.place(op); self.nand += 1
        self.ops.append(op)
    def mcx(self, ws, t, dg=False):
        if len(ws) == 1: self.raw(('cx', ws[0], t))
        elif len(ws) == 2: self.raw(('ccx_dg' if dg else 'ccx', ws[0], ws[1], t))
        elif len(ws) == 3: self.raw(('c3x_dg' if dg else 'c3x', ws[0], ws[1], ws[2], t))
        else: raise ValueError(len(ws))


def assemble_forms(E, forms):
    """put each form (eq, c) on a distinct raw wire in place; returns (wires, undo ops).
    A form x_p + sum x_j + c goes on wire p (its lowest bit) via CX from the
    others and an X for the constant (c=1 means the equation is =1, i.e. the
    control must be active when the form is 1: for c=0 we need the negation)."""
    undo = []; wires = []
    used = set()
    for eq, c in forms:
        bits = [j for j in range(6) if (eq >> j) & 1]
        p = next(j for j in bits if j not in used) if any(j not in used for j in bits) else None
        if p is None: return None, None
        used.add(p)
        for j in bits:
            if j != p:
                E.raw(('cx', j, p)); undo.append(('cx', j, p))
        if c == 0:
            E.raw(('x', p)); undo.append(('x', p))
        wires.append(p)
    return wires, undo


def emit_piece(E, forms, A, t):
    """R ^= indicator(subspace).  A = (forms held on A_W) or None."""
    forms = list(forms)
    useA = A is not None and all(f in forms for f in A)
    rest = [f for f in forms if not (useA and f in A)]
    if useA:
        if len(rest) <= 2:
            ws, undo = assemble_forms(E, rest)
            E.mcx([A_W] + ws, t)
            for op in reversed(undo): E.raw(op)
        else:
            # V = product of up to 3 forms, then A ^ (rest) ^ V
            vf, rf = rest[:3], rest[3:]
            ws, undo = assemble_forms(E, vf); E.mcx(ws, V_W)
            for op in reversed(undo): E.raw(op)
            ws, undo = assemble_forms(E, rf); E.mcx([A_W] + ws + [V_W], t)
            for op in reversed(undo): E.raw(op)
            ws, undo = assemble_forms(E, vf); E.mcx(ws, V_W, dg=True)
            for op in reversed(undo): E.raw(op)
    else:
        if len(rest) <= 3:
            ws, undo = assemble_forms(E, rest); E.mcx(ws, t)
            for op in reversed(undo): E.raw(op)
        elif len(rest) <= 5:
            vf, rf = rest[:len(rest) - 2], rest[len(rest) - 2:]
            ws, undo = assemble_forms(E, vf); E.mcx(ws, V_W)
            for op in reversed(undo): E.raw(op)
            ws, undo = assemble_forms(E, rf); E.mcx(ws + [V_W], t)
            for op in reversed(undo): E.raw(op)
            ws, undo = assemble_forms(E, vf); E.mcx(ws, V_W, dg=True)
            for op in reversed(undo): E.raw(op)
        elif A is None:
            vf, wf, rf = rest[:3], rest[3:5], rest[5:]
            ws, undo = assemble_forms(E, vf); E.mcx(ws, V_W)
            for op in reversed(undo): E.raw(op)
            ws, undo = assemble_forms(E, wf); E.mcx(ws, A_W)
            for op in reversed(undo): E.raw(op)
            ws, undo = assemble_forms(E, rf); E.mcx(ws + [V_W, A_W], t)
            for op in reversed(undo): E.raw(op)
            ws, undo = assemble_forms(E, wf); E.mcx(ws, A_W, dg=True)
            for op in reversed(undo): E.raw(op)
            ws, undo = assemble_forms(E, vf); E.mcx(ws, V_W, dg=True)
            for op in reversed(undo): E.raw(op)
        else:
            raise ValueError('6-form piece with A')


def choose_A(pieces_list):
    """most common pair of forms across all pieces of a group."""
    from collections import Counter
    cnt = Counter()
    for pieces in pieces_list:
        for forms in pieces:
            for pair in itertools.combinations(sorted(forms), 2): cnt[pair] += 1
    if not cnt: return None
    pair, n = cnt.most_common(1)[0]
    return pair if n >= 2 else None


def compile_group(E, funcs, AFF, verbose=False, tag=''):
    """accumulate funcs (in order) on R_W, cz markers, then undo."""
    prev = 0; incs = [f ^ prev for f in funcs]
    for i in range(1, len(funcs)): incs[i] = funcs[i] ^ funcs[i - 1]
    # first pass: cover with no A to pick A, then re-cover with A
    pre = [cover(g, AFF) for g in incs]
    A = choose_A([p for p in pre if p])
    covs = [cover(g, AFF, A) for g in incs]
    if any(c is None for c in covs):
        A = None; covs = [cover(g, AFF, None) for g in incs]
        if any(c is None for c in covs): return None
    body = []
    n0 = len(E.ops)
    if A is not None:
        ws, undo = assemble_forms(E, list(A)); E.mcx(ws, A_W)
        for op in reversed(undo): E.raw(op)
    for i, (f, pieces) in enumerate(zip(funcs, covs)):
        a0 = E.nand; o0 = len(E.ops)
        for forms in pieces: emit_piece(E, forms, A, R_W)
        assert E.cont[R_W] == f, 'accumulation mismatch'
        E.ops.append(('cz', R_W, tag, i))
        if verbose: print('  %s term %d: %d pieces, +%d gates, total %d, depth %d' % (tag, i, len(pieces), E.nand - a0, E.nand, max(E.lay)), flush=True)
    if A is not None:
        ws, undo = assemble_forms(E, list(A)); E.mcx(ws, A_W, dg=True)
        for op in reversed(undo): E.raw(op)
    body = [op for op in E.ops[n0:] if op[0] != 'cz']
    INV = {'ccx': 'ccx_dg', 'ccx_dg': 'ccx', 'c3x': 'c3x_dg', 'c3x_dg': 'c3x'}
    for op in reversed(body): E.raw((INV.get(op[0], op[0]),) + tuple(op[1:]))
    assert E.cont == list(LIN) + [0, 0, 0]
    return True


if __name__ == '__main__':
    import time
    t0 = time.time()
    AFF = all_affine()
    print('affine subspaces:', len(AFF), '%.0fs' % (time.time() - t0), flush=True)
    from cpfk_syn import basis_pair
    xf, yf = basis_pair()
    # scheme A: nested-interval groups, x cumulative c_i, y partition b_i
    xg = [[xf[0], xf[1], xf[2], xf[3], xf[4]], [xf[5], xf[6], xf[7], xf[8], xf[9]]]
    yg = [[yf[0], yf[1], yf[2], yf[3], yf[4]], [yf[5], yf[6], yf[7], yf[8], yf[9]]]
    for name, groups in (('x', xg), ('y', yg)):
        E = Emitter()
        for gi, grp in enumerate(groups):
            r = compile_group(E, grp, AFF, verbose=True, tag='%s%d' % (name, gi))
            if r is None: print('  group failed'); break
        kinds = {}
        for op in E.ops: kinds[op[0]] = kinds.get(op[0], 0) + 1
        print('TOTAL side %s (both directions): gates %d  ops %s  model depth %d' % (name, E.nand, kinds, max(E.lay)), flush=True)
        pickle.dump(E.ops, open('cpfk_affine_%s.pkl' % name, 'wb'))
