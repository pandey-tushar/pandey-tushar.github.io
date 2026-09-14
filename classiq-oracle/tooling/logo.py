"""Real Classiq logo (released Aug 28): predicate -> image -> exact oracle,
run through both emitters, then transpiled to the challenge's u3/cx basis to
get the actual scored metrics (depth after per-qubit layering, cx tiebreak).
"""
import time

import numpy as np
from qiskit import transpile

from analyze import N, DIM, img_to_f, walsh_hadamard, verify
from graywalk import emit_gray
from sched import emit_sched

EPS = 1e-12


def logo_pixel(x, y):
    return ((2 <= x <= 26 and 29 <= y <= 53)
        or (26 <= x <= 49 and 39 <= y <= 43)
        or (x - 55) ** 2 + (y - 41) ** 2 <= 42
        or (x - 40) ** 2 + (y - 19) ** 2 <= 72)


def build_logo():
    img = np.zeros((64, 64), dtype=np.int8)
    for y in range(64):
        for x in range(64):
            if logo_pixel(x, y):
                img[y, x] = 1
    return img


def challenge_metrics(qc, f):
    """Transpile to u3/cx, re-verify, pick the lowest-depth level tried."""
    best = None
    for level in (1, 2, 3):
        t0 = time.time()
        tqc = transpile(qc, basis_gates=["u3", "cx"], optimization_level=level)
        dt = time.time() - t0
        c = tqc.count_ops()
        d = tqc.depth()
        print(f"    opt_level={level}: depth={d}, cx={c.get('cx', 0)}, "
              f"time={dt:.1f}s")
        if best is None or d < best[1]:
            best = (level, d, c.get('cx', 0), tqc)
        if dt > 30:                    # escalating further isn't worth it
            break
    level, d, cx, tqc = best
    ok, err = verify(tqc, f)
    print(f"    verification (transpiled, level={level}): "
          f"{'PASS' if ok else 'FAIL'} (max err {err:.2e})")
    return level, d, cx


if __name__ == "__main__":
    img = build_logo()
    n_marked = int(img.sum())
    print(f"logo image: {n_marked} marked pixels")
    assert n_marked == 1097, f"expected 1097 marked pixels, got {n_marked}"

    f = img_to_f(img)
    fh = walsh_hadamard(f) / DIM
    support = np.nonzero(np.abs(fh) > EPS)[0]
    print(f"Walsh support: {len(support)} / {DIM}")
    coeffs = {int(s): fh[s] for s in support}

    results = {}
    for tag, emit in [("graywalk", emit_gray), ("sched", emit_sched)]:
        print(f"=== {tag} ===")
        qc = emit(coeffs)
        ok, err = verify(qc, f)
        c = qc.count_ops()
        print(f"  raw: depth={qc.depth()}, cx={c.get('cx', 0)}, "
              f"rz={c.get('rz', 0)}, {'PASS' if ok else 'FAIL'} "
              f"(max err {err:.2e})")
        level, d, cx = challenge_metrics(qc, f)
        print(f"  challenge metric: depth={d}, cx={cx}, width=12 "
              f"(opt_level={level})")
        results[tag] = d

    print(f"\nsched challenge depth={results['sched']} vs baseline=5329 "
          f"vs leaderboard best=726")
