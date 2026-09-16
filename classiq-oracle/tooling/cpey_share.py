import sys, pickle, collections
sys.path.insert(0,'/home/user/classiq-challenge')
from cpen_fast import NON
import cpew_state as S
p,v,_,_ = pickle.load(open('cpev_search_s23.pkl','rb'))
ops = S.realize(list(p),list(v),{})
non=[o for o in ops if o[0] in NON]
print('nonlinear ops: %d' % len(non))
# group by CONTROL SET (unordered), ignoring target and direction
g=collections.defaultdict(list)
for i,o in enumerate(ops):
    if o[0] in NON:
        g[tuple(sorted(o[1:-1]))].append((i,o[0],o[-1]))
print('distinct control sets: %d' % len(g))
h=collections.Counter(len(v) for v in g.values())
print('occurrences-per-control-set histogram:', dict(sorted(h.items())))
print('\ncontrol sets with >=4 occurrences (fan-out candidates):')
for cs,occ in sorted(g.items(), key=lambda kv:-len(kv[1])):
    if len(occ)<4: continue
    tgts=collections.Counter(t for _,_,t in occ)
    print('  ctrl %-14s n=%-3d targets %s' % (str(cs),len(occ),dict(tgts)))
tot=sum(len(v) for v in g.values())
print('\nslot-units now  : %d' % (10*tot))
best=sum(min(10*len(occ), 20+4*len(set(t for _,_,t in occ))) for occ in g.values())
print('slot-units fanout: %d  (%.0f%% of now)' % (best, 100.0*best/(10*tot)))
