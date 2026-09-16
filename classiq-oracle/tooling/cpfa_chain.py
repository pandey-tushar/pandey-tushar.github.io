"""CP-FA: longest chain of NONLINEAR ops in the banked list's SSA dependency
DAG, vs what the value DAG actually requires (6 forward levels + 6 mirror)."""
import sys, pickle, collections
sys.path.insert(0,'/home/user/classiq-challenge')
import cpet_vdag as V
import cpeu_dag as U
from cpen_fast import NON

ops = list(pickle.load(open('cpen_search_11.pkl','rb'))[1])
N,PH,nmask,A = U.load()
print('value DAG levels %s -> forward AND-depth %d, mirrored %d'
      %(A['levelw'], len(A['levelw']), 2*len(A['levelw'])))

# SSA: each wire write creates a new value; edges from readers to the value
val = {w: ('in', w) for w in range(18)}
depth = collections.defaultdict(int)     # value -> longest nonlinear chain to produce it
nl_chain = 0
for op in ops:
    k, q = op[0], op[1:]
    if k == 'x':
        continue
    if k == 'cx':
        a, b = q
        d = max(depth[val[a]], depth[val[b]])
        nv = ('v', id(op)); depth[nv] = d; val[b] = nv
    elif k in ('cz', 'ccz'):
        d = max(depth[val[w]] for w in q)
        nl_chain = max(nl_chain, d + 1)
    else:
        *ctl, t = q
        d = max([depth[val[w]] for w in ctl] + [depth[val[t]]])
        nv = ('v', id(op)); depth[nv] = d + 1; val[t] = nv
        nl_chain = max(nl_chain, d + 1)
print('banked list: longest NONLINEAR chain (SSA, unlimited wires) = %d' % nl_chain)
print('  x 7 layers/gadget                         ~ %d layers' % (7*nl_chain))
print('  measured SSA critical path (cpey_crit)      211')
print('  measured real depth                         249')
print()
need = 2*len(A['levelw'])
print('the DAG needs a nonlinear chain of only %d' % need)
print('=> the banked list is %.2fx longer than the DAG requires' % (nl_chain/need))
print('   a chain of %d would predict ~%d layers' % (need, 7*need))
