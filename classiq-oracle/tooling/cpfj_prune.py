"""CP-FJ: junk-tolerant pruning of an op list.

Strip the phase gates, then greedily delete x / cx ops (alone, or together
with their mirror partner) as long as the classical action stays the
identity and the temporal phase span still contains F exactly.  Deleting an
assembly CX leaves junk on the wires it fed; the span solver has to absorb
it.  This is the prerequisite test for junk-tolerant hosting.
"""
import sys, pickle, time, random
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfi_span as S
import cpfh_core as C
from cpfh_core import NW, F
from cpae_core import model_depth as _md, extract, sim_exact, fvec, SHAPES
from cpfi_exec import ops_to_qc

def model_depth(ops): return _md([o for o in ops if o[0] != 'z'])

def identity(ops):
    c, _ = C.replay(ops)
    return all(c[w] == C.RM[w] for w in range(NW))

def triples_for(ops, tri):
    return [(t, ws) for t in range(len(ops) + 1) for ws in tri]

def solved(ops, tri):
    r, ins = S.solve(ops, deg=3, triple_wires=triples_for(ops, tri))
    return r == 0, ins

def opt2(ops):
    qc = ops_to_qc(ops, n=18)
    from qiskit import transpile
    t = transpile(qc, basis_gates=['u3', 'cx'], optimization_level=2)
    return t.depth(), t.count_ops().get('cx', 0)

def verify(ops):
    qc = ops_to_qc(ops, n=18)
    gl, gp = extract(qc)
    err, mm = sim_exact(gl, gp, fvec(SHAPES['LOGO']))
    return err < 1e-9 and mm == 0

def partner(ops, i):
    """mirror partner: nearest identical op after i (or before)."""
    for j in range(i + 1, len(ops)):
        if ops[j] == ops[i]: return j
    for j in range(i - 1, -1, -1):
        if ops[j] == ops[i]: return j
    return None

def prune(ops, tri, kinds=('x', 'cx'), seed=0, verbose=True, limit=None, metric='model'):
    meas = (lambda o: model_depth(o)) if metric == 'model' else (lambda o: opt2(o)[0])
    rng = random.Random(seed)
    cur = list(ops)
    ok, ins = solved(cur, tri)
    assert ok, 'start not solvable'
    d0 = meas(S.insert(cur, ins))
    if verbose: print('start: %d ops model depth %d' % (len(cur), d0), flush=True)
    improved = True; rounds = 0; tried = 0; nid = 0; nsp = 0
    while improved:
        improved = False; rounds += 1
        idx = [i for i, o in enumerate(cur) if o[0] in kinds]
        rng.shuffle(idx)
        for i in idx:
            if i >= len(cur) or cur[i][0] not in kinds: continue
            if limit and tried >= limit:
                print('limit: tried %d identity-ok %d span-ok %d' % (tried, nid, nsp), flush=True); return cur, ins
            tried += 1
            for rem in ([i], None):
                if rem is None:
                    j = partner(cur, i)
                    if j is None: break
                    rem = sorted({i, j})
                trial = [o for t, o in enumerate(cur) if t not in rem]
                if not identity(trial): continue
                nid += 1
                ok2, ins2 = solved(trial, tri)
                if not ok2: continue
                nsp += 1
                d = meas(S.insert(trial, ins2))
                if d <= d0:
                    if verbose and d < d0:
                        print('  rm %s -> %d ops model %d (phase gates %d)' % ([cur[k] for k in rem], len(trial), d, len(ins2)), flush=True)
                    cur, ins, d0 = trial, ins2, d
                    improved = True
                    break
        if verbose: print('round %d: %d ops model %d  tried %d identity-ok %d span-ok %d' % (rounds, len(cur), d0, tried, nid, nsp), flush=True)
    return cur, ins

if __name__ == '__main__':
    ops = pickle.load(open('cpen_search_11.pkl', 'rb'))[1]
    ops = [tuple(o) for o in ops]
    tri = sorted({tuple(o[1:]) for o in ops if o[0] == 'ccz'})
    base = S.strip_phase(ops)
    ok, ins = solved(base, tri)
    full0 = S.insert(base, ins)
    print('stripped: solvable %s, %d phase gates, model %d, opt2 %s' % (ok, len(ins), model_depth(full0), opt2(full0)), flush=True)
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    metric = sys.argv[3] if len(sys.argv) > 3 else 'model'
    t0 = time.time()
    cur, ins = prune(base, tri, seed=seed, limit=limit, metric=metric)
    full = S.insert(cur, ins)
    print('done %.0fs: %d ops, model %d, opt2 %s, verify %s' % (time.time() - t0, len(full), model_depth(full), opt2(full), verify(full)), flush=True)
    pickle.dump(full, open('cpfj_prune_%s_s%d.pkl' % (metric, seed), 'wb'))
