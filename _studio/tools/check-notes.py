"""The notes in _studio/content/notes.json are published as notes/<slug>.html, listed
in notes/index.html and in the RSS feed notes/feed.xml, all in step with a fresh run
of build-notes.py. Each note page has its canonical, title, description, one
theme-color, the RSS alternate link and a BlogPosting JSON-LD; its table equals its
data file; its internal links resolve; its body is plain ASCII punctuation. The
sitemap lists /notes/ and every note. Exits non-zero on failure.

    python _studio/tools/build-notes.py
    python _studio/tools/check-notes.py
"""
import email.utils, html as htmllib, importlib.util, io, json, pathlib, re, sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE = 'https://pandey-tushar.com'
ALT = '<link rel="alternate" type="application/rss+xml" title="Notes by Tushar Pandey" href="/notes/feed.xml">'
read = lambda p: io.open(p, encoding='utf-8').read()
fail = []

src = ROOT / '_studio' / 'content' / 'notes.json'
if not src.exists():
    print('_studio/content/notes.json: missing'); sys.exit(1)
notes = json.loads(read(src))['notes']


def target(href, page):
    """The repo file an internal href points to, or None for an external one."""
    if re.match(r'^[a-z]+:', href) or href.startswith('//'):
        return None
    path = href.split('#')[0].split('?')[0]
    if not path:
        return page
    f = ROOT / path.lstrip('/') if path.startswith('/') else page.parent / path
    return f / 'index.html' if path.endswith('/') else f


def internal_links(page):
    for h in re.findall(r'href="([^"]*)"', re.sub(r'<script\b.*?</script>', '', read(page), flags=re.S)):
        f = target(htmllib.unescape(h), page)
        if f is not None and not f.exists():
            fail.append(f'{page.relative_to(ROOT).as_posix()}: link {h} does not resolve to a file')


def head_checks(name, html, canonical, title, desc):
    head = html.split('</head>')[0]
    if f'<link rel="canonical" href="{canonical}">' not in head:
        fail.append(f'{name}: no canonical {canonical}')
    if f'<title>{title}</title>' not in head:
        fail.append(f'{name}: title is not {title}')
    if f'<meta name="description" content="{desc}">' not in head:
        fail.append(f'{name}: meta description is not the one in notes.json')
    if len(re.findall(r'<meta name="theme-color"', head)) != 1 or '<meta name="theme-color" content="#0d1320">' not in head:
        fail.append(f'{name}: not exactly one theme-color meta #0d1320')
    if ALT not in head:
        fail.append(f'{name}: no RSS alternate link')


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


# the note pages
for n in notes:
    rel = f"notes/{n['slug']}.html"
    page = ROOT / rel
    if not page.exists():
        fail.append(f'{rel}: missing'); continue
    html = read(page)
    head_checks(rel, html, f'{SITE}/{rel}', f"{esc(n['title'])} &middot; Tushar Pandey", esc(n['description']))
    posts = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            doc = json.loads(block)
        except ValueError as e:
            fail.append(f'{rel}: JSON-LD does not parse: {e}'); continue
        if doc.get('@type') == 'BlogPosting':
            posts.append(doc)
    if len(posts) != 1:
        fail.append(f'{rel}: want one BlogPosting JSON-LD, found {len(posts)}')
    else:
        want = {'headline': n['title'], 'datePublished': n['date'], 'url': f'{SITE}/{rel}',
                'author': {'@id': f'{SITE}/#person'}}
        fail += [f'{rel}: BlogPosting {k} is {posts[0].get(k)!r}, want {v!r}' for k, v in want.items() if posts[0].get(k) != v]
    internal_links(page)

    # the body: ASCII punctuation only, in the source and in the article
    body = read(ROOT / '_studio' / 'content' / 'notes' / n['body'])
    odd = sorted({c for c in body if ord(c) > 127})
    if odd:
        fail.append(f"{n['body']}: non-ASCII characters {odd}")
    art = re.search(r'<article\b.*?</article>', html, re.S)
    art = art.group(0) if art else ''
    if not art:
        fail.append(f'{rel}: no <article>')
    if re.search(r'[^\x00-\x7f]|&(mdash|ndash|ldquo|rdquo|lsquo|rsquo|#8211|#8212|#8216|#8217|#8220|#8221);', art):
        fail.append(f'{rel}: non-ASCII punctuation in the note body')
    if 'Cite this note' not in art or f'{SITE}/{rel}' not in art:
        fail.append(f'{rel}: no cite line with its own URL')
    for h, t in (('/notes/', 'All notes'), ('/notes/feed.xml', 'RSS feed')):
        if not re.search(r'<a [^>]*href="' + re.escape(h) + r'"[^>]*>' + t + '</a>', art):
            fail.append(f'{rel}: no "{t}" link to {h}')

    # the table equals the data
    if 'data' in n:
        data = json.loads(read(ROOT / '_studio' / 'content' / 'notes' / n['data']))
        want = [(f"{c['a']} and {c['b']}", 'not resolved', '') if c['multiple'] else
                (f"{c['a']} and {c['b']}", f"{c['p']:.3f}", f"{c['lo']:.3f} to {c['hi']:.3f}")
                for c in data['crossings']]
        tab = re.search(r'<table class="nt-table">.*?<tbody>(.*?)</tbody>', html, re.S)
        rows = [tuple(re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<t[hd]\b[^>]*>(.*?)</t[hd]>', r, re.S))
                for r in re.findall(r'<tr>(.*?)</tr>', tab.group(1), re.S)] if tab else []
        if rows != want:
            fail.append(f'{rel}: table is {rows}, the data gives {want}')
        if not re.search(r'<figure class="[^"]*\bnt-fig\b[^"]*"[^>]*>\s*<div class="pc-plot"><svg [^>]*role="img"', html):
            fail.append(f'{rel}: no static SVG figure built from the data')

# the index
idx = ROOT / 'notes' / 'index.html'
if not idx.exists():
    fail.append('notes/index.html: missing')
else:
    html = read(idx)
    head = html.split('</head>')[0]
    if f'<link rel="canonical" href="{SITE}/notes/">' not in head or ALT not in head:
        fail.append('notes/index.html: no canonical /notes/ or no RSS alternate link')
    hrefs = re.findall(r'href="([^"]*)"', html)
    fail += [f"notes/index.html: does not link {n['slug']}" for n in notes if f"/notes/{n['slug']}.html" not in hrefs]
    order = [n['slug'] for n in sorted(notes, key=lambda n: n['date'], reverse=True)]
    seen = [m for m in re.findall(r'href="/notes/([\w-]+)\.html"', html) if m in order]
    if list(dict.fromkeys(seen)) != order:
        fail.append('notes/index.html: notes not listed newest first')
    internal_links(idx)

# the feed
feed = ROOT / 'notes' / 'feed.xml'
if not feed.exists():
    fail.append('notes/feed.xml: missing')
else:
    try:
        ch = ET.parse(feed).getroot().find('channel')
    except ET.ParseError as e:
        ch = None; fail.append(f'notes/feed.xml: does not parse: {e}')
    if ch is not None:
        if ch.findtext('link') != f'{SITE}/notes/':
            fail.append('notes/feed.xml: channel link is not /notes/')
        self_ = ch.find('{http://www.w3.org/2005/Atom}link')
        if self_ is None or self_.get('rel') != 'self' or self_.get('href') != f'{SITE}/notes/feed.xml':
            fail.append('notes/feed.xml: no atom:link rel="self"')
        items = ch.findall('item')
        if len(items) != len(notes):
            fail.append(f'notes/feed.xml: {len(items)} items, notes.json has {len(notes)}')
        links = {i.findtext('link') for i in items}
        for n in notes:
            u = f"{SITE}/notes/{n['slug']}.html"
            it = [i for i in items if i.findtext('link') == u]
            if not it:
                fail.append(f'notes/feed.xml: no item for {u}'); continue
            it = it[0]
            if it.findtext('guid') != u or it.findtext('title') != n['title'] or it.findtext('description') != n['description']:
                fail.append(f'notes/feed.xml: item {u} guid, title or description differs from notes.json')
            pd = it.findtext('pubDate') or ''
            try:
                ok = (re.fullmatch(r'[A-Z][a-z]{2}, \d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2} [+-]\d{4}', pd)
                      and email.utils.parsedate_to_datetime(pd).date().isoformat() == n['date'])
            except (TypeError, ValueError):
                ok = False
            if not ok:
                fail.append(f'notes/feed.xml: pubDate {pd!r} of {u} is not RFC 822 for {n["date"]}')

# the sitemap
sitemap = read(ROOT / 'sitemap.xml')
for u in [f'{SITE}/notes/'] + [f"{SITE}/notes/{n['slug']}.html" for n in notes]:
    if f'<loc>{u}</loc>' not in sitemap:
        fail.append(f'sitemap.xml: no {u}')

# in step with a fresh build
build_path = ROOT / '_studio' / 'tools' / 'build-notes.py'
if not build_path.exists():
    fail.append('build-notes.py: missing')
else:
    spec = importlib.util.spec_from_file_location('build_notes', build_path)
    build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
    for rel, text in build.build().items():
        f = ROOT / rel
        if not f.exists() or read(f) != text:
            fail.append(f'{rel}: differs from a fresh build: run build-notes.py')

print('\n'.join(fail) or 'notes ok')
sys.exit(1 if fail else 0)
