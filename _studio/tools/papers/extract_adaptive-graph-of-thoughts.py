"""Write papers/data/adaptive-graph-of-thoughts.json from the arXiv source of arXiv:2502.05078, for the
companion page papers/adaptive-graph-of-thoughts.html. Parses Tables 1 to 3 of main.tex as text; runs
nothing from the source.

    python -I _studio/tools/papers/extract_adaptive-graph-of-thoughts.py [folder]

The folder (default $AGOT_ARXIV_SRC) holds what was fetched: abs.html from https://arxiv.org/abs/2502.05078,
eprint.bin from https://arxiv.org/e-print/2502.05078, and src/ with eprint.bin unpacked. The test
_studio/tools/tests/papers/adaptive-graph-of-thoughts-data.test.mjs checks the output against the same main.tex.
"""
import datetime, hashlib, io, json, os, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / 'papers' / 'data' / 'adaptive-graph-of-thoughts.json'
ARXIV = '2502.05078'
# the paper's three tables, in source order, which is their printed numbering (checked against the v1 PDF)
LABELS = ['tab:gpt-gpqa-results', 'tab:performance_comparison', 'tab: Retrieval tasks']
# Table 2 has no metric column. Its retrieval rows are LAAS (Section 6, "where LAAS is employed as the accuracy
# measure"; checked below against Table 3), its crossword rows letter and word accuracy (Section 5.3.1).
METRIC = {'Crossword Letters': 'letter accuracy', 'Crossword Words': 'word accuracy',
          'HotpotQA': 'LAAS', 'MoreHopQA': 'LAAS', 'HybridQA': 'LAAS'}


def braced(s, i):
    """The text inside the {...} that starts at s[i]."""
    depth = 0
    for j in range(i, len(s)):
        depth += {'{': 1, '}': -1}.get(s[j], 0)
        if depth == 0:
            return s[i + 1:j]
    raise SystemExit('unbalanced braces')


def cell(s):
    s = s.strip()
    m = re.fullmatch(r'\$\\mathbf\{\\Delta\^\{?\\text\{(\w+)\}\}?_\\text\{IO\}\}\$', s)
    if m:
        return 'delta:' + m.group(1)
    s = re.sub(r'\\multirow\{\d+\}\{\*\}\{(.*)\}$', r'\1', s)
    s = re.sub(r'\\(?:textbf|texttt|mathbf)\{([^{}]*)\}', r'\1', s)
    s = re.sub(r'\$_\\text\{(\w+)\}\$', r'_\1', s)
    return s.replace('\\%', '%').strip()


def caption(s):
    s = re.sub(r'~?\\citep?\{[^}]*\}', '', s)
    s = re.sub(r'\s*\(\\autoref\{[^}]*\}\)', '', s)
    s = re.sub(r'\\(?:texttt|textbf|textit)\{([^{}]*)\}', r'\1', s)
    s = re.sub(r'\$_\\text\{(\w+)\}\$', r'_\1', s)
    return re.sub(r'\s+', ' ', s).strip()


def tables(lines):
    out, start = [], None
    for i, l in enumerate(lines):
        if re.match(r'\s*\\begin\{table\*?\}', l):
            start = i
        elif start is not None and re.match(r'\s*\\end\{table\*?\}', l):
            out.append((start, i)); start = None
    return out


def parse(lines, a, b, number):
    text = '\n'.join(lines[a:b + 1])
    label = re.search(r'\\label\{([^}]*)\}', text).group(1)
    cap = text.index('\\caption{')
    t0 = next(i for i in range(a, b) if '\\begin{tabular}' in lines[i])
    t1 = next(i for i in range(t0, b) if '\\end{tabular}' in lines[i])
    columns, rows, carry = None, [], {}
    for i in range(t0 + 1, t1):
        l = lines[i].strip()
        if not l or l.startswith('%') or re.fullmatch(r'\\(top|mid|bottom)rule', l):
            continue
        if '\\\\' not in l:   # a \multirow cell on a line of its own heads the rows below it
            m = re.fullmatch(r'\\multirow\{(\d+)\}\{\*\}\{(.*)\}', l)
            if not m:
                raise SystemExit(f'main.tex:{i + 1}: cannot read {l!r}')
            carry = {'value': cell(m.group(2)), 'left': int(m.group(1))}
            continue
        cells = [cell(c) for c in l.split('\\\\')[0].split('&')]
        if columns is None:
            columns = cells; continue
        if len(cells) != len(columns):
            raise SystemExit(f'main.tex:{i + 1}: {len(cells)} cells, header has {len(columns)}')
        if cells[0] == '':
            if not carry.get('left'):
                raise SystemExit(f'main.tex:{i + 1}: empty first cell with no \\multirow above')
            cells[0] = carry['value']; carry['left'] -= 1
        rows.append((i + 1, cells, re.findall(r'\\textbf\{([^{}]*)\}', l)))
    models = sorted(set(re.findall(r'\\texttt\{(gpt-[^}]*)\}', braced(text, cap + len('\\caption')))))
    t = {'number': number, 'label': label, 'line': a + 1 + text[:text.index('\\label{')].count('\n'),
         'tabular': [t0 + 1, t1 + 1], 'caption': caption(braced(text, cap + len('\\caption'))), 'columns': columns, 'rows': []}
    for line, cells, bold in rows:
        c = dict(zip(columns, cells))
        r = {'line': line, 'category': c.get('Category'), 'dataset': c['Dataset']}
        if 'Model' in c:
            r['model'] = c['Model']
        elif len(models) == 1:   # Tables 2 and 3 name their model in the caption only
            r['model'] = models[0]
        else:
            raise SystemExit(f'{label}: no model column and caption names {models}')
        r['metric'] = c.get('Metric') or METRIC.get(c['Dataset'], 'accuracy')
        r['scores'] = {k: float(v) for k, v in c.items() if k in ('IO', 'CoT', 'AIoT', 'AGoT')}
        r['delta'] = {k[6:]: float(v.rstrip('%')) for k, v in c.items() if k.startswith('delta:')}
        r['bold'] = bold
        r['cells'] = cells
        t['rows'].append(r)
    return t


def main(folder):
    tex = folder / 'src' / 'main.tex'
    raw = tex.read_bytes()
    lines = raw.decode('utf-8').splitlines()
    found = [parse(lines, a, b, n + 1) for n, (a, b) in enumerate(tables(lines))]
    if [t['label'] for t in found] != LABELS:
        raise SystemExit(f'tables in main.tex are {[t["label"] for t in found]}, want {LABELS}')
    t2 = {r['dataset']: r for r in found[1]['rows']}
    for r in found[2]['rows']:   # Table 2's retrieval values are Table 3's LAAS
        if r['metric'] == 'LAAS' and any(t2[r['dataset']]['scores'][m] != v for m, v in r['scores'].items()):
            raise SystemExit(f'{r["dataset"]}: Table 3 LAAS differs from Table 2')
    abs_html = io.open(folder / 'abs.html', encoding='utf-8').read()
    versions = sorted(int(v) for v in re.findall(r'\[v(\d+)\]', abs_html))
    if not versions:
        raise SystemExit('abs.html: no submission history')
    title = re.search(r'\\icmltitle\{([^}]*)\}', '\n'.join(lines)).group(1)
    fetched = datetime.date.fromtimestamp((folder / 'eprint.bin').stat().st_mtime).isoformat()
    doc = {
        'paper': {'id': 'adaptive-graph-of-thoughts-test-time-adaptive-reasoning-unif', 'arxiv': ARXIV,
                  'version': f'v{versions[-1]}', 'title': title},
        'source': {'abs': f'https://arxiv.org/abs/{ARXIV}', 'eprint': f'https://arxiv.org/e-print/{ARXIV}',
                   'file': 'main.tex', 'sha256': hashlib.sha256(raw).hexdigest(),
                   'eprint_sha256': hashlib.sha256((folder / 'eprint.bin').read_bytes()).hexdigest(),
                   'fetched': fetched, 'extracted': datetime.date.today().isoformat()},
        'tables': found,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(f'wrote {OUT.relative_to(ROOT).as_posix()} from arXiv:{ARXIV}v{versions[-1]} main.tex, '
          + ', '.join(f'Table {t["number"]} ({len(t["rows"])} rows)' for t in found))


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('AGOT_ARXIV_SRC')
    if not arg:
        raise SystemExit('give the folder holding abs.html, eprint.bin and src/main.tex, or set AGOT_ARXIV_SRC')
    main(pathlib.Path(arg))
