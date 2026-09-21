import sys, time, pickle
from cpri_round import Enc, encode, solve, decode, check, init_tables, logo_pairs, bit
from cpri_io import out_path as _out
R=int(sys.argv[1]); timeout=float(sys.argv[2]); maxsel=int(sys.argv[3])
pairs=[(u, bit(0)) for u, v in logo_pairs()]        # y side trivial
xinit=init_tables(); yinit=init_tables()
e=Enc(); encode(R,3,pairs,xinit,yinit,e,maxsel=maxsel)
print(f'x-only R={R} maxsel={maxsel} vars={e.pool.top} clauses={len(e.cl)}', flush=True)
t0=time.time(); res=solve(e.cl,timeout)
print(f'solve {time.time()-t0:.0f}s ->', 'timeout' if res=='timeout' else ('UNSAT' if res is None else 'SAT'), flush=True)
if res not in (None,'timeout'):
    s=decode(res,R,3,e); print(s['x']); print('check', check(s,pairs,xinit,yinit))
    pickle.dump(s, open(_out(f'cpri_xonly_R{R}.pkl'),'wb'))
