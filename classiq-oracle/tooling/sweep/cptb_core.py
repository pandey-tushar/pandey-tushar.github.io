"""CP-TB disk core: one forward stream + one mirror.

x fold (4 CX): c_i = x_i ^ ~x3 (i<3), s = x3 ^ x4 on wire 3.
y prep (given): wires holding V3, W3, y5, W2, W1, W0.
cross: m = x4 ^ y5 on wire 4; delta_i = c_i ^ W_i on the W_i wires.
chain: E4 = x5 ~m (A1), E3 = E4 V3 (A2), E2 = E3 ~d2 (A3),
       Q10 = ~d1 ~d0 (clean y wire), E1 = E2 ~d1 (product), E0 = E2 Q10 (product)
phase: E4 W3 + E3 ~c2 + E2 (c1^c2) + E1 (c0^c1) + E0 (1^c0^s)
target (disk core) = D1 ^ D2 ^ [x=48][17<=y<=21]
"""
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from cpae_core import ops_to_qc, real_depth, mirror, fvec, SHAPES
from cptb_yprep import TG, ALL

YW = [6, 7, 8, 9, 10, 11, 15, 16, 17]
A1, A2, A3 = 12, 13, 14

def core_target():
    t = SHAPES['D1'] ^ SHAPES['D2']
    t = t.copy()
    for y in range(17, 22): t[48, y] ^= 1
    return t

def ysim(yops):
    """local y-wire tables after the prep ops"""
    from cpri_round import bit
    w = [bit(k) for k in range(6)] + [0, 0, 0]
    for op in yops:
        if op[0] == 'x': w[op[1]] ^= ALL
        elif op[0] == 'cx': w[op[2]] ^= w[op[1]]
        elif op[0] == 'ccx': w[op[3]] ^= w[op[1]] & w[op[2]]
    return w

def locate(w):
    """target name -> (local wire, polarity) ; polarity 1 = wire holds complement"""
    out = {}; used = set()
    for name, t, care in TG:
        if name == 'y5': continue            # m = x4 ^ y5 is taken before the prep
        for i, v in enumerate(w):
            if i in used: continue
            for pol in (0, 1):
                if ((v ^ (ALL if pol else 0)) ^ t) & care == 0:
                    out[name] = (i, pol); used.add(i); break
            if name in out: break
        if name not in out: raise RuntimeError('target %s not on any wire' % name)
    free = [i for i in range(9) if i not in used and w[i] == 0]
    return out, free

def build(yops):
    ops = []
    # --- x fold (uses raw x4), then m = x4 ^ y5 on wire 4 from the raw y5 wire (11)
    ops += [('x', 3), ('cx', 3, 0), ('cx', 3, 1), ('cx', 3, 2), ('x', 3), ('cx', 4, 3)]
    ops.append(('cx', 11, 4))
    # --- y prep (local -> physical)
    for op in yops:
        ops.append((op[0],) + tuple(YW[q] for q in op[1:]))
    w = ysim(yops)
    loc, free = locate(w)
    P = lambda n: YW[loc[n][0]]
    pol = lambda n: loc[n][1]
    # --- cross: deltas on W wires (m already on wire 4)
    mpol = 0
    # E4 = x5 & ~m : control wire 4 must read ~m -> X unless mpol
    if not mpol: ops.append(('x', 4))
    ops.append(('ccx', 5, 4, A1))
    if not mpol: ops.append(('x', 4))
    for i, n in ((0, 'W0'), (1, 'W1'), (2, 'W2')):
        ops.append(('cx', i, P(n)))          # wire holds d_i ^ pol
    # ~d_i control: X on wire unless pol == 1
    def notd(n): return [] if pol(n) else [('x', P(n))]
    # E3 = E4 & V3
    vx = [('x', P('V3'))] if pol('V3') else []
    ops += vx + [('ccx', A1, P('V3'), A2)] + vx
    # readout E4 * W3
    ops.append(('cz', A1, P('W3')))
    if pol('W3'): ops.append(('z', A1))      # wire holds ~W3: E4(1^W3') = E4 ^ E4 W3'
    # E2 = E3 & ~d2 on A3
    ops += notd('W2') + [('ccx', A2, P('W2'), A3)] + notd('W2')
    # readout E3 * ~c2 : cz(A2, c2) and z(A2)
    ops += [('cz', A2, 2), ('z', A2)]
    # readout E2 * (c1 ^ c2)
    ops += [('cz', A3, 1), ('cz', A3, 2)]
    # E1 = E2 & ~d1 : product, differential vs (c0 ^ c1); target = x4 wire (garbage ok)
    diff1 = [('cz', 4, 0), ('cz', 4, 1)]
    ops += diff1 + notd('W1') + [('ccx', A3, P('W1'), 4)] + notd('W1') + diff1
    # E0 = E2 & Q10 : product, differential vs (1 ^ c0 ^ s); target = x5 wire
    diff0 = [('z', 5), ('cz', 5, 0), ('cz', 5, 3)]
    ops += diff0 + notd('W1') + notd('W0') + [('c3x', A3, P('W1'), P('W0'), 5)] + notd('W1') + notd('W0') + diff0
    full = ops + mirror([o for o in ops if o[0] not in ('cz', 'z')])
    return ops, full

def check(qc, target):
    f = np.array([int(target[i & 63, i >> 6]) for i in range(4096)])
    sgn = np.where(f == 1, -1.0, 1.0)
    rng = np.random.default_rng(3); worst = 0.0; leak = 0.0
    for _ in range(3):
        th = rng.uniform(0, 2 * np.pi, 12); x = np.arange(4096)
        amp = np.exp(1j * sum(th[j] * ((x >> j) & 1) for j in range(12))) / 64
        psi = np.zeros(1 << 18, complex); psi[:4096] = amp
        out = Statevector(psi).evolve(qc).data
        leak = max(leak, float(np.sum(abs(out[4096:]) ** 2)))
        want = amp * sgn; ph = np.vdot(want, out[:4096]); ph /= abs(ph)
        worst = max(worst, float(np.max(abs(out[:4096] - ph * want))))
    return worst, leak

if __name__ == '__main__':
    import sys, pickle
    s = pickle.load(open(sys.argv[1], 'rb'))
    yops = []
    for lins, row in zip(s['ylin'], s['y']):
        yops += [('cx', a, b) for a, b in lins]
        for a, pa, b, pb, t in row:
            yops += ([('x', a)] if pa else []) + ([('x', b)] if pb else []) + [('ccx', a, b, t)] + \
                    ([('x', a)] if pa else []) + ([('x', b)] if pb else [])
    fwd, full = build(yops)
    qc = ops_to_qc(full)
    print('forward depth/cx', real_depth(ops_to_qc(fwd)), ' full depth/cx', real_depth(qc))
    print('check vs disk core (err, leak)', check(qc, core_target()))
