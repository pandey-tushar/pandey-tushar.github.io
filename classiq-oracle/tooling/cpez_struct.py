"""CP-EZ: can node values live ON data wires?  For each node k, look at the
operands that consume n_k and see whether they carry a raw bit (so n_k can be
XORed into that data wire and the operand read in place)."""
import sys, collections
sys.path.insert(0,'/home/user/classiq-challenge')
import cpeu_dag as U
N,PH,nmask,a = U.load(); CST=U.CST
def terms(o): return [w for w in range(12) if (o>>w)&1], [j for j in range(57) if (o>>(12+j))&1]

allops=[(i,o) for i in range(57) for o in N[i]] + [(-1,o) for t in PH for o in t]
cons=collections.defaultdict(list)          # node k -> operands consuming it
for i,o in allops:
    r,s=terms(o)
    for j in s: cons[j].append((i,o,len(r),len(s)))

nraw=collections.Counter(); ok=0; tot=0
for k in range(57):
    c=cons.get(k,[])
    if not c: continue
    tot+=1
    # can n_k sit on a data wire?  every consuming operand must carry >=1 raw bit
    hasraw=[x for x in c if x[2]>=1]
    if len(hasraw)==len(c): ok+=1
    nraw[len(hasraw)==len(c)]+=1
print('nodes consumed by >=1 operand: %d'%tot)
print('nodes whose EVERY consumer carries a raw bit (data-wire resident): %d'%ok)

# how many operands are exactly (one raw bit) ^ (nodes)?  -> in-place read
inplace=sum(1 for i,o in allops if len(terms(o)[0])==1)
noraw  =sum(1 for i,o in allops if len(terms(o)[0])==0)
multiraw=sum(1 for i,o in allops if len(terms(o)[0])>1)
print('\noperands total %d : 1 raw bit %d | 0 raw bits %d | >1 raw bits %d'
      %(len(allops),inplace,noraw,multiraw))
h=collections.Counter((len(terms(o)[0]),len(terms(o)[1])) for i,o in allops)
print('(raw,node) histogram:')
for k in sorted(h): print('   raw %d node %d : %d'%(k[0],k[1],h[k]))

# peak simultaneous node-liveness by DAG level (a node is live from its
# computation until its last consumer)
lev=a['lev']
last={}
for i,o in allops:
    for j in terms(o)[1]:
        last[j]=max(last.get(j,0), lev[i] if i>=0 else 6)
live=collections.Counter()
for k in range(57):
    if k not in last: continue
    for L in range(lev[k]+1, last[k]+1): live[L]+=1
print('\nnode liveness by level (level-ordered forward pass):', dict(sorted(live.items())))
print('peak live node values: %d   (ancillas available: 6, data wires: 12)'%max(live.values()))
