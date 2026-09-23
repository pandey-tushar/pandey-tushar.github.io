"""staged y-prep: add one target per stage, keeping all earlier targets on
some wire.  Each stage is a small exact SAT (R levels, G RCCX, L CX per level)
started from the previous stage's end state; tries R = Rmin..Rmax.
usage: order(comma names) Rmin Rmax G L timeout
saves every finished stage to out/cptb_ychain_stageK.pkl"""
import sys, time, pickle
import cptb_ysat                      # patches Enc.atmost (aux-var fix)
from cpri_round import Enc, encode, solve, decode, init_tables
from cptb_yprep import TG, ALL
from cptb_ystage import endstate
from cpri_io import out_path

def stage(init, tg, R, G, L, to):
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
                if (t >> i) & 1: e.cl += [[-sel[w], lit, pol], [-sel[w], -lit, -pol]]
                else: e.cl += [[-sel[w], -lit, pol], [-sel[w], lit, -pol]]
    for w in range(9):
        e.atmost([e.v('tsel', k, w) for k in range(len(tg))], 1)
    res = solve(e.cl, to)
    if res in (None, 'timeout'): return res, None
    return 'SAT', decode(res, R, G, e, L=L, only='y')

def main():
    order = sys.argv[1].split(','); Rmin, Rmax, G, L, to = map(int, sys.argv[2:7])
    byname = {t[0]: t for t in TG}
    state = init_tables(); done = []; total = 0
    for k, name in enumerate(order):
        tg = [byname[n] for n in done + [name]]
        for R in range(Rmin, Rmax + 1):
            t0 = time.time(); st, s = stage(state, tg, R, G, L, to)
            print('stage %d (+%s) R=%d -> %s %.0fs' % (k, name, R, st if isinstance(st, str) else 'UNSAT', time.time() - t0), flush=True)
            if st == 'SAT':
                print('  lins', s['ylin']); print('  gates', s['y'], flush=True)
                pickle.dump((s, state, done + [name]), open(out_path('cptb_ychain_stage%d.pkl' % k), 'wb'))
                state = endstate(s, state); done.append(name); total += R
                break
        else:
            print('stuck at', name, flush=True); return
    print('ALL TARGETS in %d levels' % total, flush=True)

if __name__ == '__main__':
    main()
