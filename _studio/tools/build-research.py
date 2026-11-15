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


def roman(n):
    return ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII'][n - 1]


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
    return out


def byline(p):
    names = [f'<b class="me">{esc(a)}</b>' if a == ME else esc(a) for a in p['authors']]
    if len(names) == 1 and p.get('kind') != 'thesis':
        return names[0] + ', sole author'
    return ', '.join(names)


def role(p):
    a = p['authors']
    if len(a) == 1:
        return 'thesis' if p.get('kind') == 'thesis' else 'sole author'
    if len(a) == 2:
        return 'with ' + esc(a[1] if a[0] == ME else a[0])
    return f'{"first" if a[0] == ME else "author " + str(a.index(ME) + 1)} of {len(a)} authors'


def entry(p, n):
    pid = p['id']
    status = esc(p['status']) + (f" &middot; {esc(p['note'])}" if p.get('note') else '')
    claim = f'\n          <p class="claim">{rich(p["claim"])}</p>' if p.get('claim') else ''
    lk = ''.join(f'<a class="tp-link" href="{h}" rel="noopener">{esc(t)}</a>' for h, t in links(p))
    lk = lk or '<span>No public copy online</span>'
    return f'''      <li>
        <article class="paper" id="{pid}">
          <a class="no tp-plate" href="#{pid}" aria-label="Link to entry {n}">{n:02d}</a>
          <div class="body">
            <h2>{esc(p['title'])}</h2>
            <p class="by">{byline(p)}</p>
            <p class="sum">{rich(p['summary'])}</p>{claim}
          </div>
          <dl class="spec">
            <dt class="tp-lbl">Venue</dt><dd>{esc(p['venue'])}</dd>
            <dt class="tp-lbl">Year</dt><dd>{p['year']}</dd>
            <dt class="tp-lbl">Status</dt><dd>{status}</dd>
          </dl>
          <p class="links">{lk}</p>
        </article>
      </li>'''


def counted(data):
    return [p for p in data['papers'] if p.get('kind') != 'thesis']


def research_list(data):
    listed = len(counted(data))
    rest = data['total'] - listed
    out = [f'''  <p class="note"><i aria-hidden="true">&#10022;</i><span>Listed here: {listed} of Tushar Pandey&rsquo;s {data['total']} papers and preprints, grouped by area, and his doctoral thesis. The other {WORDS[rest]} are earlier arXiv preprints, from 2021 to 2023, listed on <a class="tp-link" href="https://scholar.google.com/citations?user=_ivaRgIAAAAJ" rel="noopener">Google Scholar</a>.</span></p>''']
    n = 0
    for i, area in enumerate(data['areas'], 1):
        ps = [p for p in data['papers'] if p['area'] == area['id']]
        items = []
        for p in ps:
            n += 1
            items.append(entry(p, n))
        out.append(f'''  <section class="area" aria-labelledby="area-{area['id']}">
    <div class="area-head">
      <figure class="motif tp-plate" aria-hidden="true">{motif(area['motif'])}</figure>
      <div>
        <p class="tp-lbl">Area {roman(i)} &middot; {len(ps)} {'entry' if len(ps) == 1 else 'entries'}</p>
        <p class="area-title" id="area-{area['id']}">{esc(area['title'])}</p>
        <p class="blurb">{esc(area['blurb'])}</p>
      </div>
    </div>
    <ol class="papers">
{chr(10).join(items)}
    </ol>
  </section>''')
    return '\n'.join(out)


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
        <p class="more">Selected from {data['total']} papers and preprints across quantum error correction, quantum algorithms, LLM reasoning, quantum topology and number theory. <a class="tp-link" href="/research.html">The full list, with summaries</a>.</p>'''


def jsonld(data):
    items = []
    for i, p in enumerate(data['papers'], 1):
        work = {
            '@type': 'Thesis' if p.get('kind') == 'thesis' else 'ScholarlyArticle',
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
    research = splice(research, 'papers', research_list(data))
    cv = splice(read(ROOT / 'cv.html'), 'selected', selected_list(data))
    return {'research.html': research, 'cv.html': cv}


if __name__ == '__main__':
    for page, html in build().items():
        io.open(ROOT / page, 'w', encoding='utf-8', newline='\n').write(html)
        print(f'wrote {page}')
