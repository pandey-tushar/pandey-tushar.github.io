"""Cost of a k-class rotation readout exp(i pi g(V)): phase polynomial with
parities formed in parallel.  Wires = k value wires + m zero ancillas.
Randomized greedy: each CX layer is a set of disjoint CX (s -> t) chosen to
create not-yet-rotated needed parities (nonzero Walsh coefficients of g);
Rz on every wire that holds an unrotated needed parity after each layer;
when all are rotated, the CX layers are undone in reverse (mirror).
Verified exactly (diagonal of the unitary == (-1)^g up to global phase),
then measured with the real transpile.
Usage: python3 cptd_diag.py [TRIES]   (g = readout-0 option chosen by merge4 R=2)
Checkpoint: ckpt/diag.json (best per m)"""
import sys, json, time, pickle, random
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from cpae_core import real_depth
from cptd_rot import walsh


def synth(t, m, rng):
    k = int(np.log2(len(t))); n = k + m
    W = walsh(t.astype(np.uint8))
    need = {s for s in range(1, 1 << k) if W[s] != 0}
    st = [1 << i for i in range(k)] + [0] * m
    layers, rots = [], []
    def rotate():
        r = []
        for w in range(n):
            if st[w] in need: need.discard(st[w]); r.append((w, np.pi * W[st[w]] / (1 << k)))
        rots.append(r)
    rotate()
    while need:
        busy, lay = set(), []
        cands = [(s, d) for s in range(n) for d in range(n) if s != d]
        rng.shuffle(cands)
        # pass 1: CX that create a needed parity; pass 2: copies into zero wires
        for want in (1, 2):
            for s, d in cands:
                if s in busy or d in busy or not st[s]: continue
                v = st[d] ^ st[s]
                if want == 1 and v in need and not any(st[u] == v for u in range(n)) \
                        and not (st[d] in need):
                    pass
                elif want == 2 and st[d] == 0 and rng.random() < 0.5:
                    pass
                else:
                    continue
                if want == 1 and v in [st[u] ^ st[x] for u, x in lay]: continue
                lay.append((s, d)); busy |= {s, d}
        if not lay:                 # stuck: one random move
            s_, d_ = next((s, d) for s, d in cands if st[s])
            lay = [(s_, d_)]
        for s, d in lay: st[d] ^= st[s]
        layers.append(lay); rotate()
        if len(layers) > 40: return None
    return layers, rots, n


def circuit(layers, rots, n):
    qc = QuantumCircuit(n)
    for w, a in rots[0]: qc.rz(a, w)
    for lay, r in zip(layers, rots[1:]):
        for s, d in lay: qc.cx(s, d)
        for w, a in r: qc.rz(a, w)
    for lay in reversed(layers):
        for s, d in lay: qc.cx(s, d)
    return qc


def check(qc, t, m):
    k = int(np.log2(len(t)))
    U = Operator(qc).data
    d = np.diag(U)[: 1 << k]          # ancillas |0> (high qubits)
    want = (-1.0) ** t
    ph = d[0] / want[0]
    off = np.abs(U[:, : 1 << k] - np.diag(np.diag(U))[:, : 1 << k]).max()
    return float(np.abs(d / ph - want).max()), float(off)


if __name__ == '__main__':
    tries = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    d = pickle.load(open('ckpt/merge4_R2_L2_K5.pkl', 'rb'))
    t = np.array(d['opts'][0][d['sol']['rd4'][0][0]][1], dtype=np.uint8)
    print('g over %d classes, needed parities %d' % (int(np.log2(len(t))), int((walsh(t)[1:] != 0).sum())), flush=True)
    res = {}
    for m in range(0, 7):
        rng = random.Random(m); t0 = time.time(); best = None; seen = []
        for _ in range(tries):
            s = synth(t, m, rng)
            if s and (best is None or len(s[0]) < len(best[0])): best = s
            if s and len(s[0]) == len(best[0]): seen.append(s)
        cand = sorted(seen, key=lambda s: len(s[0]))[:20]
        meas = []
        for s in cand:
            qc = circuit(*s); meas.append((real_depth(qc), s, qc))
        dep, s, qc = min(meas, key=lambda x: x[0])
        err = check(qc, t, m)
        res[m] = dict(cx_layers=2 * len(s[0]), real=dep, err=err)
        print('m=%d ancillas: CX layers %d (fwd %d)  real depth/cx %s  check (err, offdiag) %s  %.0fs'
              % (m, 2 * len(s[0]), len(s[0]), dep, err, time.time() - t0), flush=True)
        json.dump(res, open('ckpt/diag.json', 'w'), indent=1, default=str)
