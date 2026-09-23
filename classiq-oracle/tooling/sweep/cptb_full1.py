"""assemble the disk core: x fold, m, E4, phase 1 (V3 + E4*W3, local
uncompute), phase 2 (W2/W1/W0 stages from ckpt), cross CX, chain; then
exact classical check, statevector check, real depth.
usage: cptb_full1.py [order=P1,W2,W1,W0]"""
import os, sys, pickle
from cpae_core import ops_to_qc, real_depth, mirror
from cptb_core import sched_ops, core_target, check, YW
from cptb_csim import phase_table
from cptb_phase1 import phase1
from cptb_yprep import TG, ALL, V3
from cpri_round import init_tables

A1, A2, A3 = 12, 13, 14
HERE = os.path.dirname(os.path.abspath(__file__))

def ysim(yops, st):
    w = list(st)
    for op in yops:
        if op[0] == 'x': w[op[1]] ^= ALL
        elif op[0] == 'cx': w[op[2]] ^= w[op[1]]
        elif op[0] == 'ccx': w[op[3]] ^= w[op[1]] & w[op[2]]
    return w

def locate(w, names):
    tg = {n: (t, c) for n, t, c in TG}; out = {}; used = set()
    for n in names:
        t, care = tg[n]
        for i, v in enumerate(w):
            if i in used: continue
            for pol in (0, 1):
                if ((v ^ (ALL if pol else 0)) ^ t) & care == 0:
                    out[n] = (i, pol); used.add(i); break
            if n in out: break
        if n not in out: raise RuntimeError('%s not on a wire' % n)
    return out

def build(order, upto=None):
    tag = '-'.join(order)
    p2 = []
    for k in range(1, upto or len(order)):
        s, _, _ = pickle.load(open(os.path.join(HERE, 'ckpt', 'ychain_%s_stage%d.pkl' % (tag, k)), 'rb'))
        p2 += sched_ops(s)
    st0 = list(init_tables()); st0[8] = V3
    loc = locate(ysim(p2, st0), ['V3', 'W2', 'W1', 'W0'])
    P = lambda n: YW[loc[n][0]]; pol = lambda n: loc[n][1]
    ops = [('x', 3), ('cx', 3, 0), ('cx', 3, 1), ('cx', 3, 2), ('x', 3), ('cx', 4, 3)]   # x fold
    ops += [('cx', 11, 4)]                                                              # m
    ops += [('x', 4), ('ccx', 5, 4, A1), ('x', 4)]                                      # E4 = x5 ~m
    ops += phase1()                                                                     # V3, E4*W3
    ops += [(o[0],) + tuple(YW[q] for q in o[1:]) for o in p2]                         # W2 W1 W0
    for i, n in ((0, 'W0'), (1, 'W1'), (2, 'W2')):
        ops.append(('cx', i, P(n)))                                                     # delta_i
    nd = lambda n: [] if pol(n) else [('x', P(n))]
    vx = [('x', P('V3'))] if pol('V3') else []
    ops += vx + [('ccx', A1, P('V3'), A2)] + vx                                         # E3
    ops += nd('W2') + [('ccx', A2, P('W2'), A3)] + nd('W2')                             # E2
    ops += [('cz', A2, 2), ('z', A2), ('cz', A3, 1), ('cz', A3, 2)]
    d1 = [('cz', 4, 0), ('cz', 4, 1)]
    ops += d1 + nd('W1') + [('ccx', A3, P('W1'), 4)] + nd('W1') + d1                    # E1
    d0 = [('z', 5), ('cz', 5, 0), ('cz', 5, 3)]
    ops += d0 + nd('W1') + nd('W0') + [('c3x', A3, P('W1'), P('W0'), 5)] + nd('W1') + nd('W0') + d0   # E0
    full = ops + mirror([o for o in ops if o[0] not in ('cz', 'z')])
    return ops, full

def csim_ops(ops):
    return [(o[0].replace('_dg', ''),) + tuple(o[1:]) for o in ops]

if __name__ == '__main__':
    order = (sys.argv[1] if len(sys.argv) > 1 else 'P1,W2,W1,W0').split(',')
    fwd, full = build(order)
    mism = int((phase_table(csim_ops(fwd), 18) != core_target()).sum())
    print('exact phase mismatches vs disk core:', mism)
    qc = ops_to_qc(full)
    print('forward depth/cx', real_depth(ops_to_qc(fwd)), '  FULL depth/cx', real_depth(qc))
    print('statevector (err, leak):', check(qc, core_target()))
