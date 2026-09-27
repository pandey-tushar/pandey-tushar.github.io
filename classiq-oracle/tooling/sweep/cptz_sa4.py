"""sa3 model + CX layer per level + shared controls (XAG-complete per-level model).
Level l = CX layer (disjoint pairs (src, dst), depth 1 if non-empty) then a
Toffoli layer: targets distinct, a target is not a control in the same layer,
controls may be shared.  Toffoli layer depth = 7 + (max readers of one wire - 1)
+ 5 if some Toffoli has both controls shared (one of them must sit in slot b;
measured: extra slot-a reader +1, slot-b reader +5).  Terms (level l, 2-3
wires) = CZ/CCZ on the values after level l; free while they fit on wires idle
in level l+1 (capacity 2 * that level's depth), the rest and the turnaround are
charged.  Est depth = 2 * sum(level depths) + charged term load.  Free Z on
every wire at every level.  Cost = deficiency + PEN * max(0, depth - BUDGET).
Usage: python3 cptz_sa4.py LV R SEED MINUTES   (MINUTES 0: stop only on exact)
Env: BUDGET (150), PEN (2), MAXT (Toffolis per level, 12), INIT (sa2/sa3/sa4 pkl),
CYCLE, T0, FINE.  Best -> ckpt/sa4_L<LV>_R<R>_s<seed>.pkl"""
import sys, os, time, math, pickle, random
import numpy as np
import cpte_evo as E
from cptw_mcts import Env
from cptn_prefix import insert, member
from cptq_rank import ONES

LV, R, seed, minutes = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
BUDGET = int(os.environ.get('BUDGET', '150')); PEN = float(os.environ.get('PEN', '2'))
FINE = float(os.environ.get('FINE', '0.3')); MAXT = int(os.environ.get('MAXT', '12'))
rng = random.Random(seed); env = Env(E.logo_bits(), LV)
basis = np.zeros((4096, 64), dtype=np.uint64); piv = np.zeros(4096, dtype=np.int64)


def level_depth(tofs):
    if not tofs: return 0
    rd = {}
    for a, b, pa, pb, t in tofs:
        rd[a] = rd.get(a, 0) + 1; rd[b] = rd.get(b, 0) + 1
    d = 7 + max(rd.values()) - 1
    if any(rd[a] > 1 and rd[b] > 1 for a, b, _, _, _ in tofs): d += 5
    return d


def play(lv):
    """lv: list of (cxs, tofs).  states after each level, products, idle masks, level depths"""
    S = env.S0.copy(); prods = list(env.prods0); states = [S.copy()]; idle = []; deps = []
    for cxs, tofs in lv:
        used = set()
        for s, d in cxs: S[d] ^= S[s]; used |= {s, d}
        Sl = S.copy()
        for a, b, pa, pb, t in tofs:
            p = (Sl[a] ^ (ONES if pa else np.uint64(0))) & (Sl[b] ^ (ONES if pb else np.uint64(0)))
            S[t] ^= p; prods.append(p); used |= {a, b, t}
        states.append(S.copy()); idle.append([w not in used for w in range(18)])
        deps.append(level_depth(tofs) + (1 if cxs else 0))
    return states, prods, idle, deps


def score(lv, terms):
    states, prods, idle, deps = play(lv); nb_ = 0
    for p in prods: nb_ = insert(basis, piv, nb_, p)
    for S in states:
        for w in range(18): nb_ = insert(basis, piv, nb_, S[w])
    load = np.zeros((LV + 1, 18), dtype=np.int64)
    for l, t in terms:
        S = states[l]; v = S[t[0]] & S[t[1]]
        if len(t) == 3: v = v & S[t[2]]
        nb_ = insert(basis, piv, nb_, v)
        for w in t: load[l, w] += 10 if len(t) == 3 else 3
    dep = 2 * sum(deps)
    for l in range(LV + 1):
        cap = np.array([2 * deps[l] if l < LV and idle[l][w] else 0 for w in range(18)])
        dep += int(np.maximum(load[l] - cap, 0).max())
    return int(member(basis, piv, nb_, env.Fv)), dep


def rand_term():
    return (rng.randrange(LV + 1), tuple(rng.sample(range(18), 3 if rng.random() < 0.5 else 2)))


def rand_tof(tofs):
    tg = {g[4] for g in tofs}; ctl = {g[0] for g in tofs} | {g[1] for g in tofs}
    tfree = [w for w in range(18) if w not in tg and w not in ctl]
    if not tfree: return None
    t = rng.choice(tfree); cfree = [w for w in range(18) if w != t and w not in tg]
    if len(cfree) < 2: return None
    a, b = rng.sample(cfree, 2)
    return (a, b, rng.randrange(2), rng.randrange(2), t)


def mut_levels(lv):
    lv = [(list(c), list(t)) for c, t in lv]; i = rng.randrange(LV); cxs, tofs = lv[i]; r = rng.random()
    if r < 0.25:                                    # CX layer move
        used = {w for s, d in cxs for w in (s, d)}
        if cxs and rng.random() < 0.5: cxs.pop(rng.randrange(len(cxs)))
        else:
            free = [w for w in range(18) if w not in used]
            if len(free) >= 2: s, d = rng.sample(free, 2); cxs.append((s, d))
        return lv
    if tofs and rng.random() < FINE:
        j = rng.randrange(len(tofs)); a, b, pa, pb, t = tofs[j]; m = rng.randrange(4)
        others = tofs[:j] + tofs[j + 1:]; tg = {g[4] for g in others}
        if m == 0: pa ^= 1
        elif m == 1: pb ^= 1
        else:
            cand = [w for w in range(18) if w != t and w not in tg and w not in (a, b)]
            if cand:
                if m == 2: a = rng.choice(cand)
                else: b = rng.choice(cand)
        tofs[j] = (a, b, pa, pb, t); return lv
    if tofs and r < 0.55:
        j = rng.randrange(len(tofs)); g = rand_tof(tofs[:j] + tofs[j + 1:])
        if g: tofs[j] = g
    elif tofs and r < 0.7: tofs.pop(rng.randrange(len(tofs)))
    elif len(tofs) < MAXT:
        g = rand_tof(tofs)
        if g: tofs.append(g)
    return lv


def mut_terms(terms):
    terms = list(terms); j = rng.randrange(len(terms)); l, t = terms[j]; r = rng.random()
    if r < 0.4:
        t = list(t); k = rng.randrange(len(t)); t[k] = rng.choice([w for w in range(18) if w not in t]); terms[j] = (l, tuple(t))
    elif r < 0.7: terms[j] = (rng.randrange(LV + 1), t)
    else: terms[j] = rand_term()
    return terms


if os.environ.get('INIT'):
    d0 = pickle.load(open(os.environ['INIT'], 'rb')); lv0 = d0['levels']
    cur = [(list(l[0]), list(l[1])) if isinstance(l, tuple) else ([], list(l)) for l in lv0]
    cur = cur[:LV] + [([], []) for _ in range(LV - len(cur))]
    terms = list(d0['terms']) if 'terms' in d0 else [(LV, t) for t in d0['ro']]
    terms = [(min(l, LV), t) for l, t in terms][:R]
    while len(terms) < R: terms.append(rand_term())
else: cur, terms = [([], []) for _ in range(LV)], [rand_term() for _ in range(R)]
def cost(d, dep): return d + PEN * max(0, dep - BUDGET)
d, dep = score(cur, terms); c = cost(d, dep); best = (c, d, dep, cur, terms)
print('[sa4 L%d R%d s%d] start deficiency %d  est depth %d  budget %d' % (LV, R, seed, d, dep, BUDGET), flush=True)
CYCLE = float(os.environ.get('CYCLE', '0')); cyc = 0
T0 = float(os.environ.get('T0', '6')); t0 = last = time.time(); it = acc = 0
while minutes == 0 or time.time() - t0 < minutes * 60:
    it += 1
    if CYCLE:
        ph = (time.time() - t0) / (CYCLE * 60); T = T0 * (1 - (ph % 1)) + 0.3
        if int(ph) != cyc: cyc = int(ph); c, d, dep, cur, terms = best
    else: T = T0 * (1 - (time.time() - t0) / (minutes * 60)) + 0.3
    if rng.random() < 0.4: nl, nt = cur, mut_terms(terms)
    else: nl, nt = mut_levels(cur), terms
    nd, ndep = score(nl, nt); nc = cost(nd, ndep)
    if nc <= c or rng.random() < math.exp(-(nc - c) / T):
        cur, terms, c, d, dep = nl, nt, nc, nd, ndep; acc += 1
        if c < best[0]:
            best = (c, d, dep, cur, terms)
            pickle.dump(dict(levels=cur, terms=terms, deficiency=d, depth=dep), open('ckpt/sa4_L%d_R%d_s%d.pkl' % (LV, R, seed), 'wb'))
            if d == 0 and dep <= BUDGET: print('[sa4] EXACT within budget', flush=True); break
    if time.time() - last > 10:
        last = time.time(); nt_ = sum(len(t) for _, t in cur); ncx = sum(len(cx) for cx, _ in cur)
        print('[sa4 L%d R%d s%d] %5.0fs it %d acc %d  cur def %d dep %d (tof %d cx %d)  best def %d dep %d' % (LV, R, seed, last - t0, it, acc, d, dep, nt_, ncx, best[1], best[2]), flush=True)
print('[sa4 L%d R%d s%d] final best deficiency %d depth %d' % (LV, R, seed, best[1], best[2]), flush=True)
