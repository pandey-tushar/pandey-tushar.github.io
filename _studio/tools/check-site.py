"""Every published page carries the one site identity: the tp-theme pre-paint
snippet, the site icons and one theme-color, the shared header and nav, a main landmark, one
h1, no web fonts. lib/site.css carries the token values in the table in
_studio/site-system.md, and every text colour on both grounds passes WCAG AA.
Every og:image is a 1200x630 PNG on disk; the books, homepage, CV and research
pages carry their covers, portrait and emblems. The homepage is published byte
for byte from its source. See
_studio/site-system.md. Exits non-zero on failure.

    python _studio/tools/check-site.py
"""
import io, pathlib, re, sys
from urllib.parse import urljoin

PAGES = ['index.html', 'cv.html', 'research.html', 'books.html', 'qubit-dialogues.html',
         'life/index.html', 'illustrated/index.html', 'qec-in-practice/index.html',
         'qec-in-practice/lesson-1.html', 'qec-in-practice/lesson-2.html',
         'qec-in-practice/lesson-3.html', 'qec-in-practice/lesson-4.html',
         'qec-in-practice/repetition-code.html', 'qec-in-practice/decoding.html',
         'qec-in-practice/threshold.html', 'qec-in-practice/lattice-surgery.html', '404.html',
         'papers/bb-erasure-baselines.html', 'papers/lifted-surgery.html', 'papers/adaptive-graph-of-thoughts.html',
         'tools/bb-codes.html', 'notes/index.html', 'notes/crossing-is-not-the-threshold.html',
         'why-error-correction.html', 'qec-in-practice/glossary.html', 'logical/index.html']
FULL = ['index.html', 'cv.html', 'research.html', 'books.html', 'qec-in-practice/index.html',
        'qec-in-practice/lesson-1.html', 'qec-in-practice/repetition-code.html', 'qec-in-practice/decoding.html',
        'qec-in-practice/threshold.html', 'qec-in-practice/lattice-surgery.html', '404.html',
        'papers/bb-erasure-baselines.html', 'papers/lifted-surgery.html', 'papers/adaptive-graph-of-thoughts.html',
        'tools/bb-codes.html', 'notes/index.html', 'notes/crossing-is-not-the-threshold.html',
        'why-error-correction.html', 'qec-in-practice/glossary.html', 'logical/index.html']

NAV = [('Research', '/research.html'), ('Books', '/books.html'), ('Lessons', '/qec-in-practice/'),
       ('CV', '/cv.html'), ('Contact', '/#contact')]

# (page, rule): one-line reason
EXEMPT = {
    ('index.html', 'home link'): 'it is home',
}

ICONS = ['<link rel="icon" href="/favicon.ico" sizes="16x16 32x32 48x48">',
         '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
         '<link rel="apple-touch-icon" href="/apple-touch-icon.png">']
ICON_FILES = ['favicon.ico', 'favicon.svg', 'apple-touch-icon.png']

# pages whose share card is their own
OG = {'index.html': 'og-home.png', 'research.html': 'og-research.png', 'cv.html': 'og-cv.png',
      'books.html': 'og-book.png', 'qec-in-practice/index.html': 'og-qec.png',
      'papers/bb-erasure-baselines.html': 'og-research.png',
      'papers/lifted-surgery.html': 'og-research.png', 'papers/adaptive-graph-of-thoughts.html': 'og-research.png',
      'tools/bb-codes.html': 'og-research.png', 'notes/index.html': 'og-research.png',
      'notes/crossing-is-not-the-threshold.html': 'og-research.png',
      'why-error-correction.html': 'og-qec.png'}

# leftovers of the old costume and copy that must not come back
GONE = [r'(?i)quantum (&#215;|&times;|×) AI', r'(?i)systems that ship']

# book covers, in the order of books.html
COVERS = ['qubit-dialogues', 'an-unpolarized-life', 'qubit-dialogues-illustrated']
PORTRAIT = '/img/tushar-pandey-b'

# text tokens that must read at AA (4.5:1) on both grounds, in both themes
TEXT = ['ink', 'text', 'dim', 'acc', 'warm']
GROUNDS = ['void', 'void2']

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE = 'https://pandey-tushar.com/'
read = lambda p: io.open(p, encoding='utf-8').read()
fail = []


def strip(html):
    return re.sub(r'<script\b.*?</script>|<!--.*?-->', '', html, flags=re.S)


def block(css, selector):
    m = re.search(re.escape(selector) + r'\s*\{(.*?)\}', css, re.S)
    return m.group(1) if m else ''


def tokens(body, prefix):
    return {k: v.strip().lower() for k, v in re.findall(r'--' + prefix + r'([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;', body)}


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + .05) / (lb + .05)


def png_size(p):
    b = p.read_bytes()[:24]
    return (int.from_bytes(b[16:20], 'big'), int.from_bytes(b[20:24], 'big')) if b[:8] == b'\x89PNG\r\n\x1a\n' else None


for f in ICON_FILES:
    if not (ROOT / f).exists():
        fail.append(f'{f}: missing')
# the static theme-color is the dark ground (the pre-paint fallback); site.js
# swaps it between the two grounds of the token table
js = read(ROOT / 'lib' / 'site.js')
m = re.search(r'setAttribute\("content", light \? "(#[0-9a-f]{6})" : "(#[0-9a-f]{6})"\)', js)
grounds = m.groups() if m else None

src = ROOT / '_studio' / 'prototypes' / 'site-full' / 'index.html'
if src.read_bytes() != (ROOT / 'index.html').read_bytes():
    fail.append('index.html: differs from _studio/prototypes/site-full/index.html: run deploy.ps1')

# the token table in site-system.md is the source of truth for the values
doc = read(ROOT / '_studio' / 'site-system.md')
table = {k: (d.lower(), l.lower()) for k, d, l in
         re.findall(r'^\| `([\w-]+)` \|[^|\n]*\| (#[0-9a-fA-F]{6}) \| (#[0-9a-fA-F]{6}) \|', doc, re.M)}
if not table:
    fail.append('site-system.md: no token table')
css = read(ROOT / 'lib' / 'site.css')
have = {'dark': tokens(block(css, ':root'), 'tp-'),
        'light': tokens(block(css, ':root[data-theme="light"]'), 'tp-')}
for k, (dark, light) in table.items():
    for theme, want in (('dark', dark), ('light', light)):
        if have[theme].get(k) != want:
            fail.append(f'lib/site.css: {theme} --tp-{k} is {have[theme].get(k)}, site-system.md has {want}')
for theme, i in (('dark', 0), ('light', 1)):
    for fg in TEXT:
        for bg in GROUNDS:
            if fg in table and bg in table:
                r = ratio(table[fg][i], table[bg][i])
                if r < 4.5:
                    fail.append(f'{theme}: --tp-{fg} on --tp-{bg} is {r:.2f}:1, under AA 4.5')
for t in TEXT + GROUNDS + ['rule']:
    if t not in table:
        fail.append(f'site-system.md: no token {t}')

for page in PAGES:
    p = ROOT / page
    if not p.exists():
        fail.append(f'{page}: missing'); continue
    html = read(p)
    head = html.split('</head>')[0]
    static = strip(html)
    here = urljoin(SITE, page)
    links = [urljoin(here, h) for h in re.findall(r'href="([^"]*)"', static)]
    m = re.search(r'<header class="tp-bar".*?<nav[^>]*>(.*?)</nav>', static, re.S)
    nav = [(re.sub(r'<[^>]+>', '', t).strip(), urljoin(here, h))
           for h, t in re.findall(r'<a [^>]*?href="([^"]*)"[^>]*>(.*?)</a>', m.group(1), re.S)] if m else []
    checks = {
        'pre-paint': (re.search(r'getItem\(\s*["\']tp-theme["\']\s*\)', head) is not None,
                      'no tp-theme pre-paint snippet in <head>'),
        'qd-theme': (re.search(r'setItem\(\s*["\']qd-theme', html) is None, 'still writes qd-theme'),
        'favicon': (all(i in head for i in ICONS) and 'data:image/svg+xml' not in head,
                    'not the site icons (/favicon.ico, /favicon.svg, /apple-touch-icon.png)'),
        'theme-color': (grounds is not None and re.findall(r'<meta name="theme-color" content="([^"]*)">', head) == [grounds[1]]
                        and grounds == (table.get('void', ('', ''))[1], table.get('void', ('', ''))[0]),
                        'theme-color is not one meta with the dark ground site.js swaps from'),
        'leftovers': (not any(re.search(g, static) for g in GONE), 'old copy (Quantum x AI, systems that ship)'),
        'home link': (SITE in links, 'no link home'),
        'header': ('class="tp-bar"' in static, 'no shared header'),
        'nav': (nav == [(t, urljoin(SITE, h)) for t, h in NAV], f'nav is {[t for t, _ in nav]}, not the shared list'),
        'main': (len(re.findall(r'<main[\s>]', static)) == 1, 'not exactly one <main>'),
        'h1': (len(re.findall(r'<h1[\s>]', static)) == 1, f'{len(re.findall(r"<h1[\s>]", static))} static <h1>, want 1'),
        'web fonts': ('fonts.googleapis.com' not in html, 'loads Google Fonts'),
        'stylesheet': ('href="/lib/site.css"' in head, 'does not link /lib/site.css'),
        'script': ('src="/lib/site.js"' in html, 'does not load /lib/site.js'),
    }
    if page in FULL:
        checks['full'] = (re.search(r'<html [^>]*class="tp-full[ "]', head) is not None, 'not in full mode')
        checks['costume'] = (not re.search(r'background-clip:\s*text|backdrop-filter|tp-lattice', html),
                             'gradient text, backdrop blur or the lattice wash')
    og = re.findall(r'<meta property="og:image" content="([^"]*)">', head)
    tw = re.findall(r'<meta name="twitter:image" content="([^"]*)">', head)
    for u in og:
        f = ROOT / u.replace(SITE, '', 1) if u.startswith(SITE) else None
        if f is None or not f.exists():
            fail.append(f'{page}: og:image {u} is not a file in the repo')
        elif png_size(f) != (1200, 630):
            fail.append(f'{page}: og:image {u} is {png_size(f)}, want (1200, 630)')
    if page in OG:
        want = SITE + OG[page]
        checks['share card'] = (og == [want] and tw == [want]
                                and '<meta property="og:image:width" content="1200">' in head
                                and '<meta property="og:image:height" content="630">' in head,
                                f'og:image, twitter:image and 1200x630 size are not all {OG[page]}')
    for rule, (ok, msg) in checks.items():
        if not ok and (page, rule) not in EXEMPT:
            fail.append(f'{page}: {msg}')


def imgs(html):
    return [dict(re.findall(r'([\w-]+)="([^"]*)"', t)) for t in re.findall(r'<img\b[^>]*>', strip(html))]


# books: each entry shows its cover at 300w with a 600w source, sized, described, lazy below the fold
books = read(ROOT / 'books.html')
bimgs = imgs(books)
for i, slug in enumerate(COVERS):
    im = [a for a in bimgs if a.get('src') == f'/img/covers/{slug}-300.webp']
    a = im[0] if im else {}
    ok = (len(im) == 1 and f'/img/covers/{slug}.webp 600w' in a.get('srcset', '')
          and a.get('width') and a.get('height') and len(a.get('alt', '')) > 12
          and (i == 0 or a.get('loading') == 'lazy'))
    if not ok:
        fail.append(f'books.html: no sized, described cover {slug}-300.webp with a 600w srcset'
                    + (' and lazy loading' if i else ''))
    if f'"image": "{SITE}img/covers/{slug}.webp"' not in books:
        fail.append(f'books.html: Book JSON-LD has no image img/covers/{slug}.webp')
if 'class="seal' in books:
    fail.append('books.html: the drawn plates are still there')

# homepage: the regraded portrait, in the JSON-LD and on the page
home = read(ROOT / 'index.html')
if f'"image": "{SITE}img/tushar-pandey-b.webp"' not in home:
    fail.append('index.html: Person JSON-LD image is not img/tushar-pandey-b.webp')
if not any(a.get('src', '').startswith(PORTRAIT) and a.get('class') == 'face' for a in imgs(home)):
    fail.append('index.html: the portrait is not tushar-pandey-b')
if 'tushar-pandey-320.webp' in home or '"/img/tushar-pandey.webp' in home:
    fail.append('index.html: still uses the old portrait')

# cv: the portrait near the name, kept out of print
cv = read(ROOT / 'cv.html')
if not any(a.get('src', '').startswith(PORTRAIT) for a in imgs(cv)):
    fail.append('cv.html: no portrait')
pm = re.search(r'@media print\{(.*?)\n\}', cv, re.S)
if not pm or not re.search(r'\.face\{[^}]*display:none', pm.group(1)):
    fail.append('cv.html: the portrait is not hidden in print')

# research: every area emblem is the img/figures drawing, inlined
research = read(ROOT / 'research.html')
heads = re.findall(r'<figure class="motif[^"]*"[^>]*>(.*?)</figure>', research, re.S)
if not heads:
    fail.append('research.html: no area emblems')
for h in heads:
    if not h.startswith('<svg') or 'img/figures' in h:
        fail.append('research.html: an area emblem is not an inline SVG'); break
figs = {p.stem: re.sub(r'<title>.*?</title>', '', read(p).strip()) for p in (ROOT / 'img' / 'figures').glob('*.svg')}
inlined = [h for h in heads if any(re.sub(r'\s(role|aria-label|aria-hidden|focusable)="[^"]*"', '', h)
                                   == re.sub(r'\s(role|aria-label|aria-hidden|focusable)="[^"]*"', '', s) for s in figs.values())]
if len(inlined) != len(heads):
    fail.append(f'research.html: {len(heads) - len(inlined)} of {len(heads)} area emblems are not from img/figures/')
if '--tp-accent' in research or any('--tp-accent' in s for s in figs.values()):
    fail.append('img/figures: uses --tp-accent, which is not a token (--tp-acc)')

# copy that must hold on the owned pages: (page, pattern, wanted present, reason)
COPY = [
    ('index.html', r'Every paper and preprint', False, 'research link claims completeness'),
    ('cv.html', r'The full list, with summaries', False, 'research link claims completeness'),
    ('cv.html', r'Co-organizer', False, 'Co-organizer, not Organizer'),
    ('cv.html', r'>[^<]*Q-Volution', False, 'Q-Volution breaks at its hyphen'),
    ('cv.html', r'<meta name="description" content="[^"]*Senior Software Engineer at DataRobot', True, 'description does not name role and employer'),
    ('cv.html', r'<meta property="og:description" content="[^"]*Senior Software Engineer at DataRobot', True, 'og:description does not name role and employer'),
    ('books.html', r'(?i)twenty two', False, '"twenty two" without the hyphen'),
    ('books.html', r'An Unpolarized Life \(about 35 minutes\)', True, 'lede does not offer An Unpolarized Life to new readers'),
    ('index.html', r'Begun at Oak Ridge\. Sole author', False, 'semion card still reads as fragments'),
    ('index.html', r'>The record<', False, 'Google Site link still labelled "The record"'),
    ('index.html', r'href="https://sites.google.com/view/tusharpandey"[^>]*>Talks and older work<', True, 'Google Site link not labelled "Talks and older work"'),
    ('research.html', r'href="https://sites.google.com/view/tusharpandey"[^>]*>Talks and older work<', True, 'Google Site link not labelled "Talks and older work"'),
    ('research.html', r'<p class="area-title"', False, 'area titles are not headings'),
    ('research.html', r'<h2 class="area-title"', True, 'area titles are not h2'),
    ('research.html', r'<p class="why">', True, 'no plain why-it-matters line under the area titles'),
]
for page in ('index.html', 'cv.html', 'books.html', 'research.html', '404.html'):
    for bad in ('Lead author', '30 to 40 percent', 'tripled', 'systems that ship', 'Dynamo'):
        if bad in read(ROOT / page):
            fail.append(f'{page}: says "{bad}"')
for page, pat, want, why in COPY:
    if (re.search(pat, read(ROOT / page)) is not None) != want:
        fail.append(f'{page}: {why}')
# the homepage: a live hero, one window-sized pane per entry that opens a sheet, contact as the last pane, and no more
for pat, why in ((r'class="n"', 'section numbers'), (r'<b>Fig\.', 'figure numbers'), (r'In plain words', 'the plain-words paragraph'),
                 (r'Start here', 'the Start here strip'), (r'id="(try|books|record)"', 'a section the top navigation already covers'),
                 (r'<p class="plain">', 'a second summary sentence on a work card'),
                 (r'What I build|>Writing<|Selected work', 'a school-report section heading'),
                 (r'class="sec-head"|class="tiles"|class="shelf"|tp-index', 'the old sections or the compact index')):
    if re.search(pat, home):
        fail.append(f'index.html: still has {why}')
if re.findall(r'<section[^>]*?(?:id|class)="([^"]+)"', home) != ['hero', 'work', 'contact']:
    fail.append('index.html: sections are not hero, work, contact')


def section(name):
    m = re.search(r'<section[^>]*?(?:id|class)="' + name + r'".*?</section>', home, re.S)
    return m.group(0) if m else ''


hero, work, contact = (section(s) for s in ('hero', 'work', 'contact'))
outside = re.sub(r'<dialog\b.*?</dialog>', '', strip(home), flags=re.S)
if re.search(r'<h2(?! class="tp-pane-name")[\s>]', outside):
    fail.append('index.html: a section heading outside the sheets (only pane names are h2)')
if re.search(r'&mdash;|—', outside) or re.search(r'[^\x00-\x7f]', re.sub(r'<[^>]+>', '', outside)):
    fail.append('index.html: non-ASCII or an em dash in the visible text outside the sheets')
# the panes: one window-sized pane per entry, in this order, each with a tag, its
# name, one short line, a live canvas and one Open link to its sheet; contact last
ENTRIES = ['TokenGrid', 'Error correction for the doubled semion model', 'Adaptive Graph of Thoughts',
           'The volume conjecture', 'The Qubit Dialogues', 'An Unpolarized Life', 'The Qubit Dialogues, Illustrated',
           'Quantum Error Correction in Practice', 'Toric code playground']
panes = re.findall(r'<(article|section)\b([^>]*\bclass="tp-pane(?:\s[^"]*)?"[^>]*)>(.*?)</\1>', outside, re.S)
entries = [(a, b) for t, a, b in panes if t == 'article']
names = [''.join(re.findall(r'<h2 class="tp-pane-name"[^>]*>([^<]+)</h2>', b)) for _, b in entries]
if names != ENTRIES:
    fail.append(f'index.html: the panes are {names}, not {ENTRIES}')
if len(re.findall(r'<article class="tp-pane', work)) != len(ENTRIES):
    fail.append('index.html: the entry panes are not all inside the work section')
if not panes or 'id="contact"' not in panes[-1][1] or len(panes) != len(ENTRIES) + 1:
    fail.append('index.html: contact is not the last pane, after the nine entries')
sheets, order = {}, []
for attrs, body in entries:
    pid = re.search(r'\bid="([\w-]+)"', attrs)
    opens = re.findall(r'<a class="tp-pane-open" href="#([\w-]+)"', body)
    line = re.search(r'<p class="tp-pane-line">([^<]+)</p>', body)
    if not (pid and len(opens) == 1):
        fail.append(f'index.html: a pane lacks its id or its one Open link: {attrs.strip()!r}'); continue
    sid = opens[0]; order.append(sid)
    if not (line and re.search(r'<p class="tp-pane-tag">[^<]+</p>', body)):
        fail.append(f'index.html: pane #{sid} lacks its tag or its one line'); continue
    if len(line.group(1)) > 64 or re.match(r'I\b', line.group(1)) or re.search(r'[a-z]\. ', line.group(1)):
        fail.append(f'index.html: pane #{sid} line is not one short phrase: {line.group(1)!r}')
    if not re.search(r'<div class="tp-pane-viz[^"]*">\s*<canvas data-live="\w+" aria-hidden="true">', body):
        fail.append(f'index.html: pane #{sid} has no live canvas')
    m = re.search(r'<dialog class="tp-sheet" id="' + sid + r'" aria-labelledby="([\w-]+)"[^>]*>(.*?)</dialog>', home, re.S)
    if not m or f'id="{m.group(1)}"' not in m.group(2) or 'tp-sheet-close' not in m.group(2):
        fail.append(f'index.html: pane #{sid} opens no labelled sheet with a close button'); continue
    sheets[sid] = m.group(2)
# the rail: one link per pane, in order, contact last
rail = re.search(r'<nav class="tp-rail"[^>]*>(.*?)</nav>', outside, re.S)
ids = [m.group(1) for m in (re.search(r'\bid="([\w-]+)"', a) for _, a, _ in panes) if m]
if not rail or re.findall(r'href="#([\w-]+)"', rail.group(1)) != ids:
    fail.append(f'index.html: the rail does not link every pane in order: {ids}')
if '<p class="lede">Senior Software Engineer at DataRobot, working on LLM inference, and a researcher in quantum error correction with a Ph.D. in mathematics from Texas A&amp;M.</p>' not in hero or '<dl' in hero:
    fail.append('index.html: the hero lede is not the original sentence')
if not re.search(r'<p class="head">Inference, error correction, and proofs\.</p>', hero):
    fail.append('index.html: the hero headline is not "Inference, error correction, and proofs."')
if not re.search(r'<h1 class="eyebrow">Tushar Pandey / Research and engineering</h1>', hero):
    fail.append('index.html: the hero eyebrow is not the h1 "Tushar Pandey / Research and engineering"')
if 'Tushar Pandey' not in ''.join(re.findall(r'<h1[\s>].*?</h1>', home, re.S)):
    fail.append('index.html: the h1 does not carry the name "Tushar Pandey"')
if not re.search(r'<canvas[^>]*aria-hidden="true"', hero):
    fail.append('index.html: the hero has no live canvas, hidden from assistive tech')
if not (re.search(r'href="#work"[^>]*>See the work<', hero) and re.search(r'href="#contact"[^>]*>Get in touch<', hero)):
    fail.append('index.html: the hero buttons are not See the work (#work) and Get in touch (#contact)')
# the sheets keep the full descriptions, links and covers the homepage used to show,
# but not the captions of the old static figures (the sheets now show live canvases)
DESC = ['LLM inference at DataRobot: co-author of <b>TokenGrid</b>, a token-aware capacity scheduler for multi-tenant model serving.',
        'I began this work at Oak Ridge and published it as sole author in APL Quantum in 2025. <b>Variational eigensolvers</b> on real processors, first author, Physica Scripta 2026.',
        '<b>AGoT</b> grows chains, trees and graphs as it runs. Shipped at Agnostiq as a production agentic-AI blueprint (2024&ndash;25); code open source.',
        'Ph.D. work under Tian Yang in quantum topology. A generalized <b>Bonahon&ndash;Wong&ndash;Yang volume conjecture</b>, proved for the figure-eight knot complement with Ka Ho Wong (Algebraic &amp; Geometric Topology, to appear); and, sole author, the conjecture verified for four-puncture sphere bundles under technical conditions.']
LINKS = [['https://www.datarobot.com/blog/llm-inference-rate-limiting-tokengrid/'],
         ['https://doi.org/10.1063/5.0255351', 'https://doi.org/10.1088/1402-4896/ae9e06', 'https://sites.google.com/view/tusharpandey'],
         ['https://github.com/AgnostiqHQ/multi-agent-llm', 'https://arxiv.org/abs/2502.05078', '/papers/adaptive-graph-of-thoughts.html'],
         ['https://arxiv.org/abs/2311.13151', 'https://arxiv.org/abs/2402.04483']]
CAPS = ['Three tenants (outline, hatched, tinted) share one model. Each request is counted by its tokens against one shared capacity.',
        'The doubled semion ground state is a signed sum over closed loops on the honeycomb lattice, like the two here. An open string (warm) violates the vertices at its ends; those are what error correction has to find.',
        'AGoT breaks a query into a graph of subproblems and expands only the hard one (warm) into a nested graph of its own.',
        'The figure-eight knot. A generalized Bonahon&ndash;Wong&ndash;Yang volume conjecture is proved for its complement.']
for i, (d, ls, c) in enumerate(zip(DESC, LINKS, CAPS)):
    s = sheets.get(order[i], '') if i < len(order) else ''
    if d not in s or not all(f'href="{u}"' in s for u in ls):
        fail.append(f'index.html: the sheet for {ENTRIES[i]} lacks its original description or links')
    if c in s:
        fail.append(f'index.html: the sheet for {ENTRIES[i]} still carries the old static-figure caption')
if 'href="/research.html">Papers and preprints, with summaries<' not in ''.join(sheets.values()):
    fail.append('index.html: no sheet links /research.html as "Papers and preprints, with summaries"')
for i, slug in enumerate(COVERS):
    s = sheets.get(order[4 + i], '') if 4 + i < len(order) else ''
    if f'/img/covers/{slug}-300.webp' not in s:
        fail.append(f'index.html: the sheet for {ENTRIES[4 + i]} has no cover')
if 'href="/qec-in-practice/"' not in sheets.get(order[7] if len(order) > 7 else '', ''):
    fail.append('index.html: the course sheet does not link the course')
toric = sheets.get(order[8] if len(order) > 8 else '', '')
if not all(f'id="{i}"' in toric for i in ('lattice', 'fix', 'reset', 'lat-status')):
    fail.append('index.html: the toric code sheet does not hold the interactive lattice')
if strip(home).count('Dallas, TX') != 1 or 'Dallas, TX' not in contact:
    fail.append('index.html: "Dallas, TX" is not in the contact band alone')
if not re.search(r'<a class="tp-btn[^"]*" href="mailto:[^"]+"[^>]*>Get in touch<', contact):
    fail.append('index.html: the contact band has no Get in touch button to the email')
# every pane's live figure is the background of the whole pane, the words laid
# over it; the words move from pane to pane, never twice in a row in one place
POS = {'': 'bottom left', 'tp-pane-mid': 'centre left', 'tp-pane-end': 'bottom right', 'tp-pane-top': 'top left'}
OLD = r'tp-pane-(?:flip|frame|band|bleed)\b'
if re.search(OLD, home) or re.search(OLD, css) or re.search(OLD, doc):
    fail.append('index.html, site.css or site-system.md: a side, framed, flipped or band pane layout is still there')
vb = block(css, '.tp-pane-viz')
if not ('position:absolute' in vb and 'inset:0' in vb and 'z-index:-1' in vb):
    fail.append('lib/site.css: .tp-pane-viz is not a background layer under the whole pane')
if not re.search(r'\.tp-pane-viz::after\{[^}]*gradient', css):
    fail.append('lib/site.css: no scrim between the background figure and the words')
places = []
for attrs, body in entries:
    cls = re.search(r'class="tp-pane((?:\s[\w-]+)*)"', attrs).group(1).split()
    mods = [c for c in cls if c in POS]
    if len(mods) > 1 or set(cls) - set(POS):
        fail.append(f'index.html: pane classes {cls} are not one text position from {sorted(POS)}')
    places.append(mods[0] if mods else '')
    if body.count('<div class="tp-pane-viz">') != 1 or body.find('tp-pane-viz') > body.find('tp-pane-text'):
        fail.append(f'index.html: pane {attrs.strip()!r} does not lay its words over one background figure')
if any(a == b for a, b in zip(places, places[1:])) or len(set(places)) < 3:
    fail.append(f'index.html: the words sit {[POS[p] for p in places]}: no rhythm')
# one system: every pane's figure is a field over the whole pane, quieted near
# the words, never an object set in the room the words leave (only covers are)
hjs = re.search(r'DOMContentLoaded", function\(\)\{(.*?\nvar MAKE = \{[^}]*\})', home, re.S)
hjs = hjs.group(1) if hjs else ''
if hjs.count('room(') != 2 or not re.search(r'function cover\([^)]*\)\{[^}]*room\(', hjs):
    fail.append('index.html: a pane figure is placed in the room the words leave; only covers are')
for live in sorted({m for _, b in entries for m in re.findall(r'data-live="(\w+)"', b)}):
    maker = re.search(r'var MAKE = \{[^}]*\b' + live + r': (\w+)', hjs)
    fn = maker and re.search(r'\nfunction ' + maker.group(1) + r'\(pane\)\{(.*?)\n(?=function |/\* -{10}|var MAKE)', hjs, re.S)
    if not fn or 'words(' not in fn.group(1):
        fail.append(f'index.html: the {live} pane figure is not a field quieted near the words')
for slug, (_, body) in zip(COVERS, entries[4:7]):
    if not re.search(r'<div class="tp-pane-viz"><canvas data-live="\w+" aria-hidden="true"></canvas><img class="tp-pane-cover" src="/img/covers/' + slug, body):
        fail.append(f'index.html: the {slug} cover is not set into its pane\'s background figure')
# contact is quiet: no display-size call to action, and not window-tall
cb = block(re.search(r'<style>(.*?)</style>', home, re.S).group(1), '.contact')
if re.search(r'\.cta\b|class="cta"', home) or 'height:auto' not in cb:
    fail.append('index.html: the contact pane keeps the display-size Get in touch, or is window-tall')
# our own marks, not a borrowed template: lattice-edge eyebrow mark, a lit check
# after section headings, no accent-coloured heading word, no filled primary button
hstyle = re.search(r'<style>(.*?)</style>', home, re.S).group(1)
if re.search(r'<h2[^>]*>[^<]*<span class="acc">', home):
    fail.append('index.html: a section heading has an accent-coloured word')
if not re.search(r'\.eyebrow::before\{[^}]*mask[^}]*svg', hstyle):
    fail.append('index.html: the eyebrow mark is not the lattice-edge svg')
if re.search(r'\.tp-btn\.pri\{[^}]*background:var\(--tp-acc\)', hstyle):
    fail.append('index.html: the primary button is a filled accent block')
if re.search(r'tp-serif', hstyle) or 'Geist' not in hstyle:
    fail.append('index.html: the homepage is not set in Geist')
if '@font-face' in hstyle:
    fail.append('index.html: declares its own @font-face; Geist lives in lib/site.css')
# shared components: the index, the sheet and the live-canvas helper, documented
for f in ('Geist', 'Geist Mono'):
    if not re.search(r'@font-face\{font-family:"' + f + r'";src:url\(/lib/fonts/' + f.replace(' ', '') + r'\.woff2\)', css):
        fail.append(f'lib/site.css: no @font-face for {f}')
for sel in ('.tp-pane{', '.tp-pane-open{', '.tp-rail{', '.tp-sheet{', '.tp-sheet-close{'):
    if sel not in css:
        fail.append(f'lib/site.css: no shared {sel[:-1]}')
if 'tp-index' in css or 'tp-index' in js or '_tpAwake' in js:
    fail.append('lib/site.css or lib/site.js: the compact index or its hover wake is still there')
# a pane is the window under the header; snapping is gentle and off under reduced motion
pb = block(css, '.tp-pane')
if 'calc(100svh - var(--tp-barh))' not in pb or 'min-height' not in pb:
    fail.append('lib/site.css: .tp-pane is not window-sized with a min-height')
snap = re.search(r'@media \(prefers-reduced-motion:no-preference\)\{[^@]*scroll-snap-type:y proximity', css)
if not snap or 'mandatory' in css:
    fail.append('lib/site.css: scroll snap is not proximity, or not limited to no-preference motion')
for name in ('TP.live', 'TP.sheet'):
    if name + ' =' not in js:
        fail.append(f'lib/site.js: no shared {name}')
for name in ('tp-pane', 'tp-rail', 'tp-sheet', 'TP.live'):
    if f'`{name}`' not in doc:
        fail.append(f'site-system.md: {name} is not documented')
if 'tp-index' in doc:
    fail.append('site-system.md: still documents tp-index')
# research: every paper title sits under its area's h2
if (re.search(r'<article class="paper[ "][^>]*>(?:(?!</article>).)*<h2[\s>]', research, re.S)
        or len(re.findall(r'<article class="paper[ "][^>]*>(?:(?!</article>).)*<h3>', research, re.S)) != research.count('<article class="paper')
        or research.count('<p class="why">') != 5):
    fail.append('research.html: paper titles are not h3 under the area h2, or an area lacks its why line')
if books.count('.tp-btn.go{') > 1:
    fail.append('books.html: .tp-btn.go declared more than once')

# the hubs: a live hero with the page's one h1, then one window-sized pane per entry,
# each with a tag, a name, one line, a live figure and an Open link to a labelled sheet
# that stays in the page, the rail linking every pane in order, the words moving
fm = re.search(r'TP\.live\.fig = \{(.*?)\};', js, re.S)
FIGS = set(re.findall(r'(\w+): (?:\w+|function)', fm.group(1))) if fm else set()
HUBS = {'research.html': 5, 'books.html': 3, 'cv.html': 8, 'notes/index.html': 1, 'qec-in-practice/index.html': 8, '404.html': 0}
for page, n in HUBS.items():
    html = read(ROOT / page)
    s = strip(html)
    hero = re.search(r'<section class="tp-hero[^"]*"[^>]*>(.*?)</section>', s, re.S)
    if not re.search(r'<html [^>]*class="[^"]*\btp-geist\b', html):
        fail.append(f'{page}: not set in Geist (tp-geist)')
    if not hero or not re.search(r'^\s*<canvas data-fig="\w+" aria-hidden="true">', hero.group(1)) or '<h1' not in hero.group(1):
        fail.append(f'{page}: no live hero holding the h1'); continue
    outside = re.sub(r'<dialog\b.*?</dialog>', '', s, flags=re.S)
    panes = re.findall(r'<article class="tp-pane((?: [\w-]+)*)" id="([\w-]+)"[^>]*>(.*?)</article>', outside, re.S)
    if len(panes) != n:
        fail.append(f'{page}: {len(panes)} panes, want {n}')
    places = []
    for cls, pid, body in panes:
        sid = re.findall(r'<a class="tp-pane-open" href="#([\w-]+)"', body)
        ok = (len(sid) == 1 and re.search(r'<p class="tp-pane-tag">[^<]+</p>', body) and re.search(r'<h2 class="tp-pane-name"[^>]*>[^<]+</h2>', body)
              and re.search(r'<p class="tp-pane-line">.+?</p>', body)
              and re.search(r'<div class="tp-pane-viz"><canvas data-fig="\w+" aria-hidden="true">', body))
        if not ok:
            fail.append(f'{page}: pane #{pid} lacks its tag, name, line, live figure or one Open link'); continue
        m = re.search(r'<dialog class="tp-sheet[^"]*" id="' + sid[0] + r'" aria-labelledby="([\w-]+)"[^>]*>(.*?)</dialog>', html, re.S)
        if not m or f'id="{m.group(1)}"' not in m.group(2) or 'tp-sheet-close' not in m.group(2):
            fail.append(f'{page}: pane #{pid} opens no labelled sheet with a close button')
        places.append(cls.strip())
    if any(a == b for a, b in zip(places, places[1:])):
        fail.append(f'{page}: the words sit in one place twice in a row: {places}')
    for f in re.findall(r'data-fig="(\w+)"', s):
        if f not in FIGS:
            fail.append(f'{page}: data-fig="{f}" is not a figure in TP.live.fig')
    if n:
        rail = re.search(r'<nav class="tp-rail"[^>]*>(.*?)</nav>', outside, re.S)
        if not rail or re.findall(r'href="#([\w-]+)"', rail.group(1)) != [p[1] for p in panes]:
            fail.append(f'{page}: the rail does not link every pane in order')
    if re.search(r'<h2(?! class="tp-pane-name")[\s>]', outside):
        fail.append(f'{page}: a heading outside the sheets (only pane names are h2)')
    if re.search(r'Part \d|Area [IVX]+|class="(?:no|num|rn)"', outside):
        fail.append(f'{page}: numbering or a school-report heading outside the sheets')
    if page != 'cv.html' and ('Dallas, TX' in s or 'id="contact"' in s):
        fail.append(f'{page}: carries contact, which belongs to the homepage')

if re.search(r'background-clip:\s*text|backdrop-filter|tp-lattice', css):
    fail.append('lib/site.css: gradient text, backdrop blur or the lattice wash')

print('\n'.join(fail) or 'site ok')
sys.exit(1 if fail else 0)
