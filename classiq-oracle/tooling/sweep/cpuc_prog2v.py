""".prog netlist (cpdh syntax: AND t a b / CX t a / X t / CZ e1^e2 w) -> Verilog for
cptr_map.parse / cptu_width.py.  Inputs x_k = bit k, y_k = bit 6+k (cpdh_core order).
Usage: python3 cpuc_prog2v.py IN.prog OUT.v"""
import sys
src, dst = sys.argv[1], sys.argv[2]
form = {}
for k in range(6): form['x%d' % k] = 1 << (1 + k); form['y%d' % k] = 1 << (7 + k)
ands = []; Fo = None
for ln in open(src):
    p = ln.split()
    if not p: continue
    if p[0] == 'AND':
        bit = 1 << (13 + len(ands)); ands.append((form.get(p[2], 0), form.get(p[3], 0)))
        form[p[1]] = form.get(p[1], 0) ^ bit
    elif p[0] == 'CX': form[p[1]] = form.get(p[1], 0) ^ form.get(p[2], 0)
    elif p[0] == 'X': form[p[1]] = form.get(p[1], 0) ^ 1
    elif p[0] == 'CZ':
        e = 0
        for t in p[1].split('^'): e ^= form.get(t, 0)
        w = form.get(p[2], 0)
        if w == 1: Fo = e
        elif e == 1: Fo = w
        else:
            bit = 1 << (13 + len(ands)); ands.append((e, w)); Fo = bit
    else: raise ValueError(ln)
assert Fo is not None
out = ['module f(' + ','.join('x%d' % i for i in range(12)) + ',y);',
       'input ' + ','.join('x%d' % i for i in range(12)) + ';', 'output y;']
def tok(b): return 'x%d' % (b - 1) if b <= 12 else 'n%d' % (b - 13)
def chain(name, L):
    """emit xor chain for form L, return final signal name"""
    bits = [b for b in range(1, 200) if L >> b & 1]
    if not bits: return "C1" if L & 1 else "C0"
    toks = [tok(b) for b in bits]
    if L & 1: toks[-1] = '~' + toks[-1]
    if len(toks) == 1: out.append('assign %s_0 = %s;' % (name, toks[0])); return name + '_0'
    cur = toks[0]
    for i, t in enumerate(toks[1:]):
        out.append('assign %s_%d = %s ^ %s;' % (name, i, cur, t)); cur = '%s_%d' % (name, i)
    return cur
for j, (A, B) in enumerate(ands):
    a = chain('a%d' % j, A); b = chain('b%d' % j, B)
    out.append('assign n%d = %s & %s;' % (j, a, b))
o = chain('o', Fo); out.append('assign y = %s;' % o); out.append('endmodule')
open(dst, 'w').write('\n'.join(out).replace('C1', "1'b1").replace('C0', "1'b0") + '\n')
print('ANDs %d, output form bits %d' % (len(ands), bin(Fo).count('1')))
