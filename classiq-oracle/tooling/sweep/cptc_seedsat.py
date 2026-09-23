"""idea 2: round SAT (fixed 11-pair decomposition, both sides) with the x side
starting in folded coordinates (c0, c1, c2, s, x4, x5) -- the 4-CX fold is
applied before round 1.  usage: R timeout maxsel"""
import sys, time, pickle
import cptb_ysat                                   # aux-var fix
from cpri_round import Enc, encode, solve, decode, logo_pairs, init_tables, check
from cpri_io import out_path
ALL = (1 << 64) - 1
def tab(f): return sum(1 << v for v in range(64) if f(v))
def folded():
    b = lambda i: tab(lambda x: (x >> i) & 1)
    nx3 = b(3) ^ ALL
    return [b(0) ^ nx3, b(1) ^ nx3, b(2) ^ nx3, b(3) ^ b(4), b(4), b(5), 0, 0, 0]
R, to, maxsel = int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
to = None if to <= 0 else to            # 0 = no timeout (blocking wait; watcher kills)
pairs = logo_pairs(); xi = folded(); yi = init_tables()
e = Enc(); encode(R, 3, pairs, xi, yi, e, maxsel=maxsel)
print('R=%d maxsel=%d vars %d clauses %d' % (R, maxsel, e.pool.top, len(e.cl)), flush=True)
t0 = time.time(); res = solve(e.cl, to)
st = 'timeout' if res == 'timeout' else ('UNSAT' if res is None else 'SAT')
print('solve %.0fs -> %s' % (time.time() - t0, st), flush=True)
if st == 'SAT':
    s = decode(res, R, 3, e); print('check', check(s, pairs, xi, yi))
    pickle.dump(s, open(out_path('cptc_seedsat_R%d.pkl' % R), 'wb'))
