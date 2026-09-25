"""XAG -> exact phase-oracle circuit (whole truth table, no partition).
Every wire holds an affine form over the signals (const, x0..x11, the AND
nodes computed so far); the 18 forms stay linearly independent.
Internal AND n = L1*L2: bring L1, L2 onto wires with CX (span unchanged),
Toffoli into a target t (form_t -> form_t ^ n); t may be a clean ancilla or,
when every still-needed form stays in the span, any other wire (in place).
Phase: y = affine form over signals -> Z on x_i at t=0, Z before+after the
Toffoli of every AND in y; output-only ANDs L1*L2 -> CZ (+Z for polarities)
on the wires holding L1, L2 as soon as both are formable.  Then the mirror
of the permutation part.  Checks: classical replay, statevector, real depth.
Usage: python3 cptr_map.py FILE.v [SEED] [TRIALS]"""
import re, sys, random, pickle
import numpy as np
from cpae_core import mirror, ops_to_qc, real_depth, sv_check_gp, SHAPES, fvec
from cpth_emit import replay

NW, ND = 18, 12


def parse(path):
    defs = []
    for line in open(path):
        m = re.match(r"\s*assign (\S+) = (.*?);?\s*$", line)
        if m: defs.append((m.group(1), m.group(2).replace("1'b0", "C0").replace("1'b1", "C1")))
    form = {'x%d' % i: 1 << (1 + i) for i in range(12)}
    form['C0'] = 0; form['C1'] = 1
    ands = []                          # (bit, L1, L2)
    pend = dict(defs)
    def get(tok):
        tok = tok.strip(); neg = tok.startswith('~'); tok = tok.lstrip('~').strip()
        if tok not in form: ev(tok)
        return form[tok] ^ (1 if neg else 0)
    def ev(n):
        e = pend[n]
        if '&' in e:
            a, b = e.split('&'); A, B = get(a), get(b)
            bit = 1 << (13 + len(ands)); ands.append((bit, A, B)); form[n] = bit
        elif '^' in e:
            a, b = e.split('^'); form[n] = get(a) ^ get(b)
        else: form[n] = get(e)
    sys.setrecursionlimit(10000)
    for n, _ in defs:
        if n not in form: ev(n)
    y = [n for n, _ in defs if n.startswith('y') or n.startswith('po')][-1]
    return ands, form[y]


def reduce_basis(vecs):
    """returns list of (pivot_bit, vec, combo_mask over wire indices)"""
    B = []
    for i, v in vecs:
        c = 1 << i
        for pb, bv, bc in B:
            if v & pb: v ^= bv; c ^= bc
        if v:
            pb = v & -v
            for k in range(len(B)):
                if B[k][1] & pb: B[k] = (B[k][0], B[k][1] ^ v, B[k][2] ^ c)
            B.append((pb, v, c))
    return B


def rep(B, L):
    """wire combo giving L (linear part), or None"""
    c = 0
    for pb, bv, bc in B:
        if L & pb: L ^= bv; c ^= bc
    return None if L else c


def build(ands, Fo, rng, prefer_inplace=True):
    nA = len(ands)
    use = {}
    for k, (bit, A, B) in enumerate(ands):
        for L in (A, B):
            for j in range(nA):
                if L & ands[j][0]: use.setdefault(j, set()).add(k)
    internal = [k for k in range(nA) if k in use]
    outonly = [k for k in range(nA) if k not in use and Fo & ands[k][0]]
    lvl = {}
    for k, (bit, A, B) in enumerate(ands):
        lvl[k] = 1 + max([lvl[j] for j in range(k) if (A | B) & ands[j][0]] + [0])
    height = {}
    for k in reversed(range(nA)):
        height[k] = 1 + max([height[j] for j in use.get(k, ())] + [0])
    forms = [1 << (1 + i) for i in range(ND)] + [0] * (NW - ND)
    ops = [('z', i) for i in range(ND) if Fo & (1 << (1 + i))]
    done_mask = (1 << 13) - 2                      # inputs computed
    todo = sorted(internal, key=lambda k: (lvl[k], -height[k], rng.random()))
    outs = set(outonly)

    def basis(): return reduce_basis([(i, forms[i] & ~1) for i in range(NW) if forms[i] & ~1])

    def form_on(L, avoid):
        """CX ops putting linear part of L on one wire (not in avoid); returns wire or None"""
        Lc = L & ~1
        c = rep(basis(), Lc)
        if c is None: return None
        S = [i for i in range(NW) if c >> i & 1]
        cand = [p for p in S if p not in avoid]
        if not cand: return None
        p = min(cand, key=lambda q: bin(forms[q]).count('1'))
        for i in S:
            if i != p: ops.append(('cx', i, p)); forms[p] ^= forms[i]
        assert forms[p] & ~1 == Lc
        return p

    def needs():
        out = []
        for k in todo: out += [ands[k][1], ands[k][2]]
        for k in outs: out += [ands[k][1], ands[k][2]]
        return out

    def do_outputs():
        for k in sorted(outs):
            bit, A, B = ands[k]
            if ((A | B) >> 13) & ~(done_mask >> 13): continue
            Al, Bl = A & ~1, B & ~1
            if Al == 0 or Bl == 0 or Al == Bl:            # degenerate product: affine
                lin = []
                if Al == Bl: lin = [(Al, (A & 1) | (B & 1), (A & 1) & (B & 1))]
                # A==const: product = const*B
                if Al == 0 and (A & 1): lin = [(Bl, B & 1, 0)]
                if Bl == 0 and (B & 1): lin = [(Al, A & 1, 0)]
                for (L, c, _) in lin:
                    if Al == Bl and (A & 1) != (B & 1): break      # L*(L^1) = 0
                    p = form_on(L, set()); ops.append(('z', p))
                outs.discard(k); continue
            p1 = form_on(Al, set())
            p2 = form_on(Bl, {p1})
            if p1 is None or p2 is None: continue
            ops.append(('cz', p1, p2))
            if B & 1: ops.append(('z', p1))
            if A & 1: ops.append(('z', p2))
            outs.discard(k)

    do_outputs()
    while todo:
        # first ready AND in priority order
        k = next(k for k in todo if not (((ands[k][1] | ands[k][2]) >> 13) & ~(done_mask >> 13)))
        todo.remove(k)
        bit, A, B = ands[k]
        a = form_on(A, set()); b = form_on(B, {a})
        if a is None or b is None: return None, 'operand not formable (AND %d)' % k
        nd = needs()
        best = None
        for t in range(NW):
            if t in (a, b): continue
            old = forms[t]
            if old & ~1 and not prefer_inplace: continue
            forms[t] = old ^ bit
            Bn = basis(); dm = done_mask | bit
            ok = True; cost = 0
            for L in nd:
                Lc = L & ~1 & (dm | ((1 << 13) - 1))
                c = rep(Bn, Lc)
                if c is None: ok = False; break
                cost += bin(c).count('1') - 1
            forms[t] = old
            if ok:
                key = (0 if old & ~1 else 1, cost, rng.random()) if prefer_inplace else (cost, rng.random())
                if best is None or key < best[0]: best = (key, t)
        if best is None: return None, 'no feasible target (AND %d, level %d)' % (k, lvl[k])
        t = best[1]
        ph = bool(Fo & bit)
        if ph: ops.append(('z', t))
        fl = [q for q, L in ((a, A), (b, B)) if (forms[q] ^ L) & 1]
        ops.extend(('x', q) for q in fl); ops.append(('ccx', a, b, t)); ops.extend(('x', q) for q in fl)
        if ph: ops.append(('z', t))
        forms[t] ^= bit; done_mask |= bit
        do_outputs()
    if outs: return None, 'output ANDs left %d' % len(outs)
    return ops, 'ok'


if __name__ == '__main__':
    path = sys.argv[1]; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    trials = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    ands, Fo = parse(path)
    F = fvec(SHAPES['LOGO']).astype(np.int64)
    print('%s: ANDs %d' % (path, len(ands)), flush=True)
    best = None
    for tr in range(trials):
        rng = random.Random(seed * 1000 + tr)
        for pi in (True, False):
            ops, msg = build(ands, Fo, rng, pi)
            if ops is None: print('  trial %d inplace=%s: %s' % (tr, pi, msg), flush=True); continue
            perm = [o for o in ops if o[0] not in ('z', 'cz')]
            full = ops + mirror(perm)
            mism, ident = replay(full, F)
            d, cx = real_depth(ops_to_qc(full))
            print('  trial %d inplace=%s: toffolis %d  classical mism %d ident %s  real depth %d cx %d' %
                  (tr, pi, sum(o[0] == 'ccx' for o in ops), mism, ident, d, cx), flush=True)
            if mism == 0 and ident and (best is None or (d, cx) < best[:2]): best = (d, cx, full)
    if best:
        err, leak = sv_check_gp(ops_to_qc(best[2]), 'LOGO')
        print('best real depth %d cx %d  statevector err %.1e leak %.1e' % (best[0], best[1], err, leak), flush=True)
        pickle.dump(best[2], open(path.replace('.v', '_map_ops.pkl'), 'wb'))
