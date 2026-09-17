"""cpfo: XOR-AND beam search for one side (9 wires: data 0-5 raw, 6-8 zero).

State  = 9 wire contents (64-bit tables over the side's 6 bits).
Action = w ^= a & b (or a & b & c) with operands a, b single contents or the
         XOR of two contents; w any wire (data wires included, so contents may
         become x_k ^ product: intentional dirty algebra).
Score  = number of target functions inside S = span(1, contents, pairwise
         products of contents), i.e. what CZ/CCZ phases can reach at this
         moment; tiebreak rank(S).
"""
import sys, itertools, pickle, time
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfk_syn as SY

M64 = (1 << 64) - 1
RAW = [sum(((v >> i) & 1) << v for v in range(64)) for i in range(6)]

def reduce_basis(vecs):
    """GF(2) echelon basis as dict pivot->vec; returns list."""
    piv = {}
    for v in vecs:
        while v:
            p = v.bit_length() - 1
            if p in piv: v ^= piv[p]
            else: piv[p] = v; break
    return piv

def rank_with(piv, vecs):
    """rank increase when adding vecs to an echelon basis (does not modify)."""
    piv = dict(piv); r = 0
    for v in vecs:
        while v:
            p = v.bit_length() - 1
            if p in piv: v ^= piv[p]
            else: piv[p] = v; r += 1; break
    return r

def span_S(contents):
    L = [c for c in contents if c] + [M64]
    prods = [a & b for a, b in itertools.combinations(L, 2)]
    return reduce_basis(L + prods)

def score(contents, targets):
    L = [c for c in contents if c] + [M64]
    prods = [a & b for a, b in itertools.combinations(L, 2)]
    piv = reduce_basis(L + prods)
    missing = rank_with(piv, targets)
    trip = [a & b & c for a, b, c in itertools.combinations(L, 3)]
    piv3 = dict(piv)
    for v in trip:
        while v:
            p = v.bit_length() - 1
            if p in piv3: v ^= piv3[p]
            else: piv3[p] = v; break
    missing3 = rank_with(piv3, targets)
    # residual weight of the targets modulo S (smaller = closer)
    resw = 0
    for v in targets:
        while v:
            p = v.bit_length() - 1
            if p in piv: v ^= piv[p]
            else: break
        resw += bin(v).count('1')
    return (len(targets) - missing, len(targets) - missing3, -resw, len(piv))

def operands(contents):
    ops = [(c, (i,)) for i, c in enumerate(contents) if c]
    for i, j in itertools.combinations(range(9), 2):
        v = contents[i] ^ contents[j]
        if v and contents[i] and contents[j]: ops.append((v, (i, j)))
    return ops

def actions(contents, triples=True):
    ops = operands(contents)
    zero = [w for w in range(9) if contents[w] == 0]
    targets_w = [w for w in range(9) if contents[w]] + zero[:1]
    seen = set()
    for (a, da), (b, db) in itertools.combinations(ops, 2):
        if set(da) & set(db): continue
        p = a & b
        if p == 0 or p in seen: continue
        seen.add(p)
        for w in targets_w:
            if w in da or w in db: continue
            yield p, (da, db, w)
    if triples:
        singles = [(c, i) for i, c in enumerate(contents) if c]
        for (a, i), (b, j), (c, k) in itertools.combinations(singles, 3):
            p = a & b & c
            if p == 0 or p in seen: continue
            seen.add(p)
            for w in targets_w:
                if w in (i, j, k): continue
                yield p, ((i,), (j,), (k,), w)

def beam(targets, budget, width, verbose=True, triples=True):
    start = tuple(RAW + [0, 0, 0])
    front = [(score(start, targets), start, [])]
    best = front[0]
    for step in range(1, budget + 1):
        t0 = time.time(); cand = {}
        for sc, st, hist in front:
            for p, act in actions(st, triples):
                w = act[-1]
                new = list(st); new[w] ^= p; new = tuple(new)
                key = tuple(sorted(new))
                if key in cand: continue
                s2 = score(new, targets)
                cand[key] = (s2, new, hist + [act])
        if not cand: break
        front = sorted(cand.values(), key=lambda c: c[0], reverse=True)[:width]
        if front[0][0] > best[0]: best = front[0]
        if verbose: print('step', step, 'cands', len(cand), 'best', front[0][0], 'front', [c[0] for c in front[:6]], '%.1fs' % (time.time() - t0), flush=True)
        if front[0][0][0] == len(targets): return front[0]
    return best

if __name__ == '__main__':
    which = sys.argv[1]; budget = int(sys.argv[2]); width = int(sys.argv[3])
    xf, yf = SY.basis_pair()
    fs = xf if which.startswith('x') else yf
    if ':' in which: fs = [fs[int(i)] for i in which.split(':')[1].split(',')]
    print('targets', len(fs), 'weights', [bin(f).count('1') for f in fs], flush=True)
    r = beam(fs, budget, width)
    print('RESULT covered', r[0], 'ANDs', len(r[2]))
    for a in r[2]: print('  ', a)
    pickle.dump(r, open('cpfo_%s.pkl' % which.replace(':', '_').replace(',', '-'), 'wb'))
