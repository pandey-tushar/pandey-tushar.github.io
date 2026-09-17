"""CP-FI: execute per-episode pebbling plans jointly on 18 wires.

Each episode has a plan (cpfi_plan: sequence of ('c', k) / ('u', k) /
('p', j)).  The executor interleaves the episodes by earliest start time,
assigns each compute a wire (a free ancilla, or a data wire on which the
node is reader-compatible and temporally safe within its own plan), and
emits ops.  Phase moves are ignored: the phase gates are chosen afterwards
by the temporal span solver (cpfi_span), which also cancels any raw-bit
junk.  Result verified by exact replay + statevector, scored by transpile.
"""
import sys, random, time, pickle
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfi_joint as J
import cpfi_plan as P
import cpfi_span as S
import cpfh_core as C
from cpae_core import model_depth as _md, ops_to_qc as _otq
from collections import Counter
from qiskit import QuantumCircuit

def model_depth(ops):
    return _md([o for o in ops if o[0] != 'z'])

def ops_to_qc(ops, n=18):
    qc = _otq([o for o in ops if o[0] != 'z'], n) if not any(o[0] == 'z' for o in ops) else None
    if qc is not None: return qc
    qc = QuantumCircuit(n)
    from qiskit.circuit.library import RCCXGate, RC3XGate, CCZGate
    for op in ops:
        k, qs = op[0], list(op[1:])
        if k == 'x': qc.x(qs[0])
        elif k == 'z': qc.z(qs[0])
        elif k == 'cx': qc.cx(*qs)
        elif k == 'cz': qc.cz(*qs)
        elif k == 'ccz': qc.append(CCZGate(), qs)
        elif k == 'ccx': qc.append(RCCXGate(), qs)
        elif k == 'ccx_dg': qc.append(RCCXGate().inverse(), qs)
        elif k == 'c3x': qc.append(RC3XGate(), qs)
        elif k == 'c3x_dg': qc.append(RC3XGate().inverse(), qs)
        else: raise ValueError(k)
    return qc

N, preds, succ = J.N, J.preds, J.succ
NW = 18


class Exec(J.Sched):
    def __init__(self, eps, plans, rng, data_pref=True, jitter=0.0, lazy=True):
        super().__init__(eps, rng, anc_pref=not data_pref, jitter=jitter)
        self.lazy = lazy
        self.plans = plans; self.pos = [0] * len(eps)
        self.hostable = [P.hostable(ep) for ep in eps]
        self.data_pref = data_pref
        self.rem = [sum(13 if len(N[m[1]]) == 3 else 7 for m in pl if m[0] != 'p') for pl in plans]

    def temporal_safe(self, e, i, k, w):
        """no action of episode e between plan index i and k's next uncompute
        reads x_w without n_k."""
        pl = self.plans[e]; nb = 1 << (12 + k)
        for j in range(i + 1, len(pl)):
            a, m = pl[j]
            if a == 'u' and m == k:
                return True
            if a == 'p':
                continue
            for f in N[m]:
                if (f >> w) & 1 and not (f & nb):
                    return False
        return True

    def next_action(self, e, dry):
        pl = self.plans[e]; i = self.pos[e]
        if i >= len(pl): return None
        a, k = pl[i]
        if a == 'p':
            return 0.0                                  # free marker
        if a == 'u':
            return self.fire(k, uncompute=True, dry=dry)
        # compute: choose target
        cands = []
        for w in self.hostable[e].get(k, []):
            if self.cont[w] == J.RAW[w] and self.temporal_safe(e, i, k, w):
                cands.append(w)
        anc = [w for w in range(12, NW) if self.cont[w] == 0]
        order = (cands + anc) if self.data_pref else (anc + cands)
        if self.jitter and len(order) > 1:
            self.rng.shuffle(order)
        best = None
        for w in order:
            t = self.fire(k, dry=True, tgt=w)
            if t is None: continue
            if best is None or t < best[0]:
                best = (t, w)
            if not self.jitter: break
        if best is None: return None
        if dry: return best[0]
        return self.fire(k, tgt=best[1])

    def run(self):
        while True:
            if all(self.pos[e] >= len(self.plans[e]) for e in range(len(self.eps))):
                self.restore()
                return True
            opts = []
            for e in range(len(self.eps)):
                t = self.next_action(e, dry=True)
                if t is None: continue
                opts.append((t + self.rng.random() * self.jitter, -self.rem[e], e))
            if not opts:
                if self.verbose:
                    print('    DEADLOCK pos %s host %s' % (self.pos, self.host))
                return False
            opts.sort()
            e = opts[0][2]
            a, k = self.plans[e][self.pos[e]]
            r = self.next_action(e, dry=False)
            if r is None: return False
            if a != 'p': self.rem[e] -= 13 if len(N[k]) == 3 else 7
            self.pos[e] += 1


def finish(ops, eps, verbose=True):
    """phase gates via the temporal span solver; returns (ops_with_phase, mismatch, dirty)"""
    want = J.expected_phase(eps)
    r, ins = S.solve(ops, target=want, deg=2)
    if r:
        # allow triples at every time where the arity-3 episode could fire (all times, restricted wires)
        tw = []
        for e, ep in enumerate(eps):
            if len(ep['term']) == 3:
                snaps = S.timeline(ops)
                for t in range(len(snaps)):
                    tw.append((t, tuple(range(NW))))
        r, ins = S.solve(ops, target=want, deg=3, triple_wires=tw[:400])
    if ins is None:
        return None, r, None
    new = S.insert(ops, ins)
    c, ph = C.replay(new)
    dirty = [w for w in range(NW) if c[w] != C.RM[w]]
    return new, bin(ph ^ want).count('1'), dirty


def attempt(eps, plans, seed, data_pref=True, jitter=0.0, verbose=False):
    rng = random.Random(seed)
    x = Exec(eps, plans, rng, data_pref=data_pref, jitter=jitter)
    x.verbose = verbose
    if not x.run():
        return None
    ops = x.oplist()
    new, mism, dirty = finish(ops, eps, verbose)
    if new is None or mism or dirty:
        return ('BAD', mism, dirty)
    return (model_depth(new), new)


if __name__ == '__main__':
    eps_all = J.episodes()
    sel = sys.argv[1] if len(sys.argv) > 1 else '0123'
    A = [int(a) for a in (sys.argv[2] if len(sys.argv) > 2 else '6,6,6,6').split(',')]
    iters = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    jitter = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
    eps = [eps_all[int(c)] for c in sel]
    plans = []
    for c, ep in zip(sel, eps):
        fn = 'cpfi_plan_%s_A%d.pkl' % (c, A[int(c)])
        try:
            plans.append(pickle.load(open(fn, 'rb')))
        except FileNotFoundError:
            r = P.plan(ep, A[int(c)], verbose=True)
            assert r is not None, 'no plan for episode %s at A=%d' % (c, A[int(c)])
            pickle.dump(r[1], open(fn, 'wb')); plans.append(r[1])
        print('episode %s plan: %s' % (c, dict(Counter(m[0] for m in plans[-1]))))
    best = None; fails = bad = 0
    t0 = time.time()
    for seed in range(iters):
        for dp in (True, False):
            r = attempt(eps, plans, seed, data_pref=dp, jitter=jitter if seed else 0.0, verbose=(seed == 0))
            if r is None: fails += 1; continue
            if r[0] == 'BAD': bad += 1; print('  seed %d dp %s BAD mism %s dirty %s' % (seed, dp, r[1], r[2])); continue
            d, ops = r
            if best is None or d < best[0]:
                best = (d, ops, seed, dp)
                print('  seed %d dp %s model depth %d ops %d (%.0fs)' % (seed, dp, d, len(ops), time.time() - t0), flush=True)
    print('episodes %s: fails %d bad %d' % (sel, fails, bad))
    if best:
        d, ops, seed, dp = best
        print('best model depth %d  ops %s' % (d, dict(Counter(o[0] for o in ops))))
        pickle.dump(ops, open('cpfi_exec_%s.pkl' % sel, 'wb'))
        from cpae_core import extract, sim_exact, fvec, SHAPES
        from qiskit import transpile
        qc = ops_to_qc(ops, n=18)
        tq = transpile(qc, basis_gates=['u3', 'cx'], optimization_level=2, seed_transpiler=0)
        print('opt2 depth %d cx %d' % (tq.depth(), tq.count_ops().get('cx', 0)))
        if len(sel) == 4:
            gl, gp = extract(qc)
            err, mm = sim_exact(gl, gp, fvec(SHAPES['LOGO']))
            print('sim_exact err %.1e mism %d' % (err, mm))
