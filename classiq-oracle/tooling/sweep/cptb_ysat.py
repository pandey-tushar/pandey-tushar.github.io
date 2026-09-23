"""exact synthesis of the forward-only y prep: R levels, <=G RCCX and <=L CX
per level on 9 y wires; final wires must hold the targets (either polarity,
distinct wires) on their care sets.  usage: R G L timeout"""
from cpri_io import out_path as _out
import sys, time, pickle
from cpri_round import Enc, encode, solve, decode, init_tables, simulate
from cptb_yprep import TG, ALL
from pysat.card import CardEnc, EncType
import cpri_round

def _atmost(self, lits, bound):
    cnf = CardEnc.atmost(lits=lits, bound=bound, top_id=self.pool.top, encoding=EncType.seqcounter)
    self.cl.extend(cnf.clauses)
    if cnf.nv > self.pool.top:
        self.pool.occupy(self.pool.top + 1, cnf.nv)
        self.pool.top = cnf.nv          # advance, so back-to-back calls do not share aux vars
cpri_round.Enc.atmost = _atmost

def main():
    import os
    global TG
    if os.environ.get('NOY5'): TG = [t for t in TG if t[0] != 'y5']   # NOY5: y5 wire free after m
    R, G, L, to = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
    e = Enc(); init = init_tables()
    sides, rho = encode(R, G, [], init, init, e, maxsel=1, L=L, only='y')
    W = sides['y'][0]
    NWI = 9
    for k, (name, t, care) in enumerate(TG):
        sel = [e.v('tsel', k, w) for w in range(NWI)]
        pol = e.v('tpol', k)
        e.exactly_one(sel)
        for w in range(NWI):
            for i in range(64):
                if not (care >> i) & 1: continue
                lit = W[(R, w)][i]; bitv = (t >> i) & 1
                # sel -> (lit xor pol) == bitv
                if bitv:
                    e.cl.append([-sel[w], lit, pol]); e.cl.append([-sel[w], -lit, -pol])
                else:
                    e.cl.append([-sel[w], -lit, pol]); e.cl.append([-sel[w], lit, -pol])
    for w in range(NWI):
        e.atmost([e.v('tsel', k, w) for k in range(len(TG))], 1)
    print('R=%d G=%d L=%d vars %d clauses %d' % (R, G, L, e.pool.top, len(e.cl)), flush=True)
    t0 = time.time(); res = solve(e.cl, to)
    st = 'timeout' if res == 'timeout' else ('UNSAT' if res is None else 'SAT')
    print('solve %.0fs -> %s' % (time.time() - t0, st), flush=True)
    if st == 'SAT':
        s = decode(res, R, G, e, L=L, only='y')
        print('lins', s['ylin']); print('gates', s['y'])
        pickle.dump(s, open(_out('cptb_ysat_R%d_G%d_L%d.pkl' % (R, G, L)), 'wb'))

if __name__ == '__main__':
    main()
