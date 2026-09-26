"""Depth-faithful annealing with phase gates at EVERY level (not only the
turnaround).  Term = (level l, 2 or 3 wires): CZ/CCZ on the wire values that
exist after level l (l = LV: turnaround).  Single-wire Z on every level is
free.  Depth model: 14*LV for the Toffoli layers (prefix + mirror); a term at
level l < LV is free while it fits on wires idle in Toffoli layer l+1 (7 layers
per side, 14 total: CZ = 3, CCZ = 10); the excess and all turnaround terms are
charged.  Cost = deficiency + PEN * max(0, est_depth - BUDGET).
Usage: python3 cptz_sa3.py LV R SEED MINUTES   (MINUTES 0: stop only on exact)
Env: BUDGET (depth), PEN, INIT (sa2/sa3 pkl), CYCLE, T0, FINE.
Best -> ckpt/sa3_L<LV>_R<R>_s<seed>.pkl"""
import sys, os, time, math, pickle, random
import numpy as np
import cpte_evo as E
from cptw_mcts import Env, rand_action
from cptn_prefix import insert, member
from cptq_rank import ONES

LV, R, seed, minutes = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
BUDGET = int(os.environ.get('BUDGET', '120')); PEN = float(os.environ.get('PEN', '2'))
FINE = float(os.environ.get('FINE', '0.3'))
rng = random.Random(seed); env = Env(E.logo_bits(), LV)
basis = np.zeros((4096, 64), dtype=np.uint64); piv = np.zeros(4096, dtype=np.int64)


def play(lv):
    """states after each level (S_0 .. S_LV), products, idle mask per Toffoli layer"""
    S = env.S0.copy(); prods = list(env.prods0); states = [S.copy()]; idle = []
    for l in lv:
        used = set()
        for a, b, pa, pb, t in l:
            p = (S[a] ^ (ONES if pa else np.uint64(0))) & (S[b] ^ (ONES if pb else np.uint64(0)))
            S[t] ^= p; prods.append(p); used |= {a, b, t}
        states.append(S.copy()); idle.append([w not in used for w in range(18)])
    return states, prods, idle


def score(lv, terms):
    states, prods, idle = play(lv); nb_ = 0
    for p in prods: nb_ = insert(basis, piv, nb_, p)
    for S in states:
        for w in range(18): nb_ = insert(basis, piv, nb_, S[w])
    load = np.zeros((LV + 1, 18), dtype=np.int64)
    for l, t in terms:
        S = states[l]; v = S[t[0]] & S[t[1]]
        if len(t) == 3: v = v & S[t[2]]
        nb_ = insert(basis, piv, nb_, v)
        for w in t: load[l, w] += 10 if len(t) == 3 else 3
    dep = 14 * LV
    for l in range(LV + 1):
        cap = np.array([14 if l < LV and idle[l][w] else 0 for w in range(18)])
        dep += int(np.maximum(load[l] - cap, 0).max())
    d = int(member(basis, piv, nb_, env.Fv))
    return d, dep


def rand_term():
    return (rng.randrange(LV + 1), tuple(rng.sample(range(18), 3 if rng.random() < 0.5 else 2)))


def mut_levels(lv):
    lv = [list(l) for l in lv]; i = rng.randrange(LV); l = lv[i]; used = set()
    if l and rng.random() < FINE:
        j = rng.randrange(len(l)); a, b, pa, pb, t = l[j]
        for g in l[:j] + l[j + 1:]: used |= {g[0], g[1], g[4]}
        free = [w for w in range(18) if w not in used and w not in (a, b, t)]; m = rng.randrange(5)
        if m == 0: pa ^= 1
        elif m == 1: pb ^= 1
        elif free and m == 2: a = rng.choice(free)
        elif free and m == 3: b = rng.choice(free)
        elif free: t = rng.choice(free)
        l[j] = (a, b, pa, pb, t); return lv
    r = rng.random()
    if l and r < 0.5:
        j = rng.randrange(len(l))
        for g in l[:j] + l[j + 1:]: used |= {g[0], g[1], g[4]}
        a = rand_action(used, rng)
        if a: l[j] = a
    elif l and r < 0.7: l.pop(rng.randrange(len(l)))
    elif len(l) < 6:
        for g in l: used |= {g[0], g[1], g[4]}
        a = rand_action(used, rng)
        if a: l.append(a)
    return lv


def mut_terms(terms):
    terms = list(terms); j = rng.randrange(len(terms)); l, t = terms[j]; r = rng.random()
    if r < 0.4:
        t = list(t); k = rng.randrange(len(t)); t[k] = rng.choice([w for w in range(18) if w not in t]); terms[j] = (l, tuple(t))
    elif r < 0.7: terms[j] = (rng.randrange(LV + 1), t)
    else: terms[j] = rand_term()
    return terms


if os.environ.get('INIT'):
    d0 = pickle.load(open(os.environ['INIT'], 'rb')); cur = d0['levels']
    terms = d0['terms'] if 'terms' in d0 else [(LV, t) for t in d0['ro']]
    while len(terms) < R: terms.append(rand_term())
else: cur, terms = [[] for _ in range(LV)], [rand_term() for _ in range(R)]
def cost(d, dep): return d + PEN * max(0, dep - BUDGET)
d, dep = score(cur, terms); c = cost(d, dep); best = (c, d, dep, cur, terms)
print('[sa3 L%d R%d s%d] start deficiency %d  est depth %d  budget %d' % (LV, R, seed, d, dep, BUDGET), flush=True)
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
            pickle.dump(dict(levels=cur, terms=terms, deficiency=d, depth=dep), open('ckpt/sa3_L%d_R%d_s%d.pkl' % (LV, R, seed), 'wb'))
            if d == 0 and dep <= BUDGET: print('[sa3] EXACT within budget', flush=True); break
    if time.time() - last > 10:
        last = time.time()
        print('[sa3 L%d R%d s%d] %5.0fs it %d acc %d  cur def %d dep %d  best def %d dep %d' % (LV, R, seed, last - t0, it, acc, d, dep, best[1], best[2]), flush=True)
print('[sa3 L%d R%d s%d] final best deficiency %d depth %d' % (LV, R, seed, best[1], best[2]), flush=True)
