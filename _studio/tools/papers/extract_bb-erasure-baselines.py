"""Write papers/data/bb-erasure-baselines.json from a clone of the paper's repository,
https://github.com/pandey-tushar/QLDPC, for the companion page papers/bb-erasure-baselines.html.
Reads only the result files and the arXiv source; runs none of the repository's code.

    python _studio/tools/papers/extract_bb-erasure-baselines.py [path-to-QLDPC-clone]

The clone path defaults to $QLDPC_CLONE. The test _studio/tools/tests/papers/bb-erasure-baselines-data.test.mjs
checks the output against the same files.
"""
import csv, datetime, io, json, os, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / 'papers' / 'data' / 'bb-erasure-baselines.json'
FSS = 'results/fss_prelim/fss_results.json'          # the pure-erasure FSS fit of the paper
CI = 'results/ci/threshold_ci_table.json'             # Table 1: p* with 95% bootstrap CI
TEX = 'arxiv_submission/main.tex'                     # the source of arXiv v3
TORIC = [('erasure_aware', 'Erasure-aware MWPM', 'results/baseline_surface_20260318T172201Z_erasure_aware_50k.csv'),
         ('uninformed', 'Uninformed MWPM', 'results/baseline_surface_20260115T062510Z_surface_mwpm.csv')]


def rows(clone, f):
    return list(csv.DictReader(io.open(clone / f, encoding='utf-8', newline='')))


def paper_fit(clone):
    lines = io.open(clone / TEX, encoding='utf-8').read().splitlines()
    out = {'file': TEX}
    for key, pat in (('p_star_inf', r'p\^\*_\\infty &= ([\d.]+) \\pm ([\d.]+)'), ('nu', r'\\nu +&= ([\d.]+) +\\pm ([\d.]+)')):
        hits = [(i + 1, m) for i, l in enumerate(lines) for m in [re.search(pat, l)] if m]
        if len(hits) != 1:
            raise SystemExit(f'{TEX}: want one line matching {pat}, found {len(hits)}')
        n, m = hits[0]
        out[key], out[key + '_pm'], out['line_' + key] = float(m.group(1)), float(m.group(2)), n
    return out


def main(clone):
    fss_doc = json.load(io.open(clone / FSS, encoding='utf-8'))
    fit = fss_doc['fss_fit']
    csv_files = [f.replace('\\', '/') for f in fss_doc['csv_files']]
    ci = {c['N']: c for c in json.load(io.open(clone / CI, encoding='utf-8'))['threshold_ci']}

    # every BB row the fit read, once per (L, M, p); fit_count says how often the fit saw it
    sizes = {}
    for f in csv_files:
        for r in rows(clone, f):
            if r['family'] != 'bivariate_bicycle':
                continue
            key = (int(r['L']), int(r['M']))
            s = sizes.setdefault(key, {'N': int(r['N']), 'K': int(r['K']), 'files': [], 'pts': {}})
            if f not in s['files']:
                s['files'].append(f)
            p, fails, shots = float(r['p']), int(r['fails']), int(r['shots'])
            q = s['pts'].get(p)
            if q is None:
                s['pts'][p] = {'p': p, 'fails': fails, 'shots': shots, 'fit_count': 1}
            elif (q['fails'], q['shots']) != (fails, shots):
                raise SystemExit(f'{f}: L={key[0]} M={key[1]} p={p} disagrees with an earlier file')
            else:
                q['fit_count'] += 1
    bb = []
    for (L, M), s in sorted(sizes.items(), key=lambda kv: kv[1]['N']):
        c = ci[s['N']]
        bb.append({'label': f'{L}x{M}', 'L': L, 'M': M, 'N': s['N'], 'K': s['K'], 'files': s['files'],
                   'center': fit['per_size'][f'L{L}M{M}']['p_star_interp'],
                   'p_star': c['p_star'], 'p_star_ci95': [c['ci_lo_95'], c['ci_hi_95']], 'ci_file': CI,
                   'points': [s['pts'][p] for p in sorted(s['pts'])]})

    toric = []
    for tid, label, f in TORIC:
        rs = rows(clone, f)
        shots = {int(r['shots']) for r in rs}
        if len(shots) != 1:
            raise SystemExit(f'{f}: more than one shot count')
        by = {}
        for r in rs:
            by.setdefault(int(r['N']), {'L': int(r['L']), 'N': int(r['N']), 'K': int(r['K']), 'points': []})['points'].append(
                {'p': float(r['p']), 'fails': int(r['fails']), 'shots': int(r['shots'])})
        for s in by.values():
            s['points'].sort(key=lambda q: q['p'])
        toric.append({'id': tid, 'label': label, 'file': f, 'shots_per_point': shots.pop(),
                      'sizes': [by[n] for n in sorted(by)]})

    commit = subprocess.run(['git', '-C', str(clone), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    doc = {
        'paper': {'id': 'fair-decoder-baselines-and-rigorous-finite-size-scaling-for', 'arxiv': '2603.19062'},
        'source': {'repository': 'https://github.com/pandey-tushar/QLDPC', 'commit': commit,
                   'extracted': datetime.date.today().isoformat(),
                   'files': sorted(set(csv_files + [FSS, CI, TEX] + [f for _, _, f in TORIC]))},
        'paper_fit': paper_fit(clone),
        'fss_fit': {'file': FSS, 'csv_files': csv_files, 'p_star_inf': fit['p_star_fit'], 'nu': fit['nu_fit'],
                    'p_star_inf_ci95': fit['p_star_ci_95'], 'nu_ci95': fit['nu_ci_95'],
                    'residual_ss': fit['residual_ss'], 'poly_degree': fit['poly_degree'], 'p_window': fit['p_window'],
                    'bootstrap_iterations': fss_doc['bootstrap_iterations'], 'target_wer': fss_doc['target_wer']},
        'bb': bb,
        'toric': toric,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(doc, indent=1) + '\n')
    print(f'wrote {OUT.relative_to(ROOT).as_posix()} from {commit[:12]}')


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('QLDPC_CLONE')
    if not arg:
        raise SystemExit('give the path to a QLDPC clone, or set QLDPC_CLONE')
    main(pathlib.Path(arg))
