"""Run the whole round-schedule search matrix in parallel and log every row.

Each job is an independent subprocess (cpri_job.py), so the sweep scales to
whatever cores the machine has and a job that hangs or blows up its memory
limit cannot take the sweep with it.  Results are appended to results.csv as
they land and the sweep is resumable: rerunning skips job ids already in the
file.

The matrix runs in four tiers, cheapest first:

  1 singles   one pair at a time, x-only and y-only, small R.  These decide
              fast and give the true minimum number of rounds each of the 11
              functions needs.  That is the number the hand design never had.
  2 subsets   rings / P-Q / bands / halves, one side at a time.
  3 sides     all 11 pairs, one side at a time, across R, G, L and maxsel.
  4 joint     all 11 pairs, both sides together, several solver seeds.

A tier-4 SAT model is emitted, transpiled for its real depth and checked on
the statevector in the same job, so a live row in results.csv is a circuit,
not a promise.  Depth over 200 is marked DEAD.

usage: cpri_sweep.py [--workers N] [--timeout S] [--tier 1,2] [--only SUBSTR]
                     [--list] [--mem-gb G]
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = ['job', 'tier', 'mode', 'pairs', 'R', 'G', 'L', 'maxsel', 'seed',
          'status', 'encode_s', 'solve_s', 'vars', 'clauses', 'depth', 'cx',
          'err', 'pkl', 'note']


def matrix():
    jobs = []

    def add(tier, mode, pairs, R, G=3, L=0, maxsel=3, seed=0):
        jobs.append({'tier': tier, 'mode': mode, 'pairs': pairs, 'R': R,
                     'G': G, 'L': L, 'maxsel': maxsel, 'seed': seed})

    # 1: one pair at a time, each side alone -- minimum rounds per function
    for k in range(11):
        for mode in ('x', 'y'):
            for R in (2, 3, 4, 5):
                add(1, mode, 'k%d' % k, R)

    # 2: structural subsets, each side alone
    for sub in ('bands', 'pq', 'rings', 'halfa', 'halfb'):
        for mode in ('x', 'y'):
            for R in (3, 4, 5, 6, 7, 8):
                for L in (0, 2):
                    add(2, mode, sub, R, L=L)

    # 3: all 11 pairs, each side alone
    for mode in ('x', 'y'):
        for R in (6, 7, 8, 9, 10, 12):
            for G in (3, 4):
                for L in (0, 2, 3):
                    for maxsel in (3, 5):
                        add(3, mode, 'all', R, G=G, L=L, maxsel=maxsel)

    # 4: both sides together, the thing that actually produces a circuit
    for R in (6, 7, 8, 9, 10, 12):
        for L in (0, 2):
            for maxsel in (3, 5):
                for seed in (0, 1):
                    add(4, 'joint', 'all', R, L=L, maxsel=maxsel, seed=seed)

    npair = {'all': 11, 'rings': 6, 'pq': 3, 'bands': 2, 'halfa': 6,
             'halfb': 5}
    for j in jobs:
        n = npair.get(j['pairs'], 1)
        sides = 2 if j['mode'] == 'joint' else 1
        j['cost'] = j['R'] * j['G'] * n * sides * (1 + j['L'])
        j['job'] = 'm%s_p%s_R%d_G%d_L%d_s%d_z%d' % (
            j['mode'], j['pairs'], j['R'], j['G'], j['L'], j['maxsel'],
            j['seed'])
    jobs.sort(key=lambda j: (j['tier'], j['cost']))
    return jobs


def done_ids(path):
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return set(r['job'] for r in csv.DictReader(f) if r.get('job'))


def launch(j, args, logdir):
    cmd = [sys.executable, os.path.join(HERE, 'cpri_job.py'),
           '--mode', j['mode'], '--pairs', j['pairs'],
           '--R', str(j['R']), '--G', str(j['G']), '--L', str(j['L']),
           '--maxsel', str(j['maxsel']), '--seed', str(j['seed']),
           '--timeout', str(args.timeout)]
    if args.mem_gb:
        cmd += ['--mem-gb', str(args.mem_gb)]
    log = open(os.path.join(logdir, j['job'] + '.log'), 'w')
    p = subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.PIPE,
                         stderr=log, text=True)
    return {'proc': p, 'job': j, 'log': log, 't0': time.time()}


def collect(run, args):
    out, _ = run['proc'].communicate()
    run['log'].close()
    rec = None
    for line in (out or '').splitlines():
        if line.startswith('RESULT '):
            rec = json.loads(line[7:])
    if rec is None:
        rec = {'job': run['job']['job'], 'status': 'crash',
               'note': 'no result line'}
        for k in ('mode', 'pairs', 'R', 'G', 'L', 'maxsel', 'seed'):
            rec[k] = run['job'][k]
    rec['tier'] = run['job']['tier']
    return rec


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workers', type=int, default=os.cpu_count() or 4)
    p.add_argument('--timeout', type=float, default=7200,
                   help='solver seconds per job')
    p.add_argument('--tier', default='1,2,3,4')
    p.add_argument('--only', default='', help='substring filter on job id')
    p.add_argument('--mem-gb', type=float, default=3.0)
    p.add_argument('--results', default=os.path.join(HERE, 'results.csv'))
    p.add_argument('--list', action='store_true')
    args = p.parse_args()

    tiers = set(int(t) for t in args.tier.split(',') if t.strip())
    jobs = [j for j in matrix() if j['tier'] in tiers]
    if args.only:
        jobs = [j for j in jobs if args.only in j['job']]
    seen = done_ids(args.results)
    jobs = [j for j in jobs if j['job'] not in seen]

    if args.list:
        for j in jobs:
            print(j['tier'], j['job'], 'cost', j['cost'])
        print(len(jobs), 'jobs')
        return
    if not jobs:
        print('nothing to do (%d already in %s)' % (len(seen), args.results))
        return

    logdir = os.path.join(HERE, 'logs')
    os.makedirs(logdir, exist_ok=True)
    new = not os.path.exists(args.results)
    fh = open(args.results, 'a', newline='')
    w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction='ignore')
    if new:
        w.writeheader()
        fh.flush()

    print('%d jobs, %d workers, %gs solver timeout each'
          % (len(jobs), args.workers, args.timeout), flush=True)
    pend = list(jobs)
    live = []
    n = 0
    kill_after = args.timeout + 300
    while pend or live:
        while pend and len(live) < args.workers:
            live.append(launch(pend.pop(0), args, logdir))
        time.sleep(1)
        for run in list(live):
            if run['proc'].poll() is None:
                if time.time() - run['t0'] > kill_after:
                    run['proc'].kill()
                else:
                    continue
            live.remove(run)
            rec = collect(run, args)
            w.writerow(rec)
            fh.flush()
            n += 1
            print('[%d/%d] %s %s %ss %s'
                  % (n, len(jobs), rec['job'], rec['status'],
                     rec.get('solve_s', ''), rec.get('note', '')), flush=True)
    fh.close()
    print('done')


if __name__ == '__main__':
    main()
