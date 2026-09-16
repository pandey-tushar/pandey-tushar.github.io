"""CP-FA: EXACT symbolic trace of the banked op list.
Wire state = (affine mask over 12 raw bits, const bit, frozenset of nodes).
Tracked through the ops, never decomposed -- so the numbers are exact."""
import sys, pickle, collections
sys.path.insert(0,'/home/user/classiq-challenge')
import cpet_vdag as V
from cpen_fast import NON

ops = list(pickle.load(open('cpen_search_11.pkl','rb'))[1])
nodes, nmask, phases, _ = V.vdag(ops)
n = len(nodes); FULL = V.FULL; RM = V.raw_masks(12)
mask2node = {}
for i in range(n): mask2node.setdefault(nmask[i], i)

aff = [1 << w if w < 12 else 0 for w in range(18)]   # raw-bit affine part
cst = [0]*18
S   = [frozenset() for _ in range(18)]
m   = [RM[w] if w < 12 else 0 for w in range(18)]    # truth mask, for identifying nodes

setsize=collections.Counter(); live_hist=[]; reloc=0; basemix=0
where=collections.defaultdict(set)   # node -> set of wires it has ever occupied
prev_loc={}
unknown=0
for op in ops:
    k,q = op[0], op[1:]
    if k=='x':
        cst[q[0]] ^= 1; m[q[0]] ^= FULL
    elif k=='cx':
        a,b=q
        aff[b]^=aff[a]; cst[b]^=cst[a]; S[b]=S[b]^S[a]; m[b]^=m[a]
        if a<12 and b<12: basemix+=1
    elif k in ('ccx','ccx_dg','c3x','c3x_dg'):
        *ctl,t = q
        prod = m[ctl[0]]
        for c in ctl[1:]: prod &= m[c]
        i = mask2node.get(prod)
        if i is None: unknown += 1
        else: S[t] = S[t] ^ frozenset([i])
        m[t] ^= prod
    elif k in ('cz','ccz'): pass
    if k in NON:
        liv=set()
        for w in range(18):
            setsize[len(S[w])]+=1
            for i in S[w]: liv.add(i); where[i].add(w)
        live_hist.append(len(liv))
        loc={}
        for w in range(18):
            for i in S[w]: loc.setdefault(i,set()).add(w)
        for i,ws in loc.items():
            if i in prev_loc and prev_loc[i]!=ws: reloc+=1
        prev_loc=loc

print('ops %d  nonlinear %d  nodes %d  unidentified products %d'%(len(ops),sum(1 for o in ops if o[0] in NON),n,unknown))
print('wire node-set SIZE histogram :', dict(sorted(setsize.items())))
print('max nodes on one wire        :', max(setsize))
print('max distinct live node values:', max(live_hist), ' (18 wires available)')
print('mean live                    : %.1f'%(sum(live_hist)/len(live_hist)))
print('node location-change events  :', reloc)
print('data->data cx (base mixing)  :', basemix)
print('distinct wires a node ever occupies:', dict(sorted(collections.Counter(len(v) for v in where.values()).items())))
print('total cx in list             :', sum(1 for o in ops if o[0]=='cx'))
