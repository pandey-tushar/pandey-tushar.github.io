"""Every published page carries the one site identity: the tp-theme pre-paint
snippet, the homepage favicon, the shared header and nav, a main landmark, one
h1, no web fonts, and lib/site.css mirroring the homepage tokens. See
_studio/site-system.md. Exits non-zero on failure.

    python _studio/tools/check-site.py
"""
import io, pathlib, re, sys
from urllib.parse import urljoin

PAGES = ['index.html', 'cv.html', 'research.html', 'books.html', 'qubit-dialogues.html',
         'life/index.html', 'illustrated/index.html', 'qec-in-practice/index.html',
         'qec-in-practice/lesson-1.html', 'qec-in-practice/lesson-2.html',
         'qec-in-practice/lesson-3.html', 'qec-in-practice/lesson-4.html', '404.html']

NAV = [('Research', '/research.html'), ('Books', '/books.html'), ('Lessons', '/qec-in-practice/'),
       ('CV', '/cv.html'), ('Contact', '/#contact')]

# (page, rule): one-line reason
EXEMPT = {
    ('index.html', 'home link'): 'it is home',
    ('index.html', 'stylesheet'): 'keeps its own inline CSS for first paint; lib/site.css mirrors it',
    ('index.html', 'script'): 'runs its own switch, which also repaints its canvases',
}

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
    out = {}
    for k, v in re.findall(r'--' + prefix + r'([\w-]+)\s*:\s*([^;]+);', body):
        v = v.strip()
        if re.match(r'#|rgba?\(', v) or k in ('sans', 'mono'):
            out[k] = re.sub(r'\s+', '', v)
    return out


home = read(ROOT / 'index.html')
icon = re.search(r'<link rel="icon" href="([^"]+)"', home).group(1)

css_path = ROOT / 'lib' / 'site.css'
if not css_path.exists():
    fail.append('lib/site.css: missing')
else:
    css = read(css_path)
    for sel, theme in ((':root', 'dark'), (':root[data-theme="light"]', 'light')):
        want = tokens(block(home, sel), '')
        have = tokens(block(css, sel), 'tp-')
        for k, v in want.items():
            if have.get(k) != v:
                fail.append(f'lib/site.css: {theme} --tp-{k} is {have.get(k)}, index.html has {v}')

for page in PAGES:
    p = ROOT / page
    if not p.exists():
        fail.append(f'{page}: missing'); continue
    html = read(p)
    head = html.split('</head>')[0]
    static = strip(html)
    here = urljoin(SITE, page)
    links = [urljoin(here, h) for h in re.findall(r'href="([^"]*)"', static)]
    m = re.search(r'<header class="(?:tp-)?bar".*?<nav[^>]*>(.*?)</nav>', static, re.S)
    nav = [(re.sub(r'<[^>]+>', '', t).strip(), urljoin(here, h))
           for h, t in re.findall(r'<a [^>]*?href="([^"]*)"[^>]*>(.*?)</a>', m.group(1), re.S)] if m else []
    checks = {
        'pre-paint': (re.search(r'getItem\(\s*["\']tp-theme["\']\s*\)', head) is not None,
                      'no tp-theme pre-paint snippet in <head>'),
        'qd-theme': (re.search(r'setItem\(\s*["\']qd-theme', html) is None, 'still writes qd-theme'),
        'favicon': (f'<link rel="icon" href="{icon}">' in head, 'not the homepage favicon'),
        'home link': (SITE in links, 'no link home'),
        'header': (('<header class="bar"' if page == 'index.html' else 'class="tp-bar"') in static,
                   'no shared header'),
        'nav': (nav == [(t, urljoin(SITE, h)) for t, h in NAV], f'nav is {[t for t, _ in nav]}, not the shared list'),
        'main': (len(re.findall(r'<main[\s>]', static)) == 1, 'not exactly one <main>'),
        'h1': (len(re.findall(r'<h1[\s>]', static)) == 1, f'{len(re.findall(r"<h1[\s>]", static))} static <h1>, want 1'),
        'web fonts': ('fonts.googleapis.com' not in html, 'loads Google Fonts'),
        'stylesheet': ('href="/lib/site.css"' in head, 'does not link /lib/site.css'),
        'script': ('src="/lib/site.js"' in html, 'does not load /lib/site.js'),
    }
    for rule, (ok, msg) in checks.items():
        if not ok and (page, rule) not in EXEMPT:
            fail.append(f'{page}: {msg}')

print('\n'.join(fail) or 'site ok')
sys.exit(1 if fail else 0)
