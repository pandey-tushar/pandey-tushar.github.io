"""CP-AE core: exact phase-tracking classical simulator + timing model.

Every gate used in this project is  D * P  (diagonal phase times a classical
permutation), so a circuit's action on a basis state is a classical
trajectory with an accumulated phase.  sim_exact() runs all 4096 data inputs
(ancillas |0>) and checks (1) net permutation = identity, (2) accumulated
phase == (-1)^f exactly, (3) ancillas clean.  This is equivalent to the
statevector check on |+>^12 (validated in __main__) and runs in ~50 ms.

model_depth() is the challenge's per-qubit ASAP layering applied to a raw
op list through the measured per-wire touch profiles of cpae_prims.py.
"""
import sys
import time

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import RCCXGate, RC3XGate, CCZGate
from qiskit.quantum_info import Operator, Statevector

XG, YG = np.meshgrid(np.arange(64), np.arange(64), indexing='ij')
SHAPES = {
    "R1": ((2 <= XG) & (XG <= 26) & (29 <= YG) & (YG <= 53)).astype(int),
    "R2t": ((27 <= XG) & (XG <= 48) & (39 <= YG) & (YG <= 43)).astype(int),
    "D1": (((XG - 55) ** 2 + (YG - 41) ** 2) <= 42).astype(int),
    "D2": (((XG - 40) ** 2 + (YG - 19) ** 2) <= 72).astype(int),
}
SHAPES["LOGO"] = SHAPES["R1"] ^ SHAPES["R2t"] ^ SHAPES["D1"] ^ SHAPES["D2"]
assert SHAPES["LOGO"].sum() == 1097


def fvec(img):
    """f as a length-4096 0/1 vector, index i = x + 64*y."""
    return np.array([int(img[i & 63, (i >> 6) & 63]) for i in range(4096)],
                    dtype=np.int8)


# --------------------------------------------------------------- gate table
_GATES = {}


def gate_data(op):
    """(perm array, phase array) over the gate's own 2^k basis, index bit j =
    j-th qubit of the instruction (little-endian)."""
    key = (op.name, tuple(np.round(op.params, 12)) if op.params else ())
    if key not in _GATES:
        k = op.num_qubits
        U = np.asarray(Operator(op).data)
        N = 1 << k
        perm = np.zeros(N, dtype=np.int64)
        ph = np.zeros(N, dtype=complex)
        for s in range(N):
            col = U[:, s]
            j = int(np.argmax(np.abs(col)))
            assert abs(abs(col[j]) - 1) < 1e-9 and \
                np.sum(np.abs(col)) - abs(col[j]) < 1e-9, \
                "gate %s is not diagonal*permutation" % op.name
            perm[s] = j
            ph[s] = col[j]
        _GATES[key] = (perm, ph)
    return _GATES[key]


def extract(qc):
    """[(name, wires, perm, phase)] from a QuantumCircuit (any gate set of
    diagonal*permutation gates)."""
    out = []
    for inst in qc.data:
        qs = tuple(qc.find_bit(q).index for q in inst.qubits)
        perm, ph = gate_data(inst.operation)
        out.append((inst.operation.name, qs, perm, ph))
    return out, float(qc.global_phase)


def sim_exact(gl, gp, f, n=40, ndata=12):
    """gl from extract().  Returns (max phase err, perm mismatches, leak)."""
    N = 1 << ndata
    state = np.arange(N, dtype=np.int64)          # ancillas 0
    phase = np.ones(N, dtype=complex) * np.exp(1j * gp)
    for name, qs, perm, ph in gl:
        k = len(qs)
        sub = np.zeros(N, dtype=np.int64)
        for j, w in enumerate(qs):
            sub |= ((state >> w) & 1) << j
        nsub = perm[sub]
        phase = phase * ph[sub]
        for j, w in enumerate(qs):
            bit = (nsub >> j) & 1
            state = (state & ~(1 << w)) | (bit << w)
    want = np.where(f == 1, -1.0, 1.0)
    err = float(np.max(np.abs(phase - want)))
    mism = int(np.sum(state != np.arange(N)))
    return err, mism


def check(qc, shape, tag="", verbose=True):
    gl, gp = extract(qc)
    err, mism = sim_exact(gl, gp, fvec(SHAPES[shape]))
    ok = err < 1e-9 and mism == 0
    if verbose:
        print("  %s exact-sim vs %s: phase err %.2e, perm mismatches %d -> %s"
              % (tag, shape, err, mism, "PASS" if ok else "FAIL"))
    return ok, err, mism


# ------------------------------------------------------------- timing model
# per-wire touch layers inside each primitive (cpae_prims.py, opt 2)
PROF = {
    "x": {0: [1]},
    "cx": {0: [1], 1: [1]},
    "cz": {0: [2], 1: [1, 2, 3]},
    "rccx": {0: [4], 1: [2, 6], 2: [1, 2, 3, 4, 5, 6, 7]},
    "rcccx": {0: [4, 8], 1: [6, 10], 2: [2, 12], 3: list(range(1, 14))},
    "ccz": {0: [3, 7, 8, 9, 10], 1: [1, 5, 6, 8, 9, 10],
            2: [1, 2, 3, 4, 5, 6, 7, 8]},
}
PROF["rccx_dg"] = PROF["rccx"]
PROF["rcccx_dg"] = PROF["rcccx"]
PROF["ccx"] = PROF["rccx"]          # op-list spelling
PROF["c3x"] = PROF["rcccx"]
PROF["ccx_dg"] = PROF["rccx"]
PROF["c3x_dg"] = PROF["rcccx"]


def mirror(ops):
    """exact inverse of an op list (RCCX/RC3X are not self-inverse)."""
    inv = {"ccx": "ccx_dg", "ccx_dg": "ccx", "c3x": "c3x_dg", "c3x_dg": "c3x"}
    return [(inv.get(op[0], op[0]),) + tuple(op[1:]) for op in reversed(ops)]


def model_depth(ops, xcost=0, n=18, ret_lay=False):
    """ops: [(name, wires...)] (op-list spelling: x/cx/ccx/c3x/cz/ccz).
    Per-wire ASAP with rigid intra-gate touch offsets.  xcost: layers for an X
    (0 = merges into a neighbouring u3)."""
    lay = [0] * n
    for op in ops:
        name, qs = op[0], op[1:]
        if name == "x":
            lay[qs[0]] += xcost
            continue
        prof = PROF[name]
        S = 0
        for j, w in enumerate(qs):
            S = max(S, lay[w] - prof[j][0] + 1)
        for j, w in enumerate(qs):
            lay[w] = S + prof[j][-1] - 1
    return (max(lay), lay) if ret_lay else max(lay)


def qc_to_ops(qc):
    """QuantumCircuit (rccx/rcccx/cx/x/cz/ccz family) -> op-list spelling."""
    nm = {"rccx": "ccx", "rccx_dg": "ccx_dg", "rcccx": "c3x",
          "rcccx_dg": "c3x_dg", "cx": "cx", "x": "x", "cz": "cz", "ccz": "ccz"}
    out = []
    for inst in qc.data:
        qs = tuple(qc.find_bit(q).index for q in inst.qubits)
        out.append((nm[inst.operation.name],) + qs)
    return out


def ops_to_qc(ops, n=18):
    qc = QuantumCircuit(n)
    for op in ops:
        k, qs = op[0], list(op[1:])
        if k == "x":
            qc.x(qs[0])
        elif k == "cx":
            qc.cx(*qs)
        elif k == "ccx":
            qc.append(RCCXGate(), qs)
        elif k == "c3x":
            qc.append(RC3XGate(), qs)
        elif k == "ccx_dg":
            qc.append(RCCXGate().inverse(), qs)
        elif k == "c3x_dg":
            qc.append(RC3XGate().inverse(), qs)
        elif k == "cz":
            qc.cz(*qs)
        elif k == "z":
            qc.z(qs[0])
        elif k == "ccz":
            qc.append(CCZGate(), qs)
        else:
            raise ValueError(k)
    return qc


def real_depth(qc, lvl=2):
    t = transpile(qc, basis_gates=["u3", "cx"], optimization_level=lvl)
    return t.depth(), t.count_ops().get("cx", 0)


def sv_check_gp(qc, shape):
    """sv_check with the global phase divided out.

    A transpiled u3/cx circuit picks up a global phase that QASM 2.0 cannot
    express (cpev_best.qasm carries -pi/8), which is physically irrelevant
    but shows up as a large error in the raw check.  Use this one on anything
    that has been through transpile().
    """
    pre = QuantumCircuit(18)
    for i in range(12):
        pre.h(i)
    sv = np.asarray(Statevector(pre.compose(qc)))
    leak = float(np.sum(np.abs(sv[4096:]) ** 2))
    a = sv[:4096] * 64.0
    ph = a[0] / abs(a[0]) if abs(a[0]) > 1e-9 else 1.0
    want = np.where(fvec(SHAPES[shape]) == 1, -1.0, 1.0)
    return float(np.max(np.abs(a / ph - want))), leak


def sv_check(qc, shape):
    pre = QuantumCircuit(18)
    for i in range(12):
        pre.h(i)
    sv = np.asarray(Statevector(pre.compose(qc)))
    leak = float(np.sum(np.abs(sv[4096:]) ** 2))
    want = np.where(fvec(SHAPES[shape]) == 1, -1.0, 1.0)
    return float(np.max(np.abs(sv[:4096] * 64.0 - want))), leak


if __name__ == "__main__":
    import cpz_r1, cpu2_rect, cpz_d1b, cpac_d2
    blocks = {"R1": cpz_r1.block(), "R2t": cpu2_rect.block(),
              "D1": cpz_d1b.block(), "D2": cpac_d2.block()}
    print("== simulator validation (exact-sim vs statevector) and timing model"
          " calibration ==")
    print("  block  sv_err   sim_err  mism | real depth/cx | model x=0  x=1")
    for nm, qc in blocks.items():
        t0 = time.time()
        gl, gp = extract(qc)
        err, mism = sim_exact(gl, gp, fvec(SHAPES[nm]))
        ts = time.time() - t0
        sve, leak = sv_check(qc, nm)
        d, c = real_depth(qc, 2)
        ops = qc_to_ops(qc)
        m0 = model_depth(ops, 0)
        m1 = model_depth(ops, 1)
        print("  %-4s  %.1e  %.1e  %d   | %4d / %4d   | %4d   %4d   (sim %.2fs)"
              % (nm, sve, err, mism, d, c, m0, m1, ts))
