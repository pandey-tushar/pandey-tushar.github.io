"""CP-EY: exhaustive SINGLE host-move sweep over the widened alphabet
(all 18 wires, 4-op form on live wires), 4 workers."""
import sys, os, time, pickle
from multiprocessing import Pool
sys.path.insert(0,'/home/user/classiq-challenge')

PRI=VEC=None
def init():
    global PRI,VEC,S,O
    import cpew_state as S_, cpew_obj as O_
    S,O = S_,O_
    p,v,_,_ = pickle.load(open('cpev_search_s23.pkl','rb'))
    PRI,VEC = list(p),list(v)

def one(arg):
    k,w = arg
    try:
        s = O.obj(S.realize(PRI,VEC,{k:(w,False)}))
        return (k,w,s['depth'],s['cx'],s['u3'],s['density'])
    except Exception as e:
        return (k,w,None,None,None,str(e)[:40])

if __name__=='__main__':
    CH = pickle.load(open('cpey_hosts_all.pkl','rb'))
    jobs=[(k,w) for k in sorted(CH) for w in CH[k]]
    print('sweeping %d single host moves on 4 workers'%len(jobs), flush=True)
    t0=time.time(); res=[]
    with Pool(4, initializer=init) as pool:
        for i,r in enumerate(pool.imap_unordered(one, jobs, chunksize=8)):
            res.append(r)
            if (i+1)%100==0: print('  %d/%d (%.0fs)'%(i+1,len(jobs),time.time()-t0), flush=True)
    pickle.dump(res, open('cpey_sweep.pkl','wb'))
    ok=[r for r in res if r[2] is not None]
    ok.sort(key=lambda r:(r[2],r[3]))
    print('\ndone %.0fs, %d ok / %d'%(time.time()-t0,len(ok),len(res)), flush=True)
    print('BASE depth 249 cx 520')
    print('\n-- best 25 single moves --')
    for k,w,d,c,u,dn in ok[:25]:
        print('  %-28s host q%-2d %s : depth %3d cx %3d u3 %3d dens %.4f  %+d'
              %(str(k),w,'DATA' if w<12 else 'anc ',d,c,u,dn,d-249))
    dat=[r for r in ok if r[1]<12]; anc=[r for r in ok if r[1]>=12]
    import statistics as st
    for nm,g in (('DATA',dat),('ANC ',anc)):
        if g: print('%s: n=%d  best %d  median %d  mean %.1f'
                    %(nm,len(g),min(r[2] for r in g),int(st.median(r[2] for r in g)),
                      st.mean(r[2] for r in g)))
    print('\nmoves that do NOT raise depth: %d'%sum(1 for r in ok if r[2]<=249))
    print('moves that LOWER depth        : %d'%sum(1 for r in ok if r[2]<249))
