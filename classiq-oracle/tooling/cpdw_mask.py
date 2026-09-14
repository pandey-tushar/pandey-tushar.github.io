"""CP-DW: one whole-logo gate list on 18 wires, tracked as exact 4096-bit
masks.  No worlds, no 3-bit blocks, no compute/uncompute.

Every wire's content is a Boolean function of the 12 inputs, held as a
4096-bit mask.  Any gate  t ^= product(other wires)  is reversible, so any
wire may hold any value at any time; the only end conditions are that every
mask is back where it started and that the accumulated phase is F.

AND gates are Margolus, not RCCX: same u3/cx depth 7 and 3 CX, but its
relative phase is  a & ~b & t  with t the target BEFORE the gate, a plain
GF(2) function, so it is carried in the same phase accumulator as the CZs
instead of needing a mirror to cancel.
"""
import itertools

import cpae_core as AE

NIN = 4096
FULL = (1 << NIN) - 1
NW = 18
XN = ["x%d" % i for i in range(6)]
YN = ["y%d" % i for i in range(6)]
SN = ["s%d" % i for i in range(6)]
NAMES = XN + YN + SN


def raw_masks():
    b = [0] * NW
    for idx in range(NIN):
        xv, yv = idx & 63, idx >> 6
        for k in range(6):
            if (xv >> k) & 1:
                b[k] |= 1 << idx
            if (yv >> k) & 1:
                b[6 + k] |= 1 << idx
    return b


RAW = raw_masks()


def lift_x(f64):
    """6-bit function of x (64-bit truth table) -> 4096-bit mask."""
    m = 0
    for idx in range(NIN):
        if (f64 >> (idx & 63)) & 1:
            m |= 1 << idx
    return m


def lift_y(f64):
    m = 0
    for idx in range(NIN):
        if (f64 >> (idx >> 6)) & 1:
            m |= 1 << idx
    return m


def logo_mask():
    img = AE.SHAPES["LOGO"]
    m = 0
    for idx in range(NIN):
        if img[idx & 63, idx >> 6]:
            m |= 1 << idx
    return m


# ------------------------------------------------------------------- GF(2)
def ech(vs):
    """echelon basis of a list of masks, highest set bit as pivot."""
    bs = []
    for v in vs:
        w = v
        for b in bs:
            if w ^ b < w:
                w ^= b
        if w:
            bs.append(w)
            bs.sort(reverse=True)
    return bs


def reduce_v(bs, v):
    for b in bs:
        if v ^ b < v:
            v ^= b
    return v


def solve(gens, v):
    """subset of indices of `gens` XORing to v, or None."""
    bs = []
    for i, g in enumerate(gens):
        w, c = g, 1 << i
        for b, cc in bs:
            if w ^ b < w:
                w ^= b
                c ^= cc
        if w:
            bs.append((w, c))
            bs.sort(key=lambda z: -z[0])
    w, c = v, 0
    for b, cc in bs:
        if w ^ b < w:
            w ^= b
            c ^= cc
    if w:
        return None
    return [i for i in range(len(gens)) if (c >> i) & 1]


class Basis(object):
    """echelon basis with coefficient tracking, for 'is this delta a XOR of
    current wire contents, and which ones'."""

    def __init__(s, gens):
        s.gens = list(gens)
        s.bs = []
        for i, g in enumerate(s.gens):
            w, c = g, 1 << i
            for b, cc in s.bs:
                if w ^ b < w:
                    w ^= b
                    c ^= cc
            if w:
                s.bs.append((w, c))
                s.bs.sort(key=lambda z: -z[0])

    def solve(s, v):
        w, c = v, 0
        for b, cc in s.bs:
            if w ^ b < w:
                w ^= b
                c ^= cc
        if w:
            return None
        return c


PROF = AE.PROF
# Margolus: ry t; cx c1 t; ry t; cx c0 t; ry t; cx c1 t; ry t
# -> same per-wire touch layers as rccx, and the same u3/cx depth 7 / 3 CX.
PROF["mand"] = PROF["rccx"]
# plus-minus-one-phase C3X: 8 Ry on the target interleaved with 8 CX along a
# gray code, u3/cx depth 16 and 8 CX, phase a&b&c&t with t before the gate.
PROF["z"] = {0: [1]}
PROF["mand3"] = {0: [2, 6, 10, 14], 1: [4, 12], 2: [8, 16],
                 3: list(range(1, 17))}


class Mach(object):
    def __init__(s):
        s.m = list(RAW)
        s.init = list(RAW)
        s.phase = 0
        s.ops = []
        s.lay = [0] * NW

    # ------------------------------------------------------------- gates
    def _sched(s, name, qs):
        pr = PROF[name]
        S = 0
        for j, w in enumerate(qs):
            S = max(S, s.lay[w] - pr[j][0] + 1)
        for j, w in enumerate(qs):
            s.lay[w] = S + pr[j][-1] - 1

    def trial(s, plan):
        lay = list(s.lay)
        for name, qs in plan:
            pr = PROF[name]
            S = 0
            for j, w in enumerate(qs):
                S = max(S, lay[w] - pr[j][0] + 1)
            for j, w in enumerate(qs):
                lay[w] = S + pr[j][-1] - 1
        return max(lay) - max(s.lay), max(lay)

    def emit(s, name, qs):
        if name == "cx":
            s.m[qs[1]] ^= s.m[qs[0]]
        elif name == "x":
            s.m[qs[0]] ^= FULL
        elif name == "mand":
            c0, c1, t = qs
            s.phase ^= s.m[c0] & (s.m[c1] ^ FULL) & s.m[t]
            s.m[t] ^= s.m[c0] & s.m[c1]
        elif name == "mand3":
            c0, c1, c2, t = qs
            s.phase ^= s.m[c0] & s.m[c1] & s.m[c2] & s.m[t]
            s.m[t] ^= s.m[c0] & s.m[c1] & s.m[c2]
        elif name == "z":
            s.phase ^= s.m[qs[0]]
        elif name == "cz":
            s.phase ^= s.m[qs[0]] & s.m[qs[1]]
        elif name == "ccz":
            s.phase ^= s.m[qs[0]] & s.m[qs[1]] & s.m[qs[2]]
        else:
            raise ValueError(name)
        s._sched(name, qs)
        s.ops.append((name,) + tuple(qs))

    # -------------------------------------------------- value construction
    def plan_delta(s, w, delta, cap=2):
        """cheapest plan XORing `delta` onto wire w.  Returns [(name, qs)]."""
        if delta == 0:
            return []
        others = [u for u in range(NW) if u != w]
        gens = [s.m[u] for u in others] + [FULL]
        B = Basis(gens)

        def chain(c):
            out = []
            for i, u in enumerate(others):
                if (c >> i) & 1:
                    out.append(("cx", (u, w)))
            if (c >> len(others)) & 1:
                out.append(("x", (w,)))
            return out

        best = None
        c = B.solve(delta)
        if c is not None:
            p = chain(c)
            best = (s.trial(p)[0], p)
        for u, v in itertools.combinations(others, 2):
            pm = s.m[u] & s.m[v]
            c = B.solve(delta ^ pm)
            if c is None:
                continue
            p = chain(c) + [("mand", (u, v, w))]
            d = s.trial(p)[0]
            if best is None or d < best[0]:
                best = (d, p)
        if best is not None or cap <= 1:
            return best[1] if best else None
        return None

    def do_delta(s, w, delta):
        p = s.plan_delta(w, delta)
        if p is None:
            return False
        for name, qs in p:
            s.emit(name, qs)
        return True

    def set_wire(s, w, want):
        return s.do_delta(w, s.m[w] ^ want)

    # ------------------------------------------------------------ output
    def depth(s):
        qc = to_qc(s.ops)
        return AE.real_depth(qc, 2)

    def restored(s):
        return [w for w in range(NW) if s.m[w] != s.init[w]]


def to_qc(ops, n=NW):
    import numpy as np
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import CCZGate
    qc = QuantumCircuit(n)
    for op in ops:
        k, qs = op[0], list(op[1:])
        if k == "x":
            qc.x(qs[0])
        elif k == "cx":
            qc.cx(*qs)
        elif k == "z":
            qc.z(qs[0])
        elif k == "cz":
            qc.cz(*qs)
        elif k == "ccz":
            qc.append(CCZGate(), qs)
        elif k == "mand3":
            g = [z ^ (z >> 1) for z in range(8)]
            seq = [(g[z] ^ g[(z + 1) % 8]).bit_length() - 1 for z in range(8)]
            t = qs[3]
            for z in range(8):
                qc.ry(np.pi / 8 * (-1) ** bin(g[z]).count("1"), t)
                qc.cx(qs[seq[z]], t)
        elif k == "mand":
            c0, c1, t = qs
            qc.ry(np.pi / 4, t)
            qc.cx(c1, t)
            qc.ry(np.pi / 4, t)
            qc.cx(c0, t)
            qc.ry(-np.pi / 4, t)
            qc.cx(c1, t)
            qc.ry(-np.pi / 4, t)
        else:
            raise ValueError(k)
    return qc


# ------------------------------------------------------- block lifts
def lift_blk(tt8, shift, side):
    """3-bit truth table over a block -> 4096 mask.  side 0 = x, 1 = y."""
    m = 0
    for idx in range(NIN):
        v = (idx & 63) if side == 0 else (idx >> 6)
        if (tt8 >> ((v >> shift) & 7)) & 1:
            m |= 1 << idx
    return m


def x_tt(mask):
    """mask that depends only on x -> its 64-bit truth table (or None)."""
    tt = 0
    for xv in range(64):
        b = (mask >> xv) & 1
        for yv in range(64):
            if ((mask >> (xv + 64 * yv)) & 1) != b:
                return None
        if b:
            tt |= 1 << xv
    return tt


def rank1(f64):
    """6-bit function -> [(u8, v8)] with XOR_i u_i(hi) & v_i(lo) == f."""
    M = [0] * 8
    for v in range(64):
        if (f64 >> v) & 1:
            M[v >> 3] |= 1 << (v & 7)
    out = []
    while any(M):
        h = next(i for i in range(8) if M[i])
        row = M[h]
        l = (row & -row).bit_length() - 1
        col = 0
        for i in range(8):
            if (M[i] >> l) & 1:
                col |= 1 << i
        out.append((col, row))
        for i in range(8):
            if (col >> i) & 1:
                M[i] ^= row
    return out


def anf3(tt8):
    """ANF coefficients of a 3-bit truth table, index = monomial bitmask."""
    a = [(tt8 >> i) & 1 for i in range(8)]
    for k in range(3):
        b = 1 << k
        for i in range(8):
            if i & b:
                a[i] ^= a[i ^ b]
    return a


# ------------------------------------------------------------------ walk
from cpdr_lib import XAT, YAT                                    # noqa: E402

SCRATCH = [None]
XB = [(0, 1, 2), (3, 4, 5)]        # x lo block wires, x hi block wires
YB = [(6, 7, 8), (9, 10, 11)]


def blk_wires(side, hi):
    return (YB if side else XB)[1 if hi else 0]


def blk_tt(mask):
    """(side, hi, tt8) if `mask` depends on one 3-bit block only, else None."""
    for side in (0, 1):
        for hi in (0, 1):
            sh = 3 if hi else 0
            tt = 0
            ok = True
            for z in range(8):
                seen = None
                for idx in range(NIN):
                    v = (idx & 63) if side == 0 else (idx >> 6)
                    if ((v >> sh) & 7) != z:
                        continue
                    b = (mask >> idx) & 1
                    if seen is None:
                        seen = b
                    elif b != seen:
                        ok = False
                        break
                if not ok:
                    break
                if seen:
                    tt |= 1 << z
            if ok:
                return side, hi, tt
    return None


def anf_ops(tt8, f, bw, scr):
    """ops XORing the block function tt8 onto wire f over raw block wires."""
    a = anf3(tt8)
    ops = []
    for mono in (1, 2, 4, 3, 5, 6, 7):
        if not a[mono]:
            continue
        bits = [i for i in range(3) if (mono >> i) & 1]
        if len(bits) == 1:
            ops.append(("cx", (bw[bits[0]], f)))
        elif len(bits) == 2:
            ops.append(("mand", (bw[bits[0]], bw[bits[1]], f)))
        else:
            if scr is None:
                return None
            # f ^= b0.b1.b2 with a scratch holding ANY value z:
            #   g = z^b0b1 ; f ^= (z^b0b1)b2 ; g = z ; f ^= z.b2
            # nets f ^= b0b1b2 and leaves g untouched, so no zero wire is
            # needed and no wire has to be cleared to make one.
            ops.append(("mand", (bw[0], bw[1], scr)))
            ops.append(("mand", (scr, bw[2], f)))
            ops.append(("mand", (bw[0], bw[1], scr)))
            ops.append(("mand", (scr, bw[2], f)))
    if a[0]:
        ops.append(("x", (f,)))
    return ops


def _clear_ops(M, g):
    """ops driving pool wire g to 0 by re-applying its own block ANF (the
    block wires are never disturbed, so re-applying cancels exactly)."""
    if not M.m[g]:
        return []
    t = blk_tt(M.m[g])
    if t is None:
        return None
    side, hi, tt = t
    bw = blk_wires(side, hi)
    scr = SCRATCH[0]
    if scr is None or scr == g or scr in bw:
        scr = next((z for z in range(NW) if z != g and z not in bw), None)
    return anf_ops(tt, g, bw, scr)


def _write(M, f, want, pool):
    """ops XORing (M.m[f] ^ want) onto f, both being block functions."""
    delta = M.m[f] ^ want
    if delta == 0:
        return []
    t = blk_tt(delta)
    if t is None:
        return None
    side, hi, tt = t
    bw = blk_wires(side, hi)
    scr = SCRATCH[0]
    if scr is None or scr == f or scr in bw:
        scr = next((g for g in range(NW) if g != f and g not in bw), None)
    o = anf_ops(tt, f, bw, scr)
    if o is not None:
        return o
    # the cubic monomial needs a zero scratch: borrow a pool wire, clearing
    # it and putting it back afterwards
    for g in pool:
        if g == f:
            continue
        cl = _clear_ops(M, g)
        if cl is None:
            continue
        o = anf_ops(tt, f, bw, g)
        if o is None:
            continue
        return cl + o + cl
    return None


def set_plan(M, f, want, pool):
    """ops driving wire f to `want`."""
    if M.m[f] == want:
        return []
    o = _write(M, f, want, pool)
    if o is not None:
        return o
    cl = _clear_ops(M, f)
    if cl is None:
        return None
    sv = M.m[f]
    M.m[f] = 0
    o2 = _write(M, f, want, pool)
    M.m[f] = sv
    if o2 is None:
        return None
    return cl + o2


FWIRE = {}


def rank1_variants(f64, tries=8):
    """several rank-1 decompositions of the same function, cheapest ANF
    first: peeling from a different pivot row each time gives different
    factor pairs, and factors whose ANF has no cubic term are much cheaper
    to put on a wire."""
    outs = []
    for start in range(8):
        M = [0] * 8
        for v in range(64):
            if (f64 >> v) & 1:
                M[v >> 3] |= 1 << (v & 7)
        terms = []
        order = [(start + i) % 8 for i in range(8)]
        while any(M):
            h = next((i for i in order if M[i]), None)
            row = M[h]
            l = (row & -row).bit_length() - 1
            col = 0
            for i in range(8):
                if (M[i] >> l) & 1:
                    col |= 1 << i
            terms.append((col, row))
            for i in range(8):
                if (col >> i) & 1:
                    M[i] ^= row
        cost = 0
        for u8, v8 in terms:
            for t8 in (u8, v8):
                if t8 == 255:
                    continue
                a = anf3(t8)
                cost += sum(a[1:]) + 3 * a[7]
        outs.append((cost + 4 * len(terms), terms))
        if len(outs) >= tries:
            break
    outs.sort(key=lambda z: z[0])
    seen = set()
    res = []
    for _, t in outs:
        k = tuple(t)
        if k in seen:
            continue
        seen.add(k)
        res.append(t)
    return res


def ensure(M, tt8, side, hi, pool, w_avoid=()):
    """the wire dedicated to this block, moved to the wanted value by the
    ANF of the DELTA -- the value already there is reused, never rebuilt."""
    want = lift_blk(tt8, 3 if hi else 0, side)
    for u in range(NW):
        if M.m[u] == want:
            return u
    f = FWIRE.get((side, hi))
    if f is None:
        return None
    plan = set_plan(M, f, want, pool)
    if plan is None:
        return None
    for name, qs in plan:
        M.emit(name, qs)
    return f


def clear_plan(M, f):
    """ops driving wire f back to 0 (ancillas only)."""
    others = [u for u in range(NW) if u != f]
    B = Basis([M.m[u] for u in others] + [FULL])
    c = B.solve(M.m[f])
    if c is None:
        return None
    out = []
    for i, u in enumerate(others):
        if (c >> i) & 1:
            out.append(("cx", (u, f)))
    if (c >> len(others)) & 1:
        out.append(("x", (f,)))
    return out


def emit_leg_side(M, w, want, side, pool):
    """drive carrier wire w (holding a function of one variable only) to
    `want` by rank-1 terms, each a Margolus from two block-value wires."""
    delta = M.m[w] ^ want
    if delta == 0:
        return True
    tt = x_tt(delta) if side == 0 else y_tt(delta)
    if tt is None:
        return False
    for u8, v8 in rank1_variants(tt)[0]:
        if u8 == 255 and v8 == 255:
            M.emit("x", (w,))
            continue
        if u8 == 255:
            wv = ensure(M, v8, side, False, pool, (w,))
            if wv is None:
                return False
            M.emit("cx", (wv, w))
            continue
        if v8 == 255:
            wu = ensure(M, u8, side, True, pool, (w,))
            if wu is None:
                return False
            M.emit("cx", (wu, w))
            continue
        wu = ensure(M, u8, side, True, pool, (w,))
        if wu is None:
            return False
        wv = ensure(M, v8, side, False, pool, (w, wu))
        if wv is None:
            return False
        M.emit("mand", (wu, wv, w))
    return True


def y_tt(mask):
    tt = 0
    for yv in range(64):
        b = (mask >> (64 * yv)) & 1
        for xv in range(64):
            if ((mask >> (xv + 64 * yv)) & 1) != b:
                return None
        if b:
            tt |= 1 << yv
    return tt


def walk(carriers, groups, orders, pool, scratch=None):
    SCRATCH[0] = scratch
    """one gate list: every carrier walks its legs, phases fire whenever the
    pair is resident, then every wire is driven home."""
    M = Mach()
    heads = [0] * len(carriers)
    live = list(range(len(carriers)))
    while live:
        c = min(live, key=lambda i: max(M.lay[carriers[i][0]],
                                        M.lay[carriers[i][1]]))
        k = orders[c][heads[c]]
        wx, wy = carriers[c]
        if not emit_leg_side(M, wx, lift_x(XAT[k]), 0, pool):
            return M, "x leg %d failed" % k
        if not emit_leg_side(M, wy, lift_y(YAT[k]), 1, pool):
            return M, "y leg %d failed" % k
        M.emit("cz", (wx, wy))
        heads[c] += 1
        if heads[c] >= len(orders[c]):
            live.remove(c)
    for wx, wy in carriers:
        if not emit_leg_side(M, wx, 0, 0, pool):
            return M, "x close failed"
        if not emit_leg_side(M, wy, 0, 1, pool):
            return M, "y close failed"
    for f in list(pool) + ([scratch] if scratch is not None else []):
        if M.m[f]:
            cp = _clear_ops(M, f)
            if cp is None:
                cp = clear_plan(M, f)
            if cp is None:
                return M, "pool close failed on %d" % f
            for name, qs in cp:
                M.emit(name, qs)
    return M, None


def walk_ccz(ycar, orders, pool, scratch=None):
    """No x-side accumulator at all.  a_k(x) is expanded into its rank-1
    pieces u_i(x-hi) . v_i(x-lo) and the phase fires as CCZ(u_i, v_i, b_k),
    so the x side never serialises through one wire; only the y carriers walk.
    """
    SCRATCH[0] = scratch
    M = Mach()
    heads = [0] * len(ycar)
    live = list(range(len(ycar)))
    while live:
        c = min(live, key=lambda i: M.lay[ycar[i]])
        k = orders[c][heads[c]]
        wy = ycar[c]
        if not emit_leg_side(M, wy, lift_y(YAT[k]), 1, pool):
            return M, "y leg %d failed" % k
        for u8, v8 in rank1(XAT[k]):
            if u8 == 255 and v8 == 255:
                M.emit("cz", (wy, wy))
                continue
            if u8 == 255:
                wv = ensure(M, v8, 0, False, pool, (wy,))
                if wv is None:
                    return M, "x factor failed"
                M.emit("cz", (wv, wy))
                continue
            if v8 == 255:
                wu = ensure(M, u8, 0, True, pool, (wy,))
                if wu is None:
                    return M, "x factor failed"
                M.emit("cz", (wu, wy))
                continue
            wu = ensure(M, u8, 0, True, pool, (wy,))
            if wu is None:
                return M, "x factor failed"
            wv = ensure(M, v8, 0, False, pool, (wy, wu))
            if wv is None:
                return M, "x factor failed"
            M.emit("ccz", (wu, wv, wy))
        heads[c] += 1
        if heads[c] >= len(orders[c]):
            live.remove(c)
    for wy in ycar:
        if not emit_leg_side(M, wy, 0, 1, pool):
            return M, "y close failed"
    for f in list(pool) + ([scratch] if scratch is not None else []):
        if M.m[f]:
            cp = _clear_ops(M, f) or clear_plan(M, f)
            if cp is None:
                return M, "pool close failed on %d" % f
            for name, qs in cp:
                M.emit(name, qs)
    return M, None


# ------------------------------------------------------- block as a state
def fast_tt(mask, side, hi):
    """mask known to be a block function -> its 8-bit truth table."""
    sh = 3 if hi else 0
    tt = 0
    for z in range(8):
        v = z << sh
        idx = v if side == 0 else (v << 6)
        if (mask >> idx) & 1:
            tt |= 1 << z
    return tt


def coordinv(vs):
    seen = [None] * 8
    for h in range(8):
        z = 0
        for j in range(3):
            if (vs[j] >> h) & 1:
                z |= 1 << j
        if seen[z] is not None:
            return None
        seen[z] = h
    return seen


class Blk(object):
    """One 3-bit block held across several wires at once.

    Members are the block's three data wires plus an ancilla.  Every member
    may hold any function of the block, the only invariant being that some
    three of them still determine the block; a wanted value is then reached
    by the ANF of the DELTA from whatever that wire already holds, and values
    already sitting on a member are reused rather than rebuilt.
    """

    def __init__(s, M, wires, side, hi):
        s.M = M
        s.w = list(wires)
        s.side = side
        s.hi = hi
        s.n = len(s.w)
        s.subs = dict((t, [o for o in itertools.combinations(
            [c for c in range(s.n) if c != t], 3)]) for t in range(s.n))

    def val(s):
        return [fast_tt(s.M.m[w], s.side, s.hi) for w in s.w]

    def walkable(s, val=None):
        val = val or s.val()
        out = []
        for t in range(s.n):
            for o in s.subs[t]:
                if coordinv([val[c] for c in o]) is not None:
                    out.append(t)
                    break
        return out

    def walk_ops(s, t, u, val=None):
        val = val or s.val()
        best = None
        for o in s.subs[t]:
            inv = coordinv([val[c] for c in o])
            if inv is None:
                continue
            g = val[t] ^ u
            vec = [(g >> inv[z]) & 1 for z in range(8)]
            a = [vec[i] for i in range(8)]
            for k in range(3):
                b = 1 << k
                for i in range(8):
                    if i & b:
                        a[i] ^= a[i ^ b]
            ow = [s.w[c] for c in o]
            tw = s.w[t]
            ops = []
            ok = True
            for mono in (1, 2, 4, 3, 5, 6, 7):
                if not a[mono]:
                    continue
                bits = [i for i in range(3) if (mono >> i) & 1]
                if len(bits) == 1:
                    ops.append(("cx", (ow[bits[0]], tw)))
                elif len(bits) == 2:
                    ops.append(("mand", (ow[bits[0]], ow[bits[1]], tw)))
                else:
                    ops.append(("mand3", (ow[0], ow[1], ow[2], tw)))
            if not ok:
                continue
            if a[0]:
                ops.append(("x", (tw,)))
            d = s.M.trial(ops)[1]
            if best is None or d < best[0]:
                best = (d, ops)
        return best[1] if best else None

    def moves(s, val, t):
        """single-gate (and negated-control) reaches from val[t]: the value
        wanted is usually one gate away from one that is already live, so it
        is never worth laying down a whole ANF."""
        out = []
        others = [c for c in range(s.n) if c != t]
        tw = s.w[t]
        for c in others:
            out.append((val[t] ^ val[c], [("cx", (s.w[c], tw))]))
        for c1, c2 in itertools.combinations(others, 2):
            a1, a2 = val[c1], val[c2]
            w1, w2 = s.w[c1], s.w[c2]
            out.append((val[t] ^ (a1 & a2), [("mand", (w1, w2, tw))]))
            # (~a1)&a2 == a2 ^ a1a2
            out.append((val[t] ^ (a2 ^ (a1 & a2)),
                        [("mand", (w1, w2, tw)), ("cx", (w2, tw))]))
            out.append((val[t] ^ (a1 ^ (a1 & a2)),
                        [("mand", (w1, w2, tw)), ("cx", (w1, tw))]))
            # (~a1)&(~a2) == 1 ^ a1 ^ a2 ^ a1a2
            out.append((val[t] ^ (255 ^ a1 ^ a2 ^ (a1 & a2)),
                        [("mand", (w1, w2, tw)), ("cx", (w1, tw)),
                         ("cx", (w2, tw)), ("x", (tw,))]))
        for c1, c2, c3 in itertools.combinations(others, 3):
            a1, a2, a3 = val[c1], val[c2], val[c3]
            out.append((val[t] ^ (a1 & a2 & a3),
                        [("mand3", (s.w[c1], s.w[c2], s.w[c3], tw))]))
        return out

    def reach2(s, val, u, avoid):
        """(ops, target) reaching u in two single-gate moves: one value is
        parked on a member, then the second move lands on u.  This is where
        most of the reuse comes from -- laying down a full ANF instead is
        three to seven gates."""
        best = None
        for t1 in range(s.n):
            for nv1, ops1 in s.moves(val, t1):
                if nv1 == val[t1]:
                    continue
                v2 = list(val)
                v2[t1] = nv1
                if not s.walkable(v2):
                    continue
                for t2 in range(s.n):
                    if s.w[t2] in avoid:
                        continue
                    for nv2, ops2 in s.moves(v2, t2):
                        if nv2 != u:
                            continue
                        v3 = list(v2)
                        v3[t2] = u
                        if not s.walkable(v3):
                            continue
                        ops = ops1 + ops2
                        if best is None or len(ops) < len(best[0]):
                            best = (ops, t2)
        return best

    def cost(s, u, avoid=()):
        """ops needed to make u readable, without emitting anything: 0 if it
        is already live, the move length if one gate away, else the ANF."""
        val = s.val()
        for i, v in enumerate(val):
            if v == u and s.w[i] not in avoid:
                return 0
        best = None
        for t in range(s.n):
            if s.w[t] in avoid:
                continue
            for nv, ops in s.moves(val, t):
                if nv != u:
                    continue
                v2 = list(val)
                v2[t] = u
                if not s.walkable(v2):
                    continue
                if best is None or len(ops) < best:
                    best = len(ops)
        if best is not None:
            return best
        r = s.reach2(val, u, avoid)
        if r is not None:
            best = len(r[0])
        for t in s.walkable(val):
            if s.w[t] in avoid:
                continue
            v2 = list(val)
            v2[t] = u
            if not s.walkable(v2):
                continue
            ops = s.walk_ops(t, u, val)
            if ops and (best is None or len(ops) < best):
                best = len(ops)
        return 99 if best is None else best

    def provide(s, u, avoid=()):
        """wire holding u.  Reuse it if it is already live; else the cheapest
        single-gate move onto some member; else a full ANF walk."""
        val = s.val()
        for i, v in enumerate(val):
            if v == u and s.w[i] not in avoid:
                return s.w[i]
        best = None
        for t in range(s.n):
            if s.w[t] in avoid:
                continue
            for nv, ops in s.moves(val, t):
                if nv != u:
                    continue
                v2 = list(val)
                v2[t] = u
                if not s.walkable(v2):
                    continue
                d = s.M.trial(ops)[1]
                if best is None or d < best[0]:
                    best = (d, ops, t)
        if best is None:
            r = s.reach2(val, u, avoid)
            if r is not None:
                best = (s.M.trial(r[0])[1], r[0], r[1])
        if best is None:
            for t in s.walkable(val):
                if s.w[t] in avoid:
                    continue
                v2 = list(val)
                v2[t] = u
                if not s.walkable(v2):
                    continue
                ops = s.walk_ops(t, u, val)
                if not ops:
                    continue
                d = s.M.trial(ops)[1]
                if best is None or d < best[0]:
                    best = (d, ops, t)
        if best is None:
            return None
        for name, qs in best[1]:
            s.M.emit(name, qs)
        return s.w[best[2]]

    def _cands(s, val, goal):
        """(ops, newstate): walk a data member straight to its coordinate, or
        park any value on an ancilla, which is the only helper there is."""
        out = []
        for t in range(s.n):
            if t < 3:
                us = [goal[t]] if val[t] != goal[t] else []
            else:
                us = range(256)
            for u in us:
                if u == val[t]:
                    continue
                v2 = list(val)
                v2[t] = u
                if not s.walkable(v2):
                    continue
                ops = None
                for nv, o in s.moves(val, t):
                    if nv == u and (ops is None or len(o) < len(ops)):
                        ops = o
                if ops is None:
                    ops = s.walk_ops(t, u, val)
                if not ops:
                    continue
                out.append((s.M.trial(ops)[1], ops, tuple(v2)))
        out.sort(key=lambda z: z[0])
        return out

    def close(s, beam=120, maxdepth=16):
        """walk every member home.  Data members are scored first: counting
        the ancilla as progress makes the search zero it early and strand
        every member that still needs it as a helper."""
        goal = [sum(((h >> j) & 1) << h for h in range(8)) for j in range(3)]
        goal = goal + [0] * (s.n - 3)
        start = tuple(s.val())
        if list(start) == goal:
            return True
        frontier = [(0.0, start, [])]
        seen = {start}
        done = None
        for _ in range(maxdepth):
            for cost, st, ops in frontier:
                if all(st[t] == goal[t] for t in range(3)):
                    done = (st, ops)
                    break
            if done:
                break
            nxt = []
            sv = s.val()
            for cost, st, ops in frontier:
                s._force(st)
                for d, mops, ns in s._cands(list(st), goal)[:beam]:
                    if ns in seen:
                        continue
                    nxt.append((cost + d,
                                sum(1 for t in range(3) if ns[t] != goal[t]),
                                ns, ops + mops))
            s._force(sv)
            if not nxt:
                break
            nxt.sort(key=lambda z: (z[1], z[0]))
            frontier = []
            for c, _o, ns, o in nxt:
                if ns in seen:
                    continue
                seen.add(ns)
                frontier.append((c, ns, o))
                if len(frontier) >= beam:
                    break
        if done is None:
            return False
        for name, qs in done[1]:
            s.M.emit(name, qs)
        for t in range(3, s.n):
            val = s.val()
            if val[t] == goal[t]:
                continue
            ops = None
            for nv, o in s.moves(val, t):
                if nv == goal[t] and (ops is None or len(o) < len(ops)):
                    ops = o
            if ops is None:
                ops = s.walk_ops(t, goal[t], val)
            if not ops:
                return False
            for name, qs in ops:
                s.M.emit(name, qs)
        return s.val() == goal

    def _force(s, st):
        """set the machine masks so this block reads back the state `st`
        (search bookkeeping only; no gates are emitted)."""
        sh = 3 if s.hi else 0
        for i, w in enumerate(s.w):
            s.M.m[w] = lift_blk(st[i], sh, s.side)


def split_sides(d):
    """d == P(x) ^ Q(y) ^ c, or None.  Every relative phase in this emitter
    comes from a gate whose controls and target are all on one side, so the
    leftover always has this shape."""
    P = Q = 0
    c = d & 1
    for xv in range(64):
        if ((d >> xv) & 1) ^ c:
            P |= 1 << xv
    for yv in range(64):
        if ((d >> (64 * yv)) & 1) ^ c:
            Q |= 1 << yv
    chk = 0
    for idx in range(NIN):
        if ((P >> (idx & 63)) & 1) ^ ((Q >> (idx >> 6)) & 1) ^ c:
            chk |= 1 << idx
    return (P, Q, c) if chk == d else None


def walk_blk(carriers, orders, anc):
    """one gate list: four blocks held as live state on their own wires, the
    carriers walking the legs, phases fired as the pairs come resident, and
    everything walked home at the end.  `anc` = the ancilla each block gets.
    """
    M = Mach()
    B = {}
    B[(0, False)] = Blk(M, list(XB[0]) + [anc[0]], 0, False)
    B[(0, True)] = Blk(M, list(XB[1]) + [anc[1]], 0, True)
    B[(1, False)] = Blk(M, list(YB[0]) + [anc[2]], 1, False)
    B[(1, True)] = Blk(M, list(YB[1]) + [anc[3]], 1, True)

    def term_tt(u8, v8):
        t = 0
        for v in range(64):
            if ((u8 >> (IDX[v] >> 3)) & 1) and ((v8 >> (IDX[v] & 7)) & 1):
                t |= 1 << v
        return t

    def leg_side(w, want, side, kdec=40):
        """move the carrier to `want` by the affine-reduced decomposition of
        the DELTA: rank-1 terms as Margolus from two live block values, the
        row/column/constant part as CX/CX/X so it never costs a term."""
        cur = x_tt(M.m[w]) if side == 0 else y_tt(M.m[w])
        tgt = x_tt(want) if side == 0 else y_tt(want)
        if cur is None or tgt is None:
            return False
        delta = cur ^ tgt
        if delta == 0:
            return True
        cands = decomps(delta, kdec)
        bestdec, bestc = None, None
        for d in cands:
            c = 0
            for u8, v8 in d:
                c += B[(side, True)].cost(u8, (w,))
                c += B[(side, False)].cost(v8, (w,))
            c += 4 * len(d)
            if bestc is None or c < bestc:
                bestc, bestdec = c, d
        dec = bestdec
        applied = 0
        for u8, v8 in dec:
            wu = B[(side, True)].provide(u8, (w,))
            if wu is None:
                return False
            wv = B[(side, False)].provide(v8, (w, wu))
            if wv is None:
                return False
            M.emit("mand", (wu, wv, w))
            applied ^= term_tt(u8, v8)
        ap = affine_part(delta, applied)
        if ap is False:
            return False
        if ap is not None:
            fA, fB, c = ap
            if fA:
                wu = B[(side, True)].provide(fA, (w,))
                if wu is None:
                    return False
                M.emit("cx", (wu, w))
            if fB:
                wv = B[(side, False)].provide(fB, (w,))
                if wv is None:
                    return False
                M.emit("cx", (wv, w))
            if c:
                M.emit("x", (w,))
        return True

    heads = [0] * len(carriers)
    live = list(range(len(carriers)))
    while live:
        c = min(live, key=lambda i: max(M.lay[carriers[i][0]],
                                        M.lay[carriers[i][1]]))
        k = orders[c][heads[c]]
        wx, wy = carriers[c]
        if not leg_side(wx, lift_x(XAT[k]), 0):
            return M, "x leg %d" % k
        if not leg_side(wy, lift_y(YAT[k]), 1):
            return M, "y leg %d" % k
        M.emit("cz", (wx, wy))
        heads[c] += 1
        if heads[c] >= len(orders[c]):
            live.remove(c)
    for wx, wy in carriers:
        if not leg_side(wx, 0, 0):
            return M, "x close"
        if not leg_side(wy, 0, 1):
            return M, "y close"
    def apply_side(side, P):
        """fire the phase (-1)^P(one side) on live block values."""
        dec = decomps(P, 40)[0]
        applied = 0
        for u8, v8 in dec:
            if u8 == 255 and v8 == 255:
                M.emit("x", (anc[0],))
                M.emit("z", (anc[0],))
                M.emit("x", (anc[0],))
                M.emit("z", (anc[0],))
            elif u8 == 255:
                wv = B[(side, False)].provide(v8)
                if wv is None:
                    return False
                M.emit("z", (wv,))
            elif v8 == 255:
                wu = B[(side, True)].provide(u8)
                if wu is None:
                    return False
                M.emit("z", (wu,))
            else:
                wu = B[(side, True)].provide(u8)
                wv = B[(side, False)].provide(v8, (wu,))
                if wu is None or wv is None:
                    return False
                M.emit("cz", (wu, wv))
            applied ^= term_tt(u8, v8)
        ap = affine_part(P, applied)
        if ap is False:
            return False
        if ap is not None:
            fA, fB, c = ap
            if fA:
                wu = B[(side, True)].provide(fA)
                if wu is None:
                    return False
                M.emit("z", (wu,))
            if fB:
                wv = B[(side, False)].provide(fB)
                if wv is None:
                    return False
                M.emit("z", (wv,))
            if c:
                w0 = anc[0]
                M.emit("x", (w0,))
                M.emit("z", (w0,))
                M.emit("x", (w0,))
                M.emit("z", (w0,))
        return True

    want = logo_mask()
    for rnd in range(8):
        for key in ((0, False), (0, True), (1, False), (1, True)):
            if not B[key].close():
                return M, "block close %s" % (key,)
        d = M.phase ^ want
        if d == 0:
            return M, None
        if rnd == 0:
            if not pf_correct(M, d, (anc[1], anc[0], carriers[0][0], anc[3]),
                              (anc[3], anc[2], carriers[0][1], anc[1])):
                return M, "phase-free correction failed"
            if M.phase == want and not M.restored():
                return M, None
            continue
        sp = split_sides(d)
        if sp is None:
            return M, "deficit does not split by side"
        P, Q, c = sp
        if c:
            w0 = anc[0]
            M.emit("x", (w0,))
            M.emit("z", (w0,))
            M.emit("x", (w0,))
            M.emit("z", (w0,))
        if P and not apply_side(0, P):
            return M, "P correction failed"
        if Q and not apply_side(1, Q):
            return M, "Q correction failed"
    return M, "phase did not converge"


from cpdr_split import apply_T, reduce49                         # noqa: E402
from cpdr_split2 import mrank                                    # noqa: E402
from cpdr_terms import factor, uclass                            # noqa: E402
from cpdr_emit2 import vec8                                      # noqa: E402
from cpdt_core import tt_of                                      # noqa: E402

IDX = apply_T([1, 2, 4, 8, 0x10, 0x20])      # identity: hi = v>>3, lo = v&7


def decomps(tt, kdec=40, cap=400):
    """rank-1 decompositions of the AFFINE-REDUCED delta, cheapest factors
    first.  The row/column/constant part is handled separately by CX/X, so it
    never costs a term."""
    m = reduce49(tt, IDX)
    if not m:
        return [[]]
    r = mrank(m)
    raw = factor(m, r, cap=cap)
    raw.sort(key=lambda dec: sum(uclass(u) + uclass(w) for u, w in dec))
    out, seen = [], set()
    for dec in raw:
        k = tuple(sorted(dec))
        if k in seen:
            continue
        seen.add(k)
        out.append([(tt_of(vec8(u)), tt_of(vec8(w))) for u, w in dec])
        if len(out) >= kdec:
            break
    return out or [[]]


def affine_part(tt, applied):
    """(fA over hi, fB over lo, const) of the residue tt ^ applied."""
    res = tt ^ applied
    if not res:
        return None
    M = [[0] * 8 for _ in range(8)]
    for v in range(64):
        M[IDX[v] >> 3][IDX[v] & 7] = (res >> v) & 1
    c = M[0][0]
    fA = [M[h][0] ^ c for h in range(8)]
    fB = [M[0][l] ^ c for l in range(8)]
    chk = 0
    for v in range(64):
        if fA[IDX[v] >> 3] ^ fB[IDX[v] & 7] ^ c:
            chk |= 1 << v
    if chk != res:
        return False
    return tt_of(fA), tt_of(fB), c


def pf_value(M, V, H, H2, tt8, bw):
    """XOR the block function tt8 onto wire V without contributing ANY phase.

    A Margolus onto a zero target contributes a & ~b & 0 = 0, and undoing it
    contributes a & ~b & (a&b) = 0, so every nonlinear monomial is laid down
    on a scratch that starts and ends at zero and copied across with a CX,
    which has no relative phase at all.  Calling this twice cancels exactly,
    so the same routine builds and clears.
    """
    a = anf3(tt8)
    for k in range(3):
        if a[1 << k]:
            M.emit("cx", (bw[k], V))
    for mono, (i, j) in ((3, (0, 1)), (5, (0, 2)), (6, (1, 2))):
        if a[mono]:
            M.emit("mand", (bw[i], bw[j], H))
            M.emit("cx", (H, V))
            M.emit("mand", (bw[i], bw[j], H))
    if a[7]:
        M.emit("mand", (bw[0], bw[1], H))
        M.emit("mand3", (bw[0], bw[1], bw[2], H2)) if False else None
        M.emit("mand", (H, bw[2], H2))
        M.emit("cx", (H2, V))
        M.emit("mand", (H, bw[2], H2))
        M.emit("mand", (bw[0], bw[1], H))
    if a[0]:
        M.emit("x", (V,))


def _pf_cost(tt8):
    a = anf3(tt8)
    return sum(a[1:4:2]) + 3 * (a[3] + a[5] + a[6]) + 5 * a[7]


def pf_correct(M, D, W0, W1):
    """apply (-1)^D with no phase of its own, D = P(x) ^ Q(y) ^ c.

    Terms are grouped by their hi factor so it is built once and reused over
    every lo factor that pairs with it, and the decomposition is chosen by
    what it actually costs to lay down phase-free."""
    sp = split_sides(D)
    if sp is None:
        return False
    P, Q, c = sp

    def flip(H=W0[2]):
        M.emit("x", (H,))
        M.emit("z", (H,))
        M.emit("x", (H,))
        M.emit("z", (H,))

    if c:
        flip()
    for side, G in ((0, P), (1, Q)):
        if not G:
            continue
        V1, V2, H, H2 = W0 if side == 0 else W1
        bhi, blo = blk_wires(side, True), blk_wires(side, False)
        best, bc = None, None
        for dec in decomps(G, 40):
            hs = {}
            for u8, v8 in dec:
                hs.setdefault(u8, []).append(v8)
            cc = sum(_pf_cost(u) * 2 for u in hs)
            cc += sum(_pf_cost(v) * 2 for vs in hs.values() for v in vs)
            if bc is None or cc < bc:
                bc, best = cc, dec
        dec = best
        red = 0
        for u8, v8 in dec:
            for v in range(64):
                if ((u8 >> (IDX[v] >> 3)) & 1) and ((v8 >> (IDX[v] & 7)) & 1):
                    red ^= 1 << v
        groups = {}
        for u8, v8 in dec:
            groups.setdefault(u8, []).append(v8)
        for u8, vs in groups.items():
            if u8 == 255:
                for v8 in vs:
                    if v8 == 255:
                        flip(H)
                    else:
                        pf_value(M, V2, H, H2, v8, blo)
                        M.emit("z", (V2,))
                        pf_value(M, V2, H, H2, v8, blo)
                continue
            pf_value(M, V1, H, H2, u8, bhi)
            for v8 in vs:
                if v8 == 255:
                    M.emit("z", (V1,))
                else:
                    pf_value(M, V2, H, H2, v8, blo)
                    M.emit("cz", (V1, V2))
                    pf_value(M, V2, H, H2, v8, blo)
            pf_value(M, V1, H, H2, u8, bhi)
        ap = affine_part(G, red)
        if ap is False:
            return False
        if ap is not None:
            fA, fB, cc2 = ap
            if fA:
                pf_value(M, V1, H, H2, fA, bhi)
                M.emit("z", (V1,))
                pf_value(M, V1, H, H2, fA, bhi)
            if fB:
                pf_value(M, V2, H, H2, fB, blo)
                M.emit("z", (V2,))
                pf_value(M, V2, H, H2, fB, blo)
            if cc2:
                flip(H)
    return True
