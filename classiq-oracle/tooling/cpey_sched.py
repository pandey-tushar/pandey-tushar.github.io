"""CP-EY: operand-assembly demand of the K=18/T=24 pebble schedule under the
XOR-accumulation (resident) model, vs the naive fresh-scratch model."""
import sys, pickle, collections
sys.path.insert(0,'/home/user/classiq-challenge')
import cpeu_dag as U
N,PH,nmask,a = U.load()
CST=U.CST
def terms(o):
    return [w for w in range(12) if (o>>w)&1], [j for j in range(57) if (o>>(12+j))&1]

S=pickle.load(open('cpet_sched_K18_T24.pkl','rb'))
T=len(S)-1
print('schedule steps %d  (K=18, CP-SAT OPTIMAL)'%T)
prev=set(S[0]); tot=0
print('%3s %5s %6s %8s %9s %9s'%('t','live','toggle','operands','fresh-wires','rawreads'))
peak_fresh=0; peak_live=0
for t in range(1,len(S)):
    cur=set(S[t]); tog=cur^prev
    ops=[]; raws=set()
    for i in tog:
        for o in N[i]:
            ops.append(o); r,_=terms(o); raws|=set(r)
    distinct=len(set(ops))
    fresh=len(ops)                     # cpet_emit3: one wire per operand instance
    peak_fresh=max(peak_fresh,fresh); peak_live=max(peak_live,len(cur))
    tot+=len(tog)
    print('%3d %5d %6d %8d %9d %9d'%(t,len(cur),len(tog),distinct,fresh,len(raws)))
    prev=cur
print('\ntoggles %d   peak live %d   peak fresh-operand wires %d'%(tot,peak_live,peak_fresh))
print('=> naive emitter needs ~%d + 12 raw = %d wires at the widest step (measured 123 total)'
      %(peak_fresh,peak_fresh+12))
# how many operands are single-part (readable in place, no assembly)?
allops=[o for i in range(57) for o in N[i]]
sing=sum(1 for o in allops if len(terms(o)[0])+len(terms(o)[1])<=1)
multi=collections.Counter(len(terms(o)[0])+len(terms(o)[1]) for o in allops)
print('\noperand size histogram (raw+node parts):',dict(sorted(multi.items())))
print('single-part operands (free to read in place): %d / %d'%(sing,len(allops)))
