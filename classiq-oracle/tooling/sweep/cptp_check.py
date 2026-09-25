"""Check a (2-input, lorina-style) verilog netlist against F; report ANDs and AND-depth.
Usage: python3 cptp_check.py FILE.v"""
import re, sys, numpy as np
from cpae_core import SHAPES, fvec
idx = np.arange(4096); env = {'x%d' % i: ((idx >> i) & 1).astype(np.uint8) for i in range(12)}; dep = {'x%d' % i: 0 for i in range(12)}
nand = 0
for line in open(sys.argv[1]):
    line = line.strip().rstrip(';')
    m = re.match(r"assign (\S+) = (.*)", line)
    if not m: continue
    e = m.group(2).replace("1'b0", "0").replace("1'b1", "1")
    toks = re.findall(r"[A-Za-z_][\w\[\]]*", e)
    env[m.group(1)] = eval(re.sub(r"~\s*([\w\[\]]+)", r"(1^\1)", e).replace('[', '_').replace(']', '_'), {}, {k.replace('[', '_').replace(']', '_'): v for k, v in env.items()}) & 1
    d = max([dep.get(t, 0) for t in toks] + [0])
    if '&' in e: nand += 1; d += 1
    dep[m.group(1)] = d
out = [k for k in env if k.startswith('y') or k.startswith('po')]
y = env.get('y', env.get(out[0] if out else 'y'))
print('%s: ANDs %d  AND-depth %d  == F: %s' % (sys.argv[1], nand, dep.get('y', max(dep.values())),
      bool((y == fvec(SHAPES['LOGO']).astype(np.uint8)).all())))
