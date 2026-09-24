"""Merge idea, garbage-aware beam: chains the readouts one segment at a time.
Segment = beam (cptd_beam moves, focus on the cheapest pending readout) until
a new readout fires; then choose how many of the segment's last steps to undo
(exact inverse steps, frees wires) by   score(remaining) + LAM * undo cost.
The whole forward stream is followed by one mirror (relative phases cancel).
Usage: python3 cptd_gbeam.py BEAM EXPAND SEED
Checkpoint: ckpt/gbeam_<seed>.pkl (op list + depth, only if exact)"""
import os, sys, time, pickle, random
import numpy as np
import cptd_beam as B
from cpae_core import mirror, ops_to_qc, real_depth
import cptd_emit3 as E

NW, N = 18, 4096
LAM = float(os.environ.get('LAM', '1.0'))
STEPC = {'cx': 0.3, 'tof': 1.0}
B.FOCUS = float(os.environ.get('FOCUS', '0.01'))


def fire(m, st, pend, pos, rds):
    held = set(st)
    for k in list(pend):
        if all(c in held for c in m.rcls[k]):
            pend.discard(k); rds[k] = pos


def apply_step(m, st, step):
    kind, mv = step; st = list(st)
    if kind == 'cx':
        for sw, tw in mv: st[tw] = m.xor[st[tw], st[sw]]
    else:
        st0 = list(st)
        for w, j in mv: st[w] = m.pt[j, st0[w]]
    return st


def segment(m, node, beam, expand, rng, maxr=30):
    """beam from node until some readout fires; returns candidate nodes"""
    front = [node]; n0 = len(node['pend'])
    for R in range(maxr):
        nxt = []
        for nd in front:
            for _ in range(expand):
                st, pend, rds = list(nd['st']), set(nd['pend']), dict(nd['rds'])
                steps, hist = list(nd['steps']), list(nd['hist'])
                for l in range(B.LCX):
                    mv, st = B.cx_layer(m, st, pend, rng, 3)
                    if mv:
                        steps.append(('cx', mv)); hist.append(st); fire(m, st, pend, len(steps), rds)
                mv, st = B.tof_layer(m, st, pend, rng, 3, 0.02)
                if mv:
                    steps.append(('tof', mv)); hist.append(st); fire(m, st, pend, len(steps), rds)
                nxt.append(dict(st=st, pend=pend, rds=rds, steps=steps, hist=hist,
                                seg0=nd['seg0'], sc=B.best_next(m, st, pend)))
        hit = [n for n in nxt if len(n['pend']) < n0]
        if hit:
            return sorted(hit, key=lambda n: n['sc'])[:beam]
        uniq = {}
        for n in sorted(nxt, key=lambda n: n['sc']):
            uniq.setdefault(tuple(n['st']), n)
        front = list(uniq.values())[:beam]
    return []


def cleanup(m, nd):
    """undo the last L steps of the current segment (inverse = same step again,
    applied in reverse order); pick L by score + LAM * cost"""
    seg = nd['steps'][nd['seg0']:]
    best = None
    for L in range(len(seg) + 1):
        undo = [seg[-1 - i] for i in range(L)]
        st = nd['hist'][len(nd['steps']) - 1 - L] if L else nd['st']
        if L == len(nd['steps']): st = list(m.init)
        sc = B.best_next(m, st, nd['pend']) + LAM * sum(STEPC[s[0]] for s in undo)
        if best is None or sc < best[0]:
            best = (sc, L, st, undo)
    _, L, st, undo = best
    steps = nd['steps'] + undo
    hist = nd['hist'] + [None] * len(undo)
    # recompute hist for the undo steps
    cur = nd['st']
    for i, s in enumerate(undo):
        cur = apply_step(m, cur, s); hist[len(nd['steps']) + i] = cur
    assert list(cur) == list(st)
    return dict(st=list(st), pend=set(nd['pend']), rds=dict(nd['rds']), steps=steps,
                hist=hist, seg0=len(steps), sc=best[0]), L


def emit(m, nd):
    s = np.arange(N, dtype=np.int64)
    bit = lambda w: ((s >> w) & 1).astype(np.uint8)
    same = np.array_equal
    vals = m.vals
    def find(v, excl=()):
        for w in range(NW):
            if w in excl: continue
            b = bit(w)
            if same(b, v): return w, False
            if same(b, v ^ 1): return w, True
        raise RuntimeError('value not held')
    stream = []
    def readouts(pos):
        for k, p in nd['rds'].items():
            if p != pos: continue
            ws = []
            for v in m.reads[k][1]:
                w, fl = find(v, ws); ws.append(w)
                if fl: stream.append(('x', w))
            stream.append(('cz' if len(ws) == 2 else 'ccz',) + tuple(ws))
            for w, v in zip(ws, m.reads[k][1]):
                if not same(bit(w), v): stream.append(('x', w))
    readouts(0)
    for i, (kind, mv) in enumerate(nd['steps']):
        if kind == 'cx':
            for sw, tw in mv:
                stream.append(('cx', sw, tw)); s = s ^ (((s >> sw) & 1) << tw)
        else:
            written = set(w for w, _ in mv); plan = []
            for w, j in mv:
                cs, pol, _ = m.P[j]; ctl = []; need = []
                for q, c in enumerate(cs):
                    v = vals[c] ^ ((pol >> q) & 1); need.append(v)
                    cw, _ = find(v, written | set(ctl)); ctl.append(cw)
                plan.append((w, ctl, need))
            for w, ctl, need in plan:
                fl = [cw for cw, v in zip(ctl, need) if not same(bit(cw), v)]
                p = np.ones(N, dtype=np.uint8)
                for v in need: p &= v
                stream += [('x', cw) for cw in fl]
                stream.append(('ccx' if len(ctl) == 2 else 'c3x',) + tuple(ctl) + (w,))
                stream += [('x', cw) for cw in fl]
                s = s ^ (p.astype(np.int64) << w)
        readouts(i + 1)
    fwd = [o for o in stream if o[0] not in ('cz', 'ccz')]
    return stream + mirror(fwd)


def run(beam, expand, seed):
    m = B.Model(); rng = random.Random(seed)
    nd = dict(st=list(m.init), pend=set(range(len(m.rcls))), rds={}, steps=[], hist=[], seg0=0)
    fire(m, nd['st'], nd['pend'], 0, nd['rds'])
    while nd['pend']:
        cands = segment(m, nd, beam, expand, rng)
        if not cands:
            print('stuck: pending %d after %d steps' % (len(nd['pend']), len(nd['steps'])), flush=True)
            return m, None
        nd, L = cleanup(m, cands[0])
        print('fired -> pending %d  steps %d  (undo %d)' % (len(nd['pend']), len(nd['steps']), L), flush=True)
    return m, nd


if __name__ == '__main__':
    beam, expand, seed = map(int, sys.argv[1:4])
    t0 = time.time()
    m, nd = run(beam, expand, seed)
    if nd is None: sys.exit(1)
    full = emit(m, nd)
    mism, ident = E.classical(full) if not os.environ.get('READS') else (-1, None)
    dep = real_depth(ops_to_qc(full))
    print('steps %d  ops %d  classical mism %s  identity %s  real depth/cx %s  %.0fs'
          % (len(nd['steps']), len(full), mism, ident, dep, time.time() - t0), flush=True)
    if mism == 0 and ident:
        os.makedirs('ckpt', exist_ok=True)
        pickle.dump(dict(depth=dep, ops=full, steps=nd['steps'], rds=nd['rds']),
                    open('ckpt/gbeam_%d.pkl' % seed, 'wb'))
        print('saved ckpt/gbeam_%d.pkl' % seed)
