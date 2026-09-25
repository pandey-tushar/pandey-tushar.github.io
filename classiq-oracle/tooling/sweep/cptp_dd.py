"""Whole-truth-table decision diagrams of F as XAGs (1 AND per node).
Per variable (in order) a decomposition type: S (Shannon, f = f0 ^ v(f0^f1)),
P (positive Davio, f = f0 ^ v f2), N (negative Davio, f = f1 ^ ~v f2),
f2 = f0 ^ f1.  Nodes are shared (reduced, ordered KFDD).  AND count = nodes
whose AND operand is not constant.  Search: random variable orders, per
variable the type chosen greedily (level by level, fewest nodes at that level
and below by a one-level lookahead), over the identity basis and saved
affine bases.  Writes the best as verilog (inputs x0..x11 = the ORIGINAL data
bits; the basis change is folded into XORs).
Usage: python3 cptp_dd.py SECONDS [basis pkl ...]
Progress every 10 s; output ckpt/dd_best.v, ckpt/dd_best.json"""
import sys, time, json, pickle
import numpy as np
from cpae_core import SHAPES, fvec

N = 4096


def cof(t, v):
    """t: uint8[4096] over original index bits; returns (t|v=0, t|v=1) as functions of the same index (v ignored)"""
    idx = np.arange(N)
    lo = t[idx & ~(1 << v)]; hi = t[idx | (1 << v)]
    return lo, hi


def build(F, order, types):
    """returns (#ANDs, node list) ; node = (level, var, type, key, key_a, key_b) with keys of child functions"""
    level = {F.tobytes(): F}
    nodes = []; nand = 0
    for li, v in enumerate(order):
        nxt = {}
        for k, t in level.items():
            lo, hi = cof(t, v)
            if np.array_equal(lo, hi):            # does not depend on v: pass through
                nxt[k] = t; continue
            f2 = lo ^ hi
            ty = types[li]
            a, b = (lo, f2) if ty == 'P' else (hi, f2) if ty == 'N' else (lo, f2)   # S: f = lo ^ v*(lo^hi)
            # AND operand is f2 in every type (S uses lo^hi as operand, children lo, hi)
            if ty == 'S': a, b = lo, hi
            opnd = f2
            if opnd.any() and not opnd.all(): nand += 1
            elif opnd.all(): pass                     # v * 1 = v : linear
            nodes.append((li, v, ty, k, a.tobytes(), b.tobytes()))
            for c in (a, b):
                nxt.setdefault(c.tobytes(), c)
        level = nxt
    return nand, nodes


def greedy_types(F, order):
    types = []
    for li in range(len(order)):
        best = None
        for ty in 'SPN':
            n, _ = build(F, order[:li + 1], types + [ty])
            if best is None or n < best[0]: best = (n, ty)
        types.append(best[1])
    return types


def write_verilog(F, nodes, path):
    names = {}; lines = []; k = 0
    zero = np.zeros(N, dtype=np.uint8).tobytes(); one = np.ones(N, dtype=np.uint8).tobytes()
    def ref(key):
        if key == zero: return "1'b0"
        if key == one: return "1'b1"
        return names[key]
    for (li, v, ty, key, a, b) in nodes: names[key] = 'n%d' % len(names)
    for (li, v, ty, key, a, b) in reversed(nodes):          # children first
        o = names[key]
        if ty == 'S':   lines.append('  assign %s = %s ^ (x%d & (%s ^ %s));' % (o, ref(a), v, ref(a), ref(b)))
        elif ty == 'P': lines.append('  assign %s = %s ^ (x%d & %s);' % (o, ref(a), v, ref(b)))
        else:           lines.append('  assign %s = %s ^ (~x%d & %s);' % (o, ref(a), v, ref(b)))
    root = ref(F.tobytes())
    with open(path, 'w') as fh:
        fh.write('module top(%s, y);\n' % ', '.join('x%d' % i for i in range(12)))
        fh.write('  input %s;\n  output y;\n' % ', '.join('x%d' % i for i in range(12)))
        fh.write('  wire %s;\n' % ', '.join(names[k] for k in names))
        fh.write('\n'.join(lines) + '\n  assign y = %s;\nendmodule\n' % root)


def apply_basis(F, cols, c):
    IDX = np.arange(N, dtype=np.int64); idx = np.zeros(N, dtype=np.int64)
    for j in range(12): idx ^= ((IDX >> j) & 1) * cols[j]
    return F[idx ^ c]


if __name__ == '__main__':
    secs = float(sys.argv[1]); bases = [('identity', None)] + [(p, pickle.load(open(p, 'rb'))) for p in sys.argv[2:]]
    F0 = fvec(SHAPES['LOGO']).astype(np.uint8)
    rng = np.random.default_rng(0); t0 = time.time(); last = t0
    best = None; tried = 0
    while time.time() - t0 < secs:
        name, bd = bases[tried % len(bases)]
        F = F0 if bd is None else apply_basis(F0, bd['cols'], bd['c'])
        order = list(rng.permutation(12)) if tried >= len(bases) else list(range(12))
        types = greedy_types(F, order)
        n, nodes = build(F, order, types)
        tried += 1
        if best is None or n < best[0]:
            best = (n, name, order, types, len(nodes))
            print('   new best: %d ANDs (%d nodes)  basis %s  order %s  types %s' % (n, len(nodes), name, order, ''.join(types)), flush=True)
            json.dump(dict(ands=n, nodes=len(nodes), basis=name, order=[int(o) for o in order], types=types),
                      open('ckpt/dd_best.json', 'w'))
        if time.time() - last > 10:
            last = time.time()
            print('[dd] %4ds  tried %d  best %d ANDs (%s)' % (last - t0, tried, best[0], best[1]), flush=True)
    print('[dd] final best %d ANDs, basis %s, order %s, types %s, nodes %d' % best, flush=True)
    n, name, order, types, _ = best
    assert name == 'identity'
    _, nodes = build(F0, order, types)
    write_verilog(F0, nodes, 'ckpt/dd_best.v')
    print('[dd] wrote ckpt/dd_best.v', flush=True)
