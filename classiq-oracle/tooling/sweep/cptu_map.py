"""Exact mapper v2 for a width-annealed XAG (cptu_width pkl): complete whenever
the width profile is <= 18.
Wire forms stay a basis of the current span S.  For AND k (operands A, B):
  N = still-needed forms after k, restricted to computed signals incl. k;
  Nn = those containing k, u_i = v_i ^ k;  M = span(N without k, u_i ^ u_1, A, B).
  Clean ancilla available -> target it (S grows).  Otherwise pick f = u_1 (or,
  if Nn is empty, any wire form outside M), a functional phi with phi(M) = 0,
  phi(f) = 1; put f on a wire t, CX(t -> j) for every other wire with
  phi(form_j) = 1 (now all others lie in H = ker phi), then form A, B on
  wires of H and Toffoli into t: new span H + <f ^ k> contains every need.
Phase: Z on x_i at t=0 for inputs in y; Z before + after the Toffoli of every
AND in y.  Then the mirror of the permutation part.
Usage: python3 cptu_map.py PKL"""
import sys, pickle
import numpy as np
from cpae_core import mirror, ops_to_qc, real_depth, sv_check_gp, SHAPES, fvec
from cpth_emit import replay
from cptr_map import reduce_basis, rep

import os
NW, ND = int(os.environ.get("NW", "18")), 12


def solve_phi(rows, target_row):
    """GF(2): find phi (bitmask over wires) with popcount(phi & r) even for r in rows, odd for target_row"""
    # unknown phi: 18 bits; equations: r . phi = 0, t . phi = 1
    eqs = [(r, 0) for r in rows] + [(target_row, 1)]
    piv = []
    for r, v in eqs:
        for pr, pv, pb in piv:
            if r >> pb & 1: r ^= pr; v ^= pv
        if r == 0:
            if v: return None
            continue
        pb = r.bit_length() - 1
        piv = [(pr ^ r, pv ^ v, b) if pr >> pb & 1 else (pr, pv, b) for pr, pv, b in piv]
        piv.append((r, v, pb))
    phi = 0
    for pr, pv, pb in piv:
        if pv: phi |= 1 << pb
    # free variables = 0; with fully reduced rows each pivot bit value = pv
    return phi


def build(ands, Fo, order):
    forms = [1 << (1 + i) for i in range(ND)] + [0] * (NW - ND)
    ops = [('z', i) for i in range(ND) if Fo & (1 << (1 + i))]
    done = (1 << 13) - 2

    def basis(): return reduce_basis([(i, forms[i] & ~1) for i in range(NW) if forms[i] & ~1])

    def cx(c, t): ops.append(('cx', c, t)); forms[t] ^= forms[c]

    def form_on(L, avoid):
        c = rep(basis(), L & ~1)
        if c is None: return None
        S = [i for i in range(NW) if c >> i & 1]
        cand = [p for p in S if p not in avoid]
        if not cand: return None
        p = min(cand, key=lambda q: bin(forms[q]).count('1'))
        for i in S:
            if i != p: cx(i, p)
        return p

    for pos, k in enumerate(order):
        A, B = ands[k]; bit = 1 << (13 + k)
        dm = done | bit
        need = set()
        for j in order[pos + 1:]:
            for L in ands[j]:
                v = L & dm & ~1
                if v: need.add(v)
        zero = [i for i in range(NW) if forms[i] & ~1 == 0]
        if zero:
            t = zero[0]
            a = form_on(A, {t}); b = form_on(B, {t, a})
            if a is None or b is None: return None, 'operand (anc) AND %d' % k
        else:
            Nn = [v ^ bit for v in need if v & bit]
            N0 = [v for v in need if not v & bit]
            Bs = basis()
            M = N0 + [u ^ Nn[0] for u in Nn[1:]] + [A & ~1, B & ~1]
            Mc = [rep(Bs, v) for v in M]
            if any(c is None for c in Mc): return None, 'need outside span at AND %d' % k
            if Nn: fcands = [Nn[0]]
            else: fcands = [forms[i] & ~1 for i in range(NW)]
            got = None
            for f in fcands:
                fc = rep(Bs, f)
                phi = solve_phi(Mc, fc)
                if phi is not None: got = (f, fc, phi); break
            if got is None: return None, 'no hyperplane at AND %d (width)' % k
            f, fc, phi = got
            S = [i for i in range(NW) if fc >> i & 1]
            # choose t in S with phi(t) = 1 (exists since phi(f) = 1)
            t = next(i for i in S if phi >> i & 1)
            for i in S:
                if i != t: cx(i, t)
            # phi is a functional on wire coordinates of the OLD basis; recompute on new forms
            Bs2 = basis()
            M2 = [rep(Bs2, v) for v in M]; f2 = rep(Bs2, f)
            phi = solve_phi(M2, f2)
            for j in range(NW):
                if j != t and phi >> j & 1: cx(t, j)
            a = form_on(A, {t}); b = form_on(B, {t, a})
            if a is None or b is None: return None, 'operand AND %d' % k
        ph = bool(Fo & bit)
        if ph: ops.append(('z', t))
        fl = [q for q, L in ((a, A), (b, B)) if (forms[q] ^ L) & 1]
        ops.extend(('x', q) for q in fl); ops.append(('ccx', a, b, t)); ops.extend(('x', q) for q in fl)
        if ph: ops.append(('z', t))
        forms[t] ^= bit; done |= bit
    return ops, 'ok'


if __name__ == '__main__':
    d = pickle.load(open(sys.argv[1], 'rb'))
    ops, msg = build(d['ands'], d['Fo'], d['order'])
    print('cost', d['cost'], 'map:', msg, flush=True)
    if ops is None: sys.exit(1)
    perm = [o for o in ops if o[0] not in ('z', 'cz')]
    full = ops + mirror(perm)
    F = fvec(SHAPES['LOGO']).astype(np.int64)
    mism, ident = replay(full, F)
    nt = sum(o[0] == 'ccx' for o in ops); ncx = sum(o[0] == 'cx' for o in ops)
    print('forward: toffoli %d cx %d   classical mism %d ident %s' % (nt, ncx, mism, ident), flush=True)
    qc = ops_to_qc(full, NW)
    d_, c_ = real_depth(qc)
    print('real depth %d cx %d' % (d_, c_), flush=True)
    if mism == 0 and ident and NW == 18:
        err, leak = sv_check_gp(qc, 'LOGO'); print('statevector err %.1e leak %.1e' % (err, leak), flush=True)
        pickle.dump(full, open(sys.argv[1].replace('.pkl', '_ops.pkl'), 'wb'))
