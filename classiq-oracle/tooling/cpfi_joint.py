"""CP-FI: joint list scheduler of independent phase-term episodes on 18
wires with exact wire contents.

Every wire holds a 70-bit linear form (bits 0..11 raw, 12+k node k, 69
const).  A node fires when each operand form is materialised on a distinct
wire (directly, or assembled by CX from wires whose contents XOR to it,
undone afterwards) and a free wire (ancilla holding 0, data wire holding its
own raw bit) takes the node bit.  Uncompute = the same gate again.  Each
term's cone is computed, its phase gate fired, and everything uncomputed;
nodes may be recomputed (registers are traded for gates).  Episodes share
the raw wires read-only and are interleaved by earliest start time under
rigid gate profiles (cpae_core.PROF).  No junk: a pure raw read waits until
the hosting node is gone.  Random restarts; the result is verified by exact
replay and scored by real transpile depth.
"""
import sys, random, time, itertools, pickle
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfg_model as M
from cpae_core import PROF, model_depth
import cpfh_core as C

N, TERMS, lev, preds, succ, NN = M.N, M.TERMS, M.lev, M.preds, M.succ, M.NN
NW = 18
CST = 1 << 69
MASK69 = (1 << 69) - 1
RAW = [1 << w if w < 12 else 0 for w in range(NW)]
KIND = {2: 'ccx', 3: 'c3x'}


def bits(v):
    return [i for i in range(70) if v >> i & 1]


def episodes():
    eps = []
    for ti, t in enumerate(TERMS):
        top = set()
        for v in t:
            top |= {b - 12 for b in bits(v) if 12 <= b < 69}
        seen = set(); st = list(top)
        while st:
            k = st.pop()
            if k in seen: continue
            seen.add(k); st.extend(preds[k])
        cone = sorted(seen)
        h = {}
        for k in sorted(cone, key=lambda k: -lev[k]):
            h[k] = (13 if len(N[k]) == 3 else 7) + max([h[s] for s in succ[k] if s in seen], default=2)
        eps.append(dict(ti=ti, term=list(t), top=sorted(top), cone=cone, cset=seen, h=h))
    return eps


class Sched:
    def __init__(self, eps, rng, anc_pref=True, jitter=0.0):
        self.eps = eps; self.rng = rng; self.jitter = jitter
        self.cont = list(RAW); self.busy = [0.0] * NW
        self.host = {}          # node -> wire
        self.phased = set()     # episode indices done
        self.ops = []           # (start, op)
        self.anc_pref = anc_pref; self.verbose = False; self.recent_freed = set()
        self.nodes_of = {k: e for e in range(len(eps)) for k in eps[e]['cone']}

    # ---- wire helpers
    def free_wires(self):
        return [w for w in range(NW) if self.cont[w] == RAW[w]]

    def free_anc(self):
        return [w for w in range(12, NW) if self.cont[w] == 0]

    def pending_forms(self):
        """every form still to be read: unfired nodes, live nodes (their
        uncompute), unphased terms."""
        out = []
        for e, ep in enumerate(self.eps):
            if e not in self.phased:
                out.extend(ep['term'])
                for k in ep['cone']:
                    out.extend(N[k])
            else:
                for k in ep['cone']:
                    if k in self.host:
                        out.extend(N[k])
        return out

    def natural(self, w, k):
        """hosting node k on data wire w keeps every pending read
        materialisable: no pending form reads x_w without n_k."""
        nb = 1 << (12 + k)
        e = self.nodes_of[k]
        cs = self.eps[e]['cset']
        forms = list(self.eps[e]['term'])
        for j in cs:                     # every read in the episode: both x_w and n_k, or neither
            forms.extend(N[j])
        # while n_k sits on w every form must read x_w and n_k together or neither
        for f in forms:
            if bool((f >> w) & 1) != bool(f & nb):
                return False
        return True

    def place(self, op, t0=0.0):
        """reserve wires for op with rigid profile starting no earlier than t0."""
        name, qs = op[0], op[1:]
        prof = PROF[name]
        S = t0
        for j, w in enumerate(qs):
            S = max(S, self.busy[w] - prof[j][0] + 1)
        for j, w in enumerate(qs):
            self.busy[w] = S + prof[j][-1] - 1
        self.ops.append((S, op))
        return S

    def apply(self, op):
        k, q = op[0], op[1:]
        if k == 'x':
            self.cont[q[0]] ^= CST
        elif k == 'cx':
            self.cont[q[1]] ^= self.cont[q[0]]
        elif k in ('ccx', 'c3x'):
            pass            # node bit handled by caller
        # cz/ccz: nothing

    # ---- materialisation
    def find_assembly_all(self, f, avoid_t, avoid_s, maxopts=6):
        """all (target, sources, xflip) options for form f, best first."""
        fm = f & MASK69
        opts = []
        for w in range(NW):
            if w in avoid_t or w in avoid_s: continue
            if (self.cont[w] & MASK69) == fm:
                opts.append(((0, self.busy[w]), w, [], ((self.cont[w] ^ f) >> 69) & 1))
        RAWB = (1 << 12) - 1
        cands = [w for w in range(NW) if w not in avoid_s and (self.cont[w] & MASK69)
                 and ((self.cont[w] & MASK69) & ~(fm | RAWB)) == 0]
        lazy = getattr(self, 'lazy', False)
        def add_combo(combo):
            acc = 0
            for w in combo: acc ^= self.cont[w] & MASK69
            if acc != fm: return
            for tgt in combo:
                if tgt in avoid_t: continue
                if lazy and tgt >= 12 and self.cont[tgt] == 0: continue
                srcs = [w for w in combo if w != tgt]
                accf = 0
                for w in combo: accf ^= self.cont[w]
                opts.append(((len(srcs), max(self.busy[w] for w in combo)), tgt, srcs, ((accf ^ f) >> 69) & 1))
        # GF(2) elimination fallback for wide forms (several pivot orders)
        def solve(order):
            piv = {}
            for w in order:
                v = self.cont[w] & MASK69; cb = 1 << w
                while v:
                    p = v & -v
                    if p in piv:
                        v ^= piv[p][0]; cb ^= piv[p][1]
                    else:
                        piv[p] = (v, cb); break
            v = fm; cb = 0
            while v:
                p = v & -v
                if p not in piv: return None
                v ^= piv[p][0]; cb ^= piv[p][1]
            return [w for w in range(NW) if cb >> w & 1]
        for r in (2, 3, 4, 5, 6, 7):
            if len(opts) >= maxopts: break
            if r >= 4:
                seen = set()
                for t in range(6):
                    order = list(cands)
                    if t: random.Random(t).shuffle(order)
                    sol = solve(order)
                    if sol and tuple(sol) not in seen:
                        seen.add(tuple(sol)); add_combo(tuple(sol))
                break
            for combo in itertools.combinations(cands, r):
                acc = 0
                for w in combo: acc ^= self.cont[w] & MASK69
                if acc != fm: continue
                for tgt in combo:
                    if tgt in avoid_t: continue
                    if lazy and tgt >= 12 and self.cont[tgt] == 0: continue
                    srcs = [w for w in combo if w != tgt]
                    accf = 0
                    for w in combo: accf ^= self.cont[w]
                    opts.append(((len(srcs), max(self.busy[w] for w in combo)), tgt, srcs, ((accf ^ f) >> 69) & 1))
        opts.sort(key=lambda o: o[0])
        return [(t, s, x) for _, t, s, x in opts[:maxopts]]

    def find_assembly(self, f, avoid_t, avoid_s):
        o = self.find_assembly_all(f, avoid_t, avoid_s, maxopts=1)
        return o[0] if o else None

    def materialise(self, forms, avoid):
        """-> list of (wire, sources, xflip), one per form on distinct wires, or
        None.  Backtracks over assembly targets so that a wire needed as a
        source by a later form is not consumed as a target by an earlier one."""
        n = len(forms)
        out = []
        def rec(i, avoid_t, avoid_s):
            if i == n: return True
            for a in self.find_assembly_all(forms[i], avoid_t, avoid_s):
                out.append(a)
                at = avoid_t | {a[0]}
                as_ = avoid_s | ({a[0]} if a[1] else set())
                if rec(i + 1, at, as_): return True
                out.pop()
            return False
        return out if rec(0, set(), set(avoid)) else None

    def emit_pre(self, mats):
        for (w, srcs, xf) in mats:
            for s in srcs:
                self.place(('cx', s, w)); self.apply(('cx', s, w))
        for (w, srcs, xf) in mats:
            if xf:
                self.place(('x', w)); self.apply(('x', w))

    def emit_post(self, mats):
        lazy = getattr(self, 'lazy', False)
        RAWBITS = (1 << 12) - 1
        def affine(w):
            return (self.cont[w] & MASK69 & ~RAWBITS) == 0
        keep = set()
        if lazy:
            for (w, srcs, xf) in mats:
                if w < 12 and affine(w) and all(affine(s) for s in srcs):
                    keep.add(w)          # pure-raw assembly on a data wire: leave it
        for (w, srcs, xf) in reversed(mats):
            if xf and w not in keep:
                self.place(('x', w)); self.apply(('x', w))
        for (w, srcs, xf) in reversed(mats):
            if w in keep: continue
            for s in reversed(srcs):
                self.place(('cx', s, w)); self.apply(('cx', s, w))

    def restore(self):
        """return every wire to its raw content by CX / X (contents must be
        affine in the raw bits, i.e. no node bits left)."""
        assert all((self.cont[w] & MASK69 & ~((1 << 12) - 1)) == 0 for w in range(NW)), 'node bits left'
        # ancillas first: clear to 0 using data wires as sources
        for w in range(NW):
            if self.cont[w] & CST:
                self.place(('x', w)); self.apply(('x', w))
        # Gaussian elimination on the 12x12 data block: make wire w hold x_w
        for w in range(12):
            if (self.cont[w] >> w) & 1 == 0:
                # find a wire holding x_w in its content (with other bits) and add it in
                src = next(v for v in range(NW) if v != w and (self.cont[v] >> w) & 1)
                self.place(('cx', src, w)); self.apply(('cx', src, w))
        # now every data wire has its own bit; eliminate the others
        changed = True
        while changed:
            changed = False
            for w in range(12):
                for b in range(12):
                    if b != w and (self.cont[w] >> b) & 1:
                        self.place(('cx', b, w)); self.apply(('cx', b, w)); changed = True
        for w in range(12, NW):
            c = self.cont[w]
            for b in range(12):
                if (c >> b) & 1:
                    self.place(('cx', b, w)); self.apply(('cx', b, w))
        assert all(self.cont[w] == RAW[w] for w in range(NW)), 'restore failed'

    # ---- actions
    def fire(self, k, uncompute=False, dry=False, tgt=None, e=None):
        """compute (or uncompute) node k.  Returns start time or None.
        tgt: explicit target wire for a compute (must be free)."""
        if e is None: e = self.nodes_of[k]
        hk = (e, k) if getattr(self, 'host_by_ep', False) else k
        forms = N[k]
        want = tgt
        if uncompute:
            tgt = self.host[hk]
        else:
            tgt = None
            if want is not None and self.cont[want] != RAW[want]:
                return None
        mats = self.materialise(forms, {tgt} if tgt is not None else ({want} if want is not None else set()))
        if mats is None: return None
        if tgt is None:
            used = {m[0] for m in mats} | {w for m in mats for w in m[1]}
            if want is not None:
                if want in used: return None
                tgt = want
            else:
                frees = [w for w in self.free_wires() if w not in used]
                anc = [w for w in frees if w >= 12]
                data = [w for w in frees if w < 12 and self.natural(w, k)]
                frees = anc + data if self.anc_pref else data + anc
                if not frees: return None
                if self.jitter and len(frees) > 1 and self.rng.random() < 0.3:
                    tgt = self.rng.choice(frees)
                else:
                    tgt = min(frees, key=lambda w: (0 if w in anc else 1, self.busy[w], w))
        if dry:
            return max([self.busy[tgt]] + [self.busy[m[0]] for m in mats] + [self.busy[w] for m in mats for w in m[1]])
        self.emit_pre(mats)
        op = (KIND[len(forms)],) + tuple(m[0] for m in mats) + (tgt,)
        S = self.place(op)
        self.cont[tgt] ^= 1 << (12 + k)
        self.emit_post(mats)
        if uncompute:
            del self.host[hk]
        else:
            self.host[hk] = tgt
        return S

    def phase(self, e, dry=False):
        ep = self.eps[e]
        mats = self.materialise(ep['term'], set())
        if mats is None: return None
        if dry:
            return max([self.busy[m[0]] for m in mats] + [self.busy[w] for m in mats for w in m[1]])
        self.emit_pre(mats)
        op = (('z', 'cz', 'ccz')[len(mats) - 1],) + tuple(m[0] for m in mats)
        S = self.place(op)
        self.emit_post(mats)
        self.phased.add(e)
        return S

    # ---- driver
    def candidates(self):
        cands = []
        for e, ep in enumerate(self.eps):
            cs = ep['cset']
            if e in self.phased:
                # uncompute nodes with no live successor
                for k in ep['cone']:
                    if k in self.host and not any(s in self.host for s in succ[k] if s in cs):
                        if all(p in self.host or lev[p] < 0 for p in preds[k]):
                            cands.append(('u', k, e))
                        else:
                            # recompute missing preds first
                            for p in preds[k]:
                                if p not in self.host and all(q in self.host for q in preds[p]):
                                    cands.append(('c', p, e))
                continue
            if all(t in self.host for t in ep['top']):
                cands.append(('p', None, e))
            for k in ep['cone']:
                if k not in self.host and all(p in self.host for p in preds[k]) and \
                        (k in ep['top'] or any(s not in self.host for s in succ[k] if s in cs)):
                    cands.append(('c', k, e))
                elif k in self.host and k not in ep['top'] and all(p in self.host for p in preds[k]) \
                        and len(self.free_anc()) <= 1:
                    cands.append(('u', k, e))       # early free under register pressure
        return cands

    def run(self, max_steps=3000):
        steps = 0; idle = 0
        while steps < max_steps:
            if len(self.phased) == len(self.eps) and not self.host:
                return True
            cands = self.candidates()
            scored = []
            nfree = len(self.free_anc())
            for (a, k, e) in cands:
                if a == 'p':
                    t = self.phase(e, dry=True)
                elif a == 'c':
                    t = self.fire(k, dry=True)
                else:
                    t = self.fire(k, uncompute=True, dry=True)
                if t is None: continue
                ep = self.eps[e]
                if a == 'c':
                    pri = -ep['h'][k]
                    if nfree <= 1: pri += 50          # register pressure: prefer freeing
                elif a == 'u':
                    pri = 0 if e in self.phased else (-40 if nfree <= 1 else 20)
                else:
                    pri = -100
                scored.append((t + self.rng.random() * self.jitter, pri, self.rng.random(), a, k, e))
            if scored and all(s[3] == 'u' and s[5] not in self.phased for s in scored) is False:
                # computes or phases available: drop pre-phase pressure uncomputes unless nothing else fires
                keep = [s for s in scored if not (s[3] == 'u' and s[5] not in self.phased)]
                if keep: scored = keep
            if not scored:
                if self.verbose:
                    print('    STUCK host %s phased %s cands %s free_anc %s' % (self.host, self.phased, cands, self.free_anc()))
                    print('    cont:', [(w, bits(self.cont[w])) for w in range(NW) if self.cont[w] != RAW[w]])
                return False
            scored.sort()
            scored = [s for s in scored if not (s[3] == 'c' and s[4] in self.recent_freed)] or scored
            _, _, _, a, k, e = scored[0]
            if a == 'p':
                r = self.phase(e); self.recent_freed.clear()
            elif a == 'c':
                r = self.fire(k); self.recent_freed.clear()
            else:
                r = self.fire(k, uncompute=True)
                if e not in self.phased: self.recent_freed.add(k)
            if r is None:
                return False
            steps += 1
        if self.verbose:
            print('    STEP LIMIT host %s phased %s' % (self.host, self.phased))
        return False

    def oplist(self):
        return [op for _, op in self.ops]        # logical order (per-wire order respected)


import cpeu_dag as U
_NM = U.load()[2]

def expected_phase(eps):
    ph = 0
    for ep in eps:
        m = C.FULL
        for v in ep['term']:
            m &= U.value(v, _NM)
        ph ^= m
    return ph

def verify(ops, eps=None):
    c, ph = C.replay(ops)
    dirty = [w for w in range(NW) if c[w] != C.RM[w]]
    want = C.F if eps is None else expected_phase(eps)
    return bin(ph ^ want).count('1'), dirty


def attempt(eps, seed, jitter=0.0, anc_pref=True):
    rng = random.Random(seed)
    s = Sched(eps, rng, anc_pref=anc_pref, jitter=jitter)
    s.verbose = (seed == 0)
    ok = s.run()
    if not ok:
        return None
    ops = s.oplist()
    mism, dirty = verify(ops, eps)
    if mism or dirty:
        return ('BAD', mism, dirty, ops)
    return (model_depth(ops), ops)


if __name__ == '__main__':
    eps = episodes()
    sel = sys.argv[1] if len(sys.argv) > 1 else '0123'
    eps = [eps[int(c)] for c in sel]
    iters = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    jitter = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    best = None; fails = 0; bad = 0
    t0 = time.time()
    for seed in range(iters):
        r = attempt(eps, seed, jitter=jitter if seed else 0.0)
        if r is None: fails += 1; continue
        if r[0] == 'BAD': bad += 1; print('  seed %d BAD mismatch %d dirty %s' % (seed, r[1], r[2])); continue
        d, ops = r
        if best is None or d < best[0]:
            best = (d, ops, seed)
            print('  seed %d model depth %d ops %d (%.0fs)' % (seed, d, len(ops), time.time() - t0), flush=True)
    print('episodes %s: %d/%d schedules, %d fails, %d bad' % (sel, iters - fails - bad, iters, fails, bad))
    if best:
        d, ops, seed = best
        from collections import Counter
        print('best seed %d model depth %d ops %s' % (seed, d, dict(Counter(o[0] for o in ops))))
        pickle.dump(ops, open('cpfi_joint_%s.pkl' % sel, 'wb'))
        if len(sel) == 4:
            from cpae_core import ops_to_qc, extract, sim_exact, fvec, SHAPES
            from qiskit import transpile
            qc = ops_to_qc(ops, n=18)
            gl, gp = extract(qc)
            err, mm = sim_exact(gl, gp, fvec(SHAPES['LOGO']))
            tq = transpile(qc, basis_gates=['u3', 'cx'], optimization_level=2, seed_transpiler=0)
            print('sim_exact err %.1e mism %d | opt2 depth %d cx %d' % (err, mm, tq.depth(), tq.count_ops().get('cx', 0)))
