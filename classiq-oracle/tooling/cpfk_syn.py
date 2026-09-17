"""CP-FK step 1: per-side exact synthesis of the 10 basis functions.

One side = 9 wires (local 0-5 raw bits, 6-8 zero ancillas), exact 64-bit
contents.  Terms are synthesised in order; each term ends with its function
sitting exactly on some wire (recorded as a cz marker); the body is
mirrored globally at the end.  Moves: ccx with either control polarity
(X gates emitted around it) targeting any wire, plus CX assembly.  Beam
search per term; a finishing macro closes the term when the target lies
in span(contents, 1) plus at most two pair products.
"""
import sys, random, time, pickle, itertools
sys.path.insert(0, '/home/user/classiq-challenge')
from cpfk_side import M64, ONE, LIN, COLS, ROWS, THR, Span64, thresholds_of, intermediates, tab
from cpae_core import PROF

NWL = 9


def basis_pair():
    """x basis = the 10 distinct nonzero columns c_i (functions of x);
    y basis = b_i(y) = [column(y) == c_i].  F = sum_i c_i(x) b_i(y) exactly."""
    order = []; seen = {}
    for y in range(64):
        c = COLS[y]
        if c and c not in seen:
            seen[c] = len(order); order.append(c)
    xf = order
    yf = [sum(1 << y for y in range(64) if COLS[y] == c) for c in order]
    return xf, yf


def basis_diff():
    """x = nested differences d_i, y = cumulative sums; still exact."""
    xf, yf = basis_pair()
    # nests: indices grouped by containment chains: sort by weight within each nest
    groups = []
    for i, c in enumerate(xf):
        placed = False
        for g in groups:
            if all((c & xf[j]) in (0, c, xf[j]) for j in g) and any((c & xf[j]) for j in g):
                g.append(i); placed = True; break
        if not placed: groups.append([i])
    dx, dy = [], []
    for g in groups:
        g = sorted(g, key=lambda i: bin(xf[i]).count('1'))
        for k, i in enumerate(g):
            prev = xf[g[k - 1]] if k else 0
            dx.append(xf[i] ^ prev)
            dy.append(0)
        # cumulative y: d_k pairs with sum_{j>=k} b_j
        for k, i in enumerate(g):
            s = 0
            for j in g[k:]: s ^= yf[j]
            dy[len(dy) - len(g) + k] = s
    return dx, dy


class State:
    def __init__(self):
        self.cont = list(LIN) + [0, 0, 0]
        self.lay = [0] * NWL
        self.ops = []          # ('ccx',a,b,t) / ('cx',a,t) / ('x',t) / ('cz',t) marker
        self.nand = 0
    def clone(self):
        s = State.__new__(State)
        s.cont = list(self.cont); s.lay = list(self.lay); s.ops = list(self.ops); s.nand = self.nand
        return s
    def place(self, op):
        prof = PROF[op[0]]; qs = op[1:]
        st = 0
        for j, w in enumerate(qs): st = max(st, self.lay[w] - prof[j][0] + 2)
        for j, w in enumerate(qs): self.lay[w] = st + prof[j][-1] - 1
    def emit(self, op):
        k = op[0]
        if k == 'x':
            self.cont[op[1]] ^= ONE
        elif k == 'cx':
            self.cont[op[2]] ^= self.cont[op[1]]; self.place(op)
        elif k == 'ccx':
            a, b, t = op[1:]; self.cont[t] ^= self.cont[a] & self.cont[b]; self.place(op); self.nand += 1
        elif k == 'cz':
            pass
        self.ops.append(op)
    def toffoli(self, a, pa, b, pb, t):
        if pa: self.emit(('x', a))
        if pb: self.emit(('x', b))
        self.emit(('ccx', a, b, t))
        if pa: self.emit(('x', a))
        if pb: self.emit(('x', b))
    def depth(self): return max(self.lay)
    def span0(self):
        return Span64([ONE] + [c for c in self.cont if c])
    def products(self):
        """(value, a, pa, b, pb) for all pair products with polarities."""
        out = []
        for a in range(NWL):
            for b in range(a + 1, NWL):
                for pa in (0, 1):
                    for pb in (0, 1):
                        v = (self.cont[a] ^ (ONE if pa else 0)) & (self.cont[b] ^ (ONE if pb else 0))
                        if v and v != ONE: out.append((v, a, pa, b, pb))
        return out


def assemble(st, f, t, extra=()):
    """make wire t hold f exactly by CX from other wires, given f ^ cont[t] in
    span(other contents, 1).  Returns True on success."""
    need = f ^ st.cont[t]
    if need == 0: return True
    # greedy elimination over the other wires' contents
    srcs = [(st.cont[w], w) for w in range(NWL) if w != t and st.cont[w]]
    S = Span64(); tags = {}
    piv = {}; combo = {}
    for v, w in srcs:
        r, c = v, 1 << w
        while r:
            p = r & -r
            if p in piv: r ^= piv[p]; c ^= combo[p]
            else: piv[p] = r; combo[p] = c; break
    r, c = need, 0
    while r:
        p = r & -r
        if p in piv: r ^= piv[p]; c ^= combo[p]
        else: break
    if r == ONE:
        st.emit(('x', t)); r = 0
    if r: return False
    for w in range(NWL):
        if (c >> w) & 1: st.emit(('cx', w, t))
    return True


def k_needed(st, f, prods, S0, kmax=2):
    """min number of pair products p such that f in S0 + span(p's); returns (k, prods_used)."""
    if S0.reduce(f) == 0: return 0, []
    if kmax < 1: return 9, None
    red = [(S0.reduce(p[0]), p) for p in prods]
    red = [(r, p) for r, p in red if r]
    rf = S0.reduce(f)
    byval = {}
    for r, p in red: byval.setdefault(r, p)
    if rf in byval: return 1, [byval[rf]]
    if kmax < 2: return 9, None
    for r, p in red:
        q = byval.get(rf ^ r)
        if q is not None: return 2, [p, q]
    return 9, None


def finish(st, f, used, avoid_busy=True):
    """apply the products in `used` onto one target wire, then assemble f there."""
    ctrl = set()
    for v, a, pa, b, pb in used: ctrl |= {a, b}
    cands = [t for t in range(NWL) if t not in ctrl]
    # prefer clean ancillas / least busy
    cands.sort(key=lambda t: (st.lay[t], 0 if st.cont[t] in (0,) else 1))
    for t in cands:
        s2 = st.clone()
        for v, a, pa, b, pb in used: s2.toffoli(a, pa, b, pb, t)
        if assemble(s2, f, t):
            return s2, t
    return None, None


def synth_term(st, f, S_I, beam=6, steps=6, rng=None, verbose=False):
    """beam search from state st until f can be finished; returns new state with cz marker."""
    rng = rng or random.Random(0)
    def evaluate(s):
        S0 = s.span0(); prods = s.products()
        k, used = k_needed(s, f, prods, S0, 2)
        # secondary: coverage of intermediate space by current contents
        UI = Span64(list(S_I.piv.values()))
        n0 = len(UI)
        for c in s.cont: UI.add(c)
        covI = n0 + 7 - (len(UI) - n0)     # higher = more contents inside I (roughly)
        clean = sum(1 for w in range(NWL) if s.cont[w] == 0 or s.cont[w] in LIN)
        return k, used, covI, clean
    front = [st]
    best = None
    for step in range(steps + 1):
        scored = []
        for s in front:
            k, used, covI, clean = evaluate(s)
            if k <= 2:
                s2, t = finish(s, f, used)
                if s2 is not None:
                    cand = (s2.nand, s2.depth())
                    if best is None or cand < best[0]:
                        best = (cand, s2, t)
            scored.append(((-k, covI, clean, -s.depth(), rng.random()), s))
        if best is not None and step >= 1:
            break
        if step == steps: break
        # expand
        nxt = []
        for sc, s in sorted(scored, key=lambda x: x[0], reverse=True)[:beam]:
            S0 = s.span0()
            moves = []
            for v, a, pa, b, pb in s.products():
                if S0.reduce(v) == 0: continue            # product adds nothing new
                for t in range(NWL):
                    if t in (a, b): continue
                    moves.append((v, a, pa, b, pb, t))
            rng.shuffle(moves)
            seen = set()
            for v, a, pa, b, pb, t in moves:
                key = (v ^ s.cont[t], t)
                if key in seen: continue
                seen.add(key)
                s2 = s.clone(); s2.toffoli(a, pa, b, pb, t)
                nxt.append(s2)
        # score children cheaply (k with kmax=1 first) and keep beam
        sc2 = []
        for s in nxt:
            S0 = s.span0(); prods = s.products()
            k, used = k_needed(s, f, prods, S0, 1)
            UI = Span64(list(S_I.piv.values())); n0 = len(UI)
            for c in s.cont: UI.add(c)
            covI = -(len(UI) - n0)
            sc2.append(((-k, covI, -s.nand, -s.depth(), rng.random()), s))
        sc2.sort(key=lambda x: x[0], reverse=True)
        front = [s for _, s in sc2[:beam * 4]]
        if verbose: print('    step %d: %d children, best k %d' % (step + 1, len(nxt), -sc2[0][0][0]), flush=True)
    if best is None: return None
    (_, s2, t) = best
    s2.emit(('cz', t))
    return s2


def synth_side(funcs, side, order=None, beam=6, steps=6, seed=0, verbose=True):
    rng = random.Random(seed)
    base = COLS if side == 'x' else ROWS
    S_I = Span64(intermediates(thresholds_of(base)) + [THR[p] for p in thresholds_of(base)] + LIN + [ONE])
    st = State()
    order = order or list(range(len(funcs)))
    for i in order:
        f = funcs[i]
        t0 = time.time()
        s2 = synth_term(st, f, S_I, beam=beam, steps=steps, rng=rng)
        if s2 is None:
            if verbose: print('  term %d FAILED' % i, flush=True)
            return None
        if verbose:
            print('  term %d: +%d ands (total %d) depth %d  %.0fs' % (i, s2.nand - st.nand, s2.nand, s2.depth(), time.time() - t0), flush=True)
        st = s2
    return st


if __name__ == '__main__':
    side = sys.argv[1] if len(sys.argv) > 1 else 'x'
    which = sys.argv[2] if len(sys.argv) > 2 else 'pair'
    beam = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    xf, yf = basis_pair() if which == 'pair' else basis_diff()
    funcs = xf if side == 'x' else yf
    print('side %s basis %s: %d functions, weights %s' % (side, which, len(funcs), [bin(f).count('1') for f in funcs]), flush=True)
    st = synth_side(funcs, side, beam=beam, seed=seed)
    if st:
        print('BODY: %d ands, depth %d, ops %d' % (st.nand, st.depth(), len(st.ops)))
        pickle.dump(st.ops, open('cpfk_syn_%s_%s_b%d_s%d.pkl' % (side, which, beam, seed), 'wb'))
