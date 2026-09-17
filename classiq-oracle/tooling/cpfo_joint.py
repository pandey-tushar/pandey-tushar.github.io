"""cpfo_joint: joint beam search over both sides.

Exact pairing condition (necessary and sufficient for CZ/CCZ phases):
  (1) colspace(F) in S_x,  (2) rowspace(F) in S_y,
  (3) F reduced columnwise mod L_x and rowwise mod L_y is zero,
where L = span(1, contents), S = span(L, pairwise products).
Score = (cov_x + cov_y, -rank(3), cov3_x + cov3_y, -residual weight, -depth).
Alternate x-steps and y-steps.
"""
import sys, itertools, pickle, time
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfo_beam as B
import cpfk_side as SD
import cpfo_join as J
from cpae_core import model_depth

COLS = SD.COLS   # F columns: function of x for each y
ROWS = SD.ROWS   # F rows: function of y for each x
M64 = B.M64

def reduce_mod(v, piv):
    for p in sorted(piv, reverse=True):
        if (v >> p) & 1: v ^= piv[p]
    return v

def side_info(contents, targets):
    L = [c for c in contents if c] + [M64]
    pivL = B.reduce_basis(L)
    prods = [a & b for a, b in itertools.combinations(L, 2)]
    pivS = B.reduce_basis(L + prods)
    cov = len(targets) - B.rank_with(pivS, targets)
    trip = [a & b & c for a, b, c in itertools.combinations(L, 3)]
    piv3 = dict(pivS)
    for v in trip:
        v = reduce_mod(v, piv3)
        if v: piv3[v.bit_length() - 1] = v
    cov3 = len(targets) - B.rank_with(piv3, targets)
    resw = sum(bin(reduce_mod(t, pivS)).count('1') for t in targets)
    return pivL, cov, cov3, resw

def rank_R(pivLx, pivLy):
    # reduce rows of F mod L_y, then columns of the result mod L_x, rank
    rows = [reduce_mod(r, pivLy) for r in ROWS]            # rows[x] over y
    cols = [sum(((rows[x] >> y) & 1) << x for x in range(64)) for y in range(64)]
    cols = [reduce_mod(c, pivLx) for c in cols]
    return len(B.reduce_basis(cols))

XT = None; YT = None
def joint_score(stx, sty, hx, hy, cache):
    kx = tuple(stx); ky = tuple(sty)
    if kx not in cache: cache[kx] = side_info(stx, XT)
    if ky not in cache: cache[ky] = side_info(sty, YT)
    px, cx, c3x, rwx = cache[kx]; py, cy, c3y, rwy = cache[ky]
    r = rank_R(px, py)
    d = max(model_depth(J.replay(hx)[1], n=9), model_depth(J.replay(hy)[1], n=9)) if (hx or hy) else 0
    return (cx + cy - 2 * r, -r, c3x + c3y, -(rwx + rwy), -d, cx + cy)

def beam(budget, width, verbose=True, maxdepth=None):
    global XT, YT
    XT = list(B.reduce_basis(COLS).values()); YT = list(B.reduce_basis(ROWS).values())
    start = tuple(B.RAW + [0, 0, 0])
    cache = {}
    front = [(joint_score(start, start, [], [], cache), start, start, [], [])]
    best = front[0]
    for step in range(1, budget + 1):
        side = 'x' if step % 2 else 'y'
        t0 = time.time(); cand = {}
        for sc, stx, sty, hx, hy in front:
            st = stx if side == 'x' else sty
            for p, act in B.actions(st):
                w = act[-1]; new = list(st); new[w] ^= p; new = tuple(new)
                if side == 'x': nx, ny, nhx, nhy = new, sty, hx + [act], hy
                else: nx, ny, nhx, nhy = stx, new, hx, hy + [act]
                key = (tuple(sorted(nx)), tuple(sorted(ny)))
                if key in cand: continue
                sc2 = joint_score(nx, ny, nhx, nhy, cache)
                if maxdepth is not None and -sc2[4] > maxdepth: continue
                cand[key] = (sc2, nx, ny, nhx, nhy)
        front = sorted(cand.values(), key=lambda c: c[0], reverse=True)[:width]
        if front[0][0] > best[0]: best = front[0]
        if verbose: print('step', step, side, 'cands', len(cand), 'best', front[0][0], 'ANDs', len(front[0][3]), len(front[0][4]), '%.0fs' % (time.time() - t0), flush=True)
        if front[0][0][0] == 20: return front[0]
    return best

if __name__ == '__main__':
    budget = int(sys.argv[1]); width = int(sys.argv[2]); md = int(sys.argv[3]) if len(sys.argv) > 3 else None
    r = beam(budget, width, maxdepth=md)
    sc, stx, sty, hx, hy = r
    print('RESULT score', sc, 'x ANDs', len(hx), 'y ANDs', len(hy))
    print('pair_check', J.pair_check(list(stx), list(sty)))
    pickle.dump(r, open('cpfo_joint_%s.pkl' % (md or 'free'), 'wb'))
