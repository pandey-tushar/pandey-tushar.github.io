"""Width-aware XAG annealing (function preserved exactly by every move).
State: AND nodes k with operands (A_k, B_k) = affine forms (int bitmasks: bit0
const, bits 1..12 inputs, bit 13+j AND signal j), output form Fo, and an order
(topological) of the ANDs.  Width after step i = GF(2) rank of the still-needed
operand forms restricted to the computed signals (must be <= 18 at every step).
Moves:
  basis flip  A*B = A ^ A*(A^B)  (or B ^ B*(A^B)): node k gets operands (A, A^B)
              and every later form containing bit k gets ^A (resp. ^B);
  reorder     move one AND to another position respecting dependencies.
Cost = (max width, sum of excess over 18, sum of widths).
Usage: python3 cptu_width.py FILE.v SEED MINUTES
Progress every 10 s; best state -> ckpt/xagd/width_<name>_s<seed>.pkl"""
import sys, time, random, pickle, os
from cptr_map import parse

CAP = int(os.environ.get('CAP', '18'))


def rank(vecs):
    B = {}
    for v in vecs:
        while v:
            h = v.bit_length()
            if h in B: v ^= B[h]
            else: B[h] = v; break
    return len(B)


def verify(ands, Fo, order):
    import numpy as np
    from cpae_core import SHAPES, fvec
    idx = np.arange(4096)
    sig = {0: np.ones(4096, np.uint8)}
    for i in range(12): sig[1 + i] = ((idx >> i) & 1).astype(np.uint8)
    def ev(L):
        v = np.zeros(4096, np.uint8)
        b = 0
        while L:
            if L & 1: v ^= sig[b]
            L >>= 1; b += 1
        return v
    for k in order: sig[13 + k] = ev(ands[k][0]) & ev(ands[k][1])
    return bool((ev(Fo) == fvec(SHAPES['LOGO']).astype(np.uint8)).all())


def widths(ands, order):
    nA = len(ands)
    done = (1 << 13) - 2
    out = []
    pos = {k: i for i, k in enumerate(order)}
    for i in range(nA + 1):
        if i: done |= 1 << (13 + order[i - 1])
        need = set()
        for k in order[i:]:
            for L in ands[k]:
                v = L & done & ~1
                if v: need.add(v)
        out.append(rank(sorted(need, reverse=True)))
    return out


NANC = int(os.environ.get('NANC', '6'))
EXACT = int(os.environ.get('EXACT', '0'))


def feas(ands, order):
    """exact cptu_map condition per in-place step: u1 not in span(M) (or rank M < CAP if k not needed alone)"""
    done = (1 << 13) - 2; fails = 0; exc = 0; tot = 0; prof = []
    for pos, k in enumerate(order):
        bit = 1 << (13 + k); A, B = ands[k]
        if pos >= NANC:
            dm = done | bit; need = set()
            for j in order[pos + 1:]:
                for L in ands[j]:
                    v = L & dm & ~1
                    if v: need.add(v)
            Nn = [v ^ bit for v in need if v & bit]; N0 = [v for v in need if not v & bit]
            M = N0 + [u ^ Nn[0] for u in Nn[1:]] + [A & ~1, B & ~1]
            r = rank(M)
            if Nn: bad = rank(M + [Nn[0]]) == r
            else: bad = r >= CAP
            fails += bad; exc += max(0, r - (CAP - 1)); tot += r; prof.append(r + (1 if bad else 0) * 100)
        done |= bit
    return (fails, exc, tot), prof


def pressure(ands, order):
    """values that cannot go in place need a register from creation to last use; peak overlap"""
    done = (1 << 13) - 2; pos_of = {k: i for i, k in enumerate(order)}; iv = []; fails = 0
    for pos, k in enumerate(order):
        bit = 1 << (13 + k); A, B = ands[k]
        dm = done | bit; need = set(); last = pos
        for j in order[pos + 1:]:
            for L in ands[j]:
                v = L & dm & ~1
                if v: need.add(v)
                if L & bit: last = max(last, pos_of[j])
        Nn = [v ^ bit for v in need if v & bit]; N0 = [v for v in need if not v & bit]
        M = N0 + [u ^ Nn[0] for u in Nn[1:]] + [A & ~1, B & ~1]
        r = rank(M)
        bad = (rank(M + [Nn[0]]) == r) if Nn else (r >= CAP)
        if bad: fails += 1; iv.append((pos, last))
        done |= bit
    peak = 0
    for p in range(len(order)):
        peak = max(peak, sum(1 for a, b in iv if a <= p < b))
    return (max(0, peak - NANC), peak, fails), [peak]


def cost(ands, order):
    if EXACT == 2: return pressure(ands, order)
    if EXACT: return feas(ands, order)
    w = widths(ands, order)
    return (max(w), sum(max(0, x - CAP) for x in w), sum(w)), w


def deps(ands, k):
    m = (ands[k][0] | ands[k][1]) >> 13
    return {j for j in range(len(ands)) if m >> j & 1}


def flip(ands, Fo, k, which):
    """rewrite node k: A*B = A ^ A*(A^B) (which=0) or B ^ B*(A^B) (which=1)"""
    A, B = ands[k]
    S = A if which == 0 else B
    new = list(ands)
    new[k] = (A, A ^ B) if which == 0 else (A ^ B, B)
    bit = 1 << (13 + k)
    for j in range(len(ands)):
        if j == k: continue
        a, b = new[j]
        if a & bit: a ^= S
        if b & bit: b ^= S
        new[j] = (a, b)
    if Fo & bit: Fo ^= S
    return new, Fo


def valid_order(ands, order):
    pos = {k: i for i, k in enumerate(order)}
    return all(pos[j] < pos[k] for k in order for j in deps(ands, k))


if __name__ == '__main__':
    path, seed, minutes = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
    rng = random.Random(seed)
    A0, Fo = parse(path)
    ands = [(A, B) for (_, A, B) in A0]
    nA = len(ands)
    order = list(range(nA))
    if os.environ.get('INIT'):
        d0 = pickle.load(open(os.environ['INIT'], 'rb')); ands, Fo, order = d0['ands'], d0['Fo'], d0['order']
    assert valid_order(ands, order) and verify(ands, Fo, order)
    c, w = cost(ands, order)
    best = (c, list(ands), Fo, list(order))
    print('[width] %s: ANDs %d  start cost %s  profile max %d' % (path, nA, c, max(w)), flush=True)
    T0 = float(os.environ.get('T0', '2.0'))
    t0 = time.time(); last = t0; it = acc = 0
    name = os.path.basename(path).replace('.v', '') + ('_x' if EXACT else '')
    while time.time() - t0 < minutes * 60:
        it += 1
        frac = (time.time() - t0) / (minutes * 60); T = T0 * (1 - frac) + 0.05
        if rng.random() < 0.5:
            k = rng.randrange(nA); nands, nFo = flip(ands, Fo, k, rng.randrange(2)); norder = order
        else:
            nands, nFo = ands, Fo
            k = rng.randrange(nA); i = order.index(k)
            lo = max([order.index(j) for j in deps(ands, k)] + [-1]) + 1
            hi = min([order.index(j) for j in range(nA) if k in deps(ands, j)] + [nA])
            if hi - lo <= 1: continue
            norder = [x for x in order if x != k]
            p = rng.randrange(lo, hi)
            norder.insert(p if p <= i else p - 1, k)
        nc, _ = cost(nands, norder)
        d = (nc[0] - c[0]) * 100 + (nc[1] - c[1]) * 3 + (nc[2] - c[2]) * 0.1
        if d <= 0 or rng.random() < pow(2.718, -d / T):
            ands, Fo, order, c = nands, nFo, norder, nc; acc += 1
            if c < best[0]:
                best = (c, list(ands), Fo, list(order))
                pickle.dump(dict(ands=ands, Fo=Fo, order=order, cost=c), open('ckpt/xagd/width_%s_s%d.pkl' % (name, seed), 'wb'))
        if time.time() - last > 10:
            last = time.time()
            print('[width s%d] %4.0fs it %d acc %d  current %s  best %s' % (seed, last - t0, it, acc, c, best[0]), flush=True)
    print('[width s%d] final best %s  verified %s  valid order %s' % (seed, best[0], verify(best[1], best[2], best[3]), valid_order(best[1], best[3])), flush=True)
