"""CP-UE assemble: T_x (cpuc_inplace x ckpt) on wires 0-5 + 12-14, T_y on 6-11 + 15-17,
the 4-term phase stage on the 8 code wires (re-deals onto host code wires, MCZ, undo),
then the inverse of the forward part (single global mirror).  Verifies the phase on all
4096 inputs (statevector, global phase removed) and reports transpiled depth / CX.
Usage: python3 cpuc_assemble.py X.pkl Y.pkl [OUT.qasm]"""
import sys, os, pickle
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import RCCXGate, ZGate
from qiskit.qasm2 import dumps
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
from cpae_core import SHAPES, fvec
from cpub_classiq import measure

D = pickle.load(open(os.path.join(HERE, 'cpuc_code810.pkl'), 'rb'))
ONES = (1 << 64) - 1
S0 = [sum(1 << v for v in range(64) if (v >> i) & 1) for i in range(6)] + [0, 0, 0]


def play(lv):
    S = list(S0)
    for cxs, tofs in lv:
        for s, d in cxs: S[d] ^= S[s]
        Sl = list(S)
        for a, b, pa, pb, t in tofs:
            S[t] ^= (Sl[a] ^ (ONES if pa else 0)) & (Sl[b] ^ (ONES if pb else 0))
    return S


def emit_side(fw, lv, m):
    for cxs, tofs in lv:
        for s, d in cxs: fw.cx(m[s], m[d])
        for a, b, pa, pb, t in tofs:
            if pa: fw.x(m[a])
            if pb: fw.x(m[b])
            fw.append(RCCXGate(), [m[a], m[b], m[t]])
            if pa: fw.x(m[a])
            if pb: fw.x(m[b])


def side(pkl, which):
    d = pickle.load(open(pkl, 'rb')); lv = d['levels']; ws = d['wires']
    T = D['tx'] if which == 'x' else D['ty']
    S = play(lv); comp = []; mis = 0
    for k in range(4):
        e0 = bin(S[ws[k]] ^ T[k]).count('1'); e1 = bin(S[ws[k]] ^ T[k] ^ ONES).count('1')
        comp.append(1 if e1 < e0 else 0); mis += min(e0, e1)
    m = [w if w < 6 else 12 + (w - 6) for w in range(9)] if which == 'x' else [6 + w if w < 6 else 15 + (w - 6) for w in range(9)]
    print('side %s: %s levels, %d Toffolis, %d CX, code wires %s comp %s, mismatch %d' % (
        which, len(lv), sum(len(t) for _, t in lv), sum(len(c) for c, _ in lv), [m[w] for w in ws], comp, mis))
    return lv, m, [m[w] for w in ws], comp, mis


def phase_stage(ph, g, comp):
    """g[p], comp[p] for code positions p = 0..7 (0-2 t, 3 s, 4-6 w, 7 r)"""
    for term in D['terms']:
        forms = []
        for mask, c in term:
            ps = [p for p in range(8) if mask >> p & 1]
            c ^= sum(comp[p] for p in ps) & 1
            forms.append((ps, c))
        hosts = []
        for i, (ps, c) in enumerate(forms):
            others = set(p for j, (q, _) in enumerate(forms) if j != i for p in q)
            cand = [p for p in ps if p not in others]
            assert cand, ('no host', term); hosts.append(cand[0])
        undo = []
        for (ps, c), h in zip(forms, hosts):
            for p in ps:
                if p != h: ph.cx(g[p], g[h]); undo.append(('cx', g[p], g[h]))
            if c: ph.x(g[h]); undo.append(('x', g[h]))
        hw = [g[h] for h in hosts]
        if len(hw) == 1: ph.z(hw[0])
        elif len(hw) == 2: ph.cz(hw[0], hw[1])
        else: ph.append(ZGate().control(len(hw) - 1), hw)
        for op in reversed(undo):
            if op[0] == 'cx': ph.cx(op[1], op[2])
            else: ph.x(op[1])


if __name__ == '__main__':
    lx, mx, gx, cx_, misx = side(sys.argv[1], 'x'); ly, my, gy, cy_, misy = side(sys.argv[2], 'y')
    fw = QuantumCircuit(18); emit_side(fw, lx, mx); emit_side(fw, ly, my)
    ph = QuantumCircuit(18); phase_stage(ph, gx + gy, cx_ + cy_)
    qc = fw.compose(ph).compose(fw.inverse())
    for nm, c in (('forward', fw), ('phase', ph)):
        t = transpile(c, basis_gates=['u3', 'cx'], optimization_level=3)
        print('  %s alone: depth %d cx %d' % (nm, t.depth(), t.count_ops().get('cx', 0)))
    f = fvec(SHAPES['LOGO']); w, d, cx, res = measure(dumps(qc), f)
    print('TOTAL width %d depth %d cx %d' % (w, d, cx))
    err, leak = res['q0-11']; print('verify: max phase err %.2e leak %.2e -> %s' % (err, leak, 'PASS' if err < 1e-8 and leak < 1e-10 else 'FAIL (code mismatch %d+%d)' % (misx, misy)))
    if len(sys.argv) > 3 and err < 1e-8 and leak < 1e-10:
        t = transpile(qc, basis_gates=['u3', 'cx'], optimization_level=3); open(sys.argv[3], 'w').write(dumps(t)); print('wrote', sys.argv[3])
