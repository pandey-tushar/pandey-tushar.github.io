"""cpfn_search: even-weight basis, per-pair fold/hold choice, local search over
elementary basis changes (c_i ^= c_j, b_j ^= b_i keeps F).  Reports both-direction
units = 2*keycost + pieces (fold side) + 2*(keycost + pieces) (hold side)."""
import sys, random, time, pickle
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfn_count as CC
import cpfk_syn as SY

def w(f): return bin(f).count('1')

def evenize(xf, yf):
    xf = list(xf); yf = list(yf)
    for fs, gs in ((xf, yf), (yf, xf)):
        odd = [i for i in range(len(fs)) if w(fs[i]) % 2]
        if len(odd) > 1:
            o = min(odd, key=lambda i: w(fs[i]))
            for i in odd:
                if i != o: fs[i] ^= fs[o]; gs[o] ^= gs[i]
    return xf, yf

def pair_cost(xf, yf):
    """per pair choose (fold x, hold y) or (hold x, fold y); keys shared per side."""
    kx = CC.Keys(); ky = CC.Keys(); tot = 0; plan = []
    for i in range(len(xf)):
        opts = []
        for mx, my in (('fold', 'hold'), ('hold', 'fold')):
            rx = CC.cover(xf[i], kx, mx); ry = CC.cover(yf[i], ky, my)
            if rx is None or ry is None: continue
            def units(r, mode):
                npc = len(r[2]); kc = r[0] - npc
                return (2 * kc + npc) if mode == 'fold' else 2 * (kc + npc)
            u = units(rx, mx) + units(ry, my)
            opts.append((u, mx, my, rx, ry))
        if not opts: return None
        u, mx, my, rx, ry = min(opts, key=lambda o: o[0])
        kx = rx[3]; ky = ry[3]; tot += u; plan.append((i, mx, my, u))
    return tot, plan, len(kx.keys), len(ky.keys)

if __name__ == '__main__':
    seed = int(sys.argv[1]); budget = float(sys.argv[2]); rng = random.Random(seed)
    xf, yf = SY.basis_pair()
    for name, (fx, fy) in (('pair', (xf, yf)), ('even', evenize(xf, yf))):
        r = pair_cost(fx, fy)
        print(name, 'both-dir units', r[0], 'keys', r[2], r[3], 'plan', [(i, mx[0], my[0], u) for i, mx, my, u in r[1]], flush=True)
    cur = evenize(xf, yf); cost, plan, _, _ = pair_cost(*cur); best = (cost, cur, plan)
    t0 = time.time(); step = 0
    while time.time() - t0 < budget:
        step += 1
        fx = list(cur[0]); fy = list(cur[1]); i, j = rng.sample(range(10), 2)
        if rng.random() < 0.5: fx[i] ^= fx[j]; fy[j] ^= fy[i]
        else: fy[i] ^= fy[j]; fx[j] ^= fx[i]
        r = pair_cost(fx, fy)
        if r is None: continue
        if r[0] <= cost:
            cur = (fx, fy); cost = r[0]
            if r[0] < best[0]:
                best = (r[0], cur, r[1]); print('step', step, 'units', r[0], 'x weights', [w(f) for f in fx], 'y weights', [w(f) for f in fy], flush=True)
                pickle.dump(best, open('cpfn_search_s%d.pkl' % seed, 'wb'))
    print('done steps', step, 'best', best[0])
