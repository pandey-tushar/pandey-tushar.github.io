"""for each y target: smallest k in {1,2} such that target = affine + sum of k
products (affine form)*(affine form) on the care set."""
import itertools
from cptb_yprep import TG, ALL
def tab(f): return sum(1 << y for y in range(64) if f(y))
lin = [tab(lambda y, m=m: bin(y & m).count('1') & 1) for m in range(1, 64)]
aff = lin + [l ^ ALL for l in lin]
prods = {}
for i in range(len(lin)):
    for j in range(i + 1, len(lin)):
        p = lin[i] & lin[j]
        prods.setdefault(p, (i, j))
    # (l ^1)(m) etc. differ from l*m only by affine terms -> same span
P = list(prods)
base = [ALL] + [tab(lambda y, b=b: y >> b & 1) for b in range(6)]
def in_span(vecs, t, care):
    rows = []
    for v in vecs:
        v &= care
        for r in rows:
            if v >> (r.bit_length() - 1) & 1: v ^= r
        if v: rows.append(v); rows.sort(reverse=True)
    t &= care
    for r in rows:
        if t >> (r.bit_length() - 1) & 1: t ^= r
    return t == 0
for name, t, care in TG:
    if in_span(base, t, care): print(name, 'affine'); continue
    k1 = [p for p in P if in_span(base + [p], t, care)]
    if k1: print(name, '1 product, e.g.', prods[k1[0]]); continue
    found = None
    for a, b in itertools.combinations(P, 2):
        if in_span(base + [a, b], t, care): found = (prods[a], prods[b]); break
    print(name, '2 products' if found else '>2 products', found or '')
