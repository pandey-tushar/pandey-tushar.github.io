import sys, time, pickle
from cpri_round import Enc, encode, solve, decode, check, init_tables, logo_pairs, bit
from cpri_io import out_path as _out
side=sys.argv[1]; R=int(sys.argv[2]); timeout=float(sys.argv[3]); maxsel=int(sys.argv[4]); L=int(sys.argv[5])
pairs=logo_pairs()
if side=='x': pairs=[(u, bit(0)) for u, v in pairs]
else: pairs=[(bit(0), v) for u, v in pairs]
xinit=init_tables(); yinit=init_tables()
e=Enc(); encode(R,3,pairs,xinit,yinit,e,maxsel=maxsel,L=L,only=side)
print(f'{side}-only R={R} maxsel={maxsel} L={L} vars={e.pool.top} clauses={len(e.cl)}', flush=True)
t0=time.time(); res=solve(e.cl,timeout)
print(f'solve {time.time()-t0:.0f}s ->', 'timeout' if res=='timeout' else ('UNSAT' if res is None else 'SAT'), flush=True)
if res not in (None,'timeout'):
    s=decode(res,R,3,e,L=L,only=side); print(s[side+'lin']); print(s[side]); print('check', check(s,pairs,xinit,yinit))
    pickle.dump(s, open(_out(f'cpri_{side}only_R{R}_L{L}.pkl'),'wb'))
