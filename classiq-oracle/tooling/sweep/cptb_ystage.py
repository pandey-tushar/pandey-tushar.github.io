"""staged y-prep synthesis.  usage: stage R G L timeout [prev.pkl]
stage 1: targets V3, W3, y5 from raw y.
stage 2: all targets, starting from the stage-1 end state."""
from cpri_io import out_path as _out
import sys, time, pickle
import cptb_ysat                      # patches Enc.atmost
from cpri_round import Enc, encode, solve, decode, init_tables, simulate
from cptb_yprep import TG, ALL

def endstate(s, init):
    st = list(init)
    for lins, row in zip(s['ylin'], s['y']):
        for a, b in lins: st[b] ^= st[a]
        prods = [((st[a] ^ (ALL if pa else 0)) & (st[b] ^ (ALL if pb else 0)), t) for a, pa, b, pb, t in row]
        for p, t in prods: st[t] ^= p
    return st

def main():
    stage, R, G, L, to = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])
    init = init_tables()
    if stage == 2:
        prev = pickle.load(open(sys.argv[6], 'rb')); init = endstate(prev, init)
    tg = [t for t in TG if t[0] in ('V3', 'W3', 'y5')] if stage == 1 else TG
    e = Enc()
    sides, _ = encode(R, G, [], init, init, e, maxsel=1, L=L, only='y')
    W = sides['y'][0]
    for k, (name, t, care) in enumerate(tg):
        sel = [e.v('tsel', k, w) for w in range(9)]; pol = e.v('tpol', k)
        e.exactly_one(sel)
        for w in range(9):
            for i in range(64):
                if not (care >> i) & 1: continue
                lit = W[(R, w)][i]
                if (t >> i) & 1:
                    e.cl += [[-sel[w], lit, pol], [-sel[w], -lit, -pol]]
                else:
                    e.cl += [[-sel[w], -lit, pol], [-sel[w], lit, -pol]]
    for w in range(9):
        e.atmost([e.v('tsel', k, w) for k in range(len(tg))], 1)
    t0 = time.time(); res = solve(e.cl, to)
    st = 'timeout' if res == 'timeout' else ('UNSAT' if res is None else 'SAT')
    print('stage %d R=%d G=%d L=%d -> %s %.0fs' % (stage, R, G, L, st, time.time() - t0), flush=True)
    if st == 'SAT':
        s = decode(res, R, G, e, L=L, only='y')
        print('lins', s['ylin']); print('gates', s['y'])
        pickle.dump(s, open(_out('cptb_ystage%d_R%d_G%d_L%d.pkl' % (stage, R, G, L)), 'wb'))

if __name__ == '__main__':
    main()
