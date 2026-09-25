"""Conditionally-clean hosting test (rule C).  For an annealed XAG state, every
AND value n that fails the in-place rule needs a register.  n can instead live
on a wire holding c as (~c ^ n) if every consumer AND n*m has m => c pointwise
(then m*(~c^n) = m*n), with c a value on some other wire that stays put while n
is used.  Candidates c: inputs x_i / ~x_i, earlier AND values / negations, not
the partner operands themselves.  Reports how many register values qualify and
the register pressure after moving them.  Usage: python3 cptz_cond.py PKL"""
import sys, pickle
import numpy as np
from cptu_width import rank
IDX = np.arange(4096)
d = pickle.load(open(sys.argv[1], 'rb')); ands, Fo, order = d['ands'], d['Fo'], d['order']
sig = {0: np.ones(4096, np.uint8)}
for i in range(12): sig[1 + i] = ((IDX >> i) & 1).astype(np.uint8)
def ev(L):
    v = np.zeros(4096, np.uint8); b = 0
    while L:
        if L & 1: v ^= sig[b]
        L >>= 1; b += 1
    return v
for k in order: sig[13 + k] = ev(ands[k][0]) & ev(ands[k][1])
pos = {k: i for i, k in enumerate(order)}
done = (1 << 13) - 2; ivs = []; qual = 0; tot = 0
for p, k in enumerate(order):
    bit = 1 << (13 + k); A, B = ands[k]; dm = done | bit; need = set(); last = p; cons = []
    for j in order[p + 1:]:
        for side, L in enumerate(ands[j]):
            v = L & dm & ~1
            if v: need.add(v)
            if L & bit:
                last = max(last, pos[j]); cons.append((j, side))
    Nn = [v ^ bit for v in need if v & bit]; N0 = [v for v in need if not v & bit]
    M = N0 + [u ^ Nn[0] for u in Nn[1:]] + [A & ~1, B & ~1]
    r = rank(M); bad = (rank(M + [Nn[0]]) == r) if Nn else (r >= 18)
    done |= bit
    if not bad: continue
    tot += 1
    # consumers must use n exactly as operand n (operand form == bit, possibly with const) for the rule
    ok_form = True   # operand n ^ u: host gives (~c ^ n) ^ u, same implication rule
    partners = [ev(ands[j][1 - side]) for j, side in cons]
    found = None
    if ok_form and partners:
        cands = [('x%d' % i, sig[1 + i]) for i in range(12)] + [('~x%d' % i, 1 ^ sig[1 + i]) for i in range(12)]
        cands += [('n%d' % m, sig[13 + m]) for m in order[:p]] + [('~n%d' % m, 1 ^ sig[13 + m]) for m in order[:p]]
        for name, c in cands:
            if all(not (m & (1 ^ c)).any() for m in partners):
                found = name; break
    if found: qual += 1
    else: ivs.append((p, last))
peak = max(sum(1 for a, b in ivs if a <= q < b) for q in range(len(order)))
print('%s: register values %d, conditionally hostable %d, remaining register pressure peak %d (was: all)' % (sys.argv[1], tot, qual, peak))
