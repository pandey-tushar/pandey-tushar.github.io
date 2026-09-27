"""CP-UA: algebraic in-place synthesis of the phase oracle from the ANF of F.
State = 18 wire values (bit-parallel truth tables) + P, the remaining phase
polynomial written in the CURRENT wire variables (set of 18-bit monomials),
so that P(W(x)) == F(x) ^ (phases emitted so far).  Steps (forward half):
  tof a b t  clean t: every monomial containing {a,b} is rewritten with t
                       (w_t = w_a w_b);  dirty t: substitution w_t -> w_t ^ w_a w_b
  cx a t     substitution w_t -> w_t ^ w_a          x t   w_t -> w_t ^ 1
Monomials of degree <= 2 are emitted at once (Z free, CZ), degree-3 ones stay
in P (CCZ if still there at the end) unless a step would split them.  A wire
that becomes identically 0 drops every monomial containing it.  P empty =
exact.  Circuit = forward steps with the phases at their instants, then the
mirror.  Beam search on  score = gate cost + emitted cost + cost-to-go(P)
- FREE * clean ancillas,  cost-to-go per monomial c(3) = CCZ, c(d) = CCZ +
TOF*(d-3).  Costs are CX counts (TOF = one Margolus pair).
Usage: python3 cpua_alg.py SEED [BEAM] [MAXSTEPS]
Env: TOF (6) CXC (2) CZ (1) CCZ (6) FREE (3) NOISE (0.0)
Progress one line per step; checkpoint ckpt/cpua_s<seed>.pkl; exact circuits
-> out/cpua_s<seed>_<n>.qasm with transpiled depth / CX printed."""
import sys, os, time, pickle, random
import numpy as np

NW, ND = 18, 12
TOF = float(os.environ.get('TOF', '6')); CXC = float(os.environ.get('CXC', '2'))
CZ = float(os.environ.get('CZ', '1')); CCZ = float(os.environ.get('CCZ', '6'))
FREE = float(os.environ.get('FREE', '3')); NOISE = float(os.environ.get('NOISE', '0'))
MASK = (1 << 4096) - 1


def popcount(m):
    return bin(m).count('1')


def cmono(d):
    if d <= 2: return 0.0
    if d == 3: return CCZ
    return CCZ + TOF * (d - 3)


def logo_int():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cpae_core import SHAPES, fvec
    f = fvec(SHAPES['LOGO'])
    return int(''.join('1' if b else '0' for b in f[::-1]), 2)


def anf_monomials(f):
    """ANF of a 4096-entry truth table (bit i of f = F(i)) as a set of 12-bit masks."""
    v = np.array([(f >> i) & 1 for i in range(4096)], dtype=np.uint8).reshape([2] * 12)
    for ax in range(12):
        v = v.copy()
        idx0 = [slice(None)] * 12; idx1 = [slice(None)] * 12
        idx0[ax] = 0; idx1[ax] = 1
        v[tuple(idx1)] ^= v[tuple(idx0)]
    flat = v.reshape(-1)
    return set(int(k) for k in np.nonzero(flat)[0])   # flat index == monomial mask (same bit order)


def init_wires():
    W = []
    for w in range(ND):
        v = 0
        for i in range(4096):
            if (i >> w) & 1: v |= 1 << i
        W.append(v)
    return W + [0] * (NW - ND)


def eval_poly(P, W):
    r = 0
    for m in P:
        v = MASK; mm = m
        while mm:
            b = mm & -mm; v &= W[b.bit_length() - 1]; mm ^= b
        r ^= v
    return r


class State:
    __slots__ = ('W', 'P', 'steps', 'emit', 'gcost', 'ecost', 'resid')

    def __init__(self, W, P, steps, emit, gcost, ecost, resid):
        self.W, self.P, self.steps, self.emit = W, P, steps, emit
        self.gcost, self.ecost, self.resid = gcost, ecost, resid

    def clean(self):
        return [w for w in range(ND, NW) if self.W[w] == 0]

    def togo(self):
        return sum(cmono(popcount(m)) for m in self.P)

    def score(self):
        return self.gcost + self.ecost + self.togo() - FREE * len(self.clean())


def settle(P, W, emit_list, inst):
    """emit degree <= 2 monomials, drop monomials on zero wires; returns (P, ecost)"""
    zero = 0
    for w in range(NW):
        if W[w] == 0: zero |= 1 << w
    out = set(); ec = 0.0
    for m in P:
        if m & zero: continue
        d = popcount(m)
        if d <= 2:
            emit_list.append((inst, m)); ec += CZ if d == 2 else 0.0
        else: out.add(m)
    return out, ec


def apply(st, step, emit3):
    """apply a step; emit3: emit degree-3 monomials on the changed wire first
    (dirty-target steps only).  Returns a new State or None if useless."""
    kind = step[0]; W = list(st.W); P = set(st.P); emit = list(st.emit)
    gcost, ecost = st.gcost, st.ecost; inst = len(st.steps)
    if kind == 'tof':
        _, a, b, t = step; ab = (1 << a) | (1 << b); tb = 1 << t
        if W[t] == 0:
            S = [m for m in P if m & ab == ab]
            for m in S: P.remove(m); P.add((m & ~ab) | tb)
            gcost += TOF
        else:
            if emit3:
                for m in [m for m in P if m & tb and popcount(m) == 3]:
                    P.remove(m); emit.append((inst, m)); ecost += CCZ
            S = [m for m in P if m & tb]
            for m in S: P ^= {(m & ~tb) | ab}
            gcost += TOF
        W[t] ^= W[a] & W[b]
    elif kind == 'cx':
        _, a, t = step; ab = 1 << a; tb = 1 << t
        if emit3:
            for m in [m for m in P if m & tb and popcount(m) == 3]:
                P.remove(m); emit.append((inst, m)); ecost += CCZ
        S = [m for m in P if m & tb]
        for m in S: P ^= {(m & ~tb) | ab}
        gcost += CXC; W[t] ^= W[a]
    else:
        _, t = step; tb = 1 << t
        S = [m for m in P if m & tb]
        for m in S: P ^= {m & ~tb}
        W[t] ^= MASK
    P, ec = settle(P, W, emit, inst + 1)
    return State(W, P, st.steps + [step], emit, gcost, ecost + ec, None)


def candidates(st):
    dirty = [w for w in range(NW) if st.W[w] != 0]
    clean = st.clean(); out = []
    for i, a in enumerate(dirty):
        for b in dirty[i + 1:]:
            if clean: out.append((('tof', a, b, clean[0]), False))
            for t in dirty:
                if t != a and t != b:
                    out.append((('tof', a, b, t), False)); out.append((('tof', a, b, t), True))
    for a in dirty:
        for t in dirty:
            if a != t: out.append((('cx', a, t), False)); out.append((('cx', a, t), True))
    for t in dirty: out.append((('x', t), False))
    return out


def build_qc(st):
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(NW)
    by_inst = {}
    for inst, m in st.emit: by_inst.setdefault(inst, []).append(m)

    def phases(inst):
        for m in by_inst.get(inst, []):
            ws = [w for w in range(NW) if (m >> w) & 1]
            if len(ws) == 1: qc.z(ws[0])
            elif len(ws) == 2: qc.cz(*ws)
            elif len(ws) == 3: qc.ccz(*ws)
    phases(0)
    for k, s in enumerate(st.steps):
        if s[0] == 'tof': qc.rccx(s[1], s[2], s[3])
        elif s[0] == 'cx': qc.cx(s[1], s[2])
        else: qc.x(s[1])
        phases(k + 1)
    for s in reversed(st.steps):
        if s[0] == 'tof': qc.append(__import__('qiskit.circuit.library', fromlist=['RCCXGate']).RCCXGate().inverse(), [s[1], s[2], s[3]])
        elif s[0] == 'cx': qc.cx(s[1], s[2])
        else: qc.x(s[1])
    return qc


def finish(st, seed, n, F, W0):
    """final check + emission of an exact state"""
    from cpae_core import real_depth, sv_check_gp
    from qiskit import transpile
    qc = build_qc(st)
    t = transpile(qc, basis_gates=['u3', 'cx'], optimization_level=3)
    d, cx = t.depth(), t.count_ops().get('cx', 0)
    err, leak = sv_check_gp(t, 'LOGO')
    ok = err < 1e-10 and leak < 1e-12
    os.makedirs('out', exist_ok=True)
    fn = 'out/cpua_s%d_%d.qasm' % (seed, n)
    from qiskit import qasm2
    qasm2.dump(t, fn)
    ntof = sum(1 for s in st.steps if s[0] == 'tof'); ncz = sum(1 for _, m in st.emit if popcount(m) == 2)
    nccz = sum(1 for _, m in st.emit if popcount(m) == 3)
    print('[cpua s%d] EXACT steps %d tof %d cz %d ccz %d -> depth %d cx %d err %.1e leak %.1e %s  %s'
          % (seed, len(st.steps), ntof, ncz, nccz, d, cx, err, leak, 'PASS' if ok else 'FAIL', fn), flush=True)
    return d, cx, ok


def main():
    seed = int(sys.argv[1]); BEAM = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    MAXS = int(sys.argv[3]) if len(sys.argv) > 3 else 80
    rng = random.Random(seed)
    F = logo_int(); W0 = init_wires(); P0 = anf_monomials(F)
    assert eval_poly(P0, W0) == F, 'ANF check failed'
    print('[cpua s%d] ANF %d monomials, max degree %d' % (seed, len(P0), max(popcount(m) for m in P0)), flush=True)
    st0 = State(W0, P0, [], [], 0.0, 0.0, None)
    st0.P, ec = settle(st0.P, st0.W, st0.emit, 0); st0.ecost += ec
    beam = [st0]; exact = []; t0 = time.time(); nex = 0; last = time.time()
    os.makedirs('ckpt', exist_ok=True)
    for step in range(1, MAXS + 1):
        pool = {}
        for st in beam:
            for cand, e3 in candidates(st):
                ns = apply(st, cand, e3)
                if ns is None: continue
                key = (frozenset(ns.P), tuple(ns.W))
                sc = ns.score() + (rng.gauss(0, NOISE) if NOISE else 0)
                if key not in pool or sc < pool[key][0]: pool[key] = (sc, ns)
                if time.time() - last > 10:
                    print('  step %d: %d candidates so far, %ds' % (step, len(pool), time.time() - t0), flush=True); last = time.time()
        ranked = sorted(pool.values(), key=lambda x: x[0])
        beam = []
        for sc, ns in ranked:
            if not ns.P:
                # verify the algebra: P empty means emitted phases reproduce F
                res = F
                # recompute residual by replaying emitted phases on the wire trajectories
                Wt = list(W0); trajs = [list(Wt)]
                for s in ns.steps:
                    if s[0] == 'tof': Wt[s[3]] ^= Wt[s[1]] & Wt[s[2]]
                    elif s[0] == 'cx': Wt[s[2]] ^= Wt[s[1]]
                    else: Wt[s[1]] ^= MASK
                    trajs.append(list(Wt))
                for inst, m in ns.emit: res ^= eval_poly({m}, trajs[inst])
                if res != 0: print('  ALGEBRA MISMATCH weight %d' % popcount(res), flush=True); continue
                nex += 1; exact.append(ns); d, cx, ok = finish(ns, seed, nex, F, W0)
                continue
            beam.append(ns)
            if len(beam) >= BEAM: break
        if not beam: break
        b = beam[0]
        degs = {}
        for m in b.P: degs[popcount(m)] = degs.get(popcount(m), 0) + 1
        print('[cpua s%d] step %3d  best score %.0f  |P| %d degs %s  gates %.0f emitted %.0f clean %d  last %s  %ds'
              % (seed, step, b.score(), len(b.P), dict(sorted(degs.items())), b.gcost, b.ecost, len(b.clean()), b.steps[-1], time.time() - t0), flush=True)
        pickle.dump({'beam': [(s.W, s.P, s.steps, s.emit, s.gcost, s.ecost) for s in beam], 'exact': [(s.steps, s.emit) for s in exact]},
                    open('ckpt/cpua_s%d.pkl' % seed, 'wb'))
    print('[cpua s%d] done: %d exact circuits, %ds' % (seed, nex, time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
