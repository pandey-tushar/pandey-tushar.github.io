"""cpfl_crit: parity tracking on a u3/cx circuit; critical-path composition and
relocation options for diagonal phases (same parity elsewhere with slack)."""
import sys, math, collections
sys.path.insert(0,'/home/user/classiq-challenge')
from qiskit import QuantumCircuit, transpile

def load(path):
    qc=QuantumCircuit.from_qasm_file(path)
    t=transpile(qc,basis_gates=['u3','cx'],optimization_level=2)
    g=[]
    for inst in t.data:
        qs=[t.find_bit(q).index for q in inst.qubits]; nm=inst.operation.name
        if nm=='cx': g.append(('cx',qs[0],qs[1],None))
        else:
            th,ph,la=[float(p) for p in inst.operation.params]
            diag = abs(math.sin(th/2))<1e-9
            g.append(('rz' if diag else 'u',qs[0],None,(th,ph,la)))
    return t,g

def times(g,n):
    ready=[0]*n; asap=[]
    for k,(nm,a,b,_) in enumerate(g):
        qs=[a] if b is None else [a,b]
        tt=max(ready[q] for q in qs); asap.append(tt)
        for q in qs: ready[q]=tt+1
    D=max(ready)
    late=[D]*n; alap=[0]*len(g)
    for k in range(len(g)-1,-1,-1):
        nm,a,b,_=g[k]; qs=[a] if b is None else [a,b]
        tt=min(late[q] for q in qs)-1; alap[k]=tt
        for q in qs: late[q]=tt
    return asap,alap,D

def parity_track(g,n):
    """label per wire as frozenset of symbols; fresh symbol after non-diagonal u."""
    lab=[frozenset([('q',i)]) for i in range(n)]; fresh=0; out=[]
    for k,(nm,a,b,_) in enumerate(g):
        if nm=='cx': lab[b]=lab[b]^lab[a]; out.append(None)
        elif nm=='u': out.append(lab[a]); fresh+=1; lab[a]=frozenset([('f',fresh)])
        else: out.append(lab[a])
    return out

if __name__=='__main__':
    t,g=load(sys.argv[1]); n=t.num_qubits
    asap,alap,D=times(g,n)
    crit=[k for k in range(len(g)) if asap[k]==alap[k]]
    comp=collections.Counter(g[k][0] for k in crit)
    print('depth',D,'gates',len(g),'critical gates',len(crit),dict(comp))
    # per layer: how many critical gates in each layer (1 => single critical path there)
    per=collections.Counter(asap[k] for k in crit)
    print('layers with exactly one critical gate',sum(1 for v in per.values() if v==1),'of',D)
    print('critical rz layers where that rz is the only critical gate',
          sum(1 for k in crit if per[asap[k]]==1 and g[k][0]=='rz'))
    print('critical u  layers where that u is the only critical gate',
          sum(1 for k in crit if per[asap[k]]==1 and g[k][0]=='u'))
    # slack of rz: adjacent u3 on same wire (fusable, zero cost) count
    lab=parity_track(g,n)
    # for each critical rz, count alternative (wire, gap) with same parity label
    wire_hist=collections.defaultdict(list)   # label -> list of (wire, asap-range)
    ready=[0]*n; cur=[frozenset([('q',i)]) for i in range(n)]; start=[0]*n
    segs=collections.defaultdict(list)
    for k,(nm,a,b,_) in enumerate(g):
        qs=[a] if b is None else [a,b]
        tt=asap[k]
        if nm=='cx':
            segs[cur[b]].append((b,start[b],tt)); cur[b]=cur[b]^cur[a]; start[b]=tt+1
        elif nm=='u':
            segs[cur[a]].append((a,start[a],tt)); cur[a]=frozenset([('u',k)]); start[a]=tt+1
    for q in range(n):
        if True: segs[cur[q]].append((q,start[q],D))
    alt=0; alt_any=0
    for k in crit:
        if g[k][0]!='rz': continue
        L=lab[k]; opts=[s for s in segs.get(L,[]) if not (s[0]==g[k][1] and s[1]<=asap[k]<=s[2])]
        if opts: alt_any+=1
    print('critical rz with same parity available on another segment',alt_any,'of',comp['rz'])

    # upper bound on any phase-relocation gain: drop every rz and re-measure
    g2=[x for x in g if x[0]!='rz']
    print('depth with all diagonal phases deleted (ASAP)',times(g2,n)[2])
    q=QuantumCircuit(n)
    for nm,a,b,p in g2:
        if nm=='cx': q.cx(a,b)
        else: q.u(*p,a)
    print('depth with all diagonal phases deleted (opt2)',transpile(q,basis_gates=['u3','cx'],optimization_level=2).depth())
    g3=[x for x in g if x[0]=='cx']
    print('depth of the CX skeleton alone (ASAP)',times(g3,n)[2])
