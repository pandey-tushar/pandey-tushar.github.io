import sys, time, pickle
sys.path.insert(0,'/home/user/classiq-challenge')
from cpen_fast import zeros, NON
import cpew_state as S, cpew_obj as O
from cpen_clean import expand

p,v,_,_ = pickle.load(open('cpev_search_s23.pkl','rb'))
pri,vec = list(p),list(v)
t0=time.time(); s=O.obj(S.realize(pri,vec,{})); t1=time.time()
print('base depth %d cx %d u3 %d dens %.4f  obj time %.2fs'
      %(s['depth'],s['cx'],s['u3'],s['density'],t1-t0), flush=True)

ops = S.realize(pri,vec,{})
z = zeros(ops)
# OLD alphabet: wires |0> at every occurrence
old={}
# NEW alphabet: ANY wire not in the op, at every occurrence (4-op form)
new={}
for i,o in enumerate(ops):
    if o[0] in NON:
        k=S.hkey(o)
        c_old=set(w for w in z[i] if w not in o[1:])
        c_new=set(w for w in range(18) if w not in o[1:])
        old[k]=c_old if k not in old else (old[k]&c_old)
        new[k]=c_new if k not in new else (new[k]&c_new)
old={k:sorted(x) for k,x in old.items() if x}
new={k:sorted(x) for k,x in new.items() if x}
print('OLD: %d keys, %d (key,wire) pairs' % (len(old), sum(len(x) for x in old.values())))
print('NEW: %d keys, %d (key,wire) pairs' % (len(new), sum(len(x) for x in new.values())))
nd=sum(1 for k in new for w in new[k] if w<12)
print('  of which host-on-DATA: %d pairs (never searched before)' % nd)
pickle.dump(new, open('cpey_hosts_all.pkl','wb'))
