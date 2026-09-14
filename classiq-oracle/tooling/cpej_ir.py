"""cpej IR: u3/cx circuit as an exact gate list with 2x2 matrices,
commutation DAG, scheduling, re-emission.

gate = ['u', w, M]   (M exact 2x2 complex) | ['cx', c, t]
"""
import cmath, math
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import U3Gate

EPS = 1e-10
I2 = np.eye(2, dtype=complex)
HM = np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)


def u3m(t, p, l):
    c, s = math.cos(t / 2), math.sin(t / 2)
    return np.array([[c, -cmath.exp(1j * l) * s],
                     [cmath.exp(1j * p) * s, cmath.exp(1j * (p + l)) * c]],
                    dtype=complex)


def rzm(a):
    return np.array([[cmath.exp(-0.5j * a), 0], [0, cmath.exp(0.5j * a)]])


def rym(a):
    c, s = math.cos(a / 2), math.sin(a / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


def rxm(a):
    c, s = math.cos(a / 2), math.sin(a / 2)
    return np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)


def is_diag(M):
    return abs(M[0, 1]) < EPS and abs(M[1, 0]) < EPS


def is_xtype(M):
    return abs(M[0, 0] - M[1, 1]) < EPS and abs(M[0, 1] - M[1, 0]) < EPS


def is_id(M):
    return np.max(np.abs(M - I2)) < EPS


def zyz(M):
    """M = e^{i g} Rz(p) Ry(t) Rz(l)   (matrix order)."""
    det = M[0, 0] * M[1, 1] - M[0, 1] * M[1, 0]
    g = cmath.phase(det) / 2.0
    S = M * cmath.exp(-1j * g)
    t = 2 * math.atan2(abs(S[1, 0]), abs(S[0, 0]))
    if abs(S[1, 0]) < 1e-12:
        p, l = 2 * cmath.phase(S[1, 1]), 0.0
    elif abs(S[0, 0]) < 1e-12:
        p, l = 2 * cmath.phase(S[1, 0]), 0.0
    else:
        a, b = cmath.phase(S[1, 1]), cmath.phase(S[1, 0])
        p, l = a + b, a - b
    return g, p, t, l


def xzx(M):
    """M = e^{i g} Rx(a) Rz(b) Rx(c)  (matrix order)."""
    g, p, t, l = zyz(HM @ M @ HM)
    return g, p + math.pi / 2, t, l - math.pi / 2


def u3_params(M):
    """(theta, phi, lam, d) with M = e^{i d} U(theta,phi,lam); d = 0 whenever
    M[0,0] is real (in particular for every gate loaded from the QASM)."""
    a00 = M[0, 0]
    d = cmath.phase(a00) if abs(a00) > 1e-12 else 0.0
    if abs(d) > 1e-15:
        Mp = M * cmath.exp(-1j * d)
    else:
        Mp = M
        d = 0.0
    c = Mp[0, 0].real
    s = abs(Mp[1, 0])
    t = 2 * math.atan2(s, c)
    if s > 1e-12:
        p = cmath.phase(Mp[1, 0])
        l = cmath.phase(-Mp[0, 1])
    elif abs(c) > 1e-12:
        p = cmath.phase(Mp[1, 1] / c)
        l = 0.0
    else:
        p = cmath.phase(Mp[1, 0]); l = cmath.phase(-Mp[0, 1])
    return t, p, l, d


def rx_probe(gates, k, th):
    """insert Rx(th) just before gates[k] (a cx) on its target wire and
    Rx(-th) just after: exact identity, merged into the neighbouring 1q
    gates when they exist."""
    t = gates[k][2]
    out = [list(g) for g in gates]
    pre = None
    for i in range(k - 1, -1, -1):
        if t in wires(out[i]):
            pre = i if out[i][0] == 'u' else None
            break
    post = None
    for i in range(k + 1, len(out)):
        if t in wires(out[i]):
            post = i if out[i][0] == 'u' else None
            break
    A, B = rxm(th), rxm(-th)
    ins = []
    if pre is not None:
        out[pre][2] = A @ out[pre][2]
    else:
        ins.append((k, ['u', t, A]))
    if post is not None:
        out[post][2] = out[post][2] @ B
    else:
        ins.append((k + 1, ['u', t, B]))
    for pos, g in sorted(ins, reverse=True):
        out.insert(pos, g)
    return out


def repair_phase(gates, gphase=0.0, tol=1e-13):
    """return a gate list whose emission has zero net leftover phase."""
    def resid(gl):
        D = total_leftover(gl) + gphase
        return (D + math.pi) % (2 * math.pi) - math.pi
    if abs(resid(gates)) < tol:
        return gates
    cand = [k for k, g in enumerate(gates) if g[0] == 'cx']
    for k in cand[:80]:
        f = lambda th: resid(rx_probe(gates, k, th))
        lo, flo = None, None
        prev = 0.0
        vals = np.linspace(0, 4 * math.pi, 721)
        for th in vals:
            v = f(th)
            if lo is not None and abs(v - flo) < 1.0 and flo * v <= 0:
                a, b = lo, th
                for _ in range(200):
                    m = (a + b) / 2
                    fm = f(m)
                    if flo * fm <= 0:
                        b = m
                    else:
                        a, flo = m, fm
                m = (a + b) / 2
                if abs(f(m)) < tol:
                    return rx_probe(gates, k, m)
            lo, flo = th, v
    raise RuntimeError("phase repair failed")


# --------------------------------------------------------------- load / save
def load(path):
    qc = QuantumCircuit.from_qasm_file(path)
    gates = []
    for inst in qc.data:
        qs = [qc.find_bit(q).index for q in inst.qubits]
        nm = inst.operation.name
        if nm == 'cx':
            gates.append(['cx', qs[0], qs[1]])
        elif nm in ('u3', 'u'):
            t, p, l = [float(x) for x in inst.operation.params]
            gates.append(['u', qs[0], u3m(t, p, l)])
        elif nm == 'x':
            gates.append(['u', qs[0], u3m(math.pi, 0, math.pi)])
        else:
            raise ValueError(nm)
    return gates, qc.num_qubits


def total_leftover(gates):
    return sum(u3_params(g[2])[3] for g in gates if g[0] == 'u')


def to_qc(gates, n=18, fixphase=True, gphase=0.0):
    if fixphase:
        gates = repair_phase(gates, gphase)
    qc = QuantumCircuit(n)
    for g in gates:
        if g[0] == 'cx':
            qc.cx(g[1], g[2])
        else:
            t, p, l, d = u3_params(g[2])
            qc.append(U3Gate(t, p, l), [g[1]])
    return qc


# ------------------------------------------------------------ commutation
def commutes(g1, g2):
    """exact commutation of two gates that share at least one wire."""
    if g1[0] == 'cx' and g2[0] == 'cx':
        c1, t1, c2, t2 = g1[1], g1[2], g2[1], g2[2]
        return (c1 == c2) or (t1 == t2)
    if g1[0] == 'u' and g2[0] == 'u':
        return False                       # same wire: merge instead
    u, c = (g1, g2) if g1[0] == 'u' else (g2, g1)
    if u[1] == c[1]:
        return is_diag(u[2])
    return is_xtype(u[2])


def wires(g):
    return (g[1],) if g[0] == 'u' else (g[1], g[2])


def build_dag(gates, use_comm=True):
    """returns preds[i] = set of j<i that must precede i."""
    n = len(gates)
    last = {}                              # wire -> list of gate indices
    preds = [set() for _ in range(n)]
    hist = {}
    for i, g in enumerate(gates):
        ws = wires(g)
        for w in ws:
            for j in reversed(hist.get(w, [])):
                if use_comm and commutes(gates[j], g):
                    continue
                preds[i].add(j)
                break
        for w in ws:
            hist.setdefault(w, []).append(i)
    if use_comm:
        # a non-commuting pair must be ordered even if a commuting gate sits
        # between them on that wire -> full scan per wire
        preds = [set() for _ in range(n)]
        hist = {}
        for i, g in enumerate(gates):
            for w in wires(g):
                for j in hist.get(w, []):
                    if not commutes(gates[j], g):
                        preds[i].add(j)
            for w in wires(g):
                hist.setdefault(w, []).append(i)
    return preds


def longest_path(gates, preds):
    n = len(gates)
    lvl = [0] * n
    best = 0
    for i in range(n):
        lvl[i] = 1 + max([lvl[j] for j in preds[i]], default=0)
        best = max(best, lvl[i])
    return best, lvl


def asap_depth(gates, preds, n=18):
    """schedule respecting preds + qubit exclusivity, ASAP in list order."""
    free = [0] * n
    t = [0] * len(gates)
    for i, g in enumerate(gates):
        s = max([t[j] for j in preds[i]], default=0)
        s = max(s, max(free[w] for w in wires(g)))
        t[i] = s + 1
        for w in wires(g):
            free[w] = s + 1
    return (max(t) if t else 0), t


def plain_depth(gates, n=18):
    free = [0] * n
    for g in gates:
        s = max(free[w] for w in wires(g)) + 1
        for w in wires(g):
            free[w] = s
    return max(free)
