"""CP-FC: REHOME a wire interval onto a free wire of the same base.

A maximal span where ancilla w is non-zero is a 'residency'.  If another
ancilla w' is zero and completely untouched across that span, renaming w->w'
inside the span is EXACTLY equivalent (same base 0, same values) and breaks
the false serial edge that wire-sharing creates.  Enumerate every such
rehome, apply singly, measure the real depth."""
import sys, os, pickle, collections, time
sys.path.insert(0,'/home/user/classiq-challenge')
import cpet_vdag as V
from cpen_fast import NON
RM=V.raw_masks(12); FULL=V.FULL

def load():
    return list(pickle.load(open('cpen_search_11.pkl','rb'))[1])

def wire_masks(ops):
    m=[RM[w] if w<12 else 0 for w in range(18)]
    snap=[]
    for op in ops:
        snap.append(list(m))
        k,q=op[0],op[1:]
        if k=='x': m[q[0]]^=FULL
        elif k=='cx': m[q[1]]^=m[q[0]]
        elif k in ('ccx','ccx_dg'): m[q[2]]^=m[q[0]]&m[q[1]]
        elif k in ('c3x','c3x_dg'): m[q[3]]^=m[q[0]]&m[q[1]]&m[q[2]]
    snap.append(list(m))
    return snap

def residencies(ops, snap):
    """maximal [a,b] with ancilla w non-zero strictly inside."""
    out=[]
    for w in range(12,18):
        i=0
        while i < len(ops):
            if snap[i][w]==0 and snap[i+1][w]!=0:
                j=i+1
                while j < len(ops) and snap[j+1][w]!=0: j+=1
                if j < len(ops): out.append((w,i,j))
                i=j+1
            else: i+=1
    return out

def touched(ops,a,b):
    s=set()
    for op in ops[a:b+1]: s.update(op[1:])
    return s

def rehome(ops,w,a,b,w2):
    out=list(ops)
    for i in range(a,b+1):
        op=out[i]
        if w in op[1:]:
            out[i]=(op[0],)+tuple(w2 if x==w else x for x in op[1:])
    return out

if __name__=='__main__':
    import cpew_obj as O
    import cpev_base as B
    import verify18
    from cpae_core import ops_to_qc
    ops=load(); snap=wire_masks(ops)
    res=residencies(ops,snap)
    print('ancilla residencies: %d'%len(res), flush=True)
    base=O.obj(ops)
    print('base depth %d cx %d u3 %d'%(base['depth'],base['cx'],base['u3']), flush=True)
    cands=[]
    for (w,a,b) in res:
        tch=touched(ops,a,b)
        for w2 in range(12,18):
            if w2==w or w2 in tch: continue
            if any(snap[i][w2]!=0 for i in range(a,b+2)): continue
            cands.append((w,a,b,w2))
    print('legal single rehomes: %d'%len(cands), flush=True)
    results=[]
    t0=time.time()
    for k,(w,a,b,w2) in enumerate(cands):
        o2=rehome(ops,w,a,b,w2)
        s2=wire_masks(o2)
        if s2[-1]!=[RM[x] if x<12 else 0 for x in range(18)]:
            continue                      # not wire-clean, reject
        st=O.obj(o2)
        results.append((st['depth'],st['cx'],w,a,b,w2))
        if (k+1)%25==0: print('  %d/%d (%.0fs)'%(k+1,len(cands),time.time()-t0), flush=True)
    results.sort()
    pickle.dump(results,open('cpfc_rehome.pkl','wb'))
    print('\nbest 20 single rehomes (base %d):'%base['depth'])
    for d,c,w,a,b,w2 in results[:20]:
        print('   q%-2d [%4d,%4d] -> q%-2d : depth %3d cx %3d  %+d'%(w,a,b,w2,d,c,d-base['depth']))
    print('\nrehomes that LOWER depth : %d'%sum(1 for r in results if r[0]<base['depth']))
    print('depth-neutral            : %d'%sum(1 for r in results if r[0]==base['depth']))
