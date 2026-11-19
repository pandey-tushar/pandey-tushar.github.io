"""Independent check of the lattice surgery in qec-in-practice/js/surgery.js with stim 1.15.

Qubit indices: stim qubit k is JS qubit k. 0..8 are patch A's data qubits and 9..17 patch B's,
both row-major on a 3 x 3 grid as in qec-in-practice/js/patch.js (B local i is 9 + i); 18, 19, 20
are the seam qubits between A's right column (2, 5, 8) and B's left column (9, 12, 15), rows 0..2.

The circuit is written out again here from the stabilizer supports (MPP), not imported from JS:
ideal preparation by measure-and-fix, seam in |+>, one round of merged checks, seam measured in X,
one round of the separate patches' checks, the Pauli frame as classically controlled Z gates,
then logical readout of both patches. For each of the 16 input pairs it records whether the
merge outcome is deterministic (exactly, from TableauSimulator.peek_observable_expectation, and
again from 2000 samples of the full circuit), whether the Z readouts always agree with the
reported parity, and the value of X_L(A) X_L(B) after the frame for X-basis inputs.

    python _studio/tools/tests/surgery/reference.py   (writes reference.json next to it)
"""
import json, pathlib
import stim

N = 21
X_STABS = [[0, 1, 3, 4], [4, 5, 7, 8], [2, 5], [3, 6]]
Z_STABS = [[1, 2, 4, 5], [3, 4, 6, 7], [0, 1], [7, 8]]
Z_FIX = [0, 8, 2, 6]   # Z on these flips only X_STABS[k]
X_FIX = [2, 6, 0, 8]   # X on these flips only Z_STABS[k]
XL, ZL = [0, 1, 2], [0, 3, 6]
SEAM = [18, 19, 20]

def patch(off):
    return [('X', [q + off for q in s]) for s in X_STABS] + [('Z', [q + off for q in s]) for s in Z_STABS]

PATCH = patch(0) + patch(9)
FACING = [('X', [2, 5]), ('X', [12, 15])]
SEAM_Z = [('Z', [2, 18]), ('Z', [5, 19, 8, 20]), ('Z', [18, 9, 19, 12]), ('Z', [20, 15])]
SEAM_X = [('X', [2, 18, 5, 19]), ('X', [19, 12, 20, 15])]
MERGED = [c for c in PATCH if c not in FACING] + SEAM_X + SEAM_Z


class Builder:
    def __init__(self):
        self.c = stim.Circuit()
        self.n = 0

    def mpp(self, typ, qs):
        self.c.append('MPP', stim.target_combined_paulis([stim.target_x(q) if typ == 'X' else stim.target_z(q) for q in qs]))
        self.n += 1
        return self.n - 1

    def mx(self, q):
        self.c.append('MX', [q])
        self.n += 1
        return self.n - 1

    def controlled(self, gate, recs, qs):
        # apply the Pauli to each q once per record: the net effect is conditioned on their parity
        for r in recs:
            for q in qs:
                self.c.append(gate, [stim.target_rec(r - self.n), q])


def prep(b, off, state):
    if state in '01':
        b.c.append('R', [off + i for i in range(9)])
        for k, s in enumerate(X_STABS):
            r = b.mpp('X', [q + off for q in s])
            b.controlled('CZ', [r], [off + Z_FIX[k]])
        if state == '1':
            b.c.append('X', [off + q for q in XL])
    else:
        b.c.append('RX', [off + i for i in range(9)])
        for k, s in enumerate(Z_STABS):
            r = b.mpp('Z', [q + off for q in s])
            b.controlled('CX', [r], [off + X_FIX[k]])
        if state == '-':
            b.c.append('Z', [off + q for q in ZL])


def circuit(a, bstate, basis):
    b = Builder()
    prep(b, 0, a)
    prep(b, 9, bstate)
    prep_only = b.c.copy()
    b.c.append('RX', SEAM)
    rec = {(t, tuple(q)): b.mpp(t, q) for t, q in MERGED}
    parity = [rec[(t, tuple(q))] for t, q in SEAM_Z] + [rec[(t, tuple(q))] for t, q in patch(0) if t == 'Z']
    m = [b.mx(q) for q in SEAM]
    for t, q in PATCH:
        b.mpp(t, q)
    sx = [rec[(t, tuple(q))] for t, q in SEAM_X]
    b.controlled('CZ', [sx[0], m[0], m[1]], [5, 8])
    b.controlled('CZ', [sx[1], m[1], m[2]], [15])
    b.controlled('CZ', [m[0]], ZL)
    ra = b.mpp(basis, ZL if basis == 'Z' else XL)
    rb = b.mpp(basis, [q + 9 for q in (ZL if basis == 'Z' else XL)])
    return prep_only, b.c, parity, ra, rb


def pauli(typ, qs):
    p = stim.PauliString(N)
    for q in qs:
        p[q] = typ
    return p


SIGN = {'0': 1, '1': -1, '+': 1, '-': -1}
SHOTS = 2000
cases = []
for a in '01+-':
    for bs in '01+-':
        prep_only, cz, parity, ra, rb = circuit(a, bs, 'Z')
        sim = stim.TableauSimulator()
        sim.set_num_qubits(N)
        sim.do_circuit(prep_only)
        exact = round(sim.peek_observable_expectation(pauli('Z', ZL + [q + 9 for q in ZL])))
        s = cz.compile_sampler(seed=1).sample(SHOTS).astype(int)
        par = 1 - 2 * (s[:, parity].sum(axis=1) % 2)
        rd = (1 - 2 * s[:, ra]) * (1 - 2 * s[:, rb])
        sampled = int(par[0]) if (par == par[0]).all() else None
        _, cx, _, xa, xb = circuit(a, bs, 'X')
        sx = cx.compile_sampler(seed=2).sample(SHOTS).astype(int)
        xx = (1 - 2 * sx[:, xa]) * (1 - 2 * sx[:, xb])
        cases.append({
            'a': a, 'b': bs,
            'parity_deterministic': exact if exact != 0 else None,
            'parity_deterministic_sampled': sampled,
            'parity_plus_fraction': float((par == 1).mean()),
            'z_readout_agrees': float((rd == par).mean()),
            'xx_after': int(xx[0]) if (xx == xx[0]).all() else None,
        })
        assert sampled == cases[-1]['parity_deterministic'], cases[-1]

out = pathlib.Path(__file__).with_name('reference.json')
out.write_text(json.dumps({'stim': stim.__version__, 'shots': SHOTS, 'cases': cases}, indent=1) + '\n')
for c in cases:
    print(c)
