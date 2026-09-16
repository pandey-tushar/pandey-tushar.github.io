"""CP-FA: replay the BANKED op list in the symbolic (set-valued) domain and
record exactly which freedoms it uses.  The next model must contain this."""
import sys, pickle, collections
sys.path.insert(0,'/home/user/classiq-challenge')
import cpet_vdag as V
from cpen_fast import NON

ops = list(pickle.load(open('cpen_search_11.pkl','rb'))[1])
nodes, nmask, phases, _ = V.vdag(ops)
n = len(nodes)
print('banked list: %d ops, %d nonlinear, %d nodes' % (len(ops), sum(1 for o in ops if o[0] in NON), n))

# symbolic replay: wire -> (raw affine mask over 12 bits, const, set of nodes)
# node identity is recovered by matching the AND of operand masks; instead we
# track the 4096-bit truth mask per wire and match against node masks.
RM = V.raw_masks(12)
NODEMASK = {i: nmask[i] for i in range(n)}
mask2node = {nmask[i]: i for i in range(n)}
FULL = V.FULL

m = [RM[w] if w < 12 else 0 for w in range(18)]
base = [RM[w] if w < 12 else 0 for w in range(18)]

def decompose(val, w):
    """express wire value as base(w) ^ XOR(subset of node masks), greedily."""
    cur = val ^ base[w]; S = []
    changed = True
    while cur and changed:
        changed = False
        for i in range(n):
            if nmask[i] and (cur & nmask[i]) == nmask[i] and bin(cur ^ nmask[i]).count('1') < bin(cur).count('1'):
                cur ^= nmask[i]; S.append(i); changed = True; break
    return S, cur

setsize = collections.Counter(); relocate = collections.Counter()
home = {}; reloc_events = 0; basemix = 0
distinct_live = []
nsteps = 0
for op in ops:
    k, q = op[0], op[1:]
    if k == 'x':   m[q[0]] ^= FULL
    elif k == 'cx':
        m[q[1]] ^= m[q[0]]
        if q[1] < 12 and q[0] < 12: basemix += 1
    elif k in ('ccx','ccx_dg'): m[q[2]] ^= m[q[0]] & m[q[1]]
    elif k in ('c3x','c3x_dg'): m[q[3]] ^= m[q[0]] & m[q[1]] & m[q[2]]
    elif k in ('cz','ccz'): pass
    if k in NON:
        nsteps += 1
        live = set()
        for w in range(18):
            S, rem = decompose(m[w], w)
            setsize[len(S)] += 1
            for i in S: live.add(i)
            for i in S:
                if home.get(i) not in (None, w):
                    reloc_events += 1
                home[i] = w
        distinct_live.append(len(live))

print('\nwire node-set SIZE histogram over all nonlinear steps:', dict(sorted(setsize.items())))
print('max nodes on one wire            :', max(setsize))
print('max distinct live node values    :', max(distinct_live))
print('node RELOCATION events           :', reloc_events)
print('data-wire -> data-wire cx (affine mixing of bases):', basemix)
print('nonlinear steps                  :', nsteps)
