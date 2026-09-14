"""CP-DH core: programs in the problem-sheet syntax, exact 4096-input replay,
width census, nested-leg block assembly, real transpile.

Program text, one op per line, registers x0..x5 y0..y5 s0..sN, '~' = complement
control (X before and after, free in transpile):
    AND  t a b        t ^= a & b            (RCCX, cpae 'ccx')
    AND3 t a b c      t ^= a & b & c        (RC3X, cpae 'c3x')
    CX   t a          t ^= a
    X    t
    CZ   a b          phase (-1)^(a b)
    CCZ  a b c
Block shape (nested legs): forward = C1 CZ1 C2 CZ2 ... Ck CZk, then the
mirror of every non-phase op in reverse.  Exact by conjugation.
"""
import re
import sys
import time

import numpy as np

import cpae_core as AE

NIN = 4096
FULL = (1 << NIN) - 1


def data_masks():
    b = {}
    for k in range(6):
        b["x%d" % k] = 0
        b["y%d" % k] = 0
    for idx in range(NIN):
        xv, yv = idx & 63, idx >> 6
        for k in range(6):
            if (xv >> k) & 1:
                b["x%d" % k] |= 1 << idx
            if (yv >> k) & 1:
                b["y%d" % k] |= 1 << idx
    return b


BASE = data_masks()
RAW = set(BASE.values()) | {FULL ^ v for v in BASE.values()}


def want_mask(shape):
    img = AE.SHAPES[shape]
    w = 0
    for idx in range(NIN):
        if img[idx & 63, idx >> 6]:
            w |= 1 << idx
    return w


def parse(text):
    """-> list of (kind, target, controls[(name, neg)])  kinds: and, and3, cx,
    x, cz, ccz."""
    ops = []
    for ln in text.splitlines():
        ln = ln.split("#")[0].strip()
        if not ln:
            continue
        parts = ln.split()
        k = parts[0].upper()
        args = []
        for p in parts[1:]:
            neg = p.startswith("~")
            args.append((p.lstrip("~"), neg))   # name may be an XOR expr a^b^c
        if k in ("AND", "AND3", "CX"):
            t = args[0][0]
            ops.append((k.lower(), t, args[1:]))
        elif k == "X":
            ops.append(("x", args[0][0], []))
        elif k in ("CZ", "CCZ"):
            ops.append((k.lower(), None, args))
        else:
            raise ValueError(ln)
    return ops


def cmask(m, a):
    """mask of an affine control expression (registers joined by ^)."""
    v = 0
    for r in a.split("^"):
        if r not in m:
            m[r] = 0
        v ^= m[r]
    return v


def replay(ops, regs=None):
    """Exact replay.  Returns (masks dict, phase mask, trace of non-raw counts
    per op, host set)."""
    m = dict(BASE)
    ph = 0
    trace = []
    hosts = set()
    for op in ops:
        k, t, cs = op
        if t and t not in m:
            m[t] = 0
        if k == "x":
            m[t] ^= FULL
        elif k == "cx":
            (a, na), = cs
            m[t] ^= cmask(m, a) ^ (FULL if na else 0)
        elif k in ("and", "and3"):
            p = FULL
            for a, na in cs:
                p &= cmask(m, a) ^ (FULL if na else 0)
            m[t] ^= p
        elif k in ("cz", "ccz"):
            p = FULL
            for a, na in cs:
                p &= cmask(m, a) ^ (FULL if na else 0)
            ph ^= p
        nr = [r for r, v in m.items() if v != 0 and v not in RAW]
        hosts.update(r for r in nr if r[0] in "xy")
        trace.append(len(nr))
    return m, ph, trace, hosts


def fwd_and_mirror(ops):
    """forward = ops (with phase gates in place); block = forward + reverse of
    the non-phase ops (AND/AND3 are relative-phase; the inverse is the
    inverse gate, handled at the qiskit level)."""
    body = [op for op in ops if op[0] not in ("cz", "ccz")]
    return ops + [("inv:" + op[0], op[1], op[2]) for op in reversed(body)]


def check_block(ops, shape="D2"):
    """classical exactness of the nested-leg block: phase == shape, all
    registers restored."""
    blk = fwd_and_mirror(ops)
    m = dict(BASE)
    ph = 0
    for op in blk:
        k, t, cs = op
        inv = k.startswith("inv:")
        k = k[4:] if inv else k
        if t and t not in m:
            m[t] = 0
        if k == "x":
            m[t] ^= FULL
        elif k == "cx":
            (a, na), = cs
            m[t] ^= cmask(m, a) ^ (FULL if na else 0)
        elif k in ("and", "and3"):
            p = FULL
            for a, na in cs:
                p &= cmask(m, a) ^ (FULL if na else 0)
            m[t] ^= p
        else:
            p = FULL
            for a, na in cs:
                p &= cmask(m, a) ^ (FULL if na else 0)
            ph ^= p
    want = want_mask(shape)
    mism = bin(ph ^ want).count("1")
    dirty = [r for r, v in m.items() if v != BASE.get(r, 0)]
    return mism, dirty


def to_cpae(ops, order):
    """named ops -> cpae op-list spelling on integer wires (order = list of
    register names -> wire index).  Complement controls -> X pairs."""
    idx = {r: i for i, r in enumerate(order)}
    out = []
    for op in ops:
        k, t, cs = op
        inv = k.startswith("inv:")
        k = k[4:] if inv else k
        pre = []
        cs2 = []
        used = set()
        for a, na in cs:
            for r in a.split("^"):
                if "^" not in a:
                    used.add(r)
        if t:
            used.add(t)
        for a, na in cs:
            rs = a.split("^")
            if len(rs) > 1:
                cand = [r for r in rs if r not in used]
                host = cand[-1] if cand else rs[-1]
                used.add(host)
                h = idx[host]
                for r in rs:
                    if r != host:
                        pre.append(("cx", idx[r], h))
                cs2.append((host, na))
            else:
                cs2.append((a, na))
        cs = cs2
        out.extend(pre)
        negs = [idx[a] for a, na in cs if na]
        for w in negs:
            out.append(("x", w))
        if k == "x":
            out.append(("x", idx[t]))
        elif k == "cx":
            out.append(("cx", idx[cs[0][0]], idx[t]))
        elif k == "and":
            out.append(("ccx_dg" if inv else "ccx", idx[cs[0][0]],
                        idx[cs[1][0]], idx[t]))
        elif k == "and3":
            out.append(("c3x_dg" if inv else "c3x", idx[cs[0][0]],
                        idx[cs[1][0]], idx[cs[2][0]], idx[t]))
        elif k == "cz":
            out.append(("cz", idx[cs[0][0]], idx[cs[1][0]]))
        elif k == "ccz":
            out.append(("ccz", idx[cs[0][0]], idx[cs[1][0]], idx[cs[2][0]]))
        for w in negs:
            out.append(("x", w))
        out.extend(reversed(pre))
    return out


def regs_of(ops):
    s = []
    for k, t, cs in ops:
        for r in ([t] if t else []) + [x for a, _ in cs for x in a.split("^")]:
            if r not in s:
                s.append(r)
    return s


def default_order(ops):
    data = ["x%d" % i for i in range(6)] + ["y%d" % i for i in range(6)]
    extra = [r for r in regs_of(ops) if r not in data]
    return data + sorted(extra, key=lambda r: (len(r), r))


def measure(ops, order=None, lvl=(2, 3), shape="D2", sv=False):
    """forward depth, block depth/cx at real transpile; classical check."""
    order = order or default_order(ops)
    n = len(order)
    mism, dirty = check_block(ops, shape)
    fwd = to_cpae([op for op in ops if op[0] not in ("cz", "ccz")], order)
    blk = to_cpae(fwd_and_mirror(ops), order)
    res = {"n": n, "mism": mism, "dirty": len(dirty)}
    qf = AE.ops_to_qc(fwd, n)
    qb = AE.ops_to_qc(blk, n)
    for l in lvl:
        res["fwd%d" % l] = AE.real_depth(qf, l)
        res["blk%d" % l] = AE.real_depth(qb, l)
    _, _, trace, hosts = replay(ops)
    res["peak"] = max(trace) if trace else 0
    res["hosts"] = sorted(hosts)
    res["ands"] = sum(1 for op in ops if op[0] == "and")
    res["and3"] = sum(1 for op in ops if op[0] == "and3")
    res["legs"] = sum(1 for op in ops if op[0] in ("cz", "ccz"))
    if sv and n == 18:
        res["sv"] = AE.sv_check(qb, shape)
    return res


def fmt(res):
    return ("n=%d mism=%d dirty=%d ANDs=%d AND3=%d legs=%d peak=%d "
            "fwd2=%s blk2=%s blk3=%s hosts=%s%s"
            % (res["n"], res["mism"], res["dirty"], res["ands"], res["and3"],
               res["legs"], res["peak"], res["fwd2"], res["blk2"],
               res.get("blk3"), ",".join(res["hosts"]),
               (" sv=%.2e/%.1e" % res["sv"]) if "sv" in res else ""))


if __name__ == "__main__":
    text = open(sys.argv[1]).read()
    ops = parse(text)
    t0 = time.time()
    res = measure(ops, sv=("--sv" in sys.argv))
    print(fmt(res), "[%.1fs]" % (time.time() - t0))
