"""One sweep job: encode a round schedule, solve it, report a JSON line.

A job is a single point of the sweep matrix: a mode (joint / x-only /
y-only), a pair subset, R rounds, G RCCX per side per round, L hosting CX
per side per round, a coverage width maxsel and a solver seed.

On SAT the schedule is checked against the pixel tables and pickled.  A
joint job over the full pair set is also emitted as a real circuit,
transpiled for its true depth and verified on the statevector.

usage: cpri_job.py --mode joint --pairs all --R 8 --G 3 --L 0 \
                   --maxsel 3 --seed 0 --timeout 7200 [--mem-gb 3]
"""
import argparse
import json
import os
import pickle
import random
import resource
import sys
import time

from cpri_io import out_path

# pair subsets of the 11-pair rank decomposition, by index into PAIRS
#   0 gA/P     1 gB/Q       2 g0^g1/Y1721  3 g1/Y1523   4 g2^g2c/Y13r
#   5 g2c/Q    6 g4^g4c/Y12r 7 g4c/Y36r    8 g6^g6c/Y11r 9 g6c/Y35r
#  10 g3/Y37r
SUBSETS = {
    'all': list(range(11)),
    'rings': [4, 6, 7, 8, 9, 10],
    'pq': [0, 1, 5],
    'bands': [2, 3],
    'halfa': [0, 1, 2, 3, 4, 5],
    'halfb': [6, 7, 8, 9, 10],
}
for _k in range(11):
    SUBSETS['k%d' % _k] = [_k]


def job_id(a):
    return 'm%s_p%s_R%d_G%d_L%d_s%d_z%d' % (
        a.mode, a.pairs, a.R, a.G, a.L, a.maxsel, a.seed)


def run(a):
    from cpri_round import (Enc, encode, solve, decode, check, init_tables,
                            logo_pairs, bit)
    rec = {'job': job_id(a), 'mode': a.mode, 'pairs': a.pairs, 'R': a.R,
           'G': a.G, 'L': a.L, 'maxsel': a.maxsel, 'seed': a.seed,
           'status': 'error', 'solve_s': 0.0, 'vars': 0, 'clauses': 0,
           'depth': '', 'cx': '', 'err': '', 'note': ''}
    idx = SUBSETS[a.pairs]
    full = logo_pairs()
    pairs = [full[k] for k in idx]
    if a.mode == 'x':
        pairs = [(u, bit(0)) for u, v in pairs]
    elif a.mode == 'y':
        pairs = [(bit(0), v) for u, v in pairs]
    only = None if a.mode == 'joint' else a.mode

    xinit = init_tables()
    yinit = init_tables()
    e = Enc()
    t0 = time.time()
    encode(a.R, a.G, pairs, xinit, yinit, e, maxsel=a.maxsel, L=a.L, only=only)
    rec['vars'] = e.pool.top
    rec['clauses'] = len(e.cl)
    rec['encode_s'] = round(time.time() - t0, 1)

    cl = e.cl
    if a.seed:
        cl = list(cl)
        random.Random(a.seed).shuffle(cl)

    t0 = time.time()
    res = solve(cl, a.timeout)
    rec['solve_s'] = round(time.time() - t0, 1)
    if res == 'timeout':
        rec['status'] = 'timeout'
        return rec
    if res is None:
        rec['status'] = 'unsat'
        return rec

    rec['status'] = 'sat'
    sched = decode(res, a.R, a.G, e, L=a.L, only=only)
    ok = check(sched, pairs, xinit, yinit)
    rec['note'] = 'check=%s' % ok
    if not ok:
        rec['status'] = 'badcheck'
        return rec
    path = out_path(job_id(a) + '.pkl')
    pickle.dump(sched, open(path, 'wb'))
    rec['pkl'] = os.path.basename(path)

    if a.mode == 'joint' and a.pairs == 'all':
        rec.update(measure(sched, pairs))
    return rec


def measure(sched, pairs):
    """emit the schedule, transpile it, verify it; anything over depth 200 is
    dead by the standing rule."""
    from cpri_emit import emit
    from cpae_core import ops_to_qc, real_depth, sv_check_gp
    out = {}
    try:
        ops = emit(sched, pairs)
        qc = ops_to_qc(ops)
        d, cx = real_depth(qc)
        out['depth'] = d
        out['cx'] = cx
        err, leak = sv_check_gp(qc, "LOGO")
        out['err'] = '%.3g' % err
        out['note'] = 'leak=%.3g %s' % (leak, 'DEAD>200' if d > 200 else 'LIVE')
    except Exception as ex:                      # emission is best effort
        out['note'] = 'emit failed: %s' % ex
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', default='joint', choices=('joint', 'x', 'y'))
    p.add_argument('--pairs', default='all', choices=sorted(SUBSETS))
    p.add_argument('--R', type=int, default=8)
    p.add_argument('--G', type=int, default=3)
    p.add_argument('--L', type=int, default=0)
    p.add_argument('--maxsel', type=int, default=3)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--timeout', type=float, default=7200)
    p.add_argument('--mem-gb', type=float, default=0)
    a = p.parse_args()
    if a.mem_gb:
        lim = int(a.mem_gb * (1 << 30))
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
    try:
        rec = run(a)
    except MemoryError:
        rec = {'job': job_id(a), 'mode': a.mode, 'pairs': a.pairs, 'R': a.R,
               'G': a.G, 'L': a.L, 'maxsel': a.maxsel, 'seed': a.seed,
               'status': 'oom', 'solve_s': 0.0, 'vars': 0, 'clauses': 0,
               'depth': '', 'cx': '', 'err': '', 'note': 'memory limit'}
    except Exception as ex:
        rec = {'job': job_id(a), 'mode': a.mode, 'pairs': a.pairs, 'R': a.R,
               'G': a.G, 'L': a.L, 'maxsel': a.maxsel, 'seed': a.seed,
               'status': 'error', 'solve_s': 0.0, 'vars': 0, 'clauses': 0,
               'depth': '', 'cx': '', 'err': '', 'note': str(ex)[:200]}
    sys.stdout.write('RESULT ' + json.dumps(rec) + '\n')


if __name__ == '__main__':
    main()
