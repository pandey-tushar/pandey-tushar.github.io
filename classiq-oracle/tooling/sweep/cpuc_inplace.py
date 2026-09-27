"""CP-UE: in-place code transform on 9 wires (6 data + 3 clean), no uncompute.
Goal: a level circuit (CX layer + <= MAXT Toffolis per level, sa4 depth model)
after which 4 of the 9 wires hold the 4 code bits of one side (cpuc_code810.pkl:
joint 4+4 code, orbit (8,10); phase stage on the 8 code wires measured 63/47),
up to complement.  Data wires are consumed (junk = their final values); the
transform is a bijection on 9 bits so no scratch is needed beyond the 3 clean.
Truth tables are 64-bit ints over the 64 side inputs.
Cost = W * mismatched bits (best assignment of 4 targets to distinct wires)
+ est depth (2 * sum level depths counted by the caller; here forward only).
Usage: python3 cpuc_inplace.py SIDE(x|y) LV SEED MINUTES   (MINUTES 0: forever)
Env: W (200), MAXT (3), T0 (3), CYCLE (min, 0 = linear), INIT (pkl).
Best -> ckpt/inpl_<side>_L<LV>_s<seed>.pkl, progress every 10 s."""
import sys, os, time, math, pickle, random
from itertools import permutations

side, LV, seed, minutes = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
W = float(os.environ.get('W', '200')); MAXT = int(os.environ.get('MAXT', '3'))
NW = 9; ONES = (1 << 64) - 1
rng = random.Random(seed)
D = pickle.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cpuc_code810.pkl'), 'rb'))
T = D['tx'] if side == 'x' else D['ty']
S0 = [sum(1 << v for v in range(64) if (v >> i) & 1) for i in range(6)] + [0, 0, 0]


def level_depth(tofs):
    if not tofs: return 0
    rd = {}
    for a, b, pa, pb, t in tofs:
        rd[a] = rd.get(a, 0) + 1; rd[b] = rd.get(b, 0) + 1
    d = 7 + max(rd.values()) - 1
    if any(rd[a] > 1 and rd[b] > 1 for a, b, _, _, _ in tofs): d += 5
    return d


def play(lv):
    S = list(S0); dep = 0
    for cxs, tofs in lv:
        for s, d in cxs: S[d] ^= S[s]
        Sl = list(S)
        for a, b, pa, pb, t in tofs:
            S[t] ^= (Sl[a] ^ (ONES if pa else 0)) & (Sl[b] ^ (ONES if pb else 0))
        dep += level_depth(tofs) + (1 if cxs else 0)
    return S, dep


def assign(S):
    C = [[min(bin(S[w] ^ t).count('1'), bin(S[w] ^ t ^ ONES).count('1')) for w in range(NW)] for t in T]
    best = (10 ** 9, None)
    for ws in permutations(range(NW), 4):
        c = C[0][ws[0]] + C[1][ws[1]] + C[2][ws[2]] + C[3][ws[3]]
        if c < best[0]: best = (c, ws)
    return best


def score(lv):
    S, dep = play(lv); m, ws = assign(S)
    return m, dep, ws


def rand_tof(tofs):
    tg = {g[4] for g in tofs}; ctl = {g[0] for g in tofs} | {g[1] for g in tofs}
    tfree = [w for w in range(NW) if w not in tg and w not in ctl]
    if not tfree: return None
    t = rng.choice(tfree); cfree = [w for w in range(NW) if w != t and w not in tg]
    if len(cfree) < 2: return None
    a, b = rng.sample(cfree, 2)
    return (a, b, rng.randrange(2), rng.randrange(2), t)


def mutate(lv):
    lv = [(list(c), list(t)) for c, t in lv]; i = rng.randrange(LV); cxs, tofs = lv[i]; r = rng.random()
    if r < 0.25:
        used = {w for s, d in cxs for w in (s, d)}
        if cxs and rng.random() < 0.5: cxs.pop(rng.randrange(len(cxs)))
        else:
            free = [w for w in range(NW) if w not in used]
            if len(free) >= 2: s, d = rng.sample(free, 2); cxs.append((s, d))
        return lv
    if tofs and r < 0.5:
        j = rng.randrange(len(tofs)); a, b, pa, pb, t = tofs[j]; m = rng.randrange(4)
        others = tofs[:j] + tofs[j + 1:]; tg = {g[4] for g in others}
        if m == 0: pa ^= 1
        elif m == 1: pb ^= 1
        else:
            cand = [w for w in range(NW) if w != t and w not in tg and w not in (a, b)]
            if cand:
                if m == 2: a = rng.choice(cand)
                else: b = rng.choice(cand)
        tofs[j] = (a, b, pa, pb, t); return lv
    if tofs and r < 0.7:
        j = rng.randrange(len(tofs)); g = rand_tof(tofs[:j] + tofs[j + 1:])
        if g: tofs[j] = g
    elif tofs and r < 0.8: tofs.pop(rng.randrange(len(tofs)))
    elif len(tofs) < MAXT:
        g = rand_tof(tofs)
        if g: tofs.append(g)
    return lv


if os.environ.get('INIT'):
    cur = pickle.load(open(os.environ['INIT'], 'rb'))['levels']
    cur = [(list(c), list(t)) for c, t in cur][:LV] + [([], []) for _ in range(LV - len(cur))]
else: cur = [([], []) for _ in range(LV)]
def cost(m, dep): return W * m + dep
m, dep, ws = score(cur); c = cost(m, dep); best = (c, m, dep, ws, cur)
name = 'ckpt/inpl_%s_L%d_s%d.pkl' % (side, LV, seed)
print('[inpl %s L%d s%d] start mismatch %d depth %d' % (side, LV, seed, m, dep), flush=True)
T0 = float(os.environ.get('T0', '3')); CYCLE = float(os.environ.get('CYCLE', '0')); cyc = 0
t0 = last = time.time(); it = acc = 0
while minutes == 0 or time.time() - t0 < minutes * 60:
    it += 1
    if CYCLE:
        ph = (time.time() - t0) / (CYCLE * 60); Tm = T0 * (1 - (ph % 1)) + 0.3
        if int(ph) != cyc: cyc = int(ph); c, m, dep, ws, cur = best
    else: Tm = T0 * (1 - (time.time() - t0) / (minutes * 60)) + 0.3
    nl = mutate(cur); nm, ndep, nws = score(nl); nc = cost(nm, ndep)
    if nc <= c or rng.random() < math.exp(-(nc - c) / Tm):
        cur, c, m, dep, ws = nl, nc, nm, ndep, nws; acc += 1
        if c < best[0]:
            best = (c, m, dep, ws, cur)
            pickle.dump(dict(levels=cur, mismatch=m, depth=dep, wires=ws, side=side), open(name, 'wb'))
            if m == 0: print('[inpl %s s%d] EXACT depth %d wires %s at %.0fs' % (side, seed, dep, ws, time.time() - t0), flush=True)
    if time.time() - last > 10:
        last = time.time(); nt = sum(len(t) for _, t in cur)
        print('[inpl %s L%d s%d] %5.0fs it %d acc %d  cur mis %d dep %d (tof %d)  best mis %d dep %d' % (side, LV, seed, last - t0, it, acc, m, dep, nt, best[1], best[2]), flush=True)
print('[inpl %s L%d s%d] final best mismatch %d depth %d wires %s' % (side, LV, seed, best[1], best[2], best[3]), flush=True)
