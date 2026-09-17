"""CP-FH stage 1: the nested-rank data as truth tables + in-place cost of the
3-bit group functions.

  F(x,y) = XOR_{(k,m) in G} a_k(x) b_m(y)
  a_k = XOR_i u_ki(lo) & v_ki(hi)      (u, v: 3-variable functions)

Every u / v must at some point sit on a wire to act as a Margolus control.
In-place programs on a group's 3 raw wires (X free, CX, CCX) reach every
bijection of the 3 bits; Dijkstra over those states gives, per needed
function, the cheapest state that hosts it and how many needed functions a
single state can host at once.
"""
import sys, heapq, itertools
sys.path.insert(0, '/home/user/classiq-challenge')
import numpy as np
import cpcj_net as N
import cpfh_core as C

NIN = 4096
RAW3 = (0xAA, 0xCC, 0xF0)      # a, b, c truth tables over index i = a + 2b + 4c


def f8_int(f8):
    return sum(int(v) << i for i, v in enumerate(f8))


def lift(f8i, bits):
    """3-var function (8-bit int over group bits) -> 4096-bit truth table."""
    m = 0
    for idx in range(NIN):
        i = sum(((idx >> b) & 1) << k for k, b in enumerate(bits))
        if (f8i >> i) & 1:
            m |= 1 << idx
    return m


def load():
    terms, plan = N.build()
    origA = [t[0].astype(np.uint8) for t in terms]
    origB = [t[1].astype(np.uint8) for t in terms]
    cA = N.coeffs_in_basis(origA, plan['x']['basis'])
    cB = N.coeffs_in_basis(origB, plan['y']['basis'])
    G = np.zeros((10, 10), dtype=np.uint8)
    for j in range(len(terms)):
        G ^= np.outer(cA[j], cB[j]) % 2
    legs = [(k, m) for k in range(10) for m in range(10) if G[k][m]]
    side = {}
    for nm, off in (('x', 0), ('y', 6)):
        lo = [off + b for b in plan[nm]['lo']]
        hi = [off + b for b in plan[nm]['hi']]
        prods = []
        for tl in plan[nm]['terms']:
            prods.append([(f8_int(u), f8_int(v)) for u, v in tl])
        side[nm] = dict(lo=lo, hi=hi, prods=prods)
    return side, legs


def basis_tt(side, nm):
    s = side[nm]
    out = []
    for tl in s['prods']:
        m = 0
        for u, v in tl:
            m ^= lift(u, s['lo']) & lift(v, s['hi'])
        out.append(m)
    return out


def dijkstra3(cost_cx=1, cost_ccx=7):
    """all bijective states of 3 wires reachable by X / CX / CCX in place.
    returns dict state -> (cost, path)."""
    start = RAW3
    dist = {start: (0, ())}
    pq = [(0, start, ())]
    while pq:
        d, s, path = heapq.heappop(pq)
        if dist[s][0] < d:
            continue
        for w in range(3):
            t = list(s); t[w] ^= 0xFF; t = tuple(t)
            if t not in dist or dist[t][0] > d:
                dist[t] = (d, path + (('x', w),)); heapq.heappush(pq, (d, t, path + (('x', w),)))
        for a in range(3):
            for b in range(3):
                if a == b:
                    continue
                t = list(s); t[b] ^= s[a]; t = tuple(t)
                nd = d + cost_cx
                if t not in dist or dist[t][0] > nd:
                    dist[t] = (nd, path + (('cx', a, b),)); heapq.heappush(pq, (nd, t, path + (('cx', a, b),)))
        for tw in range(3):
            a, b = [w for w in range(3) if w != tw]
            t = list(s); t[tw] ^= s[a] & s[b]; t = tuple(t)
            nd = d + cost_ccx
            if t not in dist or dist[t][0] > nd:
                dist[t] = (nd, path + (('ccx', a, b, tw),)); heapq.heappush(pq, (nd, t, path + (('ccx', a, b, tw),)))
    return dist


if __name__ == '__main__':
    side, legs = load()
    print('legs', len(legs), legs)
    A = basis_tt(side, 'x'); B = basis_tt(side, 'y')
    ph = 0
    for k, m in legs:
        ph ^= A[k] & B[m]
    print('F mismatch', bin(ph ^ C.F).count('1'))
    for nm in ('x', 'y'):
        s = side[nm]
        print(nm, 'lo', s['lo'], 'hi', s['hi'], 'products per basis elt',
              [len(t) for t in s['prods']])
    dist = dijkstra3()
    print('reachable 3-wire states', len(dist))
    hostable = {}          # f -> (cost, path) over balanced functions
    for st, (d, path) in dist.items():
        for w in range(3):
            f = st[w]
            if f not in hostable or hostable[f][0] > d:
                hostable[f] = (d, path)
    print('distinct hostable functions', len(hostable), '(balanced non-affine expected 70-14=56 + affine)')
    wt = lambda f: bin(f).count('1')
    for nm in ('x', 'y'):
        for part, pos in (('lo', 0), ('hi', 1)):
            need = sorted({p[pos] for tl in side[nm]['prods'] for p in tl} - {0, 0xFF})
            bal = [f for f in need if wt(f) == 4]
            print('%s.%s: %d needed functions, weights %s' % (nm, part, len(need), sorted(wt(f) for f in need)))
            print('    balanced %d in-place costs %s ; unbalanced %d' % (
                len(bal), sorted(hostable[f][0] for f in bal), len(need) - len(bal)))
        # basis freedom on rank>=2 elements: a_k = sum_i u_i v_i is invariant
        # under u <- M u, v <- M^-T v.  8x8 matrix as 64-bit int, row i = v if u_i.
        def outer(U, V):
            m = 0
            for u, v in zip(U, V):
                for i in range(8):
                    if (u >> i) & 1:
                        m ^= v << (8 * i)
            return m
        def inv_rank(rows, r):
            bs = []
            for x in rows:
                for b in bs: x = min(x, x ^ b)
                if not x: return False
                bs.append(x)
            return True
        for k, tl in enumerate(side[nm]['prods']):
            r = len(tl)
            if r == 1:
                continue
            U = [u for u, v in tl]; V = [v for u, v in tl]
            target = outer(U, V)
            best = None
            mats = [M for M in itertools.product(range(1, 1 << r), repeat=r) if inv_rank(list(M), r)]
            for M in mats:
                nu = [0] * r
                for i in range(r):
                    for j in range(r):
                        if (M[i] >> j) & 1: nu[i] ^= U[j]
                for Mv in mats:
                    nv = [0] * r
                    for i in range(r):
                        for j in range(r):
                            if (Mv[i] >> j) & 1: nv[i] ^= V[j]
                    if outer(nu, nv) == target:
                        nb = sum(wt(f) == 4 for f in nu) + sum(wt(f) == 4 for f in nv)
                        if best is None or nb > best[0]:
                            best = (nb, nu, nv)
            print('  %s basis elt %d rank %d: orig balanced %d/%d -> best %d/%d  u %s v %s' % (
                nm, k, r, sum(wt(f) == 4 for f in U) + sum(wt(f) == 4 for f in V), 2 * r,
                best[0], 2 * r, ['%02x' % f for f in best[1]], ['%02x' % f for f in best[2]]))
