"""Write the papers in _studio/content/papers.json into research.html (the full
list and its ScholarlyArticle JSON-LD) and the selected ones into cv.html,
between marker comments, as static HTML that reads with scripts off.

    python _studio/tools/build-research.py
    python _studio/tools/check-research.py
"""
import io, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE = 'https://pandey-tushar.com/'
ME = 'Tushar Pandey'
PERSON = {'@type': 'Person', '@id': SITE + '#person', 'name': ME, 'url': SITE}
WORDS = 'zero one two three four five six seven eight nine ten'.split()
read = lambda p: io.open(p, encoding='utf-8').read()


def esc(s):
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    return ''.join(c if ord(c) < 128 else f'&#{ord(c)};' for c in s)


def rich(s):
    return re.sub(r'10\^(\d+)', r'10<sup>\1</sup>', esc(s))


# an area's motif in papers.json -> its emblem in img/figures/ (drawn by
# _studio/tools/assets/emblems.py), inlined so currentColor and the tokens
# follow the theme
EMBLEMS = {'lattice': 'qec', 'circuit': 'circuit', 'graph': 'reasoning', 'knot': 'topology', 'primes': 'primes'}


def motif(name):
    svg = read(ROOT / 'img' / 'figures' / f'{EMBLEMS[name]}.svg').strip()
    svg = re.sub(r'<title>.*?</title>', '', svg)
    return re.sub(r' role="img" aria-label="[^"]*"', ' aria-hidden="true" focusable="false"', svg, count=1)


def links(p):
    out = []
    if p.get('doi'):
        out.append((f"https://doi.org/{p['doi']}", f"doi:{p['doi']}"))
    if p.get('arxiv'):
        out.append((f"https://arxiv.org/abs/{p['arxiv']}", f"arXiv:{p['arxiv']}"))
    if p.get('data'):
        out.append((f"https://doi.org/{p['data']}", 'Code and data'))
    if p.get('page'):
        out.append((p['page'], 'Companion page'))
    if p.get('code'):
        out.append((p['code'], 'Code'))
    if p.get('url'):
        out.append(tuple(p['url']))
    return out


def byline(p):
    names = [f'<b class="me">{esc(a)}</b>' if a == ME else esc(a) for a in p['authors']]
    if len(names) == 1 and p.get('kind') in (None, 'contribution'):
        return names[0] + ', sole author'
    return ', '.join(names)


def role(p):
    a = p['authors']
    if len(a) == 1:
        return 'thesis' if p.get('kind') == 'thesis' else 'sole author'
    if len(a) == 2:
        return 'with ' + esc(a[1] if a[0] == ME else a[0])
    return f'{"first" if a[0] == ME else "author " + str(a.index(ME) + 1)} of {len(a)} authors'


# an area's motif -> the live figure behind its pane and in its sheet (TP.live.fig in lib/site.js)
FIGS = {'lattice': 'toric', 'circuit': 'circuit', 'graph': 'graph', 'knot': 'knot', 'primes': 'primes'}
# where the words sit on each pane in turn, never twice in a row in one place
PLACES = ['', ' tp-pane-mid', ' tp-pane-end', ' tp-pane-top']


def where(href):
    """The place a link goes, as the sheet's small label after it."""
    m = re.match(r'https?://(?:www\.)?([^/]+)', href)
    return m.group(1) if m else 'pandey-tushar.com'


def label(text):
    """A link label: an identifier (doi:, arXiv:) is set in mono."""
    return f'<span class="tp-id">{esc(text)}</span>' if re.match(r'(doi|arXiv):', text) else esc(text)


def entry(p):
    pid = p['id']
    status = esc(p['status']) + (f" &middot; {esc(p['note'])}" if p.get('note') else '')
    claim = f'\n              <p class="claim">{rich(p["claim"])}</p>' if p.get('claim') else ''
    rel = lambda h: ' rel="noopener"' if h.startswith('http') else ''
    lk = ''.join(f'\n                <li><a href="{h}"{rel(h)}>{label(t)}<small>{where(h)}</small></a></li>' for h, t in links(p))
    lk = f'<ul class="tp-sheet-links">{lk}\n              </ul>' if lk else '<p class="links">No public copy online</p>'
    return f'''            <article class="paper tp-sheet-item" id="{pid}">
              <h3>{esc(p['title'])}</h3>
              <p class="by">{byline(p)}</p>
              <p class="sum">{rich(p['summary'])}</p>{claim}
              <dl class="spec tp-sheet-spec">
                <dt>Venue</dt><dd>{esc(p['venue'])}</dd>
                <dt>Year</dt><dd>{p['year']}</dd>
                <dt>Status</dt><dd>{status}</dd>
              </dl>
              {lk}
            </article>'''


# the works that are not papers or preprints, by kind: (one, many)
KINDS = {'talk': ('a talk', 'talks'),
         'contribution': ('a doctoral school contribution', 'doctoral school contributions'),
         'software': ('a software package', 'software packages'), 'thesis': ('a thesis', 'theses')}
# the JSON-LD type of each kind; a paper or preprint is a ScholarlyArticle
TYPES = {'thesis': 'Thesis', 'talk': 'CreativeWork',
         'contribution': 'ScholarlyArticle', 'software': 'SoftwareSourceCode'}


def counted(data):
    return [p for p in data['papers'] if not p.get('kind')]


def others(ps):
    """The works in ps that are not papers, in KINDS order: ['two talks', 'a thesis']."""
    out = []
    for k, (one, many) in KINDS.items():
        m = len([p for p in ps if p.get('kind') == k])
        if m:
            out.append(one if m == 1 else f'{WORDS[m]} {many}')
    return out


def tally(ps):
    """An area's count, as its tag: 3 papers, or 2 papers, a talk and a thesis."""
    n = len([p for p in ps if not p.get('kind')])
    t = [f"{n} paper{'' if n == 1 else 's'}"] + others(ps)
    return t[0] if len(t) == 1 else ', '.join(t[:-1]) + ' and ' + t[-1]


def count_note(data):
    listed = len(counted(data))
    if listed != data['total']:
        raise SystemExit(f"papers.json: {listed} papers listed, total says {data['total']}")
    rest = others(data['papers'])
    rest = ', '.join(rest[:-1]) + ' and ' + rest[-1]
    return f'''        <p class="tp-hero-note note">All {data['total']} papers and preprints, grouped by area, with {esc(rest)}. This is every entry on the <a class="tp-link" href="https://scholar.google.com/citations?user=_ivaRgIAAAAJ" rel="noopener">Google Scholar</a> profile.</p>'''


def research_list(data):
    """One pane per area, the rail, and one sheet per area holding every paper in it."""
    panes, rail, sheets = [], [], []
    for i, area in enumerate(data['areas']):
        aid, title = area['id'], esc(area['title'])
        ps = [p for p in data['papers'] if p['area'] == area['id']]
        fig, tag = FIGS[area['motif']], tally(ps)
        panes.append(f'''    <article class="tp-pane{PLACES[i % len(PLACES)]}" id="pane-{aid}" aria-labelledby="pane-{aid}-t">
      <div class="tp-pane-viz"><canvas data-fig="{fig}" aria-hidden="true"></canvas></div>
      <div class="tp-pane-in tp-wrap">
        <div class="tp-pane-text">
          <p class="tp-pane-tag">{tag}</p>
          <h2 class="tp-pane-name" id="pane-{aid}-t">{title}</h2>
          <p class="tp-pane-line">{esc(area['blurb'].rstrip('.'))}</p>
          <a class="tp-pane-open" href="#area-{aid}" aria-haspopup="dialog" aria-label="Open {title}">Open<i aria-hidden="true"></i></a>
        </div>
      </div>
    </article>''')
        rail.append(f'    <a href="#pane-{aid}"><span>{title}</span></a>')
        items = '\n'.join(entry(p) for p in ps)
        sheets.append(f'''  <dialog class="tp-sheet" id="area-{aid}" aria-labelledby="area-{aid}-t">
    <div class="tp-sheet-bar"><span class="tp-sheet-tag">{tag}</span><button class="tp-sheet-close" type="button" aria-label="Close">Close <kbd>Esc</kbd></button></div>
    <div class="tp-sheet-in tp-wrap">
      <div class="tp-sheet-media"><canvas data-fig="{fig}" aria-hidden="true"></canvas></div>
      <div class="tp-sheet-body">
        <figure class="motif" aria-hidden="true">{motif(area['motif'])}</figure>
        <h2 class="area-title" id="area-{aid}-t">{title}</h2>
        <p class="why">{esc(area['why'])}</p>
        <p class="blurb tp-sheet-sub">{esc(area['blurb'])}</p>
{items}
      </div>
    </div>
  </dialog>''')
    return (f'  <section id="areas" class="tp-panes" aria-label="Research areas">\n' + '\n\n'.join(panes) + '\n  </section>\n\n'
            + '  <nav class="tp-rail" aria-label="Panes">\n' + '\n'.join(rail) + '\n  </nav>\n\n' + '\n\n'.join(sheets))


def selected_list(data):
    items = []
    for p in data['papers']:
        if not p.get('selected'):
            continue
        meta = f"{esc(p['venue'])}, {p['year']}"
        if p['status'] == 'To appear':
            meta += ', to appear'
        if p.get('note'):
            meta += ', ' + esc(p['note'].lower())
        meta += ' &middot; ' + role(p)
        ext = links(p)[0]
        items.append(f'''          <li class="pub"><a class="ttl" href="/research.html#{p['id']}">{esc(p['title'])}</a>
            <span class="meta">{meta} &middot; <a class="lk" href="{ext[0]}" rel="noopener">{esc(ext[1])}</a></span></li>''')
    return f'''        <ol class="pubs">
{chr(10).join(items)}
        </ol>
        <p class="more">Selected from {data['total']} papers and preprints across quantum error correction, quantum algorithms, LLM reasoning, quantum topology and number theory. <a class="tp-link" href="/research.html">Summaries on the research page</a>.</p>'''


def jsonld(data):
    items = []
    for i, p in enumerate(data['papers'], 1):
        work = {
            '@type': TYPES.get(p.get('kind'), 'ScholarlyArticle'),
            'headline': p['title'], 'name': p['title'],
            'author': [PERSON if a == ME else {'@type': 'Person', 'name': a} for a in p['authors']],
            'datePublished': p.get('date', str(p['year'])),
            'url': f"{SITE}research.html#{p['id']}",
            'abstract': p['summary'],
        }
        if p.get('kind') == 'thesis':
            work['inSupportOf'] = 'Ph.D. in Mathematics'
            work['sourceOrganization'] = {'@type': 'CollegeOrUniversity', 'name': 'Texas A&M University'}
        else:
            work['isPartOf'] = p['venue']
        if links(p):
            work['sameAs'] = links(p)[0][0]
        items.append({'@type': 'ListItem', 'position': i, 'item': work})
    doc = {
        '@context': 'https://schema.org', '@type': 'CollectionPage',
        'name': 'Research and Publications, Tushar Pandey', 'url': SITE + 'research.html',
        'about': PERSON, 'mainEntity': {'@type': 'ItemList', 'itemListElement': items},
    }
    return '<script type="application/ld+json">\n' + json.dumps(doc, indent=1) + '\n</script>'


def splice(page, name, body):
    pat = re.compile(r'(<!-- ' + name + r':start -->\n).*?([ \t]*<!-- ' + name + r':end -->)', re.S)
    if not pat.search(page):
        raise SystemExit(f'no {name} markers')
    return pat.sub(lambda m: m.group(1) + body + '\n' + m.group(2), page, count=1)


def build():
    data = json.loads(read(ROOT / '_studio' / 'content' / 'papers.json'))
    research = read(ROOT / 'research.html')
    research = splice(research, 'jsonld', jsonld(data))
    research = splice(research, 'count', count_note(data))
    research = splice(research, 'papers', research_list(data))
    cv = splice(read(ROOT / 'cv.html'), 'selected', selected_list(data))
    return {'research.html': research, 'cv.html': cv}


if __name__ == '__main__':
    for page, html in build().items():
        io.open(ROOT / page, 'w', encoding='utf-8', newline='\n').write(html)
        print(f'wrote {page}')
