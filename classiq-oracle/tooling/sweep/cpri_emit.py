"""CP-RI emitter: schedule (from cpri_round) -> real circuit, exact check, depth.

Per round: x RCCX's, then y RCCX's (or the reverse).  A pair (u, v) placed in
round r is emitted as a set of cz's:
  option A: u = XOR of x items (wire-before values and products), v = XOR of
            y wire-before values.  cz(w, w') at round start for wire items;
            cz(t, w') before and after the x RCCX for product items.
  option B: symmetric (y products, x wire values that are not x targets).
usage: cpri_emit.py sched.pkl
"""
import sys, pickle
from cpae_core import ops_to_qc, real_depth, mirror, sv_check
from cpri_round import simulate, logo_pairs, init_tables, NW

XW = [0, 1, 2, 3, 4, 5, 12, 13, 14]
YW = [6, 7, 8, 9, 10, 11, 15, 16, 17]


def represent(items, target, forbid=()):
    """subset of items (index list) whose XOR is target, avoiding 'forbid'
    indices when possible; None if impossible."""
    idx = [i for i in range(len(items)) if i not in forbid]
    rows = []                       # (vector, combination bitmask over idx)
    for j, i in enumerate(idx):
        v, c = items[i], 1 << j
        for hv, hc in rows:
            if (v >> (hv.bit_length() - 1)) & 1:
                v ^= hv; c ^= hc
        if v:
            rows.append((v, c)); rows.sort(key=lambda t: -t[0].bit_length())
    v, c = target, 0
    for hv, hc in rows:
        if (v >> (hv.bit_length() - 1)) & 1:
            v ^= hv; c ^= hc
    if v:
        return None if not forbid else represent(items, target)
    return [idx[j] for j in range(len(idx)) if (c >> j) & 1]


def emit(sched, pairs):
    xinit = init_tables(); yinit = init_tables()
    xl = sched.get('xlin') or [[] for _ in sched['x']]; yl = sched.get('ylin') or [[] for _ in sched['y']]
    rx = simulate(xinit, sched['x'], xl); ry = simulate(yinit, sched['y'], yl)
    R = len(sched['x'])
    C = (1 << 64) - 1
    plan = {r: [] for r in range(R)}      # (opt, k, x-items, y-items, npx, npy)
    for k, (u, v) in enumerate(pairs):
        # per round: how v can be realised on the y side
        yrep = {}
        for r in range(R):
            ys, yp = ry[r]
            a = represent(ys + [C], v)
            if a is not None:
                yrep[r] = ('A', a, 0)
            else:
                b = represent(ys + yp + [C], v)
                if b is not None:
                    yrep[r] = ('B', b, len(yp))
        # union of x items over usable rounds
        items = []; where = []
        for r in yrep:
            xs, xp = rx[r]; xt = [g[4] for g in sched['x'][r]]
            opt = yrep[r][0]
            for i, val in enumerate(xs):
                if opt == 'B' and i in xt:
                    continue
                items.append(val); where.append((r, i))
            if opt == 'A':
                for j, val in enumerate(xp):
                    items.append(val); where.append((r, NW + j))
            items.append(C); where.append((r, 'const'))
        sel = represent(items, u)
        if sel is None:
            raise RuntimeError(f'pair {k} not emittable')
        byr = {}
        for s in sel:
            r, i = where[s]; byr.setdefault(r, []).append(i)
        for r, xi in byr.items():
            opt, yi, npy = yrep[r]
            plan[r].append((opt, k, xi, yi, len(rx[r][1]), npy))
    ops = []
    for r in range(R):
        xg = sched['x'][r]; yg = sched['y'][r]
        pre, mid, post = [], [], []
        def ph(a, b):                      # phase gate for a pair of wire-or-const
            if a is None and b is None: return None
            if a is None: return ('z', b)
            if b is None: return ('z', a)
            return ('cz', a, b)
        for opt, k, sx, sy, npx, npy in plan[r]:
            if opt == 'A':
                for i in sx:
                    for j in sy:
                        yw = None if j == NW else YW[j]
                        if i == 'const':
                            g = ph(None, yw)
                            if g: pre.append(g)
                        elif i < NW:
                            g = ph(XW[i], yw)
                            if g: pre.append(g)
                        else:
                            t = XW[xg[i - NW][4]]
                            pre.append(ph(t, yw)); mid.append(ph(t, yw))
            else:
                for j in sy:
                    for i in sx:
                        xw = None if i == 'const' else XW[i]
                        if j < NW:
                            g = ph(xw, YW[j])
                            if g: pre.append(g)
                        elif j == NW + npy:
                            g = ph(xw, None)
                            if g: pre.append(g)
                        else:
                            t = YW[yg[j - NW][4]]
                            mid.append(ph(xw, t)); post.append(ph(xw, t))
        for s_, d_ in xl[r]:
            ops.append(('cx', XW[s_], XW[d_]))
        for s_, d_ in yl[r]:
            ops.append(('cx', YW[s_], YW[d_]))
        ops += pre
        for a, pa, b, pb, t in xg:
            if pa: ops.append(('x', XW[a]))
            if pb: ops.append(('x', XW[b]))
            ops.append(('ccx', XW[a], XW[b], XW[t]))
            if pa: ops.append(('x', XW[a]))
            if pb: ops.append(('x', XW[b]))
        ops += mid
        for a, pa, b, pb, t in yg:
            if pa: ops.append(('x', YW[a]))
            if pb: ops.append(('x', YW[b]))
            ops.append(('ccx', YW[a], YW[b], YW[t]))
            if pa: ops.append(('x', YW[a]))
            if pb: ops.append(('x', YW[b]))
        ops += post
    fwd = ops
    full = fwd + mirror([o for o in fwd if o[0] not in ('cz', 'z')])
    return full


def main():
    sched = pickle.load(open(sys.argv[1], 'rb'))
    full = emit(sched, logo_pairs())
    qc = ops_to_qc(full)
    print('gates', len(full), 'depth/cx', real_depth(qc))
    print('sv check (err, leak)', sv_check(qc, 'LOGO'))


if __name__ == '__main__':
    main()
