"""research.html and cv.html carry the paper list from _studio/content/papers.json
as static HTML, in step with a fresh build. Exits non-zero on failure.

    python _studio/tools/build-research.py
    python _studio/tools/check-research.py
"""
import importlib.util, io, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
read = lambda p: io.open(p, encoding='utf-8').read()

# the firm count of papers and preprints, facts.md Q3 ("The '19' count")
FIRM = 18
# anchors research.html had before papers.json; links from elsewhere may use them
OLD_IDS = [
    'adaptive-graph-of-thoughts-test-time-adaptive-reasoning-unif',
    'topological-phases-of-matter-quantum-error-correction-and-to',
    'efficient-variational-quantum-eigensolver-methodologies-on-q',
    'lifted-surgery-for-non-abelian-two-block-group-algebra-codes',
    'fair-decoder-baselines-and-rigorous-finite-size-scaling-for',
    'an-architectural-capacity-ceiling-not-a-barren-plateau-why-a',
    'when-classical-baselines-are-tuned-as-carefully-as-the-quant',
    'a-quantum-reservoir-architecture-for-chaotic-forecasting-and',
    'quantum-kernels-for-parity-structured-classification-a-hybri',
    'generalized-bonahon-wong-yang-volume-conjecture-of-quantum-i',
    'the-bonahon-wong-yang-volume-conjecture-for-the-four-punctur',
    'an-intermediate-conjecture-between-goldbach-and-dubner-every',
]


def esc(s):
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    return ''.join(c if ord(c) < 128 else f'&#{ord(c)};' for c in s)


def rich(s):
    return re.sub(r'10\^(\d+)', r'10<sup>\1</sup>', esc(s))


fail = []
data_path = ROOT / '_studio' / 'content' / 'papers.json'
if not data_path.exists():
    print('papers.json: missing'); sys.exit(1)
data = json.loads(read(data_path))
papers = data['papers']
research, cv = read(ROOT / 'research.html'), read(ROOT / 'cv.html')

if data.get('total') != FIRM:
    fail.append(f"papers.json: total is {data.get('total')}, facts.md says {FIRM}")
ids = [p['id'] for p in papers]
if len(set(ids)) != len(ids):
    fail.append('papers.json: duplicate ids')
for i in OLD_IDS:
    if i not in ids:
        fail.append(f'papers.json: old anchor {i} dropped')
    if f'id="{i}"' not in research:
        fail.append(f'research.html: old anchor #{i} missing')
for page, html in (('research.html', research), ('cv.html', cv)):
    if f'{FIRM} papers and preprints' not in html:
        fail.append(f'{page}: does not state {FIRM} papers and preprints')
    if 'getElementById("cv-' in html or 'const research' in html:
        fail.append(f'{page}: still renders from a script array')

for p in papers:
    m = re.search(r'<article[^>]*\bid="' + re.escape(p['id']) + r'".*?</article>', research, re.S)
    if not m:
        fail.append(f"research.html: no entry for {p['id']}"); continue
    art = m.group(0)
    want = {'title': f"<h2>{esc(p['title'])}</h2>", 'year': str(p['year']), 'summary': rich(p['summary'])}
    want.update({f'author {a}': esc(a) for a in p['authors']})
    fail += [f"research.html: {p['id']} lacks its {k}" for k, v in want.items() if v not in art]
    if p.get('selected'):
        if esc(p['title']) not in cv or f'/research.html#{p["id"]}' not in cv:
            fail.append(f"cv.html: selected paper {p['id']} missing")
    elif esc(p['title']) in cv:
        fail.append(f"cv.html: unselected paper {p['id']} listed")

items = []
for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', research, re.S):
    try:
        doc = json.loads(block)
    except ValueError as e:
        fail.append(f'research.html: JSON-LD does not parse: {e}'); continue
    if doc.get('mainEntity', {}).get('@type') == 'ItemList':
        items = [e['item'] for e in doc['mainEntity']['itemListElement']]
if len(items) != len(papers):
    fail.append(f'research.html: JSON-LD has {len(items)} works, papers.json {len(papers)}')
for p, it in zip(papers, items):
    authors = it.get('author', [])
    authors = [authors] if isinstance(authors, dict) else authors
    if it.get('url', '').split('#')[-1] != p['id'] or it.get('name') != p['title']:
        fail.append(f"research.html: JSON-LD entry for {p['id']} out of order or misnamed")
    if not str(it.get('datePublished', '')).startswith(str(p['year'])):
        fail.append(f"research.html: JSON-LD {p['id']} datePublished")
    if [a.get('name') for a in authors] != p['authors']:
        fail.append(f"research.html: JSON-LD {p['id']} authors")

build_path = ROOT / '_studio' / 'tools' / 'build-research.py'
if not build_path.exists():
    fail.append('build-research.py: missing')
else:
    spec = importlib.util.spec_from_file_location('build_research', build_path)
    build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
    for page, html in build.build().items():
        if html != read(ROOT / page):
            fail.append(f'{page}: differs from a fresh build: run build-research.py')

print('\n'.join(fail) or 'research ok')
sys.exit(1 if fail else 0)
