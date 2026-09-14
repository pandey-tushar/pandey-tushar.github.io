"""CP-AC stage 4: build the new submission pair -- submission12.qmod + .qasm.

Same pipeline as qmod_build10.py (which produced the 421/646 submission10 pair),
retargeted at the CP-AC merged oracle (depth 415 / cx 642, cpac_oracle.py -- the
CP-Z merge with cpac_d2's shorter D2 block).  The gate list is
submission_local12.qasm, a byte copy of cpal_oracle.qasm as written by

    python cpac_oracle.py build

(order D1,D2,R2t,R1 with identity ancilla perms; qiskit transpile to u3/cx --
cpac_oracle picks the better of opt_level 2 and 3 plus the in-circuit
global-phase compensation added by cpw_oracle.fix_phase).
Classiq passes a literal statement list through synthesis 1:1, so the qmod and
the qasm are the same implementation by construction.

THE THREE PROPERTIES THAT MAKE THIS CIRCUIT DIFFERENT (as in submission6):

 1. The gates are general u3(theta, phi, lambda), not u3(0, 0, lambda) = RZ.
    The qmod carries them as U(theta, phi, lam, 0, q[i]); Classiq's U is
    exactly qiskit's u3 times e^{i*gam}, so gam = 0 reproduces u3.  check_qmod
    asserts all three angles round-trip, not just lambda.
 2. Correctness depends on a GLOBAL PHASE carried inside the circuit: the last
    two gates are u3(pi, gp-pi, 0) on q[0] (gp = 1.073938525), whose product
    is exactly e^{i*gp} * I (QASM 2.0 cannot carry global_phase).  They are
    adjacent and an optimizing transpiler is free to fuse them into the
    identity, which would silently break the oracle.  Hence the export uses NO
    Classiq transpile, the strict check compares statevectors ELEMENTWISE with
    no phase division (cpal_oracle.O.strict_err), and stage_final asserts the
    exported gate list still holds both gates.
 3. verify18.verify_fast does not apply (it is cx/rz only), so the exported
    artifact is checked with verify_sv18 plus the strict elementwise check.

As in qmod_build3/4/5/6/7/8/9/10 the model declares a single flat QArray[QBit, 18]: the
x/y/anc three-port model does NOT pin Classiq's wire numbering (q[0..5] go to
whichever port is touched first).  stage_syn asserts the exported gate list
equals the source, so a permutation cannot slip through.

  --probe   tiny 18-wire model (u3 corner cases + the phase pair) through
            synthesize/export; checks Classiq's U convention against qiskit
  --build   local only: create_model + write_qmod -> submission12.qmod
  --syn     synthesize + export QASM2, check width/depth/cx + wire numbering
  --final   export QASM2 off the synthesized program (NO classiq.transpile --
            every transpile route fuses the phase pair) -> submission12.qasm,
            then the notebook format rules and a gate-for-gate diff vs source
  --verify  verify_sv18 + strict elementwise check + format check on the
            exported submission12.qasm
"""
import math
import os
import re
import sys
import time

SRC_QASM = "submission_local13.qasm"   # byte copy of cpal_oracle.qasm
NAME = "submission12"
CACHE = os.environ.get("CP_AL_CACHE", ".")
MODEL_PATH = os.path.join(CACHE, "cpal_model.json")
QPROG_PATH = os.path.join(CACHE, "cpal_qprog.json")

EXPECT_DEPTH = 391
EXPECT_CX = 606
EXPECT_U3 = 671

ANG_TOL = 1e-15


# --------------------------------------------------------------------------
# op lists
# --------------------------------------------------------------------------

def _angle(expr):
    """QASM 2.0 angle: a decimal, or a symbolic form like '3*pi/4'."""
    expr = expr.strip()
    if not re.fullmatch(r"[-+*/(). 0-9epi]+", expr):
        raise ValueError(f"unsafe angle expression: {expr!r}")
    return float(eval(expr, {"__builtins__": {}},
                      {"pi": math.pi, "e": math.e}))


def ops_from_qasm(path_or_src, is_src=False):
    """[('c', a, b) | ('u', q, theta, phi, lam)] in file order.

    Accepts u3(...) and u(...) (Classiq's raw export may use either name).
    """
    src = path_or_src if is_src else open(path_or_src).read()
    stmts = [s.strip() for s in re.sub(r"//[^\n]*", "", src).split(";")
             if s.strip()]
    ops = []
    for s in stmts:
        if s.startswith(("OPENQASM", "include", "qreg", "creg")):
            continue
        m = re.fullmatch(r"u3?\s*\(([^,]+),([^,]+),([^,]+)\)\s*q\[(\d+)\]", s)
        if m:
            ops.append(('u', int(m.group(4)), _angle(m.group(1)),
                        _angle(m.group(2)), _angle(m.group(3))))
            continue
        m = re.fullmatch(r"cx\s*q\[(\d+)\]\s*,\s*q\[(\d+)\]", s)
        if m:
            ops.append(('c', int(m.group(1)), int(m.group(2))))
            continue
        raise ValueError(f"unparsed statement: {s}")
    return ops


def to_circuit(ops, nq=18):
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(nq)
    for o in ops:
        if o[0] == 'c':
            qc.cx(o[1], o[2])
        else:
            qc.u(o[2], o[3], o[4], o[1])
    return qc


def qiskit_metrics(ops):
    qc = to_circuit(ops)
    c = qc.count_ops()
    return qc, qc.depth(), c.get("cx", 0), c.get("u", 0) + c.get("u3", 0)


def shape(ops):
    """Gate sequence without angles -- what must be bit-identical."""
    return [(o[0], o[1]) if o[0] == 'u' else o for o in ops]


def angle_delta(a, b):
    """Worst |angle| difference between two op lists of the same shape."""
    worst = 0.0
    for x, y in zip(a, b):
        if x[0] == 'u':
            worst = max(worst, max(abs(x[i] - y[i]) for i in (2, 3, 4)))
    return worst


def diff_report(new, old):
    a, b = ops_from_qasm(new), ops_from_qasm(old)
    if len(a) != len(b):
        print(f"DIFF: {len(a)} ops vs {len(b)}")
        return False, None
    same = shape(a) == shape(b)
    worst = angle_delta(a, b) if same else None
    tail = f", max angle delta {worst:.3e}" if same else ""
    print(f"diff vs {old}: {len(a)} ops, gate sequence "
          f"{'IDENTICAL' if same else 'DIFFERS'}{tail}")
    return same, worst


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------

def build_model(ops, constraints=None):
    """@qfunc main with one literal CX/U statement per op, on one register.

    A single QArray keeps index i on q[i], which is the numbering the
    challenge verifier reads (x = q[0..5]).  U(theta, phi, lam, gam=0) is
    qiskit's u3(theta, phi, lam) exactly.
    """
    from classiq import (CX, U, Output, QArray, QBit, allocate, create_model,
                         qfunc)

    @qfunc
    def main(q: Output[QArray[QBit, 18]]) -> None:
        allocate(q)
        for op in ops:
            if op[0] == 'c':
                CX(q[op[1]], q[op[2]])
            else:
                U(float(op[2]), float(op[3]), float(op[4]), 0.0, q[op[1]])

    kw = {"constraints": constraints} if constraints is not None else {}
    return create_model(main, **kw)


QMOD_U = re.compile(
    r"U\(\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*,"
    r"\s*([-\d.eE+]+)\s*,\s*q\[(\d+)\]\s*\)")
QMOD_CX = re.compile(r"CX\(\s*q\[(\d+)\]\s*,\s*q\[(\d+)\]\s*\)")


def ops_from_qmod(path):
    """Read the literal gate list back out of the .qmod text, in order."""
    txt = open(path).read()
    ops = []
    for m in re.finditer(r"\b(CX|U)\(", txt):
        if m.group(1) == "CX":
            g = QMOD_CX.match(txt, m.start())
            if g is None:
                raise ValueError(f"unparsed CX at {m.start()}: "
                                 f"{txt[m.start():m.start() + 80]!r}")
            ops.append(('c', int(g.group(1)), int(g.group(2))))
        else:
            g = QMOD_U.match(txt, m.start())
            if g is None:
                raise ValueError(f"unparsed U at {m.start()}: "
                                 f"{txt[m.start():m.start() + 90]!r}")
            gam = float(g.group(4))
            if gam != 0.0:
                raise ValueError(f"U with nonzero gam: {g.group(0)}")
            ops.append(('u', int(g.group(5)), float(g.group(1)),
                        float(g.group(2)), float(g.group(3))))
    return ops


def check_qmod(path, ops):
    """The .qmod must hold every gate, in order, at full angle precision."""
    got = ops_from_qmod(path)
    n_cx = sum(1 for o in got if o[0] == 'c')
    n_u = len(got) - n_cx
    print(f"{path}: CX={n_cx} U={n_u}")
    assert n_cx == EXPECT_CX, f"CX count {n_cx} != {EXPECT_CX}"
    assert n_u == EXPECT_U3, f"U count {n_u} != {EXPECT_U3}"

    order_ok = shape(got) == shape(ops)
    print(f"gate order        {'preserved' if order_ok else 'REORDERED'}")
    assert order_ok, "qmod gate order/wires do not match the source op list"

    worst = angle_delta(got, ops)
    print(f"max angle error   {worst:.3e}  (limit {ANG_TOL:.0e}, all 3 params)")
    assert worst < ANG_TOL, "angle precision lost -- raise decimal_precision"
    print("qmod OK")


# --------------------------------------------------------------------------
# format check + checks on the exported artifact
# --------------------------------------------------------------------------

def notebook_metrics(source):
    """Cell 16's qasm_metrics, verbatim -- the format gate for submission."""
    statements = [s.strip() for s in re.sub(r"//[^\n]*", "", source).split(";")
                  if s.strip()]
    if statements[:2] != ["OPENQASM 2.0", 'include "qelib1.inc"']:
        raise ValueError("Expected an OpenQASM 2.0 file using qelib1.inc")
    qreg_match = (re.fullmatch(r"qreg\s+q\s*\[\s*(\d+)\s*\]", statements[2])
                  if len(statements) >= 3 else None)
    if qreg_match is None:
        raise ValueError("Expected exactly one register named q")
    width = int(qreg_match.group(1))
    if not 12 <= width <= 18:
        raise ValueError(f"QASM width must be between 12 and 18, got {width}")
    qubit_depths = [0] * width
    cx_count = 0
    for statement in statements[3:]:
        u3_match = re.fullmatch(
            r"u3\s*\([^,]+,[^,]+,[^,]+\)\s+q\s*\[\s*(\d+)\s*\]", statement)
        cx_match = re.fullmatch(
            r"cx\s+q\s*\[\s*(\d+)\s*\]\s*,\s*q\s*\[\s*(\d+)\s*\]", statement)
        if u3_match:
            qubits = (int(u3_match.group(1)),)
        elif cx_match:
            qubits = tuple(map(int, cx_match.groups()))
            cx_count += 1
        else:
            raise ValueError(f"Unsupported QASM statement: {statement}")
        if any(q >= width for q in qubits):
            raise ValueError(f"Qubit index out of range: {statement}")
        if len(set(qubits)) != len(qubits):
            raise ValueError(f"Gate operands must be distinct: {statement}")
        layer = max(qubit_depths[q] for q in qubits) + 1
        for q in qubits:
            qubit_depths[q] = layer
    return width, max(qubit_depths, default=0), cx_count


def qasm_stats(src):
    """width / per-qubit-layer depth / cx count, tolerant of u vs u3."""
    stmts = [s.strip() for s in re.sub(r"//[^\n]*", "", src).split(";")
             if s.strip()]
    width = None
    for s in stmts:
        m = re.fullmatch(r"qreg\s+(\w+)\s*\[\s*(\d+)\s*\]", s)
        if m:
            width = int(m.group(2))
            break
    if width is None:
        return None, None, None, {}
    d = [0] * width
    counts = {}
    for s in stmts:
        m = re.match(r"([a-zA-Z0-9_]+)(\([^)]*\))?\s+(.*)", s)
        if not m or m.group(1) in ("qreg", "creg", "include", "OPENQASM",
                                   "barrier"):
            continue
        name = m.group(1)
        qs = [int(v) for v in re.findall(r"\[\s*(\d+)\s*\]", m.group(3))]
        if not qs:
            continue
        counts[name] = counts.get(name, 0) + 1
        lay = max(d[q] for q in qs) + 1
        for q in qs:
            d[q] = lay
    return width, max(d, default=0), counts.get("cx", 0), counts


def phase_pair_intact(ops, src_ops):
    """The two u3(pi, gp-pi, 0) gates that carry the global phase must
    survive verbatim; fusing them into the identity silently breaks the
    oracle and no phase-dividing verifier would notice."""
    tail_s, tail_n = src_ops[-2:], ops[-2:]
    ok = shape(tail_n) == shape(tail_s) and angle_delta(tail_n, tail_s) < 1e-12
    print(f"phase pair        {'INTACT' if ok else 'LOST/FUSED'} "
          f"(last two ops: {tail_n})")
    return ok


# --------------------------------------------------------------------------
# stages
# --------------------------------------------------------------------------

def normalize_u3(src):
    """Rename Classiq's 'u(...)' to the challenge's 'u3(...)'.

    The raw export writes the Qmod U gate as 'u', which qelib1.inc does not
    define (qiskit's own parser rejects it) and which the notebook's format
    check does not accept.  'u' and 'u3' are the same three-parameter gate,
    so this is a pure lexical alias: every statement is checked to be exactly
    'u(a,b,c) q[i]' or 'cx q[i],q[j]' first, and the op list is compared
    before and after.
    """
    out, nren = [], 0
    for line in src.splitlines():
        s = line.strip()
        if (not s or s.startswith("//") or s.startswith("OPENQASM")
                or s.startswith("include") or s.startswith("qreg")):
            out.append(line)
            continue
        if re.fullmatch(r"u\((?:[^,()]+,){2}[^,()]+\)\s*q\[\d+\];", s):
            out.append(line.replace("u(", "u3(", 1))
            nren += 1
            continue
        if re.fullmatch(r"cx\s*q\[\d+\]\s*,\s*q\[\d+\];", s):
            out.append(line)
            continue
        raise ValueError(f"unexpected statement in raw export: {s!r}")
    new = "\n".join(out) + "\n"
    assert ops_from_qasm(new, is_src=True) == ops_from_qasm(src, is_src=True)
    print(f"u -> u3 rename    {nren} statements (alias only, op list identical)")
    return new


def export_qasm(qprog, route):
    """QASM 2.0 for a synthesized program.

    route 'raw'    : export the synthesized program as-is (our statements are
                     already u3/cx, so nothing has to be rewritten).
    route <option> : classiq.transpile with that TranspilationOption first.

    AUTO_OPTIMIZE is NOT usable here: it fuses the two adjacent
    u3(pi, gp-pi, 0) gates that carry the global phase into u3(0, a, -a) =
    identity, silently dropping e^{i*gp} (measured, --probe).
    """
    from classiq import TargetLanguage, TranspilationConfig, export
    if route == "raw":
        return export(qprog, TargetLanguage.QASM2)

    import classiq
    from classiq import Preferences, TranspilationOption
    from classiq.interface.generator.hardware.hardware_data import \
        CustomHardwareSettings
    tp = classiq.transpile(qprog, preferences=Preferences(
        transpilation_option=TranspilationOption(route),
        custom_hardware_settings=CustomHardwareSettings(
            basis_gates=["u3", "cx"])))
    m = classiq.get_transpiled_circuit_metrics(tp)
    print(f"  classiq.transpile({route}): width={m.width} depth={m.depth} "
          f"cx={m.count_ops.get('cx', 0)} u3={m.count_ops.get('u3', 0)}")
    return export(tp, TargetLanguage.QASM2,
                  transpilation_config=TranspilationConfig(
                      basis_gates=["u3", "cx"]))


def stage_probe():
    """One cheap synthesis: does Classiq's U match qiskit's u3 exactly, and
    which export route preserves the adjacent global-phase pair?"""
    import numpy as np
    from qiskit.quantum_info import Operator

    from classiq import Constraints, synthesize

    gp = 1.788688174144962           # = 4.930280828 - pi
    probe = [('u', 0, math.pi / 2, math.pi / 4, -math.pi),
             ('c', 0, 1),
             ('u', 1, 2.023670698512004, -math.pi / 2, 3 * math.pi / 4),
             ('c', 1, 0),
             ('u', 0, math.pi, gp, 0.0),
             ('u', 0, math.pi, gp, 0.0)]
    model = build_model(probe, constraints=Constraints(max_width=18))
    qprog = synthesize(model)
    want = Operator(to_circuit(probe, 2)).data

    for route in ("raw", "none", "decompose", "auto optimize"):
        try:
            src = export_qasm(qprog, route)
        except Exception as exc:                      # noqa: BLE001
            print(f"{route:>14}: FAILED {type(exc).__name__}: {str(exc)[:90]}")
            continue
        open(f"cpal_probe_{route.split()[0]}.qasm", "w",
             encoding="utf-8").write(src)
        try:
            got = ops_from_qasm(src, is_src=True)
        except ValueError as exc:
            print(f"{route:>14}: unparsable export ({exc})")
            continue
        err = float(np.abs(want - Operator(to_circuit(got, 2)).data).max())
        fmt = "ok"
        try:
            notebook_metrics(src)
        except ValueError as exc:
            fmt = f"REJECTED ({exc})"
        print(f"{route:>14}: {len(got)}/{len(probe)} ops, shape "
              f"{'same' if shape(got) == shape(probe) else 'DIFFERS'}, "
              f"operator delta (no phase division) {err:.3e} "
              f"{'MATCH' if err < 1e-12 else 'MISMATCH'}, format {fmt}")


def stage_build():
    from classiq import Constraints, write_qmod

    ops = ops_from_qasm(SRC_QASM)
    _, d, ncx, nu = qiskit_metrics(ops)
    print(f"source {SRC_QASM}: {len(ops)} ops, depth={d} cx={ncx} u3={nu}")
    assert (d, ncx, nu) == (EXPECT_DEPTH, EXPECT_CX, EXPECT_U3), "source drift"

    # provenance: the source must still be the emitter's own output
    if os.path.exists("cpal_oracle.qasm"):
        emit = ops_from_qasm("cpal_oracle.qasm")
        same = shape(emit) == shape(ops) and angle_delta(emit, ops) == 0.0
        print(f"vs cpal_oracle.qasm: {'IDENTICAL' if same else 'DIFFERS'}")
        assert same, "submission_local13.qasm is not cpal_oracle.qasm's output"

    t0 = time.time()
    model = build_model(ops, constraints=Constraints(max_width=18))
    print(f"create_model      {time.time() - t0:7.2f}s  ({len(model)} chars)")

    t0 = time.time()
    write_qmod(model, NAME, directory=".", decimal_precision=17)
    print(f"write_qmod        {time.time() - t0:7.2f}s  -> {NAME}.qmod")
    with open(MODEL_PATH, "w") as fh:
        fh.write(model)

    check_qmod(f"{NAME}.qmod", ops)


def stage_syn():
    from classiq import TargetLanguage, export, synthesize

    model = open(MODEL_PATH).read()
    print(f"loaded model ({len(model)} chars)")

    t0 = time.time()
    qprog = synthesize(model)
    print(f"synthesize        {time.time() - t0:7.2f}s")
    with open(QPROG_PATH, "w") as fh:
        fh.write(qprog.model_dump_json())

    t0 = time.time()
    raw = export(qprog, TargetLanguage.QASM2)
    print(f"export QASM2      {time.time() - t0:7.2f}s")
    open("cpal_raw.qasm", "w", encoding="utf-8").write(raw)
    raw = normalize_u3(raw)
    w, d, c, counts = qasm_stats(raw)
    print(f"synthesized:      width={w} depth={d} cx={c} ops={counts}")
    ok = (w, d, c) == (18, EXPECT_DEPTH, EXPECT_CX)
    print(f"1:1 preserved:    {'YES' if ok else 'NO'}")
    assert ok, f"expected 18/{EXPECT_DEPTH}/{EXPECT_CX}, got {w}/{d}/{c}"

    src_ops = ops_from_qasm(SRC_QASM)
    got = ops_from_qasm(raw, is_src=True)
    same = shape(got) == shape(src_ops)
    print(f"wire numbering:   {'IDENTICAL' if same else 'PERMUTED'}")
    assert same, "synthesis renumbered the wires -- the qasm would compute " \
                 "the transposed oracle"
    print(f"max angle delta   {angle_delta(got, src_ops):.3e}")


def stage_final():
    """Export the submission QASM straight off the synthesized program.

    NOT via classiq.transpile: every TranspilationOption (none / decompose /
    auto optimize), and export's own transpilation_config, fuse the two
    adjacent u3(pi, gp-pi, 0) gates into u3(0, a, -a) = identity and drop
    e^{i*gp} (measured, --probe).  Our statements are already u3/cx, so
    there is nothing for a transpiler to do anyway.
    """
    from classiq import TargetLanguage, export
    from classiq.interface.generator.quantum_program import QuantumProgram

    qprog = QuantumProgram.model_validate_json(open(QPROG_PATH).read())

    t0 = time.time()
    src = normalize_u3(export(qprog, TargetLanguage.QASM2))
    open(f"{NAME}.qasm", "w", encoding="utf-8").write(src)
    print(f"export QASM2      {time.time() - t0:7.2f}s  -> {NAME}.qasm")

    w, d, c = notebook_metrics(src)
    print(f"notebook qasm_metrics: width={w} depth={d} cx={c}  FORMAT OK")
    print(f"\nFINAL: width={w} depth={d} cx={c}")
    assert (w, d, c) == (18, EXPECT_DEPTH, EXPECT_CX), \
        f"metric drift: {w}/{d}/{c} != 18/{EXPECT_DEPTH}/{EXPECT_CX}"

    src_ops = ops_from_qasm(SRC_QASM)
    got = ops_from_qasm(f"{NAME}.qasm")
    same, worst = diff_report(f"{NAME}.qasm", SRC_QASM)
    assert same and worst is not None and worst < 1e-12, "gate list differs"
    assert phase_pair_intact(got, src_ops), "global-phase pair was optimized " \
                                            "away -- the oracle is broken"
    print("run --verify for the statevector checks")


def verify(path):
    import numpy as np
    from qiskit import qasm2

    import cpal_oracle
    from analyze import img_to_f
    from logo import build_logo
    from score18 import check_qasm
    from verify18 import verify_sv18

    qc = qasm2.load(path)
    c = qc.count_ops()
    print(f"loaded {path}: {qc.num_qubits} qubits, depth={qc.depth()}, "
          f"ops={dict(c)}")

    t0 = time.time()
    err, leak = cpal_oracle.O.strict_err(qc)
    print(f"STRICT (no phase division): err={err:.3e} leak={leak:.1e} "
          f"{'PASS' if err < 1e-9 and leak < 1e-20 else 'FAIL'} "
          f"({time.time() - t0:.0f}s)")

    f = img_to_f(build_logo())
    t0 = time.time()
    ok2, e2 = verify_sv18(qc, f)
    print(f"verify_sv18: {'PASS' if ok2 else 'FAIL'} (max err {e2:.2e}, "
          f"{time.time() - t0:.0f}s)")

    check_qasm(path)
    w, d, cx = notebook_metrics(open(path).read())
    print(f"CHALLENGE METRIC: width={w} depth={d} cx={cx}")

    ok1 = err < 1e-9 and leak < 1e-20
    if not (ok1 and ok2):
        sys.exit(1)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--build"
    if mode == "--probe":
        stage_probe()
    elif mode == "--build":
        stage_build()
    elif mode == "--syn":
        stage_syn()
    elif mode == "--final":
        stage_final()
    elif mode == "--verify":
        verify(f"{NAME}.qasm")
    else:
        print(f"unknown mode {mode!r}")
        sys.exit(2)
