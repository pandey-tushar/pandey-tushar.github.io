"""Flatten ckpt/dd_best.v into a 2-input verilog netlist (AND/XOR/NOT, no constants) for lorina.
Usage: python3 cptp_flat.py IN.v OUT.v ; verifies the function == F"""
import re, sys, numpy as np
from cpae_core import SHAPES, fvec
src, dst = sys.argv[1], sys.argv[2]
defs = {}
for line in open(src):
    m = re.match(r"\s*assign (\w+) = (.*);", line)
    if m: defs[m.group(1)] = m.group(2)
out = []; cnt = [0]; memo = {}
def new(expr):
    cnt[0] += 1; n = 't%d' % cnt[0]; out.append('  assign %s = %s;' % (n, expr)); return n
# signals: ('c',0/1) or ('s',name,neg)
def AND(a, b):
    if a == ('c', 0) or b == ('c', 0): return ('c', 0)
    if a == ('c', 1): return b
    if b == ('c', 1): return a
    return ('s', new('%s & %s' % (lit(a), lit(b))), 0)
def XOR(a, b):
    if a[0] == 'c': return b if a[1] == 0 else NOT(b)
    if b[0] == 'c': return a if b[1] == 0 else NOT(a)
    return ('s', new('%s ^ %s' % (lit(a), lit(b))), 0)
def NOT(a):
    if a[0] == 'c': return ('c', 1 - a[1])
    return ('s', a[1], 1 - a[2])
def lit(a):
    return ('~' if a[2] else '') + a[1]
def sig(tok):
    tok = tok.strip()
    if tok == "1'b0": return ('c', 0)
    if tok == "1'b1": return ('c', 1)
    if tok.startswith('~'): return NOT(sig(tok[1:]))
    if tok in defs: return node(tok)
    return ('s', tok, 0)
def node(n):
    if n in memo: return memo[n]
    e = defs[n]
    m = re.match(r"(\S+) \^ \((~?x\d+) & \((\S+) \^ (\S+)\)\)$", e)
    if m: r = XOR(sig(m.group(1)), AND(sig(m.group(2)), XOR(sig(m.group(3)), sig(m.group(4)))))
    else:
        m = re.match(r"(\S+) \^ \((~?x\d+) & (\S+)\)$", e)
        if m: r = XOR(sig(m.group(1)), AND(sig(m.group(2)), sig(m.group(3))))
        else: r = sig(e)
    memo[n] = r; return r
y = node('y') if 'y' in defs else sig(defs['y'])
if y[0] == 'c': raise SystemExit('constant output')
out.append('  assign y = %s;' % lit(y))
names = ['t%d' % i for i in range(1, cnt[0] + 1)]
with open(dst, 'w') as fh:
    fh.write('module top(%s, y);\n  input %s;\n  output y;\n' % (', '.join('x%d' % i for i in range(12)), ', '.join('x%d' % i for i in range(12))))
    if names: fh.write('  wire %s;\n' % ', '.join(names))
    fh.write('\n'.join(out) + '\nendmodule\n')
# verify
idx = np.arange(4096); env = {'x%d' % i: ((idx >> i) & 1).astype(np.uint8) for i in range(12)}
for line in open(dst):
    m = re.match(r"\s*assign (\w+) = (.*);", line)
    if m: env[m.group(1)] = eval(re.sub(r'~(\w+)', r'(1^\1)', m.group(2)), {}, env) & 1
print('flat netlist: %d gates, ANDs %d, == F: %s' % (cnt[0], sum(1 for l in out if '&' in l),
      bool((env['y'] == fvec(SHAPES['LOGO']).astype(np.uint8)).all())))
