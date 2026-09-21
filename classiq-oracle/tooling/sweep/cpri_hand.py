"""CP-RI hand schedule tool.  Edit XR / YR below; run to see per-round coverage.
Round = (lins, gates): lins = [(src, dst), ...] CX applied in order at round
start; gates = [(a, pa, b, pb, t), ...] RCCX (pa/pb: complement control).
Local wires: data bits 0..5, ancillas 6,7,8.
"""
import sys
from cpri_round import simulate, logo_pairs, init_tables, in_span, NW
from cph_terms import PAIRS
from cpri_io import out_path as _out
ALL = (1 << 64) - 1


def residual(vecs, target):
    basis = {}
    for v in vecs:
        for hb in sorted(basis, reverse=True):
            if (v >> hb) & 1: v ^= basis[hb]
        if v: basis[v.bit_length() - 1] = v
    for hb in sorted(basis, reverse=True):
        if (target >> hb) & 1: target ^= basis[hb]
    return target


def report(XR, YR, pairs=None, names=None):
    pairs = pairs or logo_pairs(); names = names or [f'{a}|{b}' for a, b in PAIRS]
    sched = {'x': [g for _, g in XR], 'xlin': [l for l, _ in XR],
             'y': [g for _, g in YR], 'ylin': [l for l, _ in YR]}
    R = max(len(XR), len(YR))
    sched['x'] += [[]] * (R - len(XR)); sched['xlin'] += [[]] * (R - len(XR))
    sched['y'] += [[]] * (R - len(YR)); sched['ylin'] += [[]] * (R - len(YR))
    rx = simulate(init_tables(), sched['x'], sched['xlin'])
    ry = simulate(init_tables(), sched['y'], sched['ylin'])
    ok = 0
    for k, (u, v) in enumerate(pairs):
        yr = [r for r in range(R) if in_span(ry[r][0] + [ALL], v)]
        yrB = [r for r in range(R) if r not in yr and in_span(ry[r][0] + ry[r][1] + [ALL], v)]
        items = []
        for r in yr:
            items += rx[r][0] + rx[r][1]
        for r in yrB:
            xt = [g[4] for g in sched['x'][r]]
            items += [val for i, val in enumerate(rx[r][0]) if i not in xt]
        items.append(ALL)
        res = residual(items, u)
        single = [r for r in range(R) if in_span(rx[r][0] + rx[r][1] + [ALL], u)]
        ok += (res == 0)
        print(f'{k:2d} {names[k]:14s} y-rounds {yr}{"+B" + str(yrB) if yrB else ""}  x single-round {single}  '
              f'{"OK" if res == 0 else "residual " + str([x for x in range(64) if (res >> x) & 1])}')
    print(f'covered {ok}/{len(pairs)}   rounds x={len(XR)} y={len(YR)}  rccx x={sum(len(g) for _, g in XR)} y={sum(len(g) for _, g in YR)}')
    return sched


if __name__ == '__main__':
    import importlib
    mod = importlib.import_module(sys.argv[1] if len(sys.argv) > 1 else 'cpri_design')
    sched = report(mod.XR, mod.YR)
    if len(sys.argv) > 2 and sys.argv[2] == 'emit':
        import pickle
        from cpri_emit import emit
        from cpae_core import ops_to_qc, real_depth, sv_check
        full = emit(sched, logo_pairs()); qc = ops_to_qc(full)
        print('depth/cx', real_depth(qc)); print('sv', sv_check(qc, 'LOGO'))
        pickle.dump(sched, open(_out('cpri_design.pkl'), 'wb'))
