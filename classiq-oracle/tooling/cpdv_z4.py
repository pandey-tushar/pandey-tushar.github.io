"""CP-DV: exact Z4 phase replay.

RCCX and RC3X are  D . P  with P the permutation (target ^= product of the
controls) and D diagonal in the OUTPUT basis, with entries in {1,i,-1,-i}.
A mirrored circuit cancels D against D-dagger; a self-closing one does not,
so the Z4 bookkeeping has to be carried explicitly.  For input v the gate
contributes D at index P(v), so the table is indexed by the wire values
AFTER the gate.
"""
import numpy as np
from qiskit.circuit.library import RCCXGate, RC3XGate
from qiskit.quantum_info import Operator

import cpdh_core as DH

NIN = 4096
FULL = (1 << NIN) - 1


def _diag(gate, n):
    U = Operator(gate).data
    N = 1 << n
    P = np.zeros((N, N))
    for i in range(N):
        p = 1
        for k in range(n - 1):
            p &= (i >> k) & 1
        P[i ^ (p << (n - 1)), i] = 1
    D = U @ P.T
    d = np.diag(D)
    out = []
    for z in d:
        ang = np.angle(z) / (np.pi / 2)
        k = int(round(ang)) % 4
        assert abs(z - 1j ** k) < 1e-9, z
        out.append(k)
    return out


TAB = {"and": _diag(RCCXGate(), 3), "and3": _diag(RC3XGate(), 4)}
# inverse gate: U^dg = P D^dg = (P D^dg P) P, so D'(j) = conj(D(P(j)))


def _perm_index(j, n):
    p = 1
    for k in range(n - 1):
        p &= (j >> k) & 1
    return j ^ (p << (n - 1))


TAB["and_dg"] = [(-TAB["and"][_perm_index(j, 3)]) % 4 for j in range(8)]
TAB["and3_dg"] = [(-TAB["and3"][_perm_index(j, 4)]) % 4 for j in range(16)]


def z4_replay(ops, shape="LOGO"):
    """-> (bad, odd, ph4) : bad = #inputs whose total phase is not (-1)^F,
    odd = #inputs carrying a +-i component, ph4 = the Z4 phase per input."""
    m = dict(DH.BASE)
    ph4 = [0] * NIN
    for op in ops:
        k, t, cs = op
        if t and t not in m:
            m[t] = 0
        if k in ("x", "x_dg"):
            m[t] ^= FULL
        elif k in ("cx", "cx_dg"):
            (a, na), = cs
            m[t] ^= DH.cmask(m, a) ^ (FULL if na else 0)
        elif k in ("cz", "ccz"):
            p = FULL
            for a, na in cs:
                p &= DH.cmask(m, a) ^ (FULL if na else 0)
            for v in range(NIN):
                if (p >> v) & 1:
                    ph4[v] = (ph4[v] + 2) % 4
        elif k in ("and", "and3", "and_dg", "and3_dg"):
            cm = [DH.cmask(m, a) ^ (FULL if na else 0) for a, na in cs]
            p = FULL
            for c in cm:
                p &= c
            m[t] ^= p
            tm = m[t]
            tab = TAB[k]
            nc = len(cm)
            for v in range(NIN):
                j = 0
                for b in range(nc):
                    j |= ((cm[b] >> v) & 1) << b
                j |= ((tm >> v) & 1) << nc
                f = tab[j]
                if f:
                    ph4[v] = (ph4[v] + f) % 4
        else:
            raise ValueError(k)
    want = DH.want_mask(shape)
    bad = 0
    odd = 0
    for v in range(NIN):
        w = 2 * ((want >> v) & 1)
        if ph4[v] % 2:
            odd += 1
        if ph4[v] != w:
            bad += 1
    dirty = [r for r, v in m.items() if v != DH.BASE.get(r, 0)]
    return bad, odd, ph4, dirty


if __name__ == "__main__":
    import sys
    lines = open(sys.argv[1]).read()
    ops = DH.parse(lines)
    bad, odd, ph4, dirty = z4_replay(ops)
    from collections import Counter
    print("%s: inputs with wrong phase %d/4096, with a +-i part %d, dirty %d"
          % (sys.argv[1], bad, odd, len(dirty)))
    print("  Z4 histogram:", dict(Counter(ph4)))
