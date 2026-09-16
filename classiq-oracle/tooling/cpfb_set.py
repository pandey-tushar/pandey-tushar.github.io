"""CP-FB: THE SET-VALUED WIRE MODEL.

A wire carries base(w) ^ XOR(set of live node values assigned to it).  An
operand (A,S) is readable on wire w iff base(w) matches A and the live set on
w is EXACTLY S -- so stacking is free, but reading one value out demands every
other value on that wire be dead at that instant.  Ground truth from the
banked list (cpfa_exact): up to 4 nodes per wire, 25 live values on 18 wires,
only 38 relocations, 45/57 nodes never move.

Objective: minimise the NONLINEAR CHAIN LENGTH T (banked list 26, DAG floor
12).  depth ~= 7*T + cx traffic  (26 -> 182 of the measured 211 path).

Relocation is left free (assign may vary with t); that is a relaxation in the
one axis the banked list barely uses, so the model CONTAINS the banked list.
VALIDATION: T=26 must come back feasible, else the model is refuted.
"""
import sys, time, pickle, collections
sys.path.insert(0,'/home/user/classiq-challenge')
from ortools.sat.python import cp_model
import cpeu_dag as U
import cpet_pebble as PB

N, PH, nmask, A = U.load()
n = 57
def rawset(o): return frozenset(w for w in range(12) if (o>>w)&1)
def nodeset(o): return frozenset(j for j in range(n) if (o>>(12+j))&1)

# operands, grouped by consumer
OPER = {i: [(rawset(o), nodeset(o)) for o in N[i]] for i in range(n)}
PHASE = [[(rawset(o), nodeset(o)) for o in t] for t in PH]
preds = A['preds']

def cand_wires(Aset):
    if len(Aset) == 1: return [next(iter(Aset))]          # forced data wire
    if len(Aset) == 0: return list(range(12, 18))         # clean ancilla
    return list(range(18))                                 # assembled anywhere

def solve(T, secs, hint=None):
    m = cp_model.CpModel()
    p = [[m.NewBoolVar('p%d_%d'%(i,t)) for t in range(T+1)] for i in range(n)]
    for i in range(n):
        m.Add(p[i][0]==0); m.Add(p[i][T]==0)
    tog=[[m.NewBoolVar('g%d_%d'%(i,t)) for t in range(T+1)] for i in range(n)]
    live=[[m.NewBoolVar('L%d_%d'%(i,t)) for t in range(T+1)] for i in range(n)]
    for i in range(n):
        for t in range(1,T+1):
            m.AddBoolXOr([p[i][t-1],p[i][t],tog[i][t].Not()])
            m.AddImplication(p[i][t-1],live[i][t]); m.AddImplication(p[i][t],live[i][t])
            m.AddBoolOr([p[i][t-1],p[i][t],live[i][t].Not()])
            for j in preds[i]:
                m.AddImplication(tog[i][t],p[j][t-1]); m.AddImplication(tog[i][t],p[j][t])
    # assignment: a live node occupies exactly one wire at each step
    asg=[[[m.NewBoolVar('a%d_%d_%d'%(i,w,t)) for t in range(T+1)] for w in range(18)]
         for i in range(n)]
    occ=[[[m.NewBoolVar('o%d_%d_%d'%(i,w,t)) for t in range(T+1)] for w in range(18)]
         for i in range(n)]
    for i in range(n):
        for t in range(1,T+1):
            m.Add(sum(asg[i][w][t] for w in range(18)) == 1)
            for w in range(18):
                m.AddBoolAnd([asg[i][w][t],live[i][t]]).OnlyEnforceIf(occ[i][w][t])
                m.AddBoolOr([asg[i][w][t].Not(),live[i][t].Not()]).OnlyEnforceIf(occ[i][w][t].Not())
    # readability: reading operand (Aset,S) at step t needs a wire whose LIVE
    # set is exactly S
    def readable(Aset, S, t, tag):
        outs=[]
        for w in cand_wires(Aset):
            r=m.NewBoolVar('r%s_%d_%d'%(tag,w,t))
            for k in S: m.AddImplication(r, occ[k][w][t])
            m.Add(sum(occ[k][w][t] for k in range(n) if k not in S)==0).OnlyEnforceIf(r)
            outs.append(r)
        return outs
    for i in range(n):
        for t in range(1,T+1):
            for oi,(Aset,S) in enumerate(OPER[i]):
                rs=readable(Aset,S,t,'n%d_%d_%d'%(i,oi,t))
                m.AddBoolOr(rs).OnlyEnforceIf(tog[i][t])
                # the target wire must not be an operand wire
                for w in cand_wires(Aset):
                    pass
    for q,term in enumerate(PHASE):
        ys=[]
        for t in range(1,T+1):
            y=m.NewBoolVar('y%d_%d'%(q,t))
            for oi,(Aset,S) in enumerate(term):
                rs=readable(Aset,S,t,'f%d_%d_%d'%(q,oi,t))
                m.AddBoolOr(rs).OnlyEnforceIf(y)
            ys.append(y)
        m.AddBoolOr(ys)
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=float(secs)
    sol.parameters.num_search_workers=4
    st=sol.Solve(m); nm=sol.StatusName(st)
    if st in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        wk=sum(sol.Value(tog[i][t]) for i in range(n) for t in range(1,T+1))
        sched=[[i for i in range(n) if sol.Value(p[i][t])] for t in range(T+1)]
        asgv={(i,t):[w for w in range(18) if sol.Value(asg[i][w][t])][0]
              for i in range(n) for t in range(1,T+1)}
        return nm,wk,sched,asgv
    return nm,None,None,None

if __name__=='__main__':
    secs=float(sys.argv[1]) if len(sys.argv)>1 else 300
    order=[int(x) for x in sys.argv[2].split(',')] if len(sys.argv)>2 else [26,12,14,16,18,20,22,24]
    print('SET-VALUED wire model.  banked chain 26, DAG floor 12.', flush=True)
    for T in order:
        t0=time.time(); nm,wk,sched,asgv=solve(T,secs)
        tag='  <-- VALIDATION (banked list lives here)' if T==26 else ''
        print('  T=%-3d -> %-12s toggles %-5s (%.0fs)  ~depth %s%s'
              %(T,nm,wk,time.time()-t0, (7*T if wk else '-'), tag), flush=True)
        if nm in ('OPTIMAL','FEASIBLE'):
            pickle.dump((sched,asgv),open('cpfb_set_T%d.pkl'%T,'wb'))
