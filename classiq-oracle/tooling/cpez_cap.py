"""CP-EZ: minimum makespan at K registers with a TOGGLE CAP.
cap=114 is 'each node computed once and uncomputed once' (no recomputation),
which is the regime the banked op list lives in (118 toggles, T=45).
Question: is 45 anywhere near optimal for that regime?"""
import sys, time
sys.path.insert(0,'/home/user/classiq-challenge')
from ortools.sat.python import cp_model
import cpet_pebble as PB

def solve_cap(T, K, cap, secs=120, dag=None):
    a, seeds, nodes, nmask, phases = dag
    n=a['n']; preds=a['preds']; m=cp_model.CpModel()
    p=[[m.NewBoolVar('p%d_%d'%(i,t)) for t in range(T+1)] for i in range(n)]
    for i in range(n):
        m.Add(p[i][0]==0); m.Add(p[i][T]==0)
    tog=[[m.NewBoolVar('g%d_%d'%(i,t)) for t in range(T+1)] for i in range(n)]
    for i in range(n):
        for t in range(1,T+1):
            m.AddBoolXOr([p[i][t-1],p[i][t],tog[i][t].Not()])
            for j in preds[i]:
                m.AddImplication(tog[i][t],p[j][t-1])
                m.AddImplication(tog[i][t],p[j][t])
    for t in range(1,T+1):
        u=[]
        for i in range(n):
            ui=m.NewBoolVar('u%d_%d'%(i,t))
            m.AddImplication(p[i][t-1],ui); m.AddImplication(p[i][t],ui)
            m.AddBoolOr([p[i][t-1],p[i][t],ui.Not()]); u.append(ui)
        m.Add(sum(u)<=K)
    for q,s in enumerate(seeds):
        ys=[]
        for t in range(1,T+1):
            y=m.NewBoolVar('y%d_%d'%(q,t))
            for i in s: m.AddImplication(y,p[i][t])
            ys.append(y)
        m.AddBoolOr(ys)
    m.Add(sum(tog[i][t] for i in range(n) for t in range(1,T+1)) <= cap)
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=float(secs)
    sol.parameters.num_search_workers=4
    st=sol.Solve(m); nm=sol.StatusName(st)
    if st in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        works=sum(sol.Value(tog[i][t]) for i in range(n) for t in range(1,T+1))
        sched=[[i for i in range(n) if sol.Value(p[i][t])] for t in range(T+1)]
        return nm,works,sched
    return nm,None,None

if __name__=='__main__':
    dag=PB.build_dag()
    K=int(sys.argv[1]) if len(sys.argv)>1 else 18
    cap=int(sys.argv[2]) if len(sys.argv)>2 else 118
    secs=float(sys.argv[3]) if len(sys.argv)>3 else 120
    print('K=%d toggle cap=%d  (banked list: 118 toggles, T=45, depth 249)'%(K,cap), flush=True)
    for T in (12,14,16,18,20,24,28,32,36,40,45):
        t0=time.time(); nm,wk,sched=solve_cap(T,K,cap,secs,dag)
        print('  T=%-3d -> %-12s toggles %-5s (%.0fs)   predicted depth ~%s'
              %(T,nm,wk,time.time()-t0, int(5.3*T) if wk else '-'), flush=True)
        if nm in ('OPTIMAL','FEASIBLE'):
            import pickle; pickle.dump(sched,open('cpez_sched_K%d_T%d.pkl'%(K,T),'wb'))
            break
