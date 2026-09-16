"""CP-FD: greedily accumulate DEPTH-FREE residency splits, scanning every
insertion point inside each consumer gap (not just its endpoints), then
re-time the enlarged gate set with an order ILS.
Every accepted list is checked with cpae_core.sim_exact."""
import sys, os, pickle, collections, time, random
sys.path.insert(0,'/home/user/classiq-challenge')
import cpet_vdag as V, cpeu_dag as U, cpae_core as C
import cpew_obj as O
from cpen_fast import NON, INV, dag
from cpen_rsched import rsched
RM=V.raw_masks(12); FULL=V.FULL
FV=C.fvec(C.SHAPES['LOGO'])
N,PH,nmask,A=U.load(); lev=A['lev']
mask2node={}
for i in range(57): mask2node.setdefault(nmask[i],i)

def snaps(ops):
    m=[RM[w] if w<12 else 0 for w in range(18)]; out=[]
    for op in ops:
        out.append(list(m)); k,q=op[0],op[1:]
        if k=='x': m[q[0]]^=FULL
        elif k=='cx': m[q[1]]^=m[q[0]]
        elif k in ('ccx','ccx_dg'): m[q[2]]^=m[q[0]]&m[q[1]]
        elif k in ('c3x','c3x_dg'): m[q[3]]^=m[q[0]]&m[q[1]]&m[q[2]]
    out.append(list(m)); return out

def exact(ops):
    qc=C.ops_to_qc(ops,18); gl,gp=C.extract(qc)
    err,mism=C.sim_exact(gl,gp,FV); return err<1e-9 and mism==0

def analyse(ops):
    m=[RM[x] if x<12 else 0 for x in range(18)]; S=[frozenset() for _ in range(18)]
    present=collections.defaultdict(list); reads=collections.defaultdict(list)
    for idx,op in enumerate(ops):
        k,q=op[0],op[1:]
        for x in q:
            for i in S[x]: reads[i].append(idx)
        if k=='x': m[q[0]]^=FULL
        elif k=='cx': a_,b_=q; m[b_]^=m[a_]; S[b_]=S[b_]^S[a_]
        elif k in ('ccx','ccx_dg','c3x','c3x_dg'):
            *ctl,t=q; prod=m[ctl[0]]
            for c in ctl[1:]: prod&=m[c]
            i=mask2node.get(prod)
            if i is not None: S[t]=S[t]^frozenset([i]); present[i].append((idx,t))
            m[t]^=prod
    return present,reads

def find_wires(sn,masks,exclude):
    used=set(exclude); out=[]
    for mk in masks:
        w=next((x for x in range(18) if sn[x]==mk and x not in used),None)
        if w is None: return None
        used.add(w); out.append(w)
    return out

def gen_splits(ops, minfree=10):
    """every (a,p,q) whose operands are available at BOTH insertion points."""
    sn=snaps(ops); present,reads=analyse(ops); out=[]
    for i in range(57):
        if lev[i]!=0: continue
        pr=present.get(i,[])
        if len(pr)<2: continue
        a,b=pr[0][0],pr[-1][0]
        opA=ops[a]; nm=opA[0]; ctl=list(opA[1:-1]); w=opA[-1]
        masks=[sn[a][c] for c in ctl]
        rd=sorted(set(x for x in reads.get(i,[]) if a<x<b)); pts=[a]+rd+[b]
        for j in range(len(pts)-1):
            ga,gb=pts[j],pts[j+1]
            if gb-ga < minfree: continue
            ps=[p for p in range(ga+1,gb+1) if find_wires(sn[p],masks,[w])]
            if not ps: continue
            p=min(ps); q=max(x for x in ps if x>=p)
            if q-p < minfree: continue
            out.append((q-p,i,a,p,q,nm,tuple(ctl),w,tuple(masks)))
    out.sort(reverse=True); return out

def apply_split(ops,sp):
    _,i,a,p,q,nm,ctl,w,masks=sp
    sn=snaps(ops)
    c1=find_wires(sn[p],list(masks),[w]); c2=find_wires(sn[q],list(masks),[w])
    if c1 is None or c2 is None: return None
    return ops[:p]+[(INV[nm],)+tuple(c1)+(w,)]+ops[p:q]+[(nm,)+tuple(c2)+(w,)]+ops[q:]

def ils(ops, secs, seed=0):
    succ,indeg=dag(ops); M=len(ops); rng=random.Random(seed)
    def ev(pri):
        o,_=rsched(ops,succ,indeg,pri); return O.obj(o),o
    pri=list(range(M)); s,o=ev(pri); best=(s['depth'],s['cx'],list(pri),o)
    cur=(s['depth'],list(pri)); t0=time.time()
    while time.time()-t0<secs:
        p=list(cur[1]); sc=rng.choice([3,10,40])
        for _ in range(rng.choice([1,3,10,M//4])):
            j=rng.randrange(M); p[j]+=rng.gauss(0,sc)
        s2,o2=ev(p)
        if s2['depth']<best[0] or (s2['depth']==best[0] and s2['cx']<best[1]):
            best=(s2['depth'],s2['cx'],list(p),o2)
            print('    ILS depth %d cx %d (%.0fs)'%(s2['depth'],s2['cx'],time.time()-t0), flush=True)
        if s2['depth']<=cur[0]+(1 if rng.random()<0.2 else 0): cur=(s2['depth'],p)
    return best

if __name__=='__main__':
    ROUNDS=int(os.environ.get('ROUNDS','8')); ILS=float(os.environ.get('ILS','240'))
    ops=list(pickle.load(open('cpen_search_11.pkl','rb'))[1])
    base=O.obj(ops); D0=base['depth']
    print('base depth %d cx %d ops %d'%(D0,base['cx'],len(ops)), flush=True)
    taken=[]
    for rd in range(ROUNDS):
        sps=gen_splits(ops)
        print('round %d: %d split candidates (op list %d)'%(rd,len(sps),len(ops)), flush=True)
        bestmv=None
        for sp in sps[:40]:
            o2=apply_split(ops,sp)
            if o2 is None or not exact(o2): continue
            st=O.obj(o2)
            if st['depth']<=D0 and (bestmv is None or sp[0]>bestmv[0][0]):
                bestmv=(sp,st,o2)
        if bestmv is None:
            print('  no depth-free split left -- stop', flush=True); break
        sp,st,ops=bestmv; taken.append(sp[:5])
        print('  took n%d split freeing %d op-slots -> depth %d cx %d ops %d'
              %(sp[1],sp[0],st['depth'],st['cx'],len(ops)), flush=True)
        pickle.dump((ops,taken),open('cpfd_multi.pkl','wb'))
    print('\n%d splits taken; re-timing with order ILS...'%len(taken), flush=True)
    d,c,pri,o=ils(ops,ILS)
    print('AFTER SPLITS + ILS: depth %d cx %d (base %d)'%(d,c,D0), flush=True)
    print('exact: %s'%exact(o), flush=True)
    pickle.dump((o,d,c),open('cpfd_final.pkl','wb'))
