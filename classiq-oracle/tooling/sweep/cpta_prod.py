"""after a setup: greedy count of pairwise wire products needed so that the
side's function space V lies in span{1, wires, chosen products}."""
import itertools
from cpta_tensor import Span
from cpta_deg import run, Wspan
from cpri_round import logo_pairs
ALL = (1 << 64) - 1

def need(W, wires, cap=20):
    wires = [v for v in wires if v not in (0, ALL)]
    base = [ALL] + wires
    cands = {}
    for i, j in itertools.combinations(range(len(wires)), 2):
        p = wires[i] & wires[j]
        if p not in (0, ALL): cands[(i, j)] = p
    chosen = []
    dimV = len(Wspan(W))
    def cov(extra):
        S = Span(); [S.add(v) for v in base + extra]; n0 = len(S.b)
        return dimV - sum(1 for _ in range(0)) - (len(Span_add(S, W)) )
    def inside(extra):
        S = Span(); [S.add(v) for v in base + extra]; n0 = len(S.b)
        k = sum(S.add(w) for w in W)
        return dimV - k
    cur = inside([])
    hist = [cur]
    while cur < dimV and len(chosen) < cap:
        best = max(cands, key=lambda k: inside([cands[c] for c in chosen] + [cands[k]]))
        chosen.append(best); cur = inside([cands[c] for c in chosen]); hist.append(cur)
        if hist[-1] == hist[-2]: break
    return hist, chosen

if __name__ == '__main__':
    import sys, ast
    U = [u for u, v in logo_pairs()]; V = [v for u, v in logo_pairs()]
    from cpta_deg import XSET, YSET
    for name, W, g in (('x raw', U, []), ('x fold', U, XSET), ('y raw', V, []), ('y fold', V, YSET)):
        h, c = need(W, run(g))
        print(name, 'dims covered after 0,1,2.. products:', h)
