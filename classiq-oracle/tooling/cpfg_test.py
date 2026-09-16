"""End-to-end test of the CP-FG pipeline on a SUB-DAG: the first `nlev` levels
restricted to the cone of a few phase-feeding nodes, phase terms replaced by
CZ on the sub-DAG's top nodes.  Runs the real driver code path (window model,
skips, tightening, decode, mirror), then EXACT replay + statevector-free phase
check + transpile.  Must pass before any full-scale run."""
import sys, time, pickle
sys.path.insert(0, '/home/user/classiq-challenge')
import cpfg_model as M


def make_subdag(nodes_keep):
    """restrict the global DAG to nodes_keep (must be pred-closed); rewrite the
    module-level tables that cpfg_asm / cpfg_drive read at build time."""
    import cpfg_asm as A, cpfg_drive as D
    keep = sorted(nodes_keep)
    idx = {k: i for i, k in enumerate(keep)}
    NB = M.N
    def remap(o):
        v = o & ((1 << 12) - 1) | (o & (1 << 69))
        for k in keep:
            if (o >> (12 + k)) & 1: v |= 1 << (12 + idx[k])
        return v
    N = [[remap(o) for o in NB[k]] for k in keep]
    top = [i for i, k in enumerate(keep) if not any(j in idx for j in M.succ[k])]
    TERMS = [[1 << (12 + top[0]), 1 << (12 + top[1]) if len(top) > 1 else (1 << 0)]]
    preds = [[idx[j] for j in M.preds[k]] for k in keep]
    succ = [[idx[j] for j in M.succ[k] if j in idx] for k in keep]
    lev = [M.lev[k] for k in keep]
    dur = [M.dur[k] for k in keep]
    for mod in (M, A, D):
        mod.N = N; mod.NN = len(N); mod.TERMS = TERMS
    M.preds, M.succ, M.lev, M.dur = preds, succ, lev, dur
    A.dur = dur; D.dur = dur
    return N, TERMS


def replay(ops, N, TERMS):
    """exact symbolic replay of body;phase;mirror on the sub-DAG: every Toffoli
    reads exact operands, every phase gate reads its term, all wires restored."""
    RAW = [1 << w if w < 12 else 0 for w in range(18)]
    cont = list(RAW); phase = set(); ok = True
    for op in ops:
        k = op[0]
        if k == 'x': cont[op[1]] ^= 1 << 69
        elif k == 'cx': cont[op[2]] ^= cont[op[1]]
        elif k in ('ccx', 'ccx_dg', 'c3x', 'c3x_dg'):
            *rs, tw = op[1:]; forms = sorted(cont[q] for q in rs)
            mt = [i for i in range(len(N)) if sorted(N[i]) == forms]
            if not mt: return False, 'bad toffoli read %s' % (op,)
            cont[tw] ^= 1 << (12 + mt[0])
        elif k in ('cz', 'ccz'):
            forms = sorted(cont[q] & ((1 << 69) - 1) for q in op[1:])
            if forms != sorted(t & ((1 << 69) - 1) for t in TERMS[0]): return False, 'bad phase read %s' % (op,)
            phase.add(tuple(forms))
        else: return False, 'unknown op %s' % (op,)
    if cont != RAW: return False, 'wires not restored: %s' % [w for w in range(18) if cont[w] != RAW[w]]
    if not phase: return False, 'phase never fired'
    return True, 'ok'


if __name__ == '__main__':
    n_l0 = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    # sub-DAG: a few level-1 nodes and their level-0 preds
    l1 = [k for k in range(57) if M.lev[k] == 1][:n_l0]
    keep = set(l1)
    for k in l1: keep |= set(M.preds[k])
    N, TERMS = make_subdag(keep)
    import cpfg_drive as D, cpfg_eval as E
    from cpae_core import ops_to_qc, mirror
    from qiskit import transpile
    print('sub-DAG: %d nodes, levels %s, phase term arity %d' % (len(N), sorted(set(M.lev)), len(TERMS[0])), flush=True)
    t0 = time.time()
    r = D.run(cap=6, W=2, slack=1, tlimit=60, tighten=1, min_free=0, verbose=True, ckpt=False, slide=1)
    print('driver %.0fs' % (time.time() - t0), flush=True)
    assert r is not None, 'driver failed'
    body, ph, T = r
    ops = list(body) + list(ph) + mirror(body)
    ok, why = replay(ops, N, TERMS)
    print('exact replay:', ok, why)
    assert ok, why
    qc = ops_to_qc(ops, n=18)
    tq = transpile(qc, basis_gates=['u3', 'cx'], optimization_level=2, seed_transpiler=0)
    print('transpiled depth %d cx %d for %d nodes (steps %d)' % (tq.depth(), tq.count_ops().get('cx', 0), len(N), T))
    print('TEST PASS')
