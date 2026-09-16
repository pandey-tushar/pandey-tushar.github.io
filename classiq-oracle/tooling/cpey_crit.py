"""CP-EY: pure dependency critical path (SSA, UNLIMITED wires) of the current
op list.  If this is close to 249, wire-reuse cleverness cannot help."""
import sys, pickle
sys.path.insert(0,'/home/user/classiq-challenge')
from cpae_core import PROF
from cpen_fast import NON
import cpew_state as S

DIAG={'cz','ccz'}
def ssa_crit(ops):
    ready={}; val={}; mk=0
    for w in range(18): val[w]=('in',w); ready[('in',w)]=0
    for op in ops:
        t=op[0]
        if t=='x':
            continue
        qs=list(op[1:]); prof=PROF[t]; Sst=0
        for i,w in enumerate(qs):
            Sst=max(Sst, ready[val[w]]-min(prof[i])+1)
        fin=Sst+max(max(prof[i]) for i in range(len(qs)))
        mk=max(mk,fin)
        if t not in DIAG:
            ti=len(qs)-1
            nv=('v',id(op),ti)
            ready[nv]=Sst+max(prof[ti]); val[qs[ti]]=nv
    return mk

p,v,_,_=pickle.load(open('cpev_search_s23.pkl','rb'))
ops=S.realize(list(p),list(v),{})
print('ops %d  nonlinear %d'%(len(ops),sum(1 for o in ops if o[0] in NON)))
print('SSA critical path (unlimited wires, WAR/WAW removed) : %d'%ssa_crit(ops))
from cpae_core import model_depth
print('model_depth at 18 wires (names, all hazards)         : %d'%model_depth(ops))
print('REAL transpiled depth of cpev_best.qasm              : 249')
