"""CP-FB: at each wire-sharing artifact on the critical chain, how many wires
are FREE (holding exactly their base)?  That decides whether the 11 artifact
edges can be broken by re-assigning a wire."""
import sys, pickle, collections
sys.path.insert(0,'/home/user/classiq-challenge')
import cpet_vdag as V
import cpeu_dag as U
from cpen_fast import NON

ops=list(pickle.load(open('cpen_search_11.pkl','rb'))[1])
N,PH,nmask,A=U.load(); preds=A['preds']
mask2node={}
for i in range(57): mask2node.setdefault(nmask[i],i)
RM=V.raw_masks(12); FULL=V.FULL
BASE=[RM[w] if w<12 else 0 for w in range(18)]

# first pass: record wire state before each op index
m=[RM[w] if w<12 else 0 for w in range(18)]
snap=[]
for op in ops:
    snap.append(list(m))
    k,q=op[0],op[1:]
    if k=='x': m[q[0]]^=FULL
    elif k=='cx': m[q[1]]^=m[q[0]]
    elif k in ('ccx','ccx_dg'): m[q[2]]^=m[q[0]]&m[q[1]]
    elif k in ('c3x','c3x_dg'): m[q[3]]^=m[q[0]]&m[q[1]]&m[q[2]]

# recompute the critical chain (same walk as cpfb_why)
val={w:('in',w) for w in range(18)}
depth=collections.defaultdict(int); parent={}; owner={}
m=[RM[w] if w<12 else 0 for w in range(18)]
best=(0,None)
for idx,op in enumerate(ops):
    k,q=op[0],op[1:]
    if k=='x': m[q[0]]^=FULL; continue
    if k=='cx':
        a,b=q; m[b]^=m[a]
        d=max(depth[val[a]],depth[val[b]]); src=val[a] if depth[val[a]]>=depth[val[b]] else val[b]
        nv=('v',idx); depth[nv]=d; parent[nv]=src; owner[nv]=('cx',idx,a,b); val[b]=nv
    elif k in ('cz','ccz'): pass
    else:
        *ctl,t=q; prod=m[ctl[0]]
        for c in ctl[1:]: prod&=m[c]
        i=mask2node.get(prod)
        d,src,sw=max([(depth[val[w]],val[w],w) for w in list(ctl)+[t]])
        nv=('v',idx); depth[nv]=d+1; parent[nv]=src
        owner[nv]=('nl',idx,i,tuple(ctl),t,sw); val[t]=nv; m[t]^=prod
        if d+1>best[0]: best=(d+1,nv)
chain=[]; cur=best[1]
while cur in owner: chain.append(owner[cur]); cur=parent.get(cur)
chain.reverse(); nl=[c for c in chain if c[0]=='nl']

print('artifact edges on the critical chain and the wire slack at each:')
prev=None; nart=0; tot_free=[]
for c in nl:
    _,idx,i,ctl,t,sw=c
    if prev is not None:
        pi,pidx=prev
        same_node = (pi==i)
        genuine = (pi is not None and i is not None and pi in preds[i])
        if not genuine and not same_node:
            nart+=1
            st=snap[idx]
            free=[w for w in range(18) if st[w]==BASE[w] and w!=sw]
            tot_free.append(len(free))
            print('  op %-4d n%-3s shares q%-2d with n%-3s : %2d free wires %s'
                  %(idx,i,sw,pi,len(free),free))
    prev=(i,idx)
print()
print('artifact edges examined: %d'%nart)
if tot_free:
    print('free wires at those moments: min %d  max %d  mean %.1f'
          %(min(tot_free),max(tot_free),sum(tot_free)/len(tot_free)))
    print('edges with ZERO free wires : %d'%sum(1 for f in tot_free if f==0))
