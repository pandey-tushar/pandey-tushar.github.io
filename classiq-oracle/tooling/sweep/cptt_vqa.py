"""Variational test: fixed skeleton of L CX layers (random perfect matchings on
ALL n wires, all-to-all), u3 on every wire before each CX layer and at the end.
Target: U|x,0> = e^{i g} (-1)^f(x) |x,0> for every data input x (all 2^nd columns).
Loss = 1 - |sum_x (-1)^f(x) <x,0|U|x,0>|^2 / 4^nd  (0 iff exact, global phase free).
Gradient by the adjoint method (numpy), optimiser scipy L-BFGS-B, several starts.
Usage: python3 cptt_vqa.py ND NA L STARTS [MAXITER] [TARGET: rand|logo6]
Progress every 10 s; summary line per start."""
import sys, time
import numpy as np
from scipy.optimize import minimize


def u3(t, p, l):
    c, s = np.cos(t / 2), np.sin(t / 2)
    return np.array([[c, -np.exp(1j * l) * s], [np.exp(1j * p) * s, np.exp(1j * (p + l)) * c]])


def du3(t, p, l):
    c, s = np.cos(t / 2), np.sin(t / 2)
    dt = np.array([[-s / 2, -np.exp(1j * l) * c / 2], [np.exp(1j * p) * c / 2, -np.exp(1j * (p + l)) * s / 2]])
    dp = np.array([[0, 0], [1j * np.exp(1j * p) * s, 1j * np.exp(1j * (p + l)) * c]])
    dl = np.array([[0, -1j * np.exp(1j * l) * s], [0, 1j * np.exp(1j * (p + l)) * c]])
    return dt, dp, dl


class Circ:
    def __init__(self, nd, na, L, rng):
        self.n = nd + na; self.nd = nd; self.L = L
        self.pairs = []
        for _ in range(L):
            perm = rng.permutation(self.n)
            self.pairs.append([(int(perm[i]), int(perm[i + 1])) for i in range(0, self.n - 1, 2)])
        self.np_ = (L + 1) * self.n * 3

    def apply1(self, psi, G, q):      # psi: (B, 2,...,2); qubit q -> axis q+1
        return np.moveaxis(np.tensordot(G, psi, axes=([1], [q + 1])), 0, q + 1)

    def cx(self, psi, c, t):
        psi = psi.copy()
        idx = [slice(None)] * (self.n + 1); idx[c + 1] = 1
        sub = psi[tuple(idx)]                       # control=1 slice, target axis shifts if t > c
        ta = t + 1 - (1 if t > c else 0)
        psi[tuple(idx)] = np.flip(sub, axis=ta)
        return psi

    def loss_grad(self, x, inp, tgt):
        n = self.n; P = x.reshape(self.L + 1, n, 3)
        Gs = [[u3(*P[l, q]) for q in range(n)] for l in range(self.L + 1)]
        phi = inp
        for l in range(self.L + 1):
            for q in range(n): phi = self.apply1(phi, Gs[l][q], q)
            if l < self.L:
                for c, t in self.pairs[l]: phi = self.cx(phi, c, t)
        c_ = np.vdot(tgt, phi)
        B = inp.shape[0]
        loss = 1 - abs(c_) ** 2 / B ** 2
        g = np.zeros_like(P)
        lam = tgt.copy()
        for l in range(self.L, -1, -1):
            if l < self.L:
                for c, t in reversed(self.pairs[l]): phi = self.cx(phi, c, t); lam = self.cx(lam, c, t)
            for q in reversed(range(n)):
                G = Gs[l][q]
                phi = self.apply1(phi, G.conj().T, q)
                ax = [a for a in range(n + 1) if a != q + 1]
                R = np.tensordot(lam.conj(), phi, axes=(ax, ax))      # R[i,j] = sum lam*_i phi_j
                for k, dG in enumerate(du3(*P[l, q])):
                    dc = np.sum(R * dG)
                    g[l, q, k] = -2 * np.real(np.conj(c_) * dc) / B ** 2
                lam = self.apply1(lam, G.conj().T, q)
        return loss, g.reshape(-1)


def states(nd, na, f):
    n = nd + na; B = 1 << nd
    inp = np.zeros((B,) + (2,) * n, dtype=complex); tgt = np.zeros_like(inp)
    for x in range(B):
        bits = tuple((x >> i) & 1 for i in range(nd)) + (0,) * na
        inp[(x,) + bits] = 1; tgt[(x,) + bits] = -1 if f[x] else 1
    return inp, tgt


if __name__ == '__main__':
    nd, na, L, starts = map(int, sys.argv[1:5])
    maxiter = int(sys.argv[5]) if len(sys.argv) > 5 else 3000
    tname = sys.argv[6] if len(sys.argv) > 6 else 'rand'
    rng = np.random.default_rng(7)
    f = rng.integers(0, 2, 1 << nd)
    inp, tgt = states(nd, na, f)
    circ = Circ(nd, na, L, rng)
    print('n=%d (data %d, anc %d)  CX layers %d (%d CX)  params %d  target %s weight %d' %
          (circ.n, nd, na, L, sum(len(p) for p in circ.pairs), circ.np_, tname, f.sum()), flush=True)
    best = None
    for s in range(starts):
        x0 = rng.uniform(0, 2 * np.pi, circ.np_)
        t0 = time.time(); last = [t0]; it = [0]; cur = [1.0]
        def fun(x):
            l, g = circ.loss_grad(x, inp, tgt); cur[0] = l; return l, g
        def cb(x):
            it[0] += 1
            if time.time() - last[0] > 10:
                last[0] = time.time(); print('   start %d  iter %d  loss %.3e  %.0fs' % (s, it[0], cur[0], last[0] - t0), flush=True)
        r = minimize(fun, x0, jac=True, method='L-BFGS-B', callback=cb,
                     options=dict(maxiter=maxiter, ftol=1e-16, gtol=1e-12, maxfun=maxiter * 2))
        print('start %d: loss %.3e  iters %d  %.0fs  (%s)' % (s, r.fun, r.nit, time.time() - t0, r.message), flush=True)
        if best is None or r.fun < best: best = r.fun
    print('best loss over %d starts: %.3e' % (starts, best), flush=True)
