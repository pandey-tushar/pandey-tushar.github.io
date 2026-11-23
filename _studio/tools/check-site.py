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
        checks['full'] = ('class="tp-full"' in head, 'not in full mode')
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
# the homepage is a personal page: hero, selected work, contact, and no more
for pat, why in ((r'class="n"', 'section numbers'), (r'<b>Fig\.', 'figure numbers'), (r'In plain words', 'the plain-words paragraph'),
                 (r'Start here', 'the Start here strip'), (r'id="(try|books|record)"', 'a section the top navigation already covers'),
                 (r'<p class="plain">', 'a second summary sentence on a work card')):
    if re.search(pat, home):
        fail.append(f'index.html: still has {why}')
if re.findall(r'<section[^>]*?(?:id|class)="([^"]+)"', home) != ['hero', 'work', 'contact']:
    fail.append('index.html: sections are not hero, work, contact')
if home.count('<article class="work">') != 4:
    fail.append('index.html: not four selected-work cards')
# research: every paper title sits under its area's h2
if re.search(r'<article class="paper"[^>]*>.*?<h2>', research, re.S) or research.count('<p class="why">') != 5:
    fail.append('research.html: paper titles are not h3 under the area h2, or an area lacks its why line')
if books.count('.tp-btn.go{') != 1:
    fail.append('books.html: .tp-btn.go declared more than once')

if re.search(r'background-clip:\s*text|backdrop-filter|tp-lattice', css):
    fail.append('lib/site.css: gradient text, backdrop blur or the lattice wash')

print('\n'.join(fail) or 'site ok')
sys.exit(1 if fail else 0)
