"""CP-FD: SHORTEN A RESIDENCY by splitting it.
Node i is computed at op a and uncomputed at op b.  Inside a consumer gap
(ga,gb) insert an uncompute after ga and a recompute before gb, so the wire
is free across the gap.  Level-0 nodes have purely affine operands, so the
recompute needs nothing live.
Verified with cpae_core.sim_exact (real gate matrices) -- the mask replay
would NOT catch a Margolus relative phase that fails to cancel."""
import sys, pickle, collections, time
sys.path.insert(0,'/home/user/classiq-challenge')
import cpet_vdag as V
import cpeu_dag as U
import cpae_core as C
from cpen_fast import NON, INV
RM=V.raw_masks(12); FULL=V.FULL
FV=C.fvec(C.SHAPES['LOGO'])

def snaps(ops):
    m=[RM[w] if w<12 else 0 for w in range(18)]; out=[]
    for op in ops:
        out.append(list(m))
        k,q=op[0],op[1:]
        if k=='x': m[q[0]]^=FULL
        elif k=='cx': m[q[1]]^=m[q[0]]
        elif k in ('ccx','ccx_dg'): m[q[2]]^=m[q[0]]&m[q[1]]
        elif k in ('c3x','c3x_dg'): m[q[3]]^=m[q[0]]&m[q[1]]&m[q[2]]
    out.append(list(m)); return out

def exact(ops):
    qc=C.ops_to_qc(ops,18)
    gl,gp=C.extract(qc)
    err,mism=C.sim_exact(gl,gp,FV)
    return err<1e-9 and mism==0, err, mism

def find_wires(sn, masks, exclude):
    """wires holding exactly these masks at this point, all distinct."""
    used=set(exclude); out=[]
    for mk in masks:
        w=next((x for x in range(18) if sn[x]==mk and x not in used), None)
        if w is None: return None
        used.add(w); out.append(w)
    return out

def split(ops, a, b, ga, gb):
    """insert uncompute after index ga, recompute before index gb."""
    sn=snaps(ops)
    opA=ops[a]; nm=opA[0]; ctl=list(opA[1:-1]); w=opA[-1]
    masks=[sn[a][c] for c in ctl]
    p=ga+1; q=gb
    c1=find_wires(sn[p], masks, [w])
    c2=find_wires(sn[q], masks, [w])
    if c1 is None or c2 is None: return None
    un=(INV[nm],)+tuple(c1)+(w,)
    re=(nm,)+tuple(c2)+(w,)
    out=ops[:p]+[un]+ops[p:q]+[re]+ops[q:]
    return out

if __name__=='__main__':
    import cpew_obj as O
    ops=list(pickle.load(open('cpen_search_11.pkl','rb'))[1])
    base=O.obj(ops)
    ok,err,mism=exact(ops)
    print('base depth %d cx %d | sim_exact %s err %.2e'%(base['depth'],base['cx'],ok,err), flush=True)
    CAND=pickle.load(open('cpfd_cands.pkl','rb')) if False else None
    # recompute candidates here (level-0, gap>=15)
    import cpfd_gaps as G
    N,PH,nmask,A=U.load(); lev=A['lev']
    mask2node={}
    for i in range(57): mask2node.setdefault(nmask[i],i)
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
    cands=[]
    for i in range(57):
        if lev[i]!=0: continue
        pr=present.get(i,[])
        if len(pr)<2: continue
        a,b=pr[0][0],pr[-1][0]
        rd=sorted(set(x for x in reads.get(i,[]) if a<x<b))
        if not rd: continue
        pts=[a]+rd+[b]
        for j in range(len(pts)-1):
            g=pts[j+1]-pts[j]
            if g>=15: cands.append((g,i,a,b,pts[j],pts[j+1]))
    cands.sort(reverse=True)
    print('level-0 split candidates: %d'%len(cands), flush=True)
    res=[]
    for g,i,a,b,ga,gb in cands:
        o2=split(ops,a,b,ga,gb)
        if o2 is None:
            print('  n%-3d gap %3d : operands unavailable at an insertion point'%(i,g), flush=True); continue
        ok,err,mism=exact(o2)
        if not ok:
            print('  n%-3d gap %3d : NOT EXACT (err %.2e mism %d)'%(i,g,err,mism), flush=True); continue
        st=O.obj(o2)
        res.append((st['depth'],st['cx'],i,g,ga,gb))
        print('  n%-3d gap %3d : EXACT  depth %3d cx %3d  %+d'
              %(i,g,st['depth'],st['cx'],st['depth']-base['depth']), flush=True)
    res.sort(); pickle.dump(res,open('cpfd_split.pkl','wb'))
    print('\nsplits that LOWER depth: %d | neutral: %d'
          %(sum(1 for r in res if r[0]<base['depth']),sum(1 for r in res if r[0]==base['depth'])))
