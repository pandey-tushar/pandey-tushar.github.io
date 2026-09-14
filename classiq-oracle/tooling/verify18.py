"""Verifiers for the 18-qubit variant (12 data + 6 clean ancillas).

The challenge allows up to 6 clean ancillas (qubits 12-17) that must start
and end in |0>.  A candidate circuit is then correct iff, restricted to the
ancilla=0 block, it acts as the diagonal U|x,y> = (-1)^f(x,y)|x,y> and leaves
the ancillas clean (no residual entanglement).

Two checks live here:

  verify_fast(qc, f)  -- symbolic, ~1e4x cheaper than a statevector run.
    Every gate we emit is cx or rz, so each computational basis input stays a
    computational basis state times a phase.  Track, for all 4096 data inputs
    at once (ancillas |0>), the current 18-bit basis label and the accumulated
    phase.  cx(a,b): bit b ^= bit a.  rz(theta,q): phase += -theta/2 if bit q
    is 0 else +theta/2 -- qiskit's RZ is diag(e^{-i theta/2}, e^{+i theta/2}),
    the same convention analyze.verify implicitly checks.  The circuit is
    correct iff every input returns to its own label (diagonal AND ancillas
    clean) and the phases equal (-1)^f up to one global phase.

  verify_sv18(qc, f) -- ground truth: a real 2^18 statevector run on
    |+>^12 (x) |0>^6.  Slow (~1 min) but assumes nothing about the gate set
    beyond what qiskit simulates, and independently confirms that no amplitude
    leaks out of the ancilla=0 block.

Basis convention (unchanged): index i = sum_q bit_q(i) 2^q, data i = y*64 + x,
ancillas are the high bits, so the ancilla=0 block is exactly indices 0..4095.
"""
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

NDATA = 12
NANC = 6
NTOT = NDATA + NANC
DIM = 1 << NDATA

ATOL = 1e-8          # phase tolerance
LEAK = 1e-10         # amplitude allowed outside the ancilla=0 block
_SKIP = ("barrier", "id", "delay")


def to18(qc):
    """Pad a 12-qubit circuit to 18 qubits with idle ancillas."""
    if qc.num_qubits == NTOT:
        return qc
    full = QuantumCircuit(NTOT)
    full.compose(qc, qubits=range(qc.num_qubits), inplace=True)
    return full


def circuit_ops(qc):
    """[('c', a, b), ('r', q, theta), ...] with qubit indices resolved."""
    ops = []
    for inst in qc.data:
        name = inst.operation.name
        if name in _SKIP:
            continue
        qs = [qc.find_bit(q).index for q in inst.qubits]
        if name == "cx":
            ops.append(('c', qs[0], qs[1]))
        elif name == "rz":
            ops.append(('r', qs[0], float(inst.operation.params[0])))
        else:
            raise ValueError(f"verify_fast: unsupported gate {name!r}")
    return ops


def verify_fast(qc, f):
    """Exact check for cx/rz-only circuits on 12 or 18 qubits.

    Returns (ok, max_err).  max_err is the worst amplitude deviation from
    (-1)^f after dividing out one global phase; a dirty ancilla or a
    non-diagonal action is reported as max_err = 2.0 (the largest possible
    deviation) so a failure never looks numerically small.
    """
    if qc.num_qubits not in (NDATA, NTOT):
        raise ValueError(f"expected 12 or 18 qubits, got {qc.num_qubits}")

    ident = np.arange(DIM, dtype=np.int64)
    states = ident.copy()
    phase = np.zeros(DIM, dtype=np.float64)
    for op in circuit_ops(qc):
        if op[0] == 'c':
            a, b = op[1], op[2]
            states ^= ((states >> a) & 1) << b
        else:
            q, theta = op[1], op[2]
            phase += np.where((states >> q) & 1, 0.5 * theta, -0.5 * theta)

    dirty = int(np.count_nonzero(states != ident))
    got = np.exp(1j * phase)
    target = (-1.0) ** f.astype(np.float64)
    g = got[0] / target[0]
    err = float(np.abs(got / g - target).max())
    ok = dirty == 0 and err < ATOL
    return ok, max(err, 2.0 if dirty else 0.0)


def verify_sv18(qc, f):
    """Ground truth: one 2^18 statevector run on |+>^12 (x) |0>^6."""
    full = to18(qc)
    pre = QuantumCircuit(NTOT)
    pre.h(range(NDATA))
    sv = Statevector(pre).evolve(full).data * np.sqrt(DIM)
    block, rest = sv[:DIM], sv[DIM:]
    leak = float(np.abs(rest).max())
    if abs(block[0]) < 1e-9:
        return False, 2.0
    target = (-1.0) ** f.astype(np.float64)
    g = block[0] / target[0]
    err = float(np.abs(block / g - target).max())
    return (leak < LEAK and err < ATOL), max(err, leak)


# --------------------------------------------------------------------------
# validation harness
# --------------------------------------------------------------------------

def _rebuild(qc, nq=None, bump_rz=None, delta=0.0):
    """Copy a circuit gate by gate, optionally widening it and perturbing the
    bump_rz-th rz angle by delta (used for the negative controls)."""
    out = QuantumCircuit(qc.num_qubits if nq is None else nq)
    seen = 0
    for op in circuit_ops(qc):
        if op[0] == 'c':
            out.cx(op[1], op[2])
        else:
            theta = op[2]
            if seen == bump_rz:
                theta += delta
            seen += 1
            out.rz(theta, op[1])
    return out


def _report(tag, res):
    ok, err = res
    print(f"  {tag:<44} {'PASS' if ok else 'FAIL'} (max err {err:.2e})")
    return ok


if __name__ == "__main__":
    import time

    from analyze import img_to_f, walsh_hadamard
    from logo import build_logo
    from sched import emit_sched

    EPS = 1e-12

    img = build_logo()
    print(f"logo image: {int(img.sum())} marked pixels")
    f = img_to_f(img)
    fh = walsh_hadamard(f) / DIM
    coeffs = {int(s): fh[s] for s in np.nonzero(np.abs(fh) > EPS)[0]}
    print(f"Walsh support: {len(coeffs)} / {DIM}")

    qc = emit_sched(coeffs)
    c = qc.count_ops()
    print(f"sched (12q): depth={qc.depth()}, cx={c.get('cx', 0)}, "
          f"rz={c.get('rz', 0)}")
    print()

    all_ok = True

    print("[b] 12-qubit circuit, phase sensitivity")
    t0 = time.time()
    all_ok &= _report("sched, unmodified (expect PASS)", verify_fast(qc, f))
    t_fast = time.time() - t0
    bad = _rebuild(qc, bump_rz=0, delta=1e-3)
    all_ok &= not _report("sched, one rz off by 1e-3 (expect FAIL)",
                          verify_fast(bad, f))
    print()

    print("[c] 18-qubit padding, ancilla cleanliness")
    idle = to18(qc)
    all_ok &= _report("padded to 18q, ancillas idle (expect PASS)",
                      verify_fast(idle, f))

    # 20 cx from data controls into ancilla targets, wrapped around the body:
    # controls and targets are disjoint registers, so the block commutes with
    # itself and the second copy restores the ancillas to |0>.
    touch = [(k % 12, 12 + k % 6) for k in range(20)]
    wrapped = QuantumCircuit(NTOT)
    for a, b in touch:
        wrapped.cx(a, b)
    wrapped.compose(_rebuild(qc, nq=NTOT), inplace=True)
    for a, b in touch:
        wrapped.cx(a, b)
    all_ok &= _report("+20 paired cx into ancillas (expect PASS)",
                      verify_fast(wrapped, f))

    dirty = wrapped.copy()
    dirty.cx(0, 12)
    all_ok &= not _report("+1 unpaired cx into ancilla 12 (expect FAIL)",
                          verify_fast(dirty, f))
    print()

    print("[d] timings")
    print(f"  verify_fast (12q sched):      {t_fast:6.2f}s")
    t0 = time.time()
    sv_ok = verify_sv18(wrapped, f)
    t_sv = time.time() - t0
    all_ok &= _report("verify_sv18, 18q wrapped (expect PASS)", sv_ok)
    print(f"  verify_sv18 (18q wrapped):    {t_sv:6.2f}s")
    print()

    print(f"checkpoint 1: {'ALL CHECKS AS EXPECTED' if all_ok else 'FAILURE'}")
