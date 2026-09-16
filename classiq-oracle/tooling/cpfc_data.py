"""CP-FC: rehome an ancilla residency onto an untouched DATA wire.
Renaming w->j changes the carried value from n_i to x_j ^ n_i, so it is only
exact when every read inside the residency wants x_j too.  Verified by full
4096-input phase replay, not by a wire-cleanliness check."""
import sys, pickle, time
sys.path.insert(0,'/home/user/classiq-challenge')
import cpfc_rehome as R
import cpet_wide as W
import cpdh_core as DH
import cpew_obj as O

ops=R.load(); snap=R.wire_masks(ops); res=R.residencies(ops,snap)
BASE=[R.RM[w] if w<12 else 0 for w in range(18)]
WANT=DH.want_mask('LOGO')
base=O.obj(ops)
print('base depth %d cx %d'%(base['depth'],base['cx']), flush=True)

cands=[]
for w,a,b in res:
    tch=R.touched(ops,a,b)
    for j in range(18):
        if j==w or j in tch: continue
        if any(snap[i][j]!=BASE[j] for i in range(a,b+2)): continue
        cands.append((w,a,b,j))
print('candidate rehomes (any base): %d'%len(cands), flush=True)

ok=[]; bad=0
t0=time.time()
for k,(w,a,b,j) in enumerate(cands):
    o2=R.rehome(ops,w,a,b,j)
    try: ph,dirty = W.replay(o2,18)
    except Exception: bad+=1; continue
    if dirty or (ph^WANT)!=0:
        bad+=1; continue
    st=O.obj(o2)
    ok.append((st['depth'],st['cx'],w,a,b,j))
    print('  EXACT rehome q%d[%d,%d]->q%d : depth %d cx %d  %+d'
          %(w,a,b,j,st['depth'],st['cx'],st['depth']-base['depth']), flush=True)
ok.sort()
print('\ncandidates %d | exact %d | changed the function %d (%.0fs)'
      %(len(cands),len(ok),bad,time.time()-t0))
if ok:
    print('best: depth %d (base %d)'%(ok[0][0],base['depth']))
    print('rehomes that LOWER depth: %d'%sum(1 for r in ok if r[0]<base['depth']))
pickle.dump(ok,open('cpfc_data.pkl','wb'))
