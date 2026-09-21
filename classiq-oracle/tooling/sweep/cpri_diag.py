import time, sys
from cpri_round import Enc, encode, decode, check, init_tables, bit
from pysat.solvers import Solver
xinit=init_tables(); yinit=init_tables()
u2 = bit(0) & bit(1) & bit(2); v2 = bit(3) & bit(4); vy = bit(3)
which = sys.argv[1]
cfg = {'G1': (2, 1, [(u2, v2)], 'cadical153'),
       'ytriv': (2, 3, [(u2, vy)], 'cadical153'),
       'glucose': (2, 3, [(u2, v2)], 'glucose4'),
       'maple': (2, 3, [(u2, v2)], 'maplechrono'),
       'msel1': (2, 3, [(u2, v2)], 'cadical153')}[which]
R, G, pairs, sname = cfg
e = Enc(); encode(R, G, pairs, xinit, yinit, e, maxsel=(1 if which == 'msel1' else 3))
t0 = time.time()
with Solver(name=sname, bootstrap_with=e.cl) as s:
    r = s.solve()
    print(which, 'vars', e.pool.top, '->', r, f'{time.time()-t0:.1f}s', flush=True)
    if r:
        sch = decode(s.get_model(), R, G, e); print(' ', sch['x']); print('  check', check(sch, pairs, xinit, yinit))
