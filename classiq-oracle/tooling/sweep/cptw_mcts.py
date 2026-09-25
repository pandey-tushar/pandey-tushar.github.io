"""MCTS (UCT, progressive widening) over Toffoli placements inside a fixed
depth budget: LV levels, up to 6 Toffolis per level on disjoint wires (18
wires).  Terminal reward = -deficiency: weight of the target reduced against
the GF(2) span of {1, inputs, Toffoli products, pairs + triples of the final
wire values} (cptq_rank.deficiency); 0 = exact oracle within the budget.
Rollouts: random legal completion.  Single-player: node value = best reward
seen below it (plus mean for UCT).
Usage: python3 cptw_mcts.py MODE(plant|logo) LV SEED MINUTES
Progress every 10 s; best sequence -> ckpt/mcts_<mode>_L<LV>_s<seed>.pkl"""
import sys, time, math, pickle, random
import numpy as np
import cpte_evo as E
from cptq_rank import deficiency, ONES

NW = 18


def legal(used):
    free = [w for w in range(NW) if w not in used]
    return free


def rand_action(used, rng):
    free = legal(used)
    if len(free) < 3: return None
    a, b, t = rng.sample(free, 3)
    return (a, b, rng.randrange(2), rng.randrange(2), t)


class Env:
    def __init__(self, Fv, LV):
        self.Fv, self.LV = Fv, LV
        self.basis = np.zeros((4096, 64), dtype=np.uint64); self.piv = np.zeros(4096, dtype=np.int64)
        self.S0 = E.init_state(); self.mon = None
        self.prods0 = [np.full(64, ONES)] + [self.S0[i].copy() for i in range(12)]

    def play(self, seq):
        """seq: list of actions; 'end' closes a level.  returns (S, prods)"""
        S = self.S0.copy(); prods = list(self.prods0); Sl = S.copy(); used = set(); lv = 0
        for act in seq:
            if act == 'end':
                lv += 1; Sl = S.copy(); used = set(); continue
            a, b, pa, pb, t = act
            p = (Sl[a] ^ (ONES if pa else np.uint64(0))) & (Sl[b] ^ (ONES if pb else np.uint64(0)))
            S[t] ^= p; prods.append(p); used |= {a, b, t}
        return S, prods

    def reward(self, seq):
        S, prods = self.play(seq)
        d, _ = deficiency(S, prods, self.Fv, self.basis, self.piv)
        return -int(d)

    @staticmethod
    def status(seq):
        lv = seq.count('end'); used = set(); n = 0
        for act in seq[len(seq) - seq[::-1].index('end'):] if 'end' in seq else seq:
            if act != 'end': used |= {act[0], act[1], act[4]}; n += 1
        return lv, used, n


BETA = float(__import__('os').environ.get('BETA', '0'))
_cache = {}


def unpack(v): return ((v[:, None] >> np.arange(64, dtype=np.uint64)) & np.uint64(1)).astype(np.uint8).reshape(-1)
_IDX = np.arange(4096); _DEG = np.array([bin(i).count('1') for i in range(4096)])


def _anf(t):
    a = t.copy(); h = 1
    while h < 4096:
        a = a.reshape(-1, 2 * h); a[:, h:] ^= a[:, :h]; a = a.reshape(-1); h *= 2
    return a


def scores(env, key, Sl):
    """softmax weights over (a, b, pa, pb) for the level whose start state is Sl"""
    if key in _cache: return _cache[key]
    if env.mon is None: env.mon = _IDX[_anf(unpack(env.Fv)) == 1]
    W = [unpack(Sl[w]) for w in range(NW)]
    acts, sc = [], []
    for a in range(NW):
        if not W[a].any(): continue
        for b in range(a + 1, NW):
            if not W[b].any(): continue
            for pa in range(2):
                for pb in range(2):
                    p = (W[a] ^ pa) & (W[b] ^ pb)
                    if not p.any() or p.all(): continue
                    pm = _IDX[_anf(p) == 1]; lead = pm[_DEG[pm].argmax()]
                    acts.append((a, b, pa, pb)); sc.append(((env.mon & lead) == lead).mean())
    sc = np.array(sc); sc = (sc - sc.mean()) / (sc.std() + 1e-9)
    w = np.exp(BETA * sc); w /= w.sum()
    _cache[key] = (acts, np.cumsum(w))
    return _cache[key]


def guided_action(env, seq, used, rng):
    if BETA == 0: return rand_action(used, rng)
    ends = [i for i, x in enumerate(seq) if x == 'end']
    pre = seq[:ends[-1] + 1] if ends else []
    key = tuple(pre)
    if key not in _cache:
        S, _ = env.play(pre); scores(env, key, S)
    acts, cw = _cache[key]
    for _ in range(40):
        a, b, pa, pb = acts[int(np.searchsorted(cw, rng.random() * cw[-1]))]
        if a in used or b in used: continue
        free = [w for w in range(NW) if w not in used and w not in (a, b)]
        if not free: return None
        return (a, b, pa, pb, rng.choice(free))
    return rand_action(used, rng)


class Node:
    __slots__ = ('kids', 'n', 'best', 'tot', 'tried')
    def __init__(self): self.kids = {}; self.n = 0; self.best = -1e9; self.tot = 0.0; self.tried = 0


def terminal(seq, LV): return seq.count('end') >= LV


def rollout(env, seq, rng):
    seq = list(seq)
    while not terminal(seq, env.LV):
        lv, used, n = Env.status(seq)
        act = guided_action(env, seq, used, rng) if n < 6 else None
        seq.append(act if act is not None else 'end')
    return env.reward(seq), seq


def search(env, minutes, rng, tag):
    root = Node(); best = (-1e9, None); t0 = time.time(); last = t0; it = 0
    scale = None
    while time.time() - t0 < minutes * 60:
        it += 1; node = root; seq = []; path = [root]
        while not terminal(seq, env.LV):
            lv, used, n = Env.status(seq)
            width = 2 + int(2.0 * math.sqrt(node.n))
            if len(node.kids) < width:
                act = guided_action(env, seq, used, rng) if n < 6 else None
                if act is None or (n >= 1 and rng.random() < 0.08): act = 'end'
                if act not in node.kids: node.kids[act] = Node()
                seq.append(act); node = node.kids[act]; path.append(node); break
            # UCT on best-reward (normalised)
            sc = scale or 1.0
            def ucb(item):
                a, ch = item
                return (ch.best / sc) + 0.4 * (ch.tot / ch.n / sc - ch.best / sc) + 1.2 * math.sqrt(math.log(node.n + 1) / (ch.n + 1))
            act, node = max(node.kids.items(), key=ucb)
            seq.append(act); path.append(node)
        r, full = rollout(env, seq, rng)
        if scale is None: scale = max(1.0, abs(r))
        for nd in path:
            nd.n += 1; nd.tot += r; nd.best = max(nd.best, r)
        if r > best[0]:
            best = (r, full)
            pickle.dump(dict(seq=full, reward=r), open('ckpt/mcts_%s.pkl' % tag, 'wb'))
            if r == 0: print('[mcts %s] EXACT at it %d' % (tag, it), flush=True); break
        if time.time() - last > 10:
            last = time.time()
            print('[mcts %s] %4.0fs  it %d (%.0f/s)  best deficiency %d  root kids %d' %
                  (tag, last - t0, it, it / (last - t0), -best[0], len(root.kids)), flush=True)
    return best


if __name__ == '__main__':
    mode, LV, seed, minutes = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
    rng = random.Random(seed)
    if mode == 'plant':
        # planted: random budget circuit; target = random GF(2) combination of its products + some turnaround pairs
        prng = random.Random(1000 + seed); seq = []
        for l in range(LV):
            used = set()
            for _ in range(6):
                a = rand_action(used, prng)
                if a is None: break
                seq.append(a); used |= {a[0], a[1], a[4]}
            seq.append('end')
        env0 = Env(E.logo_bits(), LV); S, prods = env0.play(seq)
        Fv = np.zeros(64, dtype=np.uint64)
        for p in prods[13:]:
            if prng.random() < 0.5: Fv ^= p
        for _ in range(20):
            a, b = prng.sample(range(NW), 2); Fv ^= S[a] & S[b]
        print('planted target: %d Toffolis, weight %d' % (sum(x != 'end' for x in seq), sum(bin(int(w)).count('1') for w in Fv)), flush=True)
    else:
        Fv = E.logo_bits()
    env = Env(Fv, LV)
    if mode == 'plant': print('planted solution deficiency (sanity, must be 0):', -env.reward(seq), flush=True)
    tag = '%s_L%d_s%d_b%g' % (mode, LV, seed, BETA)
    best = search(env, minutes, rng, tag)
    print('[mcts %s] final best deficiency %d' % (tag, -best[0]), flush=True)
