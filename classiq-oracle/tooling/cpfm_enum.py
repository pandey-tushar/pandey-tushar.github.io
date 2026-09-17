import sys, itertools, collections; sys.path.insert(0,'/home/user/classiq-challenge')
import cpfm_layout as L, cpfk_syn as SY
side=sys.argv[1]; nf=int(sys.argv[2])
xf,yf=SY.basis_pair(); fs0=xf if side=='x' else yf
costs=sorted((sum(L.gcost(len(l)) for l in L.cover(f)[1]),i) for i,f in enumerate(fs0))
pick=[i for c,i in costs[:nf]]; fs=[fs0[i] for i in pick]
best=None; feas=collections.Counter(); fails=collections.Counter()
for tg in itertools.permutations(range(9),nf):
    scratch=[w for w in (6,7,8) if w not in tg]
    if not scratch: continue
    for order in itertools.permutations(range(nf)):
        targets={i:tg[i] for i in range(nf)}
        body,mirror=L.compile_side(fs,list(order),targets,scratch)
        if body is None: fails[mirror]+=1; continue
        nd=sum(1 for t in tg if t<6); feas[nd]+=1
        ops=body+mirror; d=L.model_depth(ops,n=9)
        if best is None or d<best[0]:
            best=(d,tg,order,L.loads(ops),L.check(fs,targets,body,mirror),sum(1 for o in ops if o[0] in('ccx','c3x','ccx_dg','c3x_dg')))
print(side,'nf',nf,'pick',pick,'feasible by #data-wire accumulators',dict(feas),'fails',dict(fails))
print('best depth',best)
