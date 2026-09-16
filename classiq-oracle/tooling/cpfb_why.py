"""CP-FB: extract the banked list's critical chain of 26 nonlinear ops and
classify every edge: genuine value-DAG dependency, or wire-sharing artifact?"""
import sys, pickle, collections
sys.path.insert(0,'/home/user/classiq-challenge')
import cpet_vdag as V
import cpeu_dag as U
from cpen_fast import NON

ops = list(pickle.load(open('cpen_search_11.pkl','rb'))[1])
N,PH,nmask,A = U.load(); preds=A['preds']
mask2node={}
for i in range(57): mask2node.setdefault(nmask[i],i)
RM=V.raw_masks(12); FULL=V.FULL
m=[RM[w] if w<12 else 0 for w in range(18)]

val={w:('in',w) for w in range(18)}
depth=collections.defaultdict(int); parent={}; owner={}
best=(0,None)
for idx,op in enumerate(ops):
    k,q=op[0],op[1:]
    if k=='x': m[q[0]]^=FULL; continue
    if k=='cx':
        a,b=q; m[b]^=m[a]
        d=max(depth[val[a]],depth[val[b]])
        src = val[a] if depth[val[a]]>=depth[val[b]] else val[b]
        nv=('v',idx); depth[nv]=d; parent[nv]=src; owner[nv]=('cx',idx,a,b); val[b]=nv
    elif k in ('cz','ccz'):
        pass
    else:
        *ctl,t=q
        prod=m[ctl[0]]
        for c in ctl[1:]: prod&=m[c]
        i=mask2node.get(prod)
        cands=[(depth[val[w]],val[w],w) for w in list(ctl)+[t]]
        d,src,sw=max(cands)
        nv=('v',idx); depth[nv]=d+1; parent[nv]=src
        owner[nv]=('nl',idx,i,tuple(ctl),t,sw); val[t]=nv
        m[t]^=prod
        if d+1>best[0]: best=(d+1,nv)

# walk the chain back
chain=[]; cur=best[1]
while cur in owner:
    chain.append(owner[cur]); cur=parent.get(cur)
chain.reverse()
nl=[c for c in chain if c[0]=='nl']
print('critical chain length (nonlinear ops) = %d'%len(nl))
gen=0; art=0; det=[]
prev=None
for c in nl:
    _,idx,i,ctl,t,sw = c
    if prev is None: det.append((i,'start',sw)); prev=(i,t,ctl); continue
    pi,pt,pctl = prev
    # genuine iff the previous node's VALUE feeds this node's operands
    genuine = pi is not None and i is not None and pi in preds[i]
    if genuine: gen+=1; det.append((i,'DAG dep on n%s'%pi,sw))
    else:
        art+=1
        why = 'same wire q%d reused'%sw if sw==pt else 'operand assembly on q%d'%sw
        det.append((i,'ARTIFACT (%s, prev n%s)'%(why,pi),sw))
    prev=(i,t,ctl)
print('  genuine value-DAG dependencies : %d'%gen)
print('  wire-sharing / assembly edges  : %d'%art)
print()
for i,(node,why,sw) in enumerate(det):
    print('   %2d  n%-3s  %s'%(i,node,why))
