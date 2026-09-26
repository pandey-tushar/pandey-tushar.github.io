"""Simulated annealing on the MCTS objective (cptw_mcts.Env): fixed LV levels,
<= 6 Toffolis per level on disjoint wires; reward = -deficiency (0 = exact).
Moves: replace one gate by a random legal one in its level, delete a gate, add
a gate.  Init: random or a cptw_mcts checkpoint (INIT env).
Usage: python3 cptz_sa.py LV SEED MINUTES
Progress every 10 s; best -> ckpt/sa_L<LV>_s<seed>.pkl"""
import sys, os, time, math, pickle, random
import cpte_evo as E
from cptw_mcts import Env, rand_action

LV, seed, minutes = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
rng = random.Random(seed); env = Env(E.logo_bits(), LV)


def to_levels(seq):
    lv = [[]]
    for a in seq:
        if a == 'end': lv.append([])
        else: lv[-1].append(a)
    lv = lv[:LV]
    while len(lv) < LV: lv.append([])
    return lv


def to_seq(lv):
    out = []
    for l in lv: out += l + ['end']
    return out


def mutate(lv):
    lv = [list(l) for l in lv]; i = rng.randrange(LV); l = lv[i]; r = rng.random()
    if FINE and l and rng.random() < FINE:
        j = rng.randrange(len(l)); a, b, pa, pb, t = l[j]; used = set()
        for g in l[:j] + l[j + 1:]: used |= {g[0], g[1], g[4]}
        free = [w for w in range(18) if w not in used and w not in (a, b, t)]
        m = rng.randrange(5)
        if m == 0: pa ^= 1
        elif m == 1: pb ^= 1
        elif free and m == 2: a = rng.choice(free)
        elif free and m == 3: b = rng.choice(free)
        elif free: t = rng.choice(free)
        l[j] = (a, b, pa, pb, t); return lv
    if l and r < 0.5:
        j = rng.randrange(len(l)); used = set()
        for g in l[:j] + l[j + 1:]: used |= {g[0], g[1], g[4]}
        a = rand_action(used, rng)
        if a: l[j] = a
    elif l and r < 0.7:
        l.pop(rng.randrange(len(l)))
    elif len(l) < 6:
        used = set()
        for g in l: used |= {g[0], g[1], g[4]}
        a = rand_action(used, rng)
        if a: l.append(a)
    return lv


if os.environ.get('INIT'): cur = to_levels(pickle.load(open(os.environ['INIT'], 'rb'))['seq'])
else: cur = [[] for _ in range(LV)]
c = -env.reward(to_seq(cur)); best = (c, cur)
FINE = float(os.environ.get('FINE', '0')); KP = int(os.environ.get('KP', '1')); REHEAT = int(os.environ.get('REHEAT', '0')); last_imp = 0
T0 = float(os.environ.get('T0', '6')); t0 = last = time.time(); it = acc = 0
print('[sa L%d s%d] start deficiency %d' % (LV, seed, c), flush=True)
while time.time() - t0 < minutes * 60:
    it += 1; T = T0 * (1 - (time.time() - t0) / (minutes * 60)) + 0.3
    cands = [mutate(cur) for _ in range(KP)]
    sc = [-env.reward(to_seq(x)) for x in cands]; j = min(range(KP), key=sc.__getitem__); nl, nc = cands[j], sc[j]
    if REHEAT and it - last_imp > REHEAT: cur, c = best[1], best[0]; last_imp = it
    if nc <= c or rng.random() < math.exp(-(nc - c) / T):
        cur, c = nl, nc; acc += 1
        if c < best[0]:
            best = (c, cur); last_imp = it; pickle.dump(dict(seq=to_seq(cur), reward=-c), open('ckpt/sa_L%d_s%d%s.pkl' % (LV, seed, os.environ.get('TAG', '')), 'wb'))
            if c == 0: print('[sa] EXACT', flush=True); break
    if time.time() - last > 10:
        last = time.time()
        print('[sa L%d s%d] %5.0fs it %d acc %d  cur %d  best %d' % (LV, seed, last - t0, it, acc, c, best[0]), flush=True)
print('[sa L%d s%d] final best deficiency %d' % (LV, seed, best[0]), flush=True)
