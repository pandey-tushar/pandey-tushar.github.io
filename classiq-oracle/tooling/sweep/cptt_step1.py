"""Step 1 driver: planted (realizable) targets and random diagonal targets, 6 data + 2 anc."""
import sys, time
import numpy as np
from scipy.optimize import minimize
from cptt_vqa import Circ, states
nd, na = 6, 2
def run(c, inp, tgt, rng, starts, maxiter, tag):
    best = 1
    for s in range(starts):
        t0 = time.time()
        r = minimize(lambda x: c.loss_grad(x, inp, tgt), rng.uniform(0, 2 * np.pi, c.np_), jac=True, method='L-BFGS-B',
                     options=dict(maxiter=maxiter, maxfun=2 * maxiter, ftol=1e-16, gtol=1e-12))
        best = min(best, r.fun)
        print('  %s start %d: loss %.3e iters %d %.0fs' % (tag, s, r.fun, r.nit, time.time() - t0), flush=True)
    return best
rng = np.random.default_rng(11)
for L in [int(a) for a in sys.argv[1].split(',')]:
    c = Circ(nd, na, L, rng)
    f = rng.integers(0, 2, 64); inp, tgt0 = states(nd, na, f)
    # planted: target = U(x*) applied to the inputs (realizable by this skeleton)
    xs = rng.uniform(0, 2 * np.pi, c.np_)
    P = xs.reshape(L + 1, c.n, 3)
    from cptt_vqa import u3
    phi = inp
    for l in range(L + 1):
        for q in range(c.n): phi = c.apply1(phi, u3(*P[l, q]), q)
        if l < L:
            for a, t in c.pairs[l]: phi = c.cx(phi, a, t)
    bp = run(c, inp, phi, rng, 2, 3000, 'L%d planted' % L)
    br = run(c, inp, tgt0, rng, 3, 3000, 'L%d random-f' % L)
    print('L %d (params %d, transpiled depth ~%d): planted best %.3e | random diagonal f best %.3e' % (L, c.np_, 2 * L + 1, bp, br), flush=True)
