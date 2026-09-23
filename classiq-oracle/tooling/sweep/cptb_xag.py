"""exact XAG synthesis for one 6-input function (care set): k AND gates, each
AND takes two affine combinations of inputs and earlier ANDs; the output is
an affine combination.  Finds the multiplicative complexity by increasing k.
usage: target_name kmax timeout"""
import sys, time, pickle
import cptb_ysat                                   # aux-var fix
from cpri_round import Enc, solve
from cptb_yprep import TG, ALL, V3, W3
from cpri_io import out_path

def build(T, care, k):
    e = Enc(); rows = [r for r in range(64) if (care >> r) & 1]
    sig = {}                                       # sig[(i, r)] literal
    for i in range(6):
        for r in rows: sig[(i, r)] = e.const((r >> i) & 1)
    sel = {}
    def affine(tag, n, r):
        terms = [e.and2(sel[(tag, i)], sig[(i, r)], (tag, 'at', i, r)) for i in range(n)]
        terms.append(sel[(tag, 'c')])
        return e.xor_chain(terms, (tag, 'ax', r))
    for j in range(k):
        n = 6 + j
        for side in ('L', 'R'):
            for i in range(n): sel[((j, side), i)] = e.v('sel', j, side, i)
            sel[((j, side), 'c')] = e.v('sel', j, side, 'c')
        for r in rows:
            a = affine((j, 'L'), n, r); b = affine((j, 'R'), n, r)
            sig[(6 + j, r)] = e.and2(a, b, ('g', j, r))
    n = 6 + k
    for i in range(n): sel[('O', i)] = e.v('sel', 'O', i)
    sel[('O', 'c')] = e.v('sel', 'O', 'c')
    for r in rows:
        o = affine('O', n, r)
        e.cl.append([o] if (T >> r) & 1 else [-o])
    return e, sel

def decode(model, e, k):
    m = set(l for l in model if l > 0); out = []
    for j in range(k):
        g = []
        for side in ('L', 'R'):
            g.append(([i for i in range(6 + j) if e.v('sel', j, side, i) in m], e.v('sel', j, side, 'c') in m))
        out.append(g)
    o = ([i for i in range(6 + k) if e.v('sel', 'O', i) in m], e.v('sel', 'O', 'c') in m)
    return out, o

def main():
    name, kmax, to = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
    tg = {t[0]: t for t in TG}; tg['VAL'] = ('VAL', V3 | W3, ALL)
    _, T, care = tg[name]
    for k in range(1, kmax + 1):
        e, sel = build(T, care, k)
        t0 = time.time(); res = solve(e.cl, to)
        st = 'timeout' if res == 'timeout' else ('UNSAT' if res is None else 'SAT')
        print('%s k=%d ANDs -> %s %.0fs' % (name, k, st, time.time() - t0), flush=True)
        if st == 'SAT':
            ands, o = decode(res, e, k)
            for j, (L, R) in enumerate(ands): print('  g%d = (%s) & (%s)' % (6 + j, L, R))
            print('  out = ', o)
            pickle.dump((ands, o), open(out_path('cptb_xag_%s_k%d.pkl' % (name, k)), 'wb'))
            return
        if st == 'timeout': return

if __name__ == '__main__':
    main()
