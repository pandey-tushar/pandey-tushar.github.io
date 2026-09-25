"""Analyse a 2-input XAG (lorina verilog) for the phase-along-the-way mapping.
Each AND: 'internal' if its output reaches another AND's operand (through
XOR nodes), else 'output-only' (it only reaches y through XORs -> a CZ phase
on its operands, no wire).  Reports counts, AND-depth of internal ANDs, and
the number of internal AND values live at once in an AND-level schedule.
Usage: python3 cptp_anal.py FILE.v"""
import re, sys
from collections import defaultdict
defs = {}; outname = None
for line in open(sys.argv[1]):
    line = line.strip().rstrip(';')
    m = re.match(r"assign (\S+) = (.*)", line)
    if not m: continue
    defs[m.group(1)] = m.group(2)
    if m.group(1).startswith('y'): outname = m.group(1)
def ops(e):
    toks = re.findall(r"~?\s*[A-Za-z_]\w*", e)
    return [t.replace('~', '').strip() for t in toks], ('&' in e)
node = {}
for n, e in defs.items():
    a, isand = ops(e); node[n] = (isand, a)
# AND-support of each node through XORs: set of AND nodes (and inputs) whose XOR gives it
from functools import lru_cache
@lru_cache(None)
def xsupport(n):
    if n not in node: return frozenset()         # primary input
    isand, a = node[n]
    if isand: return frozenset([n])
    s = frozenset()
    for c in a: s = s ^ xsupport(c)              # XOR: symmetric difference (cancellation)
    return s
ands = [n for n in node if node[n][0]]
internal = set()
for n in ands:
    for c in node[n][1]: internal |= xsupport(c)
out_s = xsupport(outname)
lvl = {}
def level(n):
    if n in lvl: return lvl[n]
    if n not in node: return 0
    isand, a = node[n]
    d = max(level(c) for c in a) + (1 if isand else 0)
    lvl[n] = d; return d
for n in ands: level(n)
print('ANDs %d  internal %d  output-only %d  (output XOR support %d ANDs)' %
      (len(ands), len(internal), len([n for n in ands if n not in internal]), len(out_s)))
by = defaultdict(list)
for n in ands: by[lvl[n]].append(n)
print('ANDs per AND-level:', {k: len(v) for k, v in sorted(by.items())})
print('internal per level:', {k: sum(1 for n in v if n in internal) for k, v in sorted(by.items())})
# live internal values: an internal AND is live from its level until the last level that uses it
last = {}
for n in ands:
    for c in node[n][1]:
        for s in xsupport(c): last[s] = max(last.get(s, 0), lvl[n])
peak = max(sum(1 for s in internal if lvl[s] <= L < last.get(s, 0) + 0) for L in range(1, max(lvl.values()) + 1))
print('peak live internal AND values (level schedule): %d' % peak)
