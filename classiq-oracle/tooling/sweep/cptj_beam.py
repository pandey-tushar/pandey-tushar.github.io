"""Level-by-level construction (beam) for the phase-along-the-way oracle.
Node = wire values after k levels + accumulated phase features (Toffoli
products, inputs, constant).  Score of a node = ANF weight of the residual
of F after greedy pursuit over: accumulated features + every pair and every
triple product of the CURRENT wires (the turnaround CZ/CCZ phase layer if we
stopped here).  Residual 0 = exact circuit (then one mirror).
Expansion: a level = one CX layer + one Toffoli layer (disjoint wires).
Children per node: RAND random levels + GREEDY greedily built levels (add
the Toffoli, from a random sample, that lowers the score most).  Keep the
best BEAM distinct children.
Usage: python3 cptj_beam.py logo|test SEED LEVELS [PLANT_L]
Env: BEAM (16), RAND (60), GREEDY (4), SAMPLE (60)
Progress: one line per level + every 10 s; checkpoint ckpt/jbeam_<mode>_s<seed>.pkl"""
import os, sys, time, pickle, json
import numpy as np
import numba as nb
import cpte_evo as E
from cpte_evo import NW, NWORD, popc, init_state, logo_bits
from cpth_span import moebius

BEAM = int(os.environ.get('BEAM', '16'))
RAND = int(os.environ.get('RAND', '60'))
GREEDY = int(os.environ.get('GREEDY', '4'))
SAMPLE = int(os.environ.get('SAMPLE', '60'))
NT = NW * (NW - 1) // 2 + NW * (NW - 1) * (NW - 2) // 6


@nb.njit(cache=True)
def weight(r):
    s = 0
    for k in range(NWORD): s += popc(r[k])
    return s


@nb.njit(cache=True)
def score(cur, acc, nacc, Fa, buf):
    """acc: ANF-domain accumulated features [0:nacc]; cur: wire values (value domain).
    returns ANF weight of the greedy residual"""
    n = 0
    for a in range(NW):
        for b in range(a + 1, NW):
            for k in range(NWORD): buf[n, k] = cur[a, k] & cur[b, k]
            moebius(buf[n]); n += 1
    for a in range(NW):
        for b in range(a + 1, NW):
            for c in range(b + 1, NW):
                for k in range(NWORD): buf[n, k] = cur[a, k] & cur[b, k] & cur[c, k]
                moebius(buf[n]); n += 1
    res = Fa.copy(); cw = weight(res)
    while True:
        bi = -1; bw = cw
        for i in range(nacc):
            s = 0
            for k in range(NWORD): s += popc(res[k] ^ acc[i, k])
            if s < bw: bw = s; bi = i
        for i in range(n):
            s = 0
            for k in range(NWORD): s += popc(res[k] ^ buf[i, k])
            if s < bw: bw = s; bi = nacc + i
        if bi < 0: break
        if bi < nacc:
            for k in range(NWORD): res[k] ^= acc[bi, k]
        else:
            for k in range(NWORD): res[k] ^= buf[bi - nacc, k]
        cw = bw
    return cw


def apply_level(cur, lev):
    """lev = (cx list [(s,t)], tof list [(a,b,pa,pb,t)]) -> new values, product features (value domain)"""
    v = cur.copy()
    for s, t in lev[0]: v[t] = v[t] ^ v[s]
    w = v.copy(); prods = []
    ONES = np.uint64(0xFFFFFFFFFFFFFFFF)
    for a, b, pa, pb, t in lev[1]:
        p = (v[a] ^ (ONES if pa else np.uint64(0))) & (v[b] ^ (ONES if pb else np.uint64(0)))
        w[t] = w[t] ^ p; prods.append(p)
    return w, prods


def rand_cx(rng, k):
    perm = list(rng.permutation(NW)); out = []
    for i in range(0, 2 * k, 2): out.append((int(perm[i]), int(perm[i + 1])))
    return out


def rand_tof(rng, used):
    free = [u for u in range(NW) if u not in used]
    if len(free) < 3: return None
    a, b, t = rng.choice(free, 3, replace=False)
    return (int(a), int(b), int(rng.integers(2)), int(rng.integers(2)), int(t))


class Node:
    def __init__(self, cur, acc, levels, sc):
        self.cur, self.acc, self.levels, self.sc = cur, acc, levels, sc


def child_score(node, lev, Fa, buf):
    w, prods = apply_level(node.cur, lev)
    add = []
    for p in prods:
        q = p.copy(); moebius(q); add.append(q)
    acc = np.concatenate([node.acc, np.array(add, dtype=np.uint64).reshape(-1, NWORD)]) if add else node.acc
    return score(w, acc, len(acc), Fa, buf), w, acc


def expand(node, Fa, buf, rng):
    kids = []
    for _ in range(RAND):
        cxl = rand_cx(rng, int(rng.integers(0, 5)))
        tofs = []; used = set()
        for _ in range(int(rng.integers(1, 7))):
            g = rand_tof(rng, used)
            if g is None: break
            tofs.append(g); used |= {g[0], g[1], g[4]}
        lev = (cxl, tofs)
        sc, w, acc = child_score(node, lev, Fa, buf)
        kids.append(Node(w, acc, node.levels + [lev], sc))
    for _ in range(GREEDY):
        cxl = rand_cx(rng, int(rng.integers(0, 5)))
        tofs = []; used = set(); cur_sc = child_score(node, (cxl, []), Fa, buf)[0]
        while True:
            best = None
            for _ in range(SAMPLE):
                g = rand_tof(rng, used)
                if g is None: break
                sc = child_score(node, (cxl, tofs + [g]), Fa, buf)[0]
                if best is None or sc < best[0]: best = (sc, g)
            if best is None or best[0] >= cur_sc: break
            tofs.append(best[1]); used |= {best[1][0], best[1][1], best[1][4]}; cur_sc = best[0]
        lev = (cxl, tofs)
        sc, w, acc = child_score(node, lev, Fa, buf)
        kids.append(Node(w, acc, node.levels + [lev], sc))
    return kids


if __name__ == '__main__':
    mode, seed, LV = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    rng = np.random.default_rng(seed)
    tag = 'jbeam_%s_s%d' % (mode, seed)
    if mode == 'test':                      # planted: XOR of half the Toffoli products of a random circuit + a few final pairs
        PL = int(sys.argv[4]) if len(sys.argv) > 4 else 5
        r0 = np.random.default_rng(7000 + seed); cur = init_state(); tv = np.zeros(NWORD, dtype=np.uint64); nt = 0
        for l in range(PL):
            lev = (rand_cx(r0, 2), []); used = set()
            for _ in range(6):
                g = rand_tof(r0, used)
                if g is None: break
                lev[1].append(g); used |= {g[0], g[1], g[4]}
            cur, prods = apply_level(cur, lev); nt += len(prods)
            for p in prods:
                if r0.random() < 0.5: tv ^= p
        for a in range(NW):
            for b in range(a + 1, NW):
                if r0.random() < 0.03: tv ^= cur[a] & cur[b]
        Fv = tv
        print('[%s] planted: %d levels, %d Toffolis' % (tag, PL, nt), flush=True)
    else:
        Fv = logo_bits()
    Fa = Fv.copy(); moebius(Fa)
    buf = np.zeros((NT, NWORD), dtype=np.uint64)
    cur0 = init_state()
    acc0 = [np.full(NWORD, np.uint64(0xFFFFFFFFFFFFFFFF))] + [cur0[i].copy() for i in range(12)]
    for q in acc0: moebius(q)
    acc0 = np.array(acc0)
    root = Node(cur0, acc0, [], score(cur0, acc0, len(acc0), Fa, buf))
    print('[%s] target ANF terms %d  root score %d  BEAM %d RAND %d GREEDY %d SAMPLE %d' %
          (tag, weight(Fa), root.sc, BEAM, RAND, GREEDY, SAMPLE), flush=True)
    front = [root]; t0 = time.time(); best = root
    for L in range(1, LV + 1):
        kids = []; last = time.time()
        for i, node in enumerate(front):
            kids += expand(node, Fa, buf, rng)
            if time.time() - last > 10:
                last = time.time()
                print('   level %d: expanded %d/%d nodes, best child so far %d  %.0fs' %
                      (L, i + 1, len(front), min(k.sc for k in kids), time.time() - t0), flush=True)
        kids.sort(key=lambda k: k.sc)
        seen = set(); front = []
        for k in kids:
            key = k.cur.tobytes()
            if key in seen: continue
            seen.add(key); front.append(k)
            if len(front) == BEAM: break
        if front[0].sc < best.sc or L == 1: best = front[0]
        print('[%s] level %d  best %d  beam %s  %.0fs' % (tag, L, front[0].sc, [k.sc for k in front[:6]], time.time() - t0), flush=True)
        pickle.dump(dict(levels=front[0].levels, sc=front[0].sc, L=L, mode=mode, seed=seed), open('ckpt/%s.pkl' % tag, 'wb'))
        json.dump(dict(level=L, best=int(front[0].sc), beam=[int(k.sc) for k in front], elapsed=round(time.time() - t0)),
                  open('ckpt/%s.json' % tag, 'w'))
        if front[0].sc == 0:
            print('[%s] EXACT at level %d' % (tag, L), flush=True); break
