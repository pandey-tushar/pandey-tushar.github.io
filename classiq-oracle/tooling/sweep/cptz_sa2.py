"""Depth-faithful annealing.  cptz_sa used a readout of ALL pairs + triples of
the 18 final wire values (span rank ~1000; an exact hit could need hundreds of
CCZ).  Here the readout is an explicit list of R terms (CZ pairs / CCZ triples
on the final wires) plus free single-wire Z; depth ~ 14*LV + phase layers.
Span = {1, inputs, Toffoli products (Z-around-Toffoli), final wire values,
the R readout terms}.  Objective = deficiency (weight of F reduced against the
span; 0 = exact).  Moves: Toffoli moves as cptz_sa (incl. FINE), readout: swap
one wire of a term / replace a term.
Usage: python3 cptz_sa2.py LV R SEED MINUTES
Best -> ckpt/sa2_L<LV>_R<R>_s<seed>.pkl"""
import sys, os, time, math, pickle, random
import numpy as np
import cpte_evo as E
from cptw_mcts import Env, rand_action
from cptn_prefix import insert, member

LV, R, seed, minutes = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
rng = random.Random(seed); env = Env(E.logo_bits(), LV); FINE = float(os.environ.get('FINE', '0.3'))
basis = np.zeros((4096, 64), dtype=np.uint64); piv = np.zeros(4096, dtype=np.int64)


def to_seq(lv):
    out = []
    for l in lv: out += l + ['end']
    return out


def score(lv, ro):
    S, prods = env.play(to_seq(lv)); nb_ = 0
    for p in prods: nb_ = insert(basis, piv, nb_, p)
    for w in range(18): nb_ = insert(basis, piv, nb_, S[w])
    for t in ro:
        v = S[t[0]] & S[t[1]]
        if len(t) == 3: v = v & S[t[2]]
        nb_ = insert(basis, piv, nb_, v)
    return int(member(basis, piv, nb_, env.Fv))


def rand_term():
    return tuple(rng.sample(range(18), 3 if rng.random() < 0.6 else 2))


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


def mut_ro(ro):
    ro = list(ro); j = rng.randrange(len(ro))
    if rng.random() < 0.6:
        t = list(ro[j]); k = rng.randrange(len(t)); c = [w for w in range(18) if w not in t]; t[k] = rng.choice(c); ro[j] = tuple(t)
    else: ro[j] = rand_term()
    return ro


if os.environ.get('INIT'):
    d0 = pickle.load(open(os.environ['INIT'], 'rb')); cur, ro = d0['levels'], d0['ro']
else: cur, ro = [[] for _ in range(LV)], [rand_term() for _ in range(R)]
c = score(cur, ro); best = (c, cur, ro)
nccz = lambda ro: sum(len(t) == 3 for t in ro)
dep = 14 * LV + 10 * math.ceil(nccz(ro) / 6) + 3 * math.ceil((R - nccz(ro)) / 9)
print('[sa2 L%d R%d s%d] start deficiency %d   est. depth if exact ~%d' % (LV, R, seed, c, dep), flush=True)
T0 = float(os.environ.get('T0', '6')); t0 = last = time.time(); it = acc = 0
while time.time() - t0 < minutes * 60:
    it += 1; T = T0 * (1 - (time.time() - t0) / (minutes * 60)) + 0.3
    if R and rng.random() < 0.3: nl, nro = cur, mut_ro(ro)
    else: nl, nro = mut_levels(cur), ro
    nc = score(nl, nro)
    if nc <= c or rng.random() < math.exp(-(nc - c) / T):
        cur, ro, c = nl, nro, nc; acc += 1
        if c < best[0]:
            best = (c, cur, ro)
            pickle.dump(dict(levels=cur, ro=ro, deficiency=c), open('ckpt/sa2_L%d_R%d_s%d.pkl' % (LV, R, seed), 'wb'))
            if c == 0: print('[sa2] EXACT', flush=True); break
    if time.time() - last > 10:
        last = time.time()
        print('[sa2 L%d R%d s%d] %5.0fs it %d acc %d  cur %d  best %d' % (LV, R, seed, last - t0, it, acc, c, best[0]), flush=True)
print('[sa2 L%d R%d s%d] final best deficiency %d' % (LV, R, seed, best[0]), flush=True)
