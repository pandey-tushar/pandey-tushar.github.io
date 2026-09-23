"""staged y-prep: add one target per stage, keeping all earlier targets on
some wire.  Each stage is a small exact SAT (R levels, G RCCX, L CX per level)
started from the previous stage's end state; tries R = Rmin..Rmax.
usage: order(comma names) Rmin Rmax G L timeout [ckptdir]

Resumable: finished stages are stored in ckptdir (default ./ckpt, tracked in
git) as ychain_<order>_stageK.pkl, and every attempt is logged in
ckptdir/ychain_ledger.json.  A rerun loads finished stages and skips any
(stage, R, G, L) attempt that already timed out with a timeout >= this one."""
import sys, os, json, time, pickle
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
    ck = sys.argv[7] if len(sys.argv) > 7 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ckpt')
    os.makedirs(ck, exist_ok=True)
    tag = '-'.join(order)
    lpath = os.path.join(ck, 'ychain_ledger.json')
    ledger = json.load(open(lpath)) if os.path.exists(lpath) else []
    def log(rec):                              # re-read: several runs share the ledger
        cur = json.load(open(lpath)) if os.path.exists(lpath) else []
        cur.append(rec); json.dump(cur, open(lpath + '.tmp', 'w'), indent=1)
        os.replace(lpath + '.tmp', lpath); ledger.append(rec)
    byname = {t[0]: t for t in TG}
    import cptb_yprep as Y            # extra target: exact valid rows (V3 = VAL ^ W3)
    byname['VAL'] = ('VAL', Y.V3 | Y.W3, ALL)
    state = init_tables(); done = []; total = 0
    if order[0] == 'P1':              # start after cptb_phase1: raw y + V3 on local wire 8
        import cptb_yprep as Y
        state = list(state); state[8] = Y.V3; done = ['V3']
    for k, name in enumerate(order):
        if name == 'P1':
            continue
        f = os.path.join(ck, 'ychain_%s_stage%d.pkl' % (tag, k))
        if os.path.exists(f):                       # resume
            s, _, names = pickle.load(open(f, 'rb'))
            R = len(s['y']); state = endstate(s, state); done.append(name); total += R
            print('stage %d (+%s) R=%d -> loaded from checkpoint' % (k, name, R), flush=True)
            continue
        tg = [byname[n] for n in done + [name]]
        for R in range(Rmin, Rmax + 1):
            key = dict(order=tag, stage=k, target=name, R=R, G=G, L=L)
            prev = [r for r in ledger if all(r.get(a) == b for a, b in key.items())]
            if any(r['result'] == 'UNSAT' or (r['result'] == 'timeout' and r['timeout'] >= to) for r in prev):
                print('stage %d (+%s) R=%d -> skipped (ledger: %s)' % (k, name, R, prev[-1]['result']), flush=True)
                continue
            t0 = time.time(); st, s = stage(state, tg, R, G, L, to)
            res = st if isinstance(st, str) else 'UNSAT'
            log(dict(key, timeout=to, result=res, secs=round(time.time() - t0)))
            print('stage %d (+%s) R=%d -> %s %.0fs' % (k, name, R, res, time.time() - t0), flush=True)
            if st == 'SAT':
                print('  lins', s['ylin']); print('  gates', s['y'], flush=True)
                pickle.dump((s, state, done + [name]), open(f, 'wb'))
                state = endstate(s, state); done.append(name); total += R
                break
        else:
            print('stuck at', name, flush=True); return
    print('ALL TARGETS in %d levels' % total, flush=True)

if __name__ == '__main__':
    main()
