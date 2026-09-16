"""CP-EZ: can the T=24 schedule's live node values be parked on 18 wires?
A node parked on data wire j is readable ONLY by operands containing raw bit
j, so a node is 'data-parkable on j' iff j is in EVERY consuming operand."""
import sys, pickle, collections
sys.path.insert(0,'/home/user/classiq-challenge')
import cpeu_dag as U
N,PH,nmask,A = U.load()
def raws(o): return set(w for w in range(12) if (o>>w)&1)
def nods(o): return [j for j in range(57) if (o>>(12+j))&1]

cons=collections.defaultdict(list)
for i in range(57):
    for o in N[i]:
        for k in nods(o): cons[k].append(o)
for t in PH:
    for o in t:
        for k in nods(o): cons[k].append(o)

park={}
for k in range(57):
    c=cons.get(k,[])
    park[k] = set.intersection(*[raws(o) for o in c]) if c else set(range(12))
npark=sum(1 for k in park if park[k])
print('nodes parkable on SOME data wire (raw bit common to every consumer): %d / 57'%npark)
h=collections.Counter(len(park[k]) for k in park)
print('common-raw-bit count histogram:', dict(sorted(h.items())))

S=pickle.load(open('cpet_sched_K18_T24.pkl','rb'))
print('\nper-step: live values, parkable vs needing a clean ancilla')
worst=-99
for t in range(1,len(S)):
    live=set(S[t]); p=[k for k in live if park[k]]; np_=[k for k in live if not park[k]]
    deficit=len(np_)-6
    worst=max(worst,deficit)
    print('  t=%-3d live %2d  parkable %2d  needs-ancilla %2d  (deficit %+d)'
          %(t,len(live),len(p),len(np_),deficit))
print('\nworst deficit of non-parkable values over 6 ancillas: %+d'%worst)
print('=> %s' % ('every live value can be parked on 18 wires'
                 if worst<=0 else 'INFEASIBLE: too many values need a clean ancilla'))
