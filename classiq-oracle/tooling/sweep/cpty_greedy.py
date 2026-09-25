"""Greedy prefix search for the arbitrary-angle phase stage: each slot adds the
Toffoli (from NC random candidates) that minimises the OMP residual norm at
K = KP parity terms; levels of <= 6 disjoint Toffolis.  Final prefix gets a
full OMP to exactness.  Usage: python3 cpty_greedy.py SEED LEVELS NC KP
Checkpoint ckpt/wgreedy_s<seed>.pkl"""
import sys, time, random, pickle
import numpy as np
from multiprocessing import Pool
import cpte_evo as E
from cptw_mcts import Env, rand_action, unpack
from cpty_walsh import omp, NW
F = unpack(E.logo_bits()).astype(float)
env = Env(E.logo_bits(), 8)
def idx_of(seq):
    S, _ = env.play(seq)
    W = np.array([unpack(S[w]) for w in range(NW)]).astype(np.int64)
    return (W << np.arange(NW)[:, None]).sum(0)
def score(args):
    seq, KP = args
    out, _ = omp(idx_of(seq), F, KP, marks=(KP,))
    return out.get('exact', None) is not None and -1.0 or out[KP]
if __name__ == '__main__':
    seed, LV, NC, KP = map(int, sys.argv[1:5]); rng = random.Random(seed)
    seq = []; t0 = time.time()
    import os
    if os.environ.get('INIT'): seq = pickle.load(open(os.environ['INIT'], 'rb'))['seq']
    NP = int(os.environ.get('NP', '1'))
    base = score((seq, KP)); print('[wg s%d] empty prefix residual@%d %.3f' % (seed, KP, base), flush=True)
    with Pool(NP) as pool:
        done_lv = seq.count('end')
        for lv in range(done_lv, LV):
            cur = seq[len(seq) - seq[::-1].index('end'):] if 'end' in seq else list(seq)
            used = set()
            for c in cur: used |= {c[0], c[1], c[4]}
            for slot in range(6):
                cands = []
                for _ in range(NC):
                    a = rand_action(used, rng)
                    if a is None: break
                    cands.append(a)
                if not cands: break
                res = pool.map(score, [(seq + [c], KP) for c in cands])
                j = int(np.argmin(res))
                if res[j] >= base - 1e-9: break
                seq.append(cands[j]); base = res[j]; used |= {cands[j][0], cands[j][1], cands[j][4]}
                print('[wg s%d] level %d slot %d: residual@%d %.3f  (%s)  %.0fs' % (seed, lv + 1, slot + 1, KP, base, cands[j], time.time() - t0), flush=True)
                pickle.dump(dict(seq=seq, res=base), open('ckpt/wgreedy_s%d.pkl' % seed, 'wb'))
            seq.append('end')
    out, _ = omp(idx_of(seq), F, 4096)
    print('[wg s%d] final prefix %d Toffolis: residual by K %s' % (seed, sum(x != 'end' for x in seq),
          {k: ('%.3g' % v if k != 'exact' else v) for k, v in out.items()}), flush=True)
