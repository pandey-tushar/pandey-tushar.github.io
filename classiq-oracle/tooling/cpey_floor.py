"""CP-EY: true depth floor of the 57-node value DAG, unlimited wires.
Compares SERIAL xor accumulation (what the op list does) against BALANCED
xor trees (what associativity permits).  Forward pass, then x2 for the
compute/uncompute mirror."""
import sys, math
sys.path.insert(0,'/home/user/classiq-challenge')
import cpeu_dag as U

N, PH, nmask, a = U.load()
CST = U.CST
lev = a['lev']

def terms(o):
    """(list of raw-wire bits, list of node indices) of an operand mask."""
    raw=[w for w in range(12) if (o>>w)&1]
    nod=[j for j in range(57) if (o>>(12+j))&1]
    return raw, nod

def crit(mode, and_cost=7, and3_cost=13):
    rdy=[None]*57
    order=sorted(range(57), key=lambda i: lev[i])
    for i in order:
        st=0
        for o in N[i]:
            raw,nod=terms(o)
            m=len(raw)+len(nod)
            base=max([rdy[j] for j in nod], default=0)
            if m<=1: acc=0
            elif mode=='serial': acc=m-1          # t^=a; t^=b; ... in place
            else:                acc=math.ceil(math.log2(m))   # balanced tree
            st=max(st, base+acc)
        rdy[i]=st+(and_cost if len(N[i])==2 else and3_cost)
    # phase terms: each is an AND of operands, then a CZ/CCZ
    ph=0
    for t in PH:
        st=0
        for o in t:
            raw,nod=terms(o)
            m=len(raw)+len(nod)
            base=max([rdy[j] for j in nod], default=0)
            if m<=1: acc=0
            elif mode=='serial': acc=m-1
            else:                acc=math.ceil(math.log2(m))
            st=max(st, base+acc)
        ph=max(ph, st)
    return max(max(rdy), ph)

print('value DAG: %d nodes, levels %s, arity2 %d arity3 %d'
      %(len(N), a['levelw'], sum(1 for x in N if len(x)==2), sum(1 for x in N if len(x)==3)))
print('phase terms: %d (simplified %d)'%(len(PH), len(U.simplify_phases(PH))))
print()
for mode in ('serial','tree'):
    f=crit(mode)
    print('%-7s xor accumulation : forward %3d   x2 mirror = %3d'%(mode,f,2*f))
print()
print('MEASURED SSA critical path of the realized op list : 211')
print('MEASURED real transpiled depth                     : 249')
print('LEADER                                             : 137')
