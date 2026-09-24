"""Step 3 + rotation readouts.  Same forward model as cptd_merge3 (rounds of
LCX CX layers + one Toffoli layer over the 249 list's value classes, then one
mirror), but a readout may fire as a diagonal phase on any UNFOLDED value set:
readout values are replaced by the values they were computed from (value DAG
of cptd_rot), keeping <= KMAX classes.  The phase pi*g(V) is a function of
the held classes, emitted as a diagonal on their wires (cz/ccz when it is a
plain AND).  Readouts stay relaxed (free, no wires) as in merge3, so UNSAT at
R is a floor.
Usage: KMAX=5 LCX=2 python3 cptd_merge4.py R1 R2 ...   (PSOLVE=1 for progress)
Checkpoint: ckpt/merge4_ledger.json (keys R:LCX:KMAX),
            ckpt/merge4_R<R>_L<L>_K<K>.pkl, *_progress.json"""
import os, sys, json, time, pickle
import numpy as np
import cptd_merge3 as M
import cptd_rot as T

NW, N = 18, 4096
KMAX = int(os.environ.get('KMAX', '5'))
MAXOPT = int(os.environ.get('MAXOPT', '400'))
LEDGER = 'ckpt/merge4_ledger.json'


def options(C, vals, reads):
    """per readout: list of (class tuple, g table over the classes) incl. the
    original readout; g[idx] = phase bit, idx bit i = canonical class value i"""
    rv, ready, recipe, _, const = T.dag()
    rid = {np.packbits(v).tobytes(): i for i, v in enumerate(rv)}
    out = []
    for _, vs in reads:
        g = np.ones(N, dtype=np.uint8)
        for v in vs: g &= v
        s0 = frozenset(rid[np.packbits(v).tobytes()] for v in vs) - const
        seen, todo, opts = {s0}, [s0], {}
        while todo and len(opts) < MAXOPT:
            s = todo.pop(0)
            cls = tuple(sorted(set(C[M.key(rv[v])] for v in s)))
            if len(cls) <= KMAX and cls not in opts:
                idx = np.zeros(N, dtype=np.int64)
                for i, c in enumerate(cls): idx |= vals[c].astype(np.int64) << i
                t = np.full(1 << len(cls), -1, dtype=np.int8)
                for a, b in zip(idx, g):
                    assert t[a] in (-1, b); t[a] = b
                t[t < 0] = 0
                opts[cls] = t
            for v in s:
                if v not in recipe: continue
                s2 = (s - {v}) | (frozenset(recipe[v]) - const)
                if len(s2) <= KMAX + 1 and s2 not in seen:
                    seen.add(s2); todo.append(s2)
        out.append(list(opts.items()))
    return out


def encode(R, C, vals, P, pt, xor, opts):
    e = M.encode(R, C, vals, P, pt, xor, [])
    S = (M.LCX + 1) * R + 1
    for k, ol in enumerate(opts):
        lits = []
        for o, (cls, _) in enumerate(ol):
            for s in range(S):
                v = e.v('rd4', k, o, s); lits.append(v)
                for c in cls: e.cl.append([-v, e.v('pr', s, c)])
        e.cl.append(lits)
    return e


def decode(R, e, model, nc, P, opts):
    sol = M.decode(R, e, model, nc, P, [], None)
    m = set(l for l in model if l > 0); S = (M.LCX + 1) * R + 1
    on = lambda *k: e.pool.obj2id.get(k) in m
    sol['rd4'] = [next((o, s) for o in range(len(ol)) for s in range(S) if on('rd4', k, o, s))
                  for k, ol in enumerate(opts)]
    return sol


def emit(d):
    """forward stream (diag readouts inserted at their states) + one mirror"""
    sol, P, vals, opts = d['sol'], d['P'], d['vals'], d['opts']
    s = np.arange(N, dtype=np.int64)
    bit = lambda w: ((s >> w) & 1).astype(np.uint8)
    def find(v, excl=()):
        for w in range(NW):
            if w in excl: continue
            b = bit(w)
            if np.array_equal(b, v): return w, 0
            if np.array_equal(b, v ^ 1): return w, 1
        raise RuntimeError('value not held')
    stream, conflicts = [], 0
    def readouts(st):
        for k, (o, s0) in enumerate(sol['rd4']):
            if s0 != st: continue
            cls, t = opts[k][o]
            ws, fl = [], []
            for c in cls:
                w, f = find(vals[c], ws); ws.append(w); fl.append(f)
            # table over wire bits: class bit i = wire bit i ^ fl[i]
            tw = np.array([t[a ^ sum(f << i for i, f in enumerate(fl))] for a in range(1 << len(ws))], dtype=np.uint8)
            stream.append(('diag', tuple(ws), tw))
    K = sol['lcx'] + 1
    for r, (cxl, tfs) in enumerate(sol['layers']):
        for l, cxs in enumerate(cxl):
            readouts(K * r + l)
            for sw, tw in cxs:
                stream.append(('cx', sw, tw)); s = s ^ (((s >> sw) & 1) << tw)
        readouts(K * r + K - 1)
        written = set(w for w, _ in tfs); used = {}; plan = []
        for w, j in tfs:
            cs, pol = P[j]; ctl = []
            for i, c in enumerate(cs):
                cw, _ = find(vals[c] ^ ((pol >> i) & 1), set(written) | set(ctl))
                used[cw] = used.get(cw, 0) + 1; ctl.append(cw)
            plan.append((w, ctl, cs, pol))
        conflicts += sum(v - 1 for v in used.values() if v > 1)
        for w, ctl, cs, pol in plan:
            need = [vals[c] ^ ((pol >> i) & 1) for i, c in enumerate(cs)]
            fl = [cw for cw, v in zip(ctl, need) if not np.array_equal(bit(cw), v)]
            p = np.ones(N, dtype=np.uint8)
            for v in need: p &= v
            stream += [('x', cw) for cw in fl]
            stream.append(('ccx' if len(ctl) == 2 else 'c3x',) + tuple(ctl) + (w,))
            stream += [('x', cw) for cw in fl]
            s = s ^ (p.astype(np.int64) << w)
    readouts(K * len(sol['layers']))
    fwd = [o for o in stream if o[0] != 'diag']
    return stream + M_mirror(fwd), conflicts


def M_mirror(ops):
    from cpae_core import mirror
    return mirror(ops)


def classical(ops):
    from cpae_core import SHAPES, fvec
    s = np.arange(N, dtype=np.int64); ph = np.zeros(N, dtype=np.int64)
    b = lambda w: (s >> w) & 1
    for op in ops:
        k, q = op[0], op[1:]
        if k == 'x': s = s ^ (1 << q[0])
        elif k == 'cx': s = s ^ (b(q[0]) << q[1])
        elif k.startswith('ccx'): s = s ^ ((b(q[0]) & b(q[1])) << q[2])
        elif k.startswith('c3x'): s = s ^ ((b(q[0]) & b(q[1]) & b(q[2])) << q[3])
        elif k == 'diag':
            idx = np.zeros(N, dtype=np.int64)
            for i, w in enumerate(q[0]): idx |= b(w) << i
            ph ^= q[1][idx].astype(np.int64)
    return int((ph != fvec(SHAPES['LOGO'])).sum()), bool((s == np.arange(N)).all())


def to_qc(ops):
    from qiskit.circuit.library import DiagonalGate
    from cpae_core import ops_to_qc
    qc = ops_to_qc([])
    for o in ops:
        if o[0] != 'diag':
            qc.compose(ops_to_qc([o]), inplace=True); continue
        ws, t = o[1], o[2]
        if len(ws) == 2 and list(t) == [0, 0, 0, 1]: qc.cz(*ws)
        elif len(ws) == 3 and list(t) == [0] * 7 + [1]: qc.ccz(*ws)
        else: qc.append(DiagonalGate([(-1.0) ** int(x) for x in t]), list(ws))
    return qc


def ledger_set(k, v):
    dd = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {}
    dd[k] = v; tmp = LEDGER + '.tmp'
    json.dump(dd, open(tmp, 'w'), indent=1); os.replace(tmp, LEDGER)


if __name__ == '__main__':
    os.makedirs('ckpt', exist_ok=True)
    ops, C, vals, prods, reads = M.extract()
    xor, P, pt = M.tables(C, vals, prods)
    opts = options(C, vals, reads)
    if os.environ.get('READS'):          # reduced test: subset of readouts (phase check then fails)
        opts = [opts[int(k)] for k in os.environ['READS'].split(',')]
        LEDGER = 'ckpt/merge4_test_ledger.json'
    print('classes %d  products %d  readouts %d  options per readout %s  KMAX %d' %
          (len(vals), len(P), len(reads), [len(o) for o in opts], KMAX), flush=True)
    done = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {}
    for R in map(int, sys.argv[1:]):
        kk = '%d:%d:%d' % (R, M.LCX, KMAX)
        if kk in done and done[kk]['res'] in ('SAT', 'UNSAT'):
            print('R=%d cached %s' % (R, done[kk]['res']), flush=True); continue
        e = encode(R, C, vals, P, pt, xor, opts)
        print('R=%d vars %d clauses %d' % (R, e.pool.top, len(e.cl)), flush=True)
        t0 = time.time()
        if os.environ.get('PSOLVE'):
            from cptd_psolve import solve as psolve
            res = psolve(e.cl, 'merge4 R=%d L=%d K=%d' % (R, M.LCX, KMAX),
                         'ckpt/merge4_R%d_L%d_K%d_progress.json' % (R, M.LCX, KMAX))
        else:
            res = M.solve(e.cl, None)
        dt = time.time() - t0
        tag = 'SAT' if isinstance(res, list) else 'UNSAT'
        print('R=%d -> %s  %.0fs' % (R, tag, dt), flush=True)
        ledger_set(kk, dict(res=tag, sec=round(dt)))
        if tag == 'SAT':
            sol = decode(R, e, res, len(vals), P, opts)
            d = dict(sol=sol, P=[(cs, pol) for cs, pol, _ in P], vals=vals, opts=opts)
            pickle.dump(d, open('ckpt/merge4_R%d_L%d_K%d.pkl' % (R, M.LCX, KMAX), 'wb'))
            full, conf = emit(d)
            from cpae_core import real_depth
            print('emit: ops %d  fanout conflicts %d  classical %s  real depth/cx %s' %
                  (len(full), conf, classical(full), real_depth(to_qc(full))), flush=True)
            break
