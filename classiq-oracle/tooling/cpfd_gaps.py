"""CP-FD: where are the splittable residencies?
For each node: its compute op, its consumers, the gaps between consecutive
consumers, and whether it can be recomputed at will (operands purely affine
= level 0, or operands still live across the gap)."""
import sys, pickle, collections
sys.path.insert(0,'/home/user/classiq-challenge')
import cpet_vdag as V
import cpeu_dag as U
from cpen_fast import NON
RM=V.raw_masks(12); FULL=V.FULL

ops=list(pickle.load(open('cpen_search_11.pkl','rb'))[1])
N,PH,nmask,A=U.load(); lev=A['lev']
mask2node={}
for i in range(57): mask2node.setdefault(nmask[i],i)

# symbolic per-wire node sets, to know when node i is present on wire w
m=[RM[w] if w<12 else 0 for w in range(18)]
S=[frozenset() for _ in range(18)]
present=collections.defaultdict(list)   # node -> [(op index, wire)] where written
reads=collections.defaultdict(list)     # node -> [op indices reading it]
for idx,op in enumerate(ops):
    k,q=op[0],op[1:]
    # a read = any wire used whose set contains node i
    for w in q:
        for i in S[w]:
            reads[i].append(idx)
    if k=='x': m[q[0]]^=FULL
    elif k=='cx':
        a,b=q; m[b]^=m[a]; S[b]=S[b]^S[a]
    elif k in ('ccx','ccx_dg','c3x','c3x_dg'):
        *ctl,t=q
        prod=m[ctl[0]]
        for c in ctl[1:]: prod&=m[c]
        i=mask2node.get(prod)
        if i is not None:
            S[t]=S[t]^frozenset([i]); present[i].append((idx,t))
        m[t]^=prod

print('node  lev  residency  #reads  largest consumer gap   recomputable?')
tot_gap=0; cands=[]
for i in range(57):
    pr=present.get(i,[])
    if len(pr)<2: continue
    a=pr[0][0]; b=pr[-1][0]
    rd=sorted(set(x for x in reads.get(i,[]) if a<x<b))
    if not rd: continue
    pts=[a]+rd+[b]
    gaps=[(pts[j+1]-pts[j], pts[j], pts[j+1]) for j in range(len(pts)-1)]
    g,ga,gb=max(gaps)
    free = (lev[i]==0)
    tot_gap += g if free else 0
    if free and g>=15: cands.append((g,i,ga,gb,a,b))
    print('  n%-3d  %d   [%3d,%3d]=%3d  %2d      %3d  (ops %d..%d)   %s'
          %(i,lev[i],a,b,b-a,len(rd),g,ga,gb,'YES (affine operands)' if free else 'needs live operands'))
cands.sort(reverse=True)
print()
print('level-0 nodes with a consumer gap >= 15 ops: %d'%len(cands))
for g,i,ga,gb,a,b in cands[:15]:
    print('   n%-3d gap %3d (ops %d..%d) of residency [%d,%d]'%(i,g,ga,gb,a,b))
print('\ntotal freeable op-slots from level-0 splits: %d (of 1887 residency slots)'%tot_gap)
