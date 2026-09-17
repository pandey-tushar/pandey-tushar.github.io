"""CP-FI: temporal phase span.

Given an op list whose classical action restores every wire (compute /
uncompute mirrors, any hosting, any junk), the phase gates that can be
inserted are z / cz / ccz on wires at any time t; each contributes the
product of the wire contents at that time.  Collect the distinct products
over the whole timeline and solve over GF(2) for a set whose XOR is the
target phase F.  Exact: the inserted gates are diagonal, so the classical
action is unchanged and the relative phases of the RCCX / RC3X mirrors
still cancel.
"""
import sys, time
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfh_core as C
from cpfh_core import FULL, NW, F, NLK

DIAG = ('z', 'cz', 'ccz')


def strip_phase(ops):
    return [op for op in ops if op[0] not in DIAG]


def timeline(ops):
    """contents before each op (index t) and after the last (index len)."""
    c = C.init(); snaps = [tuple(c)]
    for op in ops:
        C.apply(c, op); snaps.append(tuple(c))
    return snaps


def touched(op):
    return () if op[0] in DIAG else tuple(op[1:])


def candidates(ops, deg=2, triple_wires=None):
    """value -> earliest (t, wires).  t = number of ops preceding the gate.
    Only re-enumerates pairs that involve a wire changed by the previous op."""
    snaps = timeline(ops)
    cand = {}
    def add(v, t, ws):
        if v and v not in cand:
            cand[v] = (t, ws)
    c = snaps[0]
    for i in range(NW):
        add(c[i], 0, (i,))
        for j in range(i + 1, NW):
            add(c[i] & c[j], 0, (i, j))
    for t in range(1, len(snaps)):
        c = snaps[t]
        ch = touched(ops[t - 1])
        for i in ch:
            add(c[i], t, (i,))
            for j in range(NW):
                if j != i:
                    add(c[i] & c[j], t, tuple(sorted((i, j))))
    if deg >= 3 and triple_wires:
        # triples only at requested (t, wire-set) spots
        for t, ws in triple_wires:
            c = snaps[t]
            ws = sorted(ws)
            for a in range(len(ws)):
                for b in range(a + 1, len(ws)):
                    for d in range(b + 1, len(ws)):
                        add(c[ws[a]] & c[ws[b]] & c[ws[d]], t, (ws[a], ws[b], ws[d]))
    return cand


def solve(ops, target=F, deg=2, triple_wires=None, verbose=False):
    """-> (residual_weight, insertions)  insertions = [(t, wires), ...]"""
    t0 = time.time()
    cand = candidates(ops, deg, triple_wires)
    vals = sorted(cand.items(), key=lambda kv: (len(kv[1][1]), kv[1][0]))
    S = C.Span()
    for idx, (v, _) in enumerate(vals):
        S.add(v, idx)
    r, combo = S.reduce(target)
    if verbose:
        print('  span: %d candidates, rank %d, residual %d  (%.1fs)'
              % (len(vals), len(S.piv), bin(r).count('1'), time.time() - t0))
    if r:
        return bin(r).count('1'), None
    ins = [vals[i][1] for i in range(len(vals)) if (combo >> i) & 1]
    return 0, ins


def insert(ops, ins):
    """insert phase gates; ins = [(t, wires)] with t = ops preceding."""
    by_t = {}
    for t, ws in ins:
        by_t.setdefault(t, []).append(ws)
    out = []
    for t in range(len(ops) + 1):
        for ws in by_t.get(t, []):
            out.append((DIAG[len(ws) - 1],) + tuple(ws))
        if t < len(ops):
            out.append(ops[t])
    return out


def check(ops):
    c, ph = C.replay(ops)
    dirty = [w for w in range(NW) if c[w] != C.RM[w]]
    return bin(ph ^ F).count('1'), dirty


if __name__ == '__main__':
    import pickle
    ops = pickle.load(open('cpen_search_11.pkl', 'rb'))[1]
    base = strip_phase(ops)
    print('249-list: %d ops, %d without phase gates' % (len(ops), len(base)))
    r, ins = solve(base, deg=2, verbose=True)
    print('deg-2 residual', r)
    if r:
        # allow triples where the original ccz sat
        tw = []
        c = 0
        for op in ops:
            if op[0] == 'ccz':
                tw.append((c, op[1:]))
            elif op[0] != 'cz':
                c += 1
        r, ins = solve(base, deg=3, triple_wires=tw, verbose=True)
        print('deg-3 residual', r)
    if ins is not None:
        new = insert(base, ins)
        mism, dirty = check(new)
        print('inserted %d phase gates -> F mismatch %d dirty %s' % (len(ins), mism, dirty))
        print('gates:', sorted(ins))
        import cpfg_eval as E
        E.evaluate([], new, sv=True) if False else None
        from cpae_core import ops_to_qc, extract, sim_exact, fvec, SHAPES
        qc = ops_to_qc(new, n=18)
        gl, gp = extract(qc)
        err, mm = sim_exact(gl, gp, fvec(SHAPES['LOGO']))
        print('sim_exact: phase err %.2e perm mismatches %d' % (err, mm))
        print('TEST', 'PASS' if err < 1e-9 and mm == 0 and mism == 0 else 'FAIL')
