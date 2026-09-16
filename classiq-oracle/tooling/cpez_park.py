"""CP-EZ: THE ACCUMULATION-AWARE PHYSICAL PEBBLE MODEL (the missing model).

Wires 0..11 carry raw bit x_j; wire j may additionally carry ONE node value
n_k as an accumulation (x_j ^ n_k), but then n_k is readable only by operands
containing x_j, so k may park on j only if j is in EVERY operand consuming k.
Wires 12..17 are clean ancillas and can carry any node value.
At every step each wire carries at most one live node value.

Minimise the makespan T.  depth ~= 5.3*T (249/45 banked, 127/24 wide).
"""
import sys, time, pickle, collections
sys.path.insert(0,'/home/user/classiq-challenge')
from ortools.sat.python import cp_model
import cpet_pebble as PB
import cpeu_dag as U

N,PH,nmask,A = U.load()
def rawset(o): return set(w for w in range(12) if (o>>w)&1)
def nods(o): return [j for j in range(57) if (o>>(12+j))&1]
cons=collections.defaultdict(list)
for i in range(57):
    for o in N[i]:
        for k in nods(o): cons[k].append(o)
for t in PH:
    for o in t:
        for k in nods(o): cons[k].append(o)
PARK={k:(set.intersection(*[rawset(o) for o in cons[k]]) if cons.get(k) else set(range(12)))
      for k in range(57)}

def solve(T, secs, dag, cap=None):
    a,seeds,nodes,nmask_,phases = dag
    n=a['n']; preds=a['preds']; m=cp_model.CpModel()
    p=[[m.NewBoolVar('p%d_%d'%(i,t)) for t in range(T+1)] for i in range(n)]
    for i in range(n):
        m.Add(p[i][0]==0); m.Add(p[i][T]==0)
    tog=[[m.NewBoolVar('g%d_%d'%(i,t)) for t in range(T+1)] for i in range(n)]
    for i in range(n):
        for t in range(1,T+1):
            m.AddBoolXOr([p[i][t-1],p[i][t],tog[i][t].Not()])
            for j in preds[i]:
                m.AddImplication(tog[i][t],p[j][t-1]); m.AddImplication(tog[i][t],p[j][t])
    u=[[m.NewBoolVar('u%d_%d'%(i,t)) for t in range(T+1)] for i in range(n)]
    for i in range(n):
        for t in range(1,T+1):
            m.AddImplication(p[i][t-1],u[i][t]); m.AddImplication(p[i][t],u[i][t])
            m.AddBoolOr([p[i][t-1],p[i][t],u[i][t].Not()])
    W=18
    park=[[m.NewBoolVar('w%d_%d'%(i,w)) for w in range(W)] for i in range(n)]
    for i in range(n):
        for w in range(12):
            if w not in PARK[i]: m.Add(park[i][w]==0)
        m.Add(sum(park[i])==1)
    for t in range(1,T+1):
        for w in range(W):
            occ=[]
            for i in range(n):
                b=m.NewBoolVar('o%d_%d_%d'%(i,w,t))
                m.AddBoolAnd([u[i][t],park[i][w]]).OnlyEnforceIf(b)
                m.AddBoolOr([u[i][t].Not(),park[i][w].Not()]).OnlyEnforceIf(b.Not())
                occ.append(b)
            m.Add(sum(occ)<=1)
    for q,s in enumerate(seeds):
        ys=[]
        for t in range(1,T+1):
            y=m.NewBoolVar('y%d_%d'%(q,t))
            for i in s: m.AddImplication(y,p[i][t])
            ys.append(y)
        m.AddBoolOr(ys)
    if cap: m.Add(sum(tog[i][t] for i in range(n) for t in range(1,T+1))<=cap)
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=float(secs)
    sol.parameters.num_search_workers=4
    st=sol.Solve(m); nm=sol.StatusName(st)
    if st in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        wk=sum(sol.Value(tog[i][t]) for i in range(n) for t in range(1,T+1))
        sched=[[i for i in range(n) if sol.Value(p[i][t])] for t in range(T+1)]
        pk={i:[w for w in range(W) if sol.Value(park[i][w])][0] for i in range(n)}
        return nm,wk,sched,pk
    return nm,None,None,None

if __name__=='__main__':
    dag=PB.build_dag()
    secs=float(sys.argv[1]) if len(sys.argv)>1 else 300
    print('accumulation-aware physical model, 18 wires', flush=True)
    print('nodes parkable on a data wire: %d/57'%sum(1 for k in PARK if PARK[k]), flush=True)
    for T in (24,28,32,36,40,45,50,56):
        t0=time.time(); nm,wk,sched,pk=solve(T,secs,dag)
        print('  T=%-3d -> %-12s toggles %-5s (%.0fs)  predicted depth ~%s'
              %(T,nm,wk,time.time()-t0,int(5.3*T) if wk else '-'), flush=True)
        if nm in ('OPTIMAL','FEASIBLE'):
            pickle.dump((sched,pk),open('cpez_park_T%d.pkl'%T,'wb'))
            print('   saved cpez_park_T%d.pkl'%T, flush=True); break
