"""randomised minimal product cover: smallest set of pairwise wire products P
such that (V cap Q2) lies in span{1, wires, P}.  Also reports dims of V in Q2."""
import itertools, random
from cpta_tensor import Span
from cpta_deg import run, Wspan, inside
from cpri_round import logo_pairs
ALL = (1 << 64) - 1

def dim_in(W, vecs):
    S = Span(); [S.add(v) for v in vecs]
    return len(Wspan(W)) - sum(S.add(w) for w in W)

def min_cover(W, wires, trials=300, seed=0):
    rng = random.Random(seed)
    wires = [v for v in set(wires) if v not in (0, ALL)]
    base = [ALL] + wires
    prods = list({wires[i] & wires[j] for i, j in itertools.combinations(range(len(wires)), 2)} - {0, ALL})
    target = dim_in(W, base + prods)
    best = None
    for t in range(trials):
        order = prods[:]; rng.shuffle(order)
        S = Span(); [S.add(v) for v in base]; chosen = []
        for p in order:
            chosen.append(p)
            if dim_in(W, base + chosen) == target: break
        for p in list(chosen):                     # prune
            rest = [q for q in chosen if q != p]
            if dim_in(W, base + rest) == target: chosen = rest
        if best is None or len(chosen) < len(best): best = chosen
    return target, len(best)

if __name__ == '__main__':
    import sys
    from cpta_deg import XSET, YSET
    U = [u for u, v in logo_pairs()]; V = [v for u, v in logo_pairs()]
    for name, W, g in (('x fold', U, XSET), ('y fold', V, YSET)):
        print(name, '(dims of V at deg<=2, min #products):', min_cover(W, run(g)))
