"""Write papers/data/lifted-surgery.json from a clone of the paper's repository,
https://github.com/pandey-tushar/liftsurg, for the companion page papers/lifted-surgery.html.
Reads only result files; runs none of the repository's code.

    python _studio/tools/papers/extract_lifted-surgery.py [path-to-liftsurg-clone]

The clone path defaults to $LIFTSURG_CLONE. The test _studio/tools/tests/papers/lifted-surgery-data.test.mjs
checks the output against the same files.

certified: the 11 codes of Table 1 (gain exactly two, exact distance) and the 16 of Table 2 (gain at least
three for a best logical). The repository spreads Table 1 over several files; the selectors below say which
record of which file gives each row, the values are read from it. candidates: the rigid gain-two codes of the
code search, whose distances are information-set estimates.
"""
import datetime, io, json, os, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / 'papers' / 'data' / 'lifted-surgery.json'
R = 'results/'
GAIN3, RIGID, SEARCH = R + 'verify_gain3.jsonl', R + 'verify_rigid_family.jsonl', R + 'search_rigid.jsonl'
GAINS, MA, MB, ILP = R + 'gains_fullgroup.jsonl', R + 'verify_mitten_A.jsonl', R + 'verify_mitten_B.jsonl', R + 'ilp_small.jsonl'
BRUTE, AUDIT = R + 'automorphisms_bruteforce.txt', R + 'audit_exhaust_distance.txt'


def jsonl(clone, f):
    return [json.loads(l) for l in io.open(clone / f, encoding='utf-8') if l.strip()]


def text(clone, f):
    return io.open(clone / f, encoding='utf-8').read()


def one(xs, what):
    if len(xs) != 1:
        raise SystemExit(f'want one {what}, found {len(xs)}')
    return xs[0]


def table2(clone):
    last = {}
    for r in jsonl(clone, GAIN3):                     # a code verified twice keeps its last certified record
        if r['fully_certified']:
            last[r['key']] = r
    return [{'id': 't2:' + r['key'], 'key': r['key'], 'table': 2, 'group': r['group'], 'n': r['n'], 'k': r['k'], 'w': r['w'],
             'd': r['d_exact'], 'dX': r['dX_exact'], 'dZ': r['dZ_exact'], 'd_exact': True,
             'E_order': r['E_order'], 'rigid': r['rigid'], 'mu': r['mu_E'], 'base': r['baseline'], 'base_order': r['baseline_order'],
             'index_Amax': r['index_E_Amax'], 'cover': r['cover_min_best'], 'a_central': r['a_central'],
             'orbits': {'total': r['n_orbits_Z'],
                        'list': [{'orbit': o['orbit'], 'mu': o['mu_E'], 'base': o['baseline'], 'gamma': o['gamma']} for o in r['per_orbit_Z']]},
             'src': [GAIN3]} for r in last.values()]


def rigid_family(clone):
    v = jsonl(clone, RIGID)
    out = []
    for r in v:
        if r['stage'] != 'prep' or r['gamma'] != 2:   # the S3xZ14 candidate has gamma 1 at minimum weight
            continue
        ex = one([e for e in v if e['stage'] == 'exhaust' and e['key'] == r['key']], f'exhaust record for {r["key"]}')
        best = next(s for s in r['per_seed'] if s['gamma'] == r['gamma'] and s['mu_S'] == r['mu_S'] and s['baseline'] == r['baseline'])
        out.append({'id': 't1:' + r['key'], 'key': r['key'], 'table': 1, 'group': r['group'], 'n': r['n'], 'k': r['k'], 'w': r['w'],
                    'd': ex['d_lower'], 'd_exact': ex['exact'], 'E_order': r['full_group_order'], 'rigid': r['rigid'],
                    'orbit': best['orbit'], 'mu': r['mu_S'], 'base': r['baseline'], 'base_order': r['baseline_order'],
                    'orbits': {'total': r['n_seed_orbits'],
                               'list': [{'orbit': s['orbit'], 'mu': s['mu_S'], 'base': s['baseline'], 'gamma': s['gamma']} for s in r['per_seed']]},
                    'src': [RIGID]})
    return out


def brute_block(clone, label):
    t = text(clone, BRUTE)
    i = t.rfind(f'== {label}:')
    if i < 0:
        raise SystemExit(f'{BRUTE}: no block {label}')
    return t[i:t.index('total [', i)]


def no_extras(clone, label):
    line = one([l for l in text(clone, BRUTE).splitlines() if l.startswith(label + ' ')], f'summary line {label}')
    return int(line[len(label):].split()[-1]) == 0


def table1_rest(clone):
    g, A, B, ilp = jsonl(clone, GAINS), jsonl(clone, MA), jsonl(clone, MB), jsonl(clone, ILP)
    out = []
    # rigid rows of gains_fullgroup.jsonl: translation group = E when the brute force finds no extra automorphism
    for group, n, k, label in (('S3xZ6', 72, 8, 'S3xZ6 [[72,8,6]]'), ('D5xZ3', 60, 12, 'D5xZ3 [[60,12,6]]'),
                               ('Z9x|8Z12', 216, 16, 'Z9x|8Z12 [[216,16,9]] (Mitten)')):
        r = one([r for r in g if (r['group'], r['n'], r['k']) == (group, n, k)], f'{GAINS} {label}')
        row = {'id': f'gains:{group}:{n}:{k}', 'key': f'{group}:{",".join(map(str, r["a"]))}:{",".join(map(str, r["b"]))}',
               'table': 1, 'group': group, 'n': n, 'k': k, 'w': r['w'], 'E_order': r['full_order'], 'rigid': no_extras(clone, label),
               'orbit': r['orbit_full'], 'mu': r['new_mu'], 'base': r['new_base'], 'base_order': r['new_base_order'],
               'orbits': None, 'src': [GAINS, BRUTE]}
        if group == 'S3xZ6':        # no certificate keyed to this presentation in results/; d as recorded in gains_fullgroup
            row.update(d=r['d'], d_exact=None)
        elif group == 'D5xZ3':
            i = one([i for i in ilp if (i['group'], i['n'], i['k'], i['a'], i['b']) == (group, n, k, r['a'], r['b'])], f'{ILP} {label}')
            row.update(d=min(i['dX_lower'], i['dZ_lower']), dX=i['dX_lower'], dZ=i['dZ_lower'],
                       d_exact=i['dX_exact'] and i['dZ_exact'] and i['dX_lower'] == i['dX_upper'] and i['dZ_lower'] == i['dZ_upper'])
            row['src'].append(ILP)
        else:
            a = one([a for a in A if a['k'] == 16], f'{MA} k=16')
            row.update(d=a['dZ_lower'], d_exact=a['dZ_exact'] and a['dX_exact'] and a['dZ_lower'] == a['dX_lower'])
            row['src'].append(MA)
        out.append(row)

    # the non-rigid r = 2 code: E is the enlarged group of the brute-force search
    b = one([b for b in B if b['label'] == 'Z9x|Z12_r2'], f'{MB} r=2')
    blk = brute_block(clone, 'Z9x|2Z12 [[216,16,9]] (r=2, Table mitten)')
    m = re.search(r'\[enl\] \|group\|=(\d+).*\n\s+orbit 1: size (\d+) mu_S=(\d+) base=(\d+) \(\|A\|=(\d+)\)', blk)
    if 'rigid = False' not in blk or not m:
        raise SystemExit(f'{BRUTE}: r=2 block not as expected')
    out.append({'id': 'brute:Z9x|2Z12:216:16', 'key': 'Z9x|2Z12:' + ','.join(map(str, b['a'])) + ':' + ','.join(map(str, b['b'])),
                'table': 1, 'group': 'Z9x|2Z12', 'n': b['n'], 'k': b['k'], 'w': len(b['a']) + len(b['b']),
                'd': b['dZ_lower'], 'd_exact': b['dZ_exact'] and b['dX_exact'] and b['dZ_lower'] == b['dX_lower'],
                'E_order': int(m[1]), 'rigid': False, 'orbit': int(m[2]), 'mu': int(m[3]), 'base': int(m[4]), 'base_order': int(m[5]),
                'orbits': None, 'src': [BRUTE, MB]})

    # the first [[216,12,12]]: rigid; distance from the exhaustive audit
    a = one([a for a in A if a['k'] == 12], f'{MA} k=12')
    blk = brute_block(clone, 'Z9x|8Z12 [[216,12,12]] (v0.7)')
    tr = re.search(r'\[trans\] \|group\|=(\d+)', blk)
    orbs = re.findall(r'orbit \d+: size (\d+) mu_S=(\d+) base=(\d+) \(\|A\|=(\d+)\) gamma=([\d.]+)', blk)
    au = re.search(r'RESULT Z9x\|8Z12_216_12: d >= (\d+) certified: True; exact d = (\d+): True', text(clone, AUDIT))
    if 'rigid = True' not in blk or not tr or len(orbs) != 2 or not au:
        raise SystemExit(f'{BRUTE} / {AUDIT}: [[216,12,12]] records not as expected')
    out.append({'id': 'brute:Z9x|8Z12:216:12', 'key': 'Z9x|8Z12:' + ','.join(map(str, a['a'])) + ':' + ','.join(map(str, a['b'])),
                'table': 1, 'group': 'Z9x|8Z12', 'n': a['n'], 'k': a['k'], 'w': len(a['a']) + len(a['b']),
                'd': int(au[2]), 'd_exact': True, 'E_order': int(tr[1]), 'rigid': True,
                'orbit': int(orbs[0][0]), 'mu': int(orbs[0][1]), 'base': int(orbs[0][2]), 'base_order': int(orbs[0][3]),
                'orbits': {'total': len(orbs), 'list': [{'orbit': int(o[0]), 'mu': int(o[1]), 'base': int(o[2]), 'gamma': float(o[4])} for o in orbs]},
                'src': [BRUTE, MA, AUDIT]})
    return out


def search(clone):
    rs = jsonl(clone, SEARCH)
    done = [r for r in rs if r['gamma'] is not None]
    cands = [{'group': r['group'], 'n': r['n'], 'k': r['k'], 'w': r['w'], 'd_est': r['d_est'],
              'mu': r['mu_S'], 'base': r['baseline'], 'base_order': r['baseline_order']} for r in rs if r['rigid'] and r['gamma'] == 2]
    counts = {'file': SEARCH, 'codes': len(done), 'rigid': sum(r['rigid'] for r in done),
              'gain_two': sum(r['gamma'] == 2 for r in done), 'rigid_gain_two': len(cands),
              'max_gamma': max(r['gamma'] for r in done)}
    return cands, counts


def main(clone):
    certified = rigid_family(clone) + table1_rest(clone) + table2(clone)
    cands, counts = search(clone)
    commit = subprocess.run(['git', '-C', str(clone), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    doc = {
        'paper': {'id': 'lifted-surgery-for-non-abelian-two-block-group-algebra-codes', 'arxiv': '2610.05307'},
        'source': {'repository': 'https://github.com/pandey-tushar/liftsurg', 'commit': commit,
                   'extracted': datetime.date.today().isoformat(),
                   'files': sorted({f for c in certified for f in c['src']} | {SEARCH})},
        'certified': certified,
        'candidates': cands,
        'search': counts,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(f'wrote {OUT.relative_to(ROOT).as_posix()} from {commit[:12]}: {len(certified)} certified codes, {len(cands)} candidates')


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('LIFTSURG_CLONE')
    if not arg:
        raise SystemExit('give the path to a liftsurg clone, or set LIFTSURG_CLONE')
    main(pathlib.Path(arg))
