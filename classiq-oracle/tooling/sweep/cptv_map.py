"""Mapper v3: whole-F XAG -> exact circuit on 18 wires with register clearing
and recomputation.  Wire forms are affine over signals (const, x0..x11, AND
values); S = span of the wire forms.
Per AND k (order from a cptu_width pkl):
  1. operands A, B must lie in S; missing AND signals are recomputed onto a
     clean register (recursively);
  2. target: in place (cptu_map hyperplane rule, applied to the still-satisfied
     needs) when possible, else a clean register; with no clean register, one
     register value is cleared by re-running its Toffoli (value whose next use
     is farthest; dead values first; its operands must be in S);
  3. X-conjugated Toffoli; Z before + after on the first computation of every
     AND that appears in y.  Inputs in y: Z at t=0.  Then the mirror.
Usage: python3 cptv_map.py PKL [SEED]"""
import sys, pickle, random
import numpy as np
from cpae_core import mirror, ops_to_qc, real_depth, sv_check_gp, SHAPES, fvec
from cpth_emit import replay
from cptr_map import reduce_basis, rep
from cptu_map import solve_phi

NW, ND = 18, 12
AB = 13


class Mapper:
    def __init__(self, ands, Fo, order, rng):
        self.ands, self.Fo, self.order, self.rng = ands, Fo, order, rng
        self.forms = [1 << (1 + i) for i in range(ND)] + [0] * (NW - ND)
        self.ops = [('z', i) for i in range(ND) if Fo & (1 << (1 + i))]
        self.done = (1 << AB) - 2           # signals ever computed (inputs + ANDs)
        self.undo = []
        self.phased = set(); self.ntof = 0; self.nre = 0; self.nclr = 0
        self.pos = 0

    # ---------- linear algebra helpers
    def basis(self): return reduce_basis([(i, f & ~1) for i, f in enumerate(self.forms) if f & ~1])
    def inS(self, L): return rep(self.basis(), L & ~1) is not None

    def cx(self, c, t): self.ops.append(('cx', c, t)); self.forms[t] ^= self.forms[c]

    def form_on(self, L, avoid, tgt=None):
        c = rep(self.basis(), L & ~1)
        if c is None: return None
        S = [i for i in range(NW) if c >> i & 1]
        cand = [p for p in S if p not in avoid and (p < ND or len(S) == 1)]
        temp = False
        if not cand:
            cand = [p for p in S if p not in avoid]
            if not cand or tgt in S: return None
            temp = True
        p = min(cand, key=lambda q: bin(self.forms[q]).count('1'))
        for i in S:
            if i != p: self.cx(i, p)
        if temp: self.undo.append((p, [i for i in S if i != p]))
        return p

    def flush_undo(self):
        for p, src in reversed(self.undo):
            for i in reversed(src): self.cx(i, p)
        self.undo = []

    def toffoli(self, k, a, b, t, first):
        A, B = self.ands[k]
        ph = first and bool(self.Fo & (1 << (AB + k))) and k not in self.phased
        if ph: self.ops.append(('z', t)); self.phased.add(k)
        fl = [q for q, L in ((a, A), (b, B)) if (self.forms[q] ^ L) & 1]
        self.ops.extend(('x', q) for q in fl); self.ops.append(('ccx', a, b, t)); self.ops.extend(('x', q) for q in fl)
        if ph: self.ops.append(('z', t))
        self.forms[t] ^= 1 << (AB + k); self.ntof += 1
        self.flush_undo()

    # ---------- needs / uses
    def future_needs(self):
        out = set()
        for j in self.order[self.pos + 1:]:
            for L in self.ands[j]:
                v = L & self.done & ~1
                if v: out.add(v)
        return out

    def next_use(self, m):
        bit = 1 << (AB + m)
        for p in range(self.pos, len(self.order)):
            j = self.order[p]
            if (self.ands[j][0] | self.ands[j][1]) & bit: return p
        return 10 ** 9

    # ---------- registers
    def registers(self):
        """wires holding exactly one AND signal"""
        out = []
        for i, f in enumerate(self.forms):
            g = f & ~1
            if g and g & (g - 1) == 0 and g >> AB: out.append((i, g.bit_length() - 1 - AB))
        return out

    def get_clean(self, protect, depth):
        z = [i for i in range(ND, NW) if self.forms[i] & ~1 == 0 and i not in protect]
        if z: return z[0]
        regs = [(self.next_use(m), i, m) for i, m in self.registers() if i not in protect]
        regs.sort(reverse=True)
        for nu, i, m in regs:
            if self.clear(i, m, protect | {i}, depth + 1): return i
        return None

    def clear(self, r, m, protect, depth):
        A, B = self.ands[m]
        if depth > 6: return False
        if not (self.inS(A) and self.inS(B)):
            if not (self.ensure(A, protect, depth + 1) and self.ensure(B, protect, depth + 1)): return False
            if self.forms[r] & ~1 != 1 << (AB + m): return False
        # clearing removes signal m from S; A, B must not depend on the wire r
        save = (list(self.forms), len(self.ops))
        a = self.form_on(A, protect, r); b = self.form_on(B, protect | {a}, r) if a is not None else None
        if a is None or b is None or r in (a, b):
            self.forms, self.ops[save[1]:] = save[0], []; return False
        self.toffoli(m, a, b, r, False); self.nclr += 1
        assert self.forms[r] & ~1 == 0
        return True

    def ensure(self, L, protect, depth):
        """make L & ~1 lie in S by recomputing a set of AND signals (solved by linear algebra)"""
        if self.inS(L): return True
        if depth > 12: return False
        Bs = self.basis()
        def red(v):
            for pb, bv, bc in Bs:
                if v & pb: v ^= bv
            return v
        r = red(L & ~1)
        cand = []
        for m in range(len(self.ands)):
            bit = 1 << (AB + m)
            if not (self.done & bit): continue
            rm = red(bit)
            if rm: cand.append((m, rm))
        B2 = reduce_basis([(i, rm) for i, (m, rm) in enumerate(cand)])
        c = rep(B2, r)
        if c is None: return False
        need = [cand[i][0] for i in range(len(cand)) if c >> i & 1]
        for m in sorted(need, key=lambda m: self.order.index(m)):
            if self.inS(1 << (AB + m)): continue
            if not self.recompute(m, protect, depth + 1): return False
        return self.inS(L)

    def recompute(self, m, protect, depth):
        A, B = self.ands[m]
        if not self.ensure(A, protect, depth) or not self.ensure(B, protect, depth): return False
        t = self.get_clean(protect, depth)
        if t is None: return False
        a = self.form_on(A, protect | {t}, t)
        b = self.form_on(B, protect | {t, a}, t) if a is not None else None
        if a is None or b is None: return False
        self.toffoli(m, a, b, t, True); self.nre += 1
        return True

    # ---------- main step
    def step(self, k):
        A, B = self.ands[k]; bit = 1 << (AB + k)
        if not self.ensure(A, set(), 0) or not self.ensure(B, set(), 0): return 'operands of AND %d' % k
        first = k not in self.phased
        self.done |= bit
        need = [v for v in self.future_needs() if self.inS(v & ~bit) or v & bit]
        Nn = [v ^ bit for v in need if v & bit and self.inS(v ^ bit)]
        N0 = [v for v in need if not v & bit and self.inS(v)]
        Bs = self.basis()
        regf = [self.forms[i] & ~1 for i in range(ND, NW) if self.forms[i] & ~1]
        live = [m for m in range(len(self.ands)) if self.done >> (AB + m) & 1 and m != k and
                (self.next_use(m) < 10 ** 9 or any(r[1] == m for r in self.registers()))]
        prot = [L & self.done & ~1 for m in live for L in self.ands[m]]
        prot = [v for v in prot if v and self.inS(v)]
        M = N0 + [u ^ Nn[0] for u in Nn[1:]] + [A & ~1, B & ~1] + regf + prot
        Mc = [rep(Bs, v) for v in M]
        got = None
        if all(c is not None for c in Mc):
            fcands = [Nn[0]] if Nn else [self.forms[i] & ~1 for i in range(ND)]
            for f in fcands:
                fc = rep(Bs, f)
                if fc is None: continue
                phi = solve_phi(Mc, fc)
                if phi is None: continue
                S = [i for i in range(NW) if fc >> i & 1]
                ts = [i for i in S if phi >> i & 1 and i < ND]
                if ts: got = (f, ts[0]); break
        if got is not None:
            f, t = got
            fc = rep(Bs, f)
            S = [i for i in range(NW) if fc >> i & 1]
            for i in S:
                if i != t: self.cx(i, t)
            Bs2 = self.basis(); phi = solve_phi([rep(Bs2, v) for v in M], rep(Bs2, f))
            for j in range(NW):
                if j != t and phi >> j & 1:
                    assert j < ND
                    self.cx(t, j)
            a = self.form_on(A, {t}, t); b = self.form_on(B, {t, a}, t) if a is not None else None
            if a is None or b is None: return 'operand forming (in place) AND %d' % k
        else:
            prot = set()
            t = self.get_clean(prot, 0)
            if t is None: return 'no clean register for AND %d' % k
            if not self.ensure(A, {t}, 0) or not self.ensure(B, {t}, 0): return 'operands lost at AND %d' % k
            a = self.form_on(A, {t}, t); b = self.form_on(B, {t, a}, t) if a is not None else None
            if a is None or b is None: return 'operand forming (register) AND %d' % k
        self.toffoli(k, a, b, t, first)
        return None

    def run(self):
        for self.pos, k in enumerate(self.order):
            err = self.step(k)
            if err: return err
        # every AND in y must have been phased
        miss = [k for k in range(len(self.ands)) if self.Fo >> (AB + k) & 1 and k not in self.phased]
        return 'unphased %s' % miss if miss else None


if __name__ == '__main__':
    d = pickle.load(open(sys.argv[1], 'rb')); seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    mp = Mapper(d['ands'], d['Fo'], d['order'], random.Random(seed))
    err = mp.run()
    print('%s: ANDs %d  map: %s  toffolis %d (recompute %d, clear %d)  cx %d' %
          (sys.argv[1], len(d['ands']), err or 'ok', mp.ntof, mp.nre, mp.nclr, sum(o[0] == 'cx' for o in mp.ops)), flush=True)
    if err: sys.exit(1)
    ops = mp.ops
    perm = [o for o in ops if o[0] not in ('z', 'cz')]
    full = ops + mirror(perm)
    F = fvec(SHAPES['LOGO']).astype(np.int64)
    mism, ident = replay(full, F)
    print('classical: phase mismatches %d  identity %s' % (mism, ident), flush=True)
    qc = ops_to_qc(full)
    dd, cc = real_depth(qc)
    print('real depth %d  cx %d' % (dd, cc), flush=True)
    if mism == 0 and ident:
        err, leak = sv_check_gp(qc, 'LOGO'); print('statevector err %.1e leak %.1e' % (err, leak), flush=True)
        pickle.dump(full, open(sys.argv[1].replace('.pkl', '_v3ops.pkl'), 'wb'))
