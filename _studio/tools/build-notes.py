"""Write the notes in _studio/content/notes.json as notes/<slug>.html, the list
notes/index.html (newest first) and the RSS 2.0 feed notes/feed.xml.

A note's body is _studio/content/notes/<body>.md in a small subset of markdown: one
h1, h2 headings, paragraphs, inline links [text](url), inline math between dollar signs
($p_{th}$, $d^{1/nu}$: see math()), one pipe table and reference lines starting [1], [2], ...
Anything else stops the build. A note with a "data" file
(the output of _studio/tools/notes/crossings.mjs) has its table rendered from that
data, after checking it agrees with the markdown table, and gets Fig. 1 drawn from it.

    python _studio/tools/build-notes.py
    python _studio/tools/check-notes.py
"""
import datetime, email.utils, io, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE = 'https://pandey-tushar.com'
CONTENT = ROOT / '_studio' / 'content'
FEED_TITLE = 'Notes by Tushar Pandey'
ABOUT = 'A note is a short write-up of one measured result or one argument, with the data and the method behind it.'
read = lambda p: io.open(p, encoding='utf-8').read()


class MarkupError(SystemExit):
    pass


def esc(s):
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    return ''.join(c if ord(c) < 128 else f'&#{ord(c)};' for c in s)


def xesc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def math(src):
    """Inline math between dollar signs: a_x or a_{xy} is a subscript, a^x or a^{xy} a superscript,
    the word nu is the Greek letter and - is a minus sign. Nothing else is special."""
    def word(s):
        return re.sub(r'\bnu\b', '&nu;', esc(s).replace('-', '&minus;'))
    def run(s):
        out, pos = [], 0
        for m in re.finditer(r'([_^])(?:\{([^{}]*)\}|(\w))', s):
            out.append(word(s[pos:m.start()]))
            tag = 'sub' if m.group(1) == '_' else 'sup'
            out.append(f'<{tag}>{word(m.group(2) if m.group(2) is not None else m.group(3))}</{tag}>')
            pos = m.end()
        out.append(word(s[pos:]))
        return ''.join(out)
    if re.search(r'[{}_^]', re.sub(r'[_^](\{[^{}]*\}|\w)', '', src)):
        raise MarkupError(f'unsupported math: {src}')
    return run(src)


def inline(text, where):
    """Escape a run of text, typeset $math$ and turn [text](url) into links; refuse other markup."""
    parts = re.split(r'\$([^$]+)\$', text)
    if '$' in ''.join(parts[::2]):
        raise MarkupError(f'{where}: unpaired $ in: {text[:60]}')
    return ''.join(links(p, where) if i % 2 == 0 else math(p) for i, p in enumerate(parts))


def links(text, where):
    """Escape a run of text and turn [text](url) into links; refuse other markup."""
    out, pos = [], 0
    for m in re.finditer(r'\[([^\]]+)\]\(([^)\s]+)\)', text):
        out.append(esc(text[pos:m.start()]))
        rel = ' rel="noopener"' if m.group(2).startswith('http') else ''
        out.append(f'<a class="tp-link" href="{esc(m.group(2))}"{rel}>{esc(m.group(1))}</a>')
        pos = m.end()
    out.append(esc(text[pos:]))
    rest = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', '', text)
    bad = re.sub(r'\[\d+\]', '', rest)
    for mark in ('[', ']', '*', '`', '<', '>', '!['):
        if mark in bad:
            raise MarkupError(f'{where}: unsupported markup {mark!r} in: {text[:60]}')
    return ''.join(out)


def arxiv(html):
    return re.sub(r'arXiv:((?:[a-z-]+/\d{7})|(?:\d{4}\.\d{4,5}))',
                  r'<a class="tp-link" href="https://arxiv.org/abs/\1" rel="noopener">arXiv:\1</a>', html)


def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def parse(md, where):
    """Blocks of the note: ('h1', text), ('h2', text), ('p', text), ('ref', n, text), ('table', head, rows)."""
    blocks, h1 = [], 0
    for chunk in re.split(r'\n\s*\n', md.strip()):
        lines = [ln.rstrip() for ln in chunk.split('\n')]
        first = lines[0]
        if first.startswith('# '):
            if len(lines) > 1 or h1:
                raise MarkupError(f'{where}: the h1 must be one line, once')
            h1 += 1; blocks.append(('h1', first[2:].strip()))
        elif first.startswith('## '):
            if len(lines) > 1:
                raise MarkupError(f'{where}: a heading must be one line: {first}')
            blocks.append(('h2', first[3:].strip()))
        elif first.startswith('|'):
            if not all(ln.startswith('|') and ln.endswith('|') for ln in lines) or len(lines) < 3:
                raise MarkupError(f'{where}: malformed table near {first}')
            if any(b[0] == 'table' for b in blocks):
                raise MarkupError(f'{where}: more than one table')
            cells = [[c.strip() for c in ln.strip('|').split('|')] for ln in lines]
            if not all(re.fullmatch(r':?-+:?', c) for c in cells[1]):
                raise MarkupError(f'{where}: table has no separator row')
            blocks.append(('table', cells[0], cells[2:]))
        elif re.match(r'\[\d+\] ', first):
            n = int(first[1:first.index(']')])
            blocks.append(('ref', n, ' '.join(lines)[len(f'[{n}] '):]))
        else:
            for ln in lines:
                if re.match(r'\s*(#|\||[-*+] |\d+[.)] |>|```|~~~|\s{4})', ln):
                    raise MarkupError(f'{where}: unsupported markup: {ln}')
            blocks.append(('p', ' '.join(lines)))
    if h1 != 1 or blocks[0][0] != 'h1':
        raise MarkupError(f'{where}: want exactly one h1, first')
    refs = [b[1] for b in blocks if b[0] == 'ref']
    if refs != list(range(1, len(refs) + 1)):
        raise MarkupError(f'{where}: references are not numbered 1, 2, ...')
    return blocks


# ---- the crossings table and figure

def crossing_rows(data):
    bad = [c for c in data['crossings'] if c['status'] != 'found']
    if bad:
        raise MarkupError(f"crossing not found for {bad[0]['a']} and {bad[0]['b']}: {bad[0]['status']}")
    return [(f"{c['a']} and {c['b']}", 'not resolved', '') if c['multiple'] else
            (f"{c['a']} and {c['b']}", f"{c['p']:.3f}", f"{c['lo']:.3f} to {c['hi']:.3f}")
            for c in data['crossings']]


def table(head, md_rows, data, where):
    rows = crossing_rows(data)
    md = [tuple(r + [''] * (3 - len(r))) for r in md_rows]
    if len(head) != 3 or md != rows:
        bad = [f'  markdown {a}\n  data     {b}' for a, b in zip(md, rows) if a != b] or [f'  {len(md)} rows against {len(rows)}']
        raise MarkupError(f'{where}: the markdown table and the data disagree:\n' + '\n'.join(bad))
    th = ''.join(f'<th scope="col">{esc(h)}</th>' for h in head)
    body = '\n'.join(f'      <tr><th scope="row">{esc(a)}</th><td>{esc(b)}</td><td>{esc(c)}</td></tr>' for a, b, c in rows)
    return (f'  <div class="nt-scroll">\n  <table class="nt-table">\n    <thead><tr>{th}</tr></thead>\n'
            f'    <tbody>\n{body}\n    </tbody>\n  </table>\n  </div>')


def figure(data):
    W, H, L, R, T, B = 340, 252, 44, 334, 26, 194
    lo_p, hi_p = 0.065, 0.106
    y = lambda p: B - (p - lo_p) / (hi_p - lo_p) * (B - T)
    cs = data['crossings']
    step = (R - L) / len(cs)
    x = lambda i: L + (i + .5) * step
    f = lambda v: f'{v:.1f}'
    out = [f'<path class="pc-grid" d="' + ''.join(f'M{L} {f(y(t))}H{R}' for t in (.07, .08, .09, .10)) + '"/>',
           f'<path class="pc-axis" d="M{L} {T}V{B}H{R}"/>']
    out += [f'<text class="pc-tick" x="{L - 6}" y="{f(y(t) + 4.5)}" text-anchor="end">{t:.2f}</text>' for t in (.07, .08, .09, .10)]
    ref = y(0.099)
    out.append(f'<path class="pc-ref" d="M{L} {f(ref)}H{R}"/>')
    out.append(f'<text class="pc-lab" x="{L + 6}" y="{f(ref - 6)}">9.9% [1]</text>')
    pts, desc = [], []
    for i, c in enumerate(cs):
        cx = f(x(i))
        out.append(f'<text class="pc-tick" x="{cx}" y="{B + 18}" text-anchor="middle">{c["a"]}, {c["b"]}</text>')
        if c['multiple']:
            mid = f((T + B) / 2)
            out.append(f'<text class="pc-tick" x="{cx}" y="{mid}" text-anchor="middle" transform="rotate(-90 {cx} {mid})">not resolved</text>')
            desc.append(f"{c['a']} and {c['b']}: not resolved")
            continue
        ylo, yhi = y(c['lo']), y(c['hi'])
        d = f'M{cx} {f(ylo)}V{f(yhi)}'
        if not c['hiOpen']:
            d += f'M{f(x(i) - 4)} {f(yhi)}h8'
        if not c['loOpen']:
            d += f'M{f(x(i) - 4)} {f(ylo)}h8'
        pts.append(f'<path class="pc-bar" d="{d}"/><circle class="pc-mark" cx="{cx}" cy="{f(y(c["p"]))}" r="3.8"/>')
        desc.append(f"{c['a']} and {c['b']}: {c['p']:.3f}, {c['lo']:.3f} to {c['hi']:.3f}")
    out.append('<g class="nt-pts">' + ''.join(pts) + '</g>')
    out.append(f'<text class="pc-lab" x="4" y="14">crossing p</text>')
    out.append(f'<text class="pc-lab" x="{R}" y="{B + 40}" text-anchor="end">pair of distances</text>')
    title = 'Pairwise crossings against the pair of distances'
    alt = ('Crossing p with one-standard-error range for each pair of consecutive distances: '
           + '; '.join(desc) + '. A dashed line marks the 9.9% threshold of reference 1.')
    svg = (f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="fig1-t fig1-d">'
           f'<title id="fig1-t">{esc(title)}</title><desc id="fig1-d">{esc(alt)}</desc>\n'
           + '\n'.join(out) + '\n</svg>')
    cap = ('Where the curves of consecutive distances cross, for union-find on the surface code under bit-flip noise '
           'with perfect measurement. Bars are one standard error. The pair 11, 13 is not resolved. '
           'The line is the 9.9% threshold of [1].')
    return (f'  <figure class="tp-plate pc-fig nt-fig" id="fig-1">\n  <div class="pc-plot">{svg}</div>\n'
            f'  <figcaption><b>Fig. 1</b>{esc(cap)}</figcaption>\n  </figure>')


# ---- pages

HEAD = '''<!doctype html>
<html lang="en" class="tp-full">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#0d1320">
<script>
(function(){
  var d = document.documentElement;
  try{
    var pref = localStorage.getItem("tp-theme");
    if (pref !== "light" && pref !== "dark") pref = "auto";
    d.dataset.pref = pref;
    d.dataset.theme =
      (pref === "auto" ? matchMedia("(prefers-color-scheme: light)").matches : pref === "light")
        ? "light" : "dark";
  }catch(e){ d.dataset.pref = "auto"; d.dataset.theme = "dark"; }
})();
</script>
<link rel="icon" href="/favicon.ico" sizes="16x16 32x32 48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/lib/site.css">
<script src="/lib/site.js" defer></script>
<!-- Google Analytics (GA4) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-DVPGC1C44Z"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-DVPGC1C44Z');
</script>
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="author" content="Tushar Pandey">
<link rel="canonical" href="{url}">
<link rel="alternate" type="application/rss+xml" title="Notes by Tushar Pandey" href="/notes/feed.xml">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="{ogtype}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="https://pandey-tushar.com/og-research.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:site_name" content="Tushar Pandey">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://pandey-tushar.com/og-research.png">
<script type="application/ld+json">
{jsonld}
</script>
<link rel="stylesheet" href="/papers/paper.css">
<link rel="stylesheet" href="/notes/notes.css">
{extra}</head>
<body>
<a class="tp-skip" href="#main">Skip to content</a>
<header class="tp-bar">
  <a class="tp-mark" href="/" aria-label="Tushar Pandey, home">
    <svg width="19" height="19" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <g fill="none" stroke="#52d6e6" stroke-width="1.05" opacity=".9">
        <circle cx="12" cy="7.6" r="5.4"/><circle cx="8.2" cy="14.2" r="5.4"/><circle cx="15.8" cy="14.2" r="5.4"/>
      </g>
    </svg>
    <span>Tushar Pandey</span>
  </a>
  <nav class="tp-nav" aria-label="Primary">
    <a href="/research.html">Research</a>
    <a href="/books.html">Books</a>
    <a href="/qec-in-practice/">Lessons</a>
    <a href="/cv.html">CV</a>
    <a href="/#contact">Contact</a>
  </nav>
  <button class="tp-toggle" type="button" aria-label="Switch theme"><b aria-hidden="true">&#9680;</b><span>Auto</span></button>
</header>

<main id="main" class="{main}">
 <div class="tp-wrap pc-cols">
'''

FOOT = ''' </div>
</main>

<footer class="tp-foot">
  <ul>
    <li><a href="/">Home</a></li>
    <li><a href="/research.html">Research</a></li>
    <li><a href="/books.html">Books</a></li>
    <li><a href="/qec-in-practice/">Lessons</a></li>
    <li><a href="/cv.html">CV</a></li>
    <li><a href="https://github.com/pandey-tushar" rel="noopener">GitHub</a></li>
    <li><a href="mailto:wtatushar@gmail.com">Email</a></li>
  </ul>
  <p>&copy; 2026 Tushar Pandey</p>
</footer>
</body>
</html>
'''


# a note opens on the live hero of the article pages (lib/article.css, lib/article.js); the index does not
ARTICLE = '<link rel="stylesheet" href="/lib/article.css">\n<script src="/lib/article.js" defer></script>\n'


def head(title, desc, url, ogtype, ld, main='pc', extra=''):
    return (HEAD.replace('{main}', main).replace('{extra}', extra).replace('{title}', title).replace('{desc}', desc).replace('{url}', url)
            .replace('{ogtype}', ogtype).replace('{jsonld}', json.dumps(ld, indent=1)))


def day(iso):
    d = datetime.date.fromisoformat(iso)
    return f'{d.day} {d:%B %Y}'


def note_page(n):
    where = n['body']
    blocks = parse(read(CONTENT / 'notes' / n['body']), where)
    if blocks[0][1] != n['title']:
        raise MarkupError(f"{where}: h1 {blocks[0][1]!r} is not the title in notes.json {n['title']!r}")
    data = json.loads(read(CONTENT / 'notes' / n['data'])) if 'data' in n else None
    url = f"{SITE}/notes/{n['slug']}.html"
    body, toc = [], []
    for b in blocks[1:]:
        if b[0] == 'h2':
            body.append(f'  <h2 id="{slugify(b[1])}">{inline(b[1], where)}</h2>')
            toc.append(f'        <li><a href="#{slugify(b[1])}">{inline(b[1], where)}</a></li>')
        elif b[0] == 'p':
            body.append(f'  <p>{inline(b[1], where)}</p>')
        elif b[0] == 'ref':
            body.append(f'  <p class="nt-ref" id="ref-{b[1]}">[{b[1]}] {arxiv(inline(b[2], where))}</p>')
        elif b[0] == 'table':
            if data is None:
                raise MarkupError(f'{where}: a table needs the note\'s data file')
            body.append(table(b[1], b[2], data, where))
            body.append(figure(data))
    ld = {'@context': 'https://schema.org', '@type': 'BlogPosting', 'headline': n['title'],
          'description': n['description'], 'datePublished': n['date'],
          'author': {'@id': f'{SITE}/#person'}, 'url': url}
    title = f"{esc(n['title'])} &middot; Tushar Pandey"
    return (head(title, esc(n['description']), url, 'article', ld, 'pc nt-note', ARTICLE)
            + f'''  <header class="ar-hero" data-art="curves">
    <canvas class="ar-viz" aria-hidden="true"></canvas>
    <div class="ar-in tp-wrap">
     <div class="ar-text">
      <p class="tp-lbl">Note</p>
      <h1>{esc(n['title'])}</h1>
      <p class="pc-status ar-line"><time datetime="{n['date']}">{day(n['date'])}</time></p>
     </div>
     <a class="ar-cue" href="#plain">Read<i aria-hidden="true"></i></a>
    </div>
  </header>

  <aside class="pc-rail" aria-label="Summary and contents">
    <section class="pc-plainwords" aria-labelledby="plain">
      <h2 class="pc-rail-h" id="plain">In plain words</h2>
      <p>{esc(n['plain'])}</p>
    </section>
    <nav class="pc-toc" aria-label="On this page">
      <p class="pc-rail-h">On this page</p>
      <ol>
{chr(10).join(toc)}
      </ol>
    </nav>
  </aside>

  <article class="pc-essay nt-essay">
{chr(10).join(body)}

  <p class="nt-cite"><span class="tp-lbl">Cite this note</span> T. Pandey, "{esc(n['title'])}" ({n['date'][:4]}), {url}</p>
  <nav class="pc-more" aria-label="More">
    <a class="tp-link" href="/notes/">All notes</a>
    <a class="tp-link" href="/notes/feed.xml">RSS feed</a>
  </nav>
  </article>
''' + FOOT)


def index_page(notes):
    url = f'{SITE}/notes/'
    desc = 'Short notes by Tushar Pandey on measurements and observations in quantum error correction, newest first.'
    ld = {'@context': 'https://schema.org', '@type': 'Blog', 'name': FEED_TITLE, 'url': url,
          'author': {'@id': f'{SITE}/#person'},
          'blogPost': [{'@type': 'BlogPosting', 'headline': n['title'], 'datePublished': n['date'],
                        'url': f"{SITE}/notes/{n['slug']}.html"} for n in notes]}
    # the index is a hero and one window-sized pane per note, each opening into a
    # sheet (lib/site.css tp-hero, tp-pane, tp-sheet); it takes the site type, not the essay's
    places = ['', ' tp-pane-mid', ' tp-pane-end', ' tp-pane-top']
    panes, rail, sheets = [], [], []
    for k, n in enumerate(notes):
        s, t, when = n['slug'], esc(n['title']), f'<time datetime="{n["date"]}">{day(n["date"])}</time>'
        panes.append(f'''    <article class="tp-pane{places[k % 4]}" id="pane-{s}" aria-labelledby="pane-{s}-t">
      <div class="tp-pane-viz"><canvas data-fig="toric" aria-hidden="true"></canvas></div>
      <div class="tp-pane-in tp-wrap">
        <div class="tp-pane-text">
          <p class="tp-pane-tag">Note</p>
          <h2 class="tp-pane-name" id="pane-{s}-t">{t}</h2>
          <p class="tp-pane-line">{when}</p>
          <a class="tp-pane-open" href="#{s}" aria-haspopup="dialog" aria-label="Open {t}">Open<i aria-hidden="true"></i></a>
        </div>
      </div>
    </article>''')
        rail.append(f'    <a href="#pane-{s}"><span>{t}</span></a>')
        sheets.append(f'''  <dialog class="tp-sheet" id="{s}" aria-labelledby="{s}-t">
    <div class="tp-sheet-bar"><span class="tp-sheet-tag">Note</span><button class="tp-sheet-close" type="button" aria-label="Close">Close <kbd>Esc</kbd></button></div>
    <div class="tp-sheet-in tp-wrap">
      <div class="tp-sheet-media"><canvas data-fig="toric" aria-hidden="true"></canvas></div>
      <div class="tp-sheet-body">
        <h2 id="{s}-t">{t}</h2>
        <p class="tp-sheet-sub">{when}</p>
        <p>{esc(n['description'])}</p>
        <ul class="tp-sheet-links">
          <li><a href="/notes/{s}.html">Read the note<small>pandey-tushar.com</small></a></li>
        </ul>
      </div>
    </div>
  </dialog>''')
    page = head('Notes &middot; Tushar Pandey', esc(desc), url, 'website', ld, 'pc nt-home')
    page = page.replace('<link rel="stylesheet" href="/papers/paper.css">\n<link rel="stylesheet" href="/notes/notes.css">\n',
                        '<style>\n/* Notes: a live hero, then one pane per note, newest first, each opening\n'
                        '   into a sheet. Everything is in /lib/site.css and /lib/site.js. */\n'
                        '.nt-about p{margin:1rem 0 0;max-width:42em;font-size:var(--tp-t-small);line-height:1.6;color:var(--tp-dim)}\n'
                        '</style>\n', 1).replace('<html lang="en" class="tp-full">', '<html lang="en" class="tp-full tp-geist">', 1)
    page = page[:page.index(' <div class="tp-wrap pc-cols">')]
    return (page + f'''  <section class="tp-hero" aria-label="Introduction">
    <canvas data-fig="crossing" aria-hidden="true"></canvas>
    <div class="tp-hero-in tp-wrap">
      <div class="tp-hero-text">
        <h1>Notes</h1>
        <p class="tp-hero-lede">Newest first.</p>
        <aside class="nt-about" aria-label="About the notes">
          <p>{ABOUT} New notes also appear in the <a class="tp-link" href="/notes/feed.xml">RSS feed</a>.</p>
        </aside>
      </div>
    </div>
  </section>

  <section id="notes" class="tp-panes" aria-label="Notes">
''' + '\n\n'.join(panes) + '''
  </section>

  <nav class="tp-rail" aria-label="Panes">
''' + '\n'.join(rail) + '''
  </nav>

''' + '\n\n'.join(sheets) + '\n' + FOOT.replace(' </div>\n</main>', '</main>', 1))


def feed(notes):
    def pub(iso):
        d = datetime.datetime.fromisoformat(iso).replace(tzinfo=datetime.timezone.utc)
        return email.utils.format_datetime(d)
    items = '\n'.join(f'''  <item>
   <title>{xesc(n['title'])}</title>
   <link>{SITE}/notes/{n['slug']}.html</link>
   <guid isPermaLink="true">{SITE}/notes/{n['slug']}.html</guid>
   <pubDate>{pub(n['date'])}</pubDate>
   <description>{xesc(n['description'])}</description>
  </item>''' for n in notes)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
 <channel>
  <title>{FEED_TITLE}</title>
  <link>{SITE}/notes/</link>
  <description>Short notes on measurements and observations in quantum error correction.</description>
  <language>en</language>
  <lastBuildDate>{pub(notes[0]['date'])}</lastBuildDate>
  <atom:link href="{SITE}/notes/feed.xml" rel="self" type="application/rss+xml"/>
{items}
 </channel>
</rss>
'''


def build():
    notes = sorted(json.loads(read(CONTENT / 'notes.json'))['notes'], key=lambda n: n['date'], reverse=True)
    out = {f"notes/{n['slug']}.html": note_page(n) for n in notes}
    out['notes/index.html'] = index_page(notes)
    out['notes/feed.xml'] = feed(notes)
    return out


if __name__ == '__main__':
    for rel, text in build().items():
        io.open(ROOT / rel, 'w', encoding='utf-8', newline='\n').write(text)
        print(f'wrote {rel}')
