"""CP-FE: the COMPOUND move -- split a level-0 node out of wire w over a
window, and rehome a critical-chain node j INTO that freed window, breaking
the false serial edge.  A split alone is a no-op (the optimizer cancels the
pair); it only pays when something occupies the window it frees.
Restricted to ancilla->ancilla rehomes, where both bases are 0 so the rename
is value-exact.  Every candidate checked with cpae_core.sim_exact."""
import sys, os, pickle, collections, time
sys.path.insert(0,'/home/user/classiq-challenge')
import cpet_vdag as V, cpeu_dag as U, cpae_core as C
import cpew_obj as O
from cpen_fast import NON, INV
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

def resid(ops):
    """node -> (first write idx, last write idx, wire); plus per-wire sets."""
    m=[RM[x] if x<12 else 0 for x in range(18)]; S=[frozenset() for _ in range(18)]
    pres=collections.defaultdict(list)
    for idx,op in enumerate(ops):
        k,q=op[0],op[1:]
        if k=='x': m[q[0]]^=FULL
        elif k=='cx': a_,b_=q; m[b_]^=m[a_]; S[b_]=S[b_]^S[a_]
        elif k in ('ccx','ccx_dg','c3x','c3x_dg'):
            *ctl,t=q; prod=m[ctl[0]]
            for c in ctl[1:]: prod&=m[c]
            i=mask2node.get(prod)
            if i is not None: S[t]=S[t]^frozenset([i]); pres[i].append((idx,t))
            m[t]^=prod
    return pres

def find_wires(sn,masks,exclude):
    used=set(exclude); out=[]
    for mk in masks:
        w=next((x for x in range(18) if sn[x]==mk and x not in used),None)
        if w is None: return None
        used.add(w); out.append(w)
    return out

def split_out(ops, node, lo, hi):
    """remove node's value from its wire across [lo,hi] (uncompute before lo,
    recompute after hi).  Returns new ops or None."""
    sn=snaps(ops); pres=resid(ops); pr=pres.get(node,[])
    if len(pr)<2: return None
    a,b=pr[0][0],pr[-1][0]
    if not (a<lo and hi<b): return None
    opA=ops[a]; nm=opA[0]; ctl=list(opA[1:-1]); w=opA[-1]
    masks=[sn[a][c] for c in ctl]
    c1=find_wires(sn[lo],masks,[w]); c2=find_wires(sn[hi+1],masks,[w])
    if c1 is None or c2 is None: return None
    return ops[:lo]+[(INV[nm],)+tuple(c1)+(w,)]+ops[lo:hi+1]+[(nm,)+tuple(c2)+(w,)]+ops[hi+1:]

def rehome(ops,v,w,lo,hi):
    for i in range(lo,hi+1):
        qs=ops[i][1:]
        if v in qs and w in qs: return None      # rename would duplicate a bit
    out=list(ops)
    for i in range(lo,hi+1):
        op=out[i]
        if v in op[1:]:
            out[i]=(op[0],)+tuple(w if x==v else x for x in op[1:])
    return out

if __name__=='__main__':
    ops=list(pickle.load(open('cpen_search_11.pkl','rb'))[1])
    base=O.obj(ops); D0=base['depth']
    print('base depth %d cx %d'%(D0,base['cx']), flush=True)
    pres=resid(ops)
    # every node's residency and wire
    R={}
    for i,pr in pres.items():
        if len(pr)>=2: R[i]=(pr[0][0],pr[-1][0],pr[0][1])
    anc=[(i,a,b,w) for i,(a,b,w) in R.items() if w>=12]
    print('ancilla residencies: %d'%len(anc), flush=True)
    tried=0; okc=0; best=[]
    t0=time.time()
    for (j,aj,bj,v) in anc:
        for w in range(12,18):
            if w==v: continue
            # who occupies w during [aj,bj]?
            occ=[i for i,(a,b,ww) in R.items() if ww==w and not (b<aj or a>bj)]
            if len(occ)!=1: continue
            k=occ[0]
            if lev[k]!=0: continue               # must be recomputable at will
            o2=split_out(ops,k,aj,bj)
            if o2 is None: continue
            # indices shifted by 1 (an op was inserted at aj)
            o3=rehome(o2,v,w,aj+1,bj+1)
            if o3 is None: continue
            tried+=1
            if not exact(o3): continue
            okc+=1
            st=O.obj(o3)
            best.append((st['depth'],st['cx'],j,v,w,k))
            print('  n%-3d q%d->q%d (split n%d out) : depth %3d cx %3d  %+d'
                  %(j,v,w,k,st['depth'],st['cx'],st['depth']-D0), flush=True)
    best.sort()
    print('\ncompound moves tried %d | exact %d (%.0fs)'%(tried,okc,time.time()-t0))
    if best:
        print('best depth %d (base %d)'%(best[0][0],D0))
        print('moves that LOWER depth: %d'%sum(1 for r in best if r[0]<D0))
    pickle.dump(best,open('cpfe_comp.pkl','wb'))
