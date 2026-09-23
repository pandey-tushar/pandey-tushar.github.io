"""exact AND count (multiplicative complexity) of a named x or y target,
over raw bits (x: raw x bits; fold is linear so MC is the same after it)."""
import sys, time
import cptb_ysat
from cpri_round import solve
from cptb_xag import build
from cptc_targets import X, Y, ALL
name, kmax, to = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
T = X.get(name, Y.get(name))
for k in range(0, kmax + 1):
    if k == 0:
        # affine?
        from cptb_tensor_free import affine
        if affine(T): print(name, 'MC = 0'); break
        continue
    e, sel = build(T, ALL, k); t0 = time.time(); res = solve(e.cl, to)
    st = 'timeout' if res == 'timeout' else ('UNSAT' if res is None else 'SAT')
    if st == 'SAT': print(name, 'MC =', k, '(%.0fs)' % (time.time() - t0), flush=True); break
    if st == 'timeout': print(name, 'MC >', k - 1, '(k=%d timeout)' % k, flush=True); break
