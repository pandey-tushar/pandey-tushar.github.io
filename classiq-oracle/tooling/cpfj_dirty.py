"""CP-FJ: junk-tolerant dirty-target compilation of phase-term cones.

Every wire holds an exact 4096-bit truth table.  A node fires as a Toffoli
whose target is ANY wire that is not one of its controls (least busy wins),
so no wire ever needs to be clean and nothing is uncomputed inside the body;
the target keeps its old content XORed with the product.  Multi-constituent
operand forms are assembled by CX onto one of their home wires (optionally
undone right after the Toffoli).  The body is mirrored exactly, and the
temporal phase-span solver chooses the z/cz/ccz insertions that make the
accumulated phase equal to the target function, absorbing the junk.
Success is measured by whether the solver finds an exact solution and by
the transpiled depth.
"""
import sys, random, time, pickle, itertools
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfg_model as M
import cpfh_core as C
import cpfi_span as S
import cpfi_joint as J
from cpae_core import PROF, mirror, extract, sim_exact, fvec, SHAPES
from cpfi_exec import ops_to_qc, model_depth

N, lev, preds, succ = M.N, M.lev, M.preds, M.succ
NW = 18
CST = 1 << 69


def bits(v): return [i for i in range(69) if v >> i & 1]


class Dirty:
    def __init__(self, rng, undo=True, keep_x=True, protect=True, jitter=0.0, target_pool=None):
        self.rng = rng; self.undo = undo; self.keep_x = keep_x; self.protect = protect
        self.jitter = jitter
        self.cont = C.init(); self.lay = [0] * NW
        self.host = {}          # node -> wire
        self.ops = []
        self.pool = list(range(NW)) if target_pool is None else list(target_pool)
        self.safe = False; self.unfired = set(); self.term_forms = []

    def emit(self, op):
        self.ops.append(op)
        C.apply(self.cont, op)
        name, qs = op[0], op[1:]
        if name == 'x':
            return
        prof = PROF[name]
        st = 0
        for j, w in enumerate(qs):
            st = max(st, self.lay[w] - prof[j][0] + 1)
        for j, w in enumerate(qs):
            self.lay[w] = st + prof[j][-1] - 1

    def home(self, b):
        return b if b < 12 else self.host[b - 12]

    def materialise(self, form, taken, sources):
        """put `form` on a wire; returns (wire, undo_ops).  `sources` = home
        wires that other forms of the same node still need to read purely:
        never pick one of them as the accumulator."""
        const = bool(form & CST)
        homes = [self.home(b) for b in bits(form)]
        if len(homes) == 1 and not const:
            return (homes[0], []) if homes[0] not in taken else None
        cands = [w for w in homes if w not in taken and w not in sources]
        if not cands:
            cands = [w for w in homes if w not in taken]
        if not cands:
            return None
        acc = min(cands, key=lambda w: (self.lay[w] + self.jitter * self.rng.random(), self.rng.random()))
        undo = []
        for w in homes:
            if w != acc:
                self.emit(('cx', w, acc)); undo.append(('cx', w, acc))
        if const and self.keep_x:
            self.emit(('x', acc)); undo.append(('x', acc))
        return acc, undo

    def legal(self, k, w):
        """may node k be stacked onto wire w?  ancillas: always.  data wire w:
        only if no unfired node reads x_w purely, or every unfired reader of
        x_w also carries n_k and every reader of n_k carries x_w (both-or-
        neither), and the same for the term forms."""
        if not self.safe or w >= 12:
            return True
        bw, bk = 1 << w, 1 << (12 + k)
        forms = [f for j in self.unfired if j != k for f in N[j]] + self.term_forms
        for f in forms:
            if bool(f & bw) != bool(f & bk):
                return False
        return True

    def fire(self, k, live_needed):
        forms = N[k]
        homes = [[self.home(b) for b in bits(f)] for f in forms]
        taken = set(); undo_all = []; got = {}
        # forms with a single constituent (no assembly) first; their home is taken
        order = sorted(range(len(forms)), key=lambda i: (len(homes[i]) > 1 or bool(forms[i] & CST), self.rng.random()))
        for i in order:
            sources = {h for j in range(len(forms)) if j != i and j not in got for h in homes[j]}
            r = self.materialise(forms[i], taken, sources)
            if r is None:
                return False
            w, undo = r
            got[i] = w; taken.add(w); undo_all = undo + undo_all
        ctrls = [got[i] for i in range(len(forms))]
        # target: least busy wire not a control (and not hosting a live needed node)
        avoid = set(ctrls)
        if self.protect:
            avoid |= {self.host[j] for j in live_needed if j in self.host}
        tc = [w for w in self.pool if w not in avoid and self.legal(k, w)]
        if not tc:
            tc = [w for w in range(12, NW) if w not in set(ctrls)]
        tgt = min(tc, key=lambda w: (self.lay[w] + self.jitter * self.rng.random(), self.rng.random()))
        self.emit((('ccx', 'c3x')[len(ctrls) - 2],) + tuple(ctrls) + (tgt,))
        self.host[k] = tgt
        if self.undo:
            for op in undo_all:
                self.emit(op)
        return True


def compile_eps(eps, rng, safe=True, **kw):
    d = Dirty(rng, **kw)
    d.safe = safe
    d.term_forms = [v for ep in eps for v in ep['term']]
    cones = [set(ep['cone']) for ep in eps]
    allnodes = sorted({k for c in cones for k in c})
    done = set(); d.unfired = set(allnodes)
    # global list order: ready nodes, priority by height (longest remaining chain), random jitter
    h = {}
    for ep in eps:
        h.update(ep['h'])
    dfs = kw.pop('dfs', False) if False else getattr(rng, 'dfs', False)
    order = []
    if dfs:
        seen = set()
        def visit(k):
            if k in seen: return
            for p in sorted(preds[k], key=lambda p: (-len([q for q in allnodes if q == p]), -h[p])):
                visit(p)
            seen.add(k); order.append(k)
        for ep in eps:
            for t in sorted(ep['top'], key=lambda t: -h[t]):
                visit(t)
    while len(done) < len(allnodes):
        if dfs:
            k = order[len(done)]
        else:
            ready = [k for k in allnodes if k not in done and all(p in done for p in preds[k])]
            ready.sort(key=lambda k: (-h[k], rng.random()))
            k = ready[0]
        # live needed: nodes done whose successors (in cones) are not all done, plus top nodes
        needed = {j for j in done if any(s in allnodes and s not in done for s in succ[j])}
        needed |= {j for ep in eps for j in ep['top']}
        if not d.fire(k, needed):
            return None
        done.add(k); d.unfired.discard(k)
    # assemble every term form on a wire at the end of the body (mirrored later)
    allforms = [v for ep in eps for v in ep['term']]
    homes = [[d.home(b) for b in bits(f)] for f in allforms]
    taken = set(); got = {}
    order = sorted(range(len(allforms)), key=lambda i: (len(homes[i]) > 1 or bool(allforms[i] & CST), rng.random()))
    for i in order:
        sources = {h for j in range(len(allforms)) if j != i and j not in got for h in homes[j]}
        r = d.materialise(allforms[i], taken, sources)
        if r is None:
            return None
        got[i] = r[0]; taken.add(r[0])
    d.term_hosts = [[got[i] for i in range(len(allforms)) if allforms[i] in ep['term']] for ep in eps]
    body = list(d.ops)
    # term wires (for phase)
    tw = []
    for ep in eps:
        ws = []
        for v in ep['term']:
            ws.append(sorted({d.home(b) for b in bits(v)}))
        tw.append(ws)
    return body, tw, d


def phase_wires(d, eps):
    """wires whose contents the phase must read: hosts of term forms."""
    out = []
    for ep in eps:
        s = set()
        for v in ep['term']:
            s |= {d.home(b) for b in bits(v)}
        out.append(sorted(s))
    return out


def solve_for(body, eps, d, extra_triples=0, rng=None):
    ops = body + mirror(body)
    target = J.expected_phase(eps)
    tri = set()
    for ws in phase_wires(d, eps):
        for c in itertools.combinations(ws, 3):
            tri.add(c)
    # also all triples among the hosts of the top nodes + their raw partners (cheap)
    tw = [(t, ws) for t in range(len(ops) + 1) for ws in tri]
    tw += [(len(body), ws) for ws in itertools.combinations(range(NW), 3)]
    r, ins = S.solve(ops, target=target, deg=3, triple_wires=tw)
    return r, ins, ops


def attempt(eps, seed, **kw):
    rng = random.Random(seed)
    rng.dfs = kw.pop('dfs', False)
    res = compile_eps(eps, rng, **kw)
    if res is None:
        return None
    body, tw, d = res
    r, ins, ops = solve_for(body, eps, d)
    if r:
        return ('res', r, model_depth(ops), len(body))
    full = S.insert(ops, ins)
    return ('ok', model_depth(full), full)


def opt2(ops):
    from qiskit import transpile
    t = transpile(ops_to_qc(ops, n=18), basis_gates=['u3', 'cx'], optimization_level=2)
    return t.depth(), t.count_ops().get('cx', 0)


def verify(ops, eps=None):
    import numpy as np
    gl, gp = extract(ops_to_qc(ops, n=18))
    if eps is None:
        f = fvec(SHAPES['LOGO'])
    else:
        ph = J.expected_phase(eps)
        f = np.array([(ph >> i) & 1 for i in range(4096)])
    err, mm = sim_exact(gl, gp, f)
    return err, mm


if __name__ == '__main__':
    eps_all = J.episodes()
    sel = [int(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 and sys.argv[1] != 'all' else [0, 1, 2, 3]
    iters = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    undo = (sys.argv[3] != 'noundo') if len(sys.argv) > 3 else True
    keep_x = (sys.argv[4] != 'nox') if len(sys.argv) > 4 else True
    protect = (sys.argv[5] != 'noprot') if len(sys.argv) > 5 else True
    dfs = (sys.argv[6] == 'dfs') if len(sys.argv) > 6 else False
    eps = [eps_all[e] for e in sel]
    print('episodes %s cones %s undo %s keep_x %s protect %s' % (sel, [len(ep['cone']) for ep in eps], undo, keep_x, protect), flush=True)
    best = None; nok = 0; resid = []
    t0 = time.time()
    for seed in range(iters):
        r = attempt(eps, seed, undo=undo, keep_x=keep_x, protect=protect, jitter=1.5, dfs=dfs)
        if r is None:
            continue
        if r[0] == 'res':
            resid.append(r[1]); continue
        nok += 1
        if best is None or r[1] < best[1]:
            best = r
            print('  seed %d model %d ops %d' % (seed, r[1], len(r[2])), flush=True)
    print('iters %d ok %d residuals(min/median) %s  %.0fs' % (iters, nok, (min(resid), sorted(resid)[len(resid)//2]) if resid else None, time.time() - t0))
    if best:
        full = best[2]
        print('best model %d opt2 %s verify %s' % (best[1], opt2(full), verify(full, eps)))
        pickle.dump(full, open('cpfj_dirty_%s.pkl' % '_'.join(map(str, sel)), 'wb'))
