"""Each lesson page must carry its title, intro, step captions, narrative and
course navigation in the raw HTML, with no script run. Every page of the course
order in qec-in-practice/data/course.json exists with its canonical, title,
description, h1, cite line and a link back to the course, and every page but the
last ends with the shared secnav endnav row (40px tap height); the course index
lists them all in order with a picture each, and the sitemap lists them.
Exits non-zero on failure.

    python _studio/tools/check-lessons.py
"""
import io, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lesson_text import state_html, plain, course, SITE

QEC = pathlib.Path(__file__).resolve().parents[2] / 'qec-in-practice'
read = lambda p: io.open(p, encoding='utf-8').read()
fail = []
BACK = '<a href="/qec-in-practice/">&larr;&nbsp;<span class="nav-long">Back to the course</span><span class="nav-short">Course</span></a>'
lessons = json.loads(read(QEC / 'data' / 'lessons.json'))
order = course(QEC)
pages = [e['page'] for e in order]
if sorted(e['lesson'] for e in order if 'lesson' in e) != [1, 2, 3, 4] or len(set(pages)) != len(pages):
    fail.append('course.json: lessons 1 to 4 must each appear once, and no page twice')


def main_of(html):
    m = re.search(r'<main[\s>].*?</main>', html, re.S)
    return m.group(0) if m else ''


for i, e in enumerate(order):
    page = QEC / e['page']
    if not page.exists():
        fail.append(f'{e["page"]}: missing'); continue
    html = read(page)
    main = main_of(html)
    cite = re.search(r'Cite this lesson(.*?)</p>', main, re.S)
    want = {
        'canonical': (f'<link rel="canonical" href="{e["url"]}">' in html),
        'title tag': re.search(r'<title>\s*[^<\s][^<]*</title>', html) is not None,
        'description': re.search(r'<meta name="description" content="[^"]+">', html) is not None,
        'h1': re.search(r'<h1[\s>]', main) is not None,
        'cite line with its own URL': cite is not None and e['url'] in cite.group(1),
        'link back to /qec-in-practice/': 'href="/qec-in-practice/"' in main,
    }
    fail += [f'{e["page"]}: no {k}' for k, ok in want.items() if not ok]
    if i < len(order) - 1 and '<nav class="secnav endnav" aria-label="Course, end of lesson">' not in main:
        fail.append(f'{e["page"]}: no end-of-lesson <nav class="secnav endnav">')
    if 'lesson' not in e:
        continue
    n = str(e['lesson'])
    info = lessons[n]
    steps = json.loads(read(QEC / 'data' / f'lesson{n}.json'))['layer_text']
    want = {'title tag': f'<title>{e["title"]}', 'h1': f'<h1 id="lesson-title">{e["title"]}</h1>',
            'intro': state_html(info['intro']),
            'canonical': f'<link rel="canonical" href="https://pandey-tushar.com/qec-in-practice/lesson-{n}.html">',
            'lesson number': f'data-lesson="{n}"',
            'description': '<meta name="description" content="' + plain(info['intro'].replace('_L', '')) + '">',
            'cite': f'<p class="cite"><span class="tp-lbl">Cite this lesson</span> T. Pandey, "{state_html(e["title"])}", '
                    f'Quantum Error Correction in Practice (2026), {e["url"]}</p>',
            'back to the course': BACK,
            'narrative head 1': '<h2>What this lesson shows</h2>', 'narrative head 2': '<h2>Things to try</h2>'}
    want.update({f'step {k}': state_html(v) for k, v in steps.items()})
    want.update({f'narrative paragraph {k + 1}': f'<p>{state_html(v)}</p>' for k, v in enumerate(info.get('shows', []))})
    want.update({f'thing to try {k + 1}': f'<li>{state_html(v)}</li>' for k, v in enumerate(info.get('try', []))})
    if i > 0:
        want['previous link'] = f'<a id="prev" href="{order[i - 1]["page"]}">'
    if i < len(order) - 1:
        want['next link'] = f'<a id="next" href="{order[i + 1]["page"]}">'
    fail += [f'{e["page"]}: no {k}' for k, v in want.items() if v not in html]
    words = len(' '.join(info.get('shows', []) + info.get('try', [])).split())
    if not 120 <= words <= 220:
        fail.append(f'{e["page"]}: narrative is {words} words, want 120 to 220')
    if any(ord(c) < 32 and c not in '\n\t' for c in html):
        fail.append(f'{e["page"]}: control character in the page')

# Every page: progress, a plain-words box right under the title (on the essay pages, at the top of the rail), a glossary link, and full titles in the
# previous/next links at the top (short on phones) and at the bottom.
for i, e in enumerate(order):
    page = QEC / e['page']
    if not page.exists():
        continue
    main = main_of(read(page))
    step = f'<p class="tp-lbl step-of">Step {i + 1} of {len(order)}</p>'
    h1 = re.search(r'<h1[\s>].*?</h1>\s*', main, re.S)
    if step not in main:
        fail.append(f'{e["page"]}: no "{step}"')
    # on the essay pages the box opens the rail, which sits under the title below 70em
    if not h1 or not re.match(r'(<div class="course-rail">\s*)?<aside class="plain" aria-label="In plain words">', main[h1.end():]):
        fail.append(f'{e["page"]}: no "In plain words" box right under the h1')
    top = re.search(r'<nav class="secnav" aria-label="Course">(.*?)</nav>', main, re.S)
    top = top.group(1) if top else ''
    end = re.search(r'<nav class="secnav endnav" aria-label="Course, end of lesson">(.*?)</nav>', main, re.S)
    end = end.group(1) if end else ''
    if '<a href="glossary.html">Glossary</a>' not in top:
        fail.append(f'{e["page"]}: no Glossary link in the course nav')
    for j, rel in ((i - 1, 'prev'), (i + 1, 'next')):
        if not 0 <= j < len(order):
            continue
        o = order[j]
        t = state_html(o['title'])
        short, full = (f'&larr; Previous<span class="nav-long">: {t}</span>', f'&larr; Previous: {t}') if rel == 'prev'             else (f'Next<span class="nav-long">: {t}</span>&nbsp;&rarr;', f'Next: {t} &rarr;')
        if f'<a id="{rel}" href="{o["page"]}">{short}</a>' not in top:
            fail.append(f'{e["page"]}: top {rel} link is not "{short}"')
        if f'<a href="{o["page"]}">{full}</a>' not in end:
            fail.append(f'{e["page"]}: end {rel} link is not "{full}"')
    if 'lesson' in e:
        n = str(e['lesson'])
        note = lessons[n].get('results_note', [])
        if not note or '<h3>How to read this table</h3>' not in main:
            fail.append(f'{e["page"]}: no "How to read this table" note')
        fail += [f'{e["page"]}: no results note paragraph {k + 1}' for k, v in enumerate(note) if f'<p>{state_html(v)}</p>' not in main]
        if '<p class="plain-text">' + state_html(lessons[n].get('plain', '')) + '</p>' not in main or not lessons[n].get('plain'):
            fail.append(f'{e["page"]}: plain-words text is not lessons.json "plain"')

last = read(QEC / order[-1]['page'])
for href in ('/tools/bb-codes.html', '/notes/crossing-is-not-the-threshold.html', '/research.html'):
    if not re.search(r'<section class="course-end"[^>]*>.*?href="' + re.escape(href) + '"', last, re.S):
        fail.append(f'{order[-1]["page"]}: the end-of-course block does not link {href}')

# The glossary: the course shell, one entry per term, linked from the index.
GLOSSARY = ['qubit', 'bit-flip', 'phase-flip', 'check', 'syndrome', 'fired', 'distance', 'logical-qubit', 'patch',
            'decoder', 'union-find', 'matching', 'threshold', 'lambda', 'bell-pair', 't-state', 'teleportation',
            'lattice-surgery', 'pauli-frame']
gpath = QEC / 'glossary.html'
if not gpath.exists():
    fail.append('glossary.html: missing')
else:
    g = read(gpath)
    gm = main_of(g)
    want = {'canonical': f'<link rel="canonical" href="{SITE}glossary.html">' in g,
            'h1': len(re.findall(r'<h1[\s>]', g)) == 1,
            'description': re.search(r'<meta name="description" content="[^"]+">', g) is not None,
            'link back': '<a href="/qec-in-practice/">' in gm,
            'theme-color': '<meta name="theme-color" content="#0d1320">' in g}
    fail += [f'glossary.html: no {k}' for k, ok in want.items() if not ok]
    for t in GLOSSARY:
        entry = re.search(rf'<dt id="{t}">.*?</dt>\s*<dd>\s*<p class="g-plain">[^<].*?</p>\s*<p class="g-tech">[^<].*?</p>\s*</dd>', gm, re.S)
        if not entry:
            fail.append(f'glossary.html: no entry {t} with a plain and a technical sentence')

# Statements the course got wrong once and must not make again.
WRONG = ['Lessons 3 and 4 also show stored results', 'from the decoding lesson on, a union-find decoder',
         'used throughout this course is a union-find', 'lit checks', 'over nine qubits and eight checks',
         'stand-in', 'not from hardware', '&#8203;<sub>L', 'The patch below can be made larger']
for f in [*QEC.glob('*.html'), QEC / 'data' / 'lessons.json', QEC / 'data' / 'course.json', *QEC.glob('js/*.js')]:
    text = read(f)
    fail += [f'{f.name}: still says "{w}"' for w in WRONG if w in text]
if not re.search(r'Wang, Harrington and Preskill \(2003\)[^.]*10\.3%[^.]*2\.9%', read(QEC / 'threshold.html')):
    fail.append('threshold.html: 10.3% and 2.9% are not attributed to Wang, Harrington and Preskill (2003)')

if not re.search(r'^\.secnav a \{[^}]*min-height: 40px', read(QEC / 'css' / 'site.css'), re.M):
    fail.append('css/site.css: .secnav a has no min-height: 40px tap area')
hub = read(QEC / 'index.html')
cards = re.findall(r'<a class="lcard" href="([^"]*)">(.*?)</a></li>', hub, re.S)
if [h for h, _ in cards] != pages:
    fail.append(f'index.html: the cards link to {[h for h, _ in cards]}, not the course order {pages}')
fail += [f'index.html: no picture on the card for {h}' for h, body in cards if not re.search(r'<figure[^>]*>\s*<svg', body)]
fail += [f'index.html: no card picture for lesson {n}' for n in lessons if f'<!-- thumb {n} --><figure' not in hub]
for need in ('href="glossary.html"', 'href="/why-error-correction.html"', 'What is this, and why does it matter?'):
    if need not in hub:
        fail.append(f'index.html: no {need}')
if f'T. Pandey, Quantum Error Correction in Practice (2026), {SITE}' not in hub:
    fail.append('index.html: no "How to cite" line for the course')
sitemap = read(QEC.parent / 'sitemap.xml')
fail += [f'sitemap.xml: no {u}' for u in [SITE] + [e['url'] for e in order] if f'<loc>{u}</loc>' not in sitemap]
for f in [QEC / 'index.html', *QEC.glob('lesson-*.html'), *QEC.glob('js/*.js'), QEC.parent / 'sitemap.xml']:
    if re.search(r'lesson\.html\?n=', read(f)):
        fail.append(f'{f.name}: still links to lesson.html?n=')
print('\n'.join(fail) or 'lessons ok')
sys.exit(1 if fail else 0)
