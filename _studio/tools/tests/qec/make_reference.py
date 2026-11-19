# Reference logical error rates from stim + pymatching (MWPM) for the JS union-find engine in qec-in-practice/js/qec/.
#
# Noise mapping (identical to the JS samplers in noise.js and the estimate() loop in montecarlo.js):
#   Codes: the same check supports as codes.js (rebuilt below with the same rule and stored in reference.json so the
#     JS test can compare them). Only X (bit-flip) errors are simulated, so only Z checks matter.
#   rounds = R. For t = 0..R-1: X_ERROR(p) on every data qubit (JS: sampleErrors 'bitflip'), then
#     - if t < R-1: each Z check measured as MPP(q) Z..Z, i.e. its outcome flipped with prob q
#       (JS: sampleMeasurementFlips), q = p here;
#     - if t = R-1: all data qubits measured perfectly with M; the final Z-check values are parities of those.
#   R = 1 is code capacity (one layer of X errors, perfect syndrome). Phenomenological uses R = d.
#   Detectors: layer t, check c = outcome[t][c] xor outcome[t-1][c] (outcome[-1] = 0), as detectionEvents().
#   Observable: parity of the final data measurement over logical Z (left column for the surface code, qubit 0 for
#     the repetition code), i.e. JS logicalFailure(...).x.
import json
import numpy as np
import stim
import pymatching

SHOTS = 200_000


def repetition_z(d):
    return [[i - 1, i] for i in range(1, d)], [0]


def surface_z(d):
    zs = []

    def add(r, c):
        if (r + c) % 2 == 0:
            return
        zs.append(sorted(i * d + j for i, j in ((r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1))
                         if 0 <= i < d and 0 <= j < d))
    for r in range(d - 1):
        for c in range(d - 1):
            add(r, c)
    for c in range(d - 1):
        if c % 2 == 0:
            add(-1, c)
    for c in range(d - 1):
        if (d - 1 + c) % 2 == 1:
            add(d - 1, c)
    return zs, [i * d for i in range(d)]


def circuit(n, zchecks, logical_z, p, q, rounds):
    c = stim.Circuit()
    m = len(zchecks)
    for t in range(rounds):
        c.append('X_ERROR', range(n), p)
        if t < rounds - 1:
            targets = []
            for s in zchecks:
                for k, i in enumerate(s):
                    if k:
                        targets.append(stim.target_combiner())
                    targets.append(stim.target_z(i))
            c.append('MPP', targets, q)
            for k in range(m):
                rec = [stim.target_rec(-m + k)]
                if t:
                    rec.append(stim.target_rec(-2 * m + k))
                c.append('DETECTOR', rec)
        else:
            c.append('M', range(n))
            for k, s in enumerate(zchecks):
                rec = [stim.target_rec(-n + i) for i in s]
                if rounds > 1:
                    rec.append(stim.target_rec(-n - m + k))
                c.append('DETECTOR', rec)
            c.append('OBSERVABLE_INCLUDE', [stim.target_rec(-n + i) for i in logical_z], 0)
    return c


def rate(kind, d, p, rounds, seed):
    zs, lz = (repetition_z if kind == 'repetition' else surface_z)(d)
    n = d if kind == 'repetition' else d * d
    circ = circuit(n, zs, lz, p, p if rounds > 1 else 0, rounds)
    matcher = pymatching.Matching.from_detector_error_model(circ.detector_error_model(decompose_errors=True))
    det, obs = circ.compile_detector_sampler(seed=seed).sample(SHOTS, separate_observables=True)
    fails = int(np.sum(matcher.decode_batch(det)[:, 0] != obs[:, 0]))
    return {'kind': kind, 'd': d, 'p': p, 'q': p if rounds > 1 else 0, 'rounds': rounds, 'model': 'bitflip',
            'seed': seed, 'shots': SHOTS, 'failures': fails, 'rate': fails / SHOTS, 'zChecks': zs, 'logicalZ': lz}


def main():
    rows, seed = [], 1000
    for kind in ('repetition', 'surface'):
        for d in (3, 5, 7):
            for p in (0.02, 0.05, 0.08, 0.10):
                seed += 1
                rows.append(rate(kind, d, p, 1, seed))
    for d in (3, 5):
        for p in (0.01, 0.02, 0.03):
            seed += 1
            rows.append(rate('surface', d, p, d, seed))
    out = {
        'stim': stim.__version__, 'pymatching': pymatching.__version__, 'decoder': 'pymatching MWPM',
        'noise': 'rounds R; each round X_ERROR(p) on all data qubits; Z checks measured with MPP(q) in rounds '
                 '0..R-2 (q = p), perfect data measurement in round R-1; R = 1 is code capacity. Observable: '
                 'parity of logical Z support. See the header of make_reference.py.',
        'rows': rows,
    }
    with open(__file__.replace('make_reference.py', 'reference.json'), 'w') as f:
        json.dump(out, f, indent=1)
    for r in rows:
        print(r['kind'], r['d'], r['p'], r['rounds'], r['rate'])


if __name__ == '__main__':
    main()
