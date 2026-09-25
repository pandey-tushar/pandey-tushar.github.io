"""Linear width profile of an XAG in topological AND order: after each AND, rank of
the still-needed operand forms restricted to computed signals (must stay <= 18).
Usage: python3 cptr_width.py FILE.v"""
import sys
from cptr_map import parse, reduce_basis
ands, Fo = parse(sys.argv[1])
nA = len(ands); prof = []
done = (1 << 13) - 2
for k in range(nA + 1):
    if k: done |= ands[k - 1][0]
    need = []
    for j in range(k, nA): need += [ands[j][1] & done, ands[j][2] & done]
    prof.append(len(reduce_basis([(0, L & ~1) for L in need if L & ~1])))
print('ANDs %d  width profile %s  max %d' % (nA, prof, max(prof)))
