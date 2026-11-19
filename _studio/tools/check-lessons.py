"""Each lesson page must carry its title, intro, step captions, narrative and
course navigation in the raw HTML, with no script run. Every page of the course
order in qec-in-practice/data/course.json exists with its canonical, title,
description, h1, cite line and a link back to the course; the course index
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
            'back to the course': '<a href="/qec-in-practice/">&larr; Back to the course</a>',
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

hub = read(QEC / 'index.html')
cards = re.findall(r'<a class="lcard" href="([^"]*)">(.*?)</a></li>', hub, re.S)
if [h for h, _ in cards] != pages:
    fail.append(f'index.html: the cards link to {[h for h, _ in cards]}, not the course order {pages}')
fail += [f'index.html: no picture on the card for {h}' for h, body in cards if not re.search(r'<figure[^>]*>\s*<svg', body)]
fail += [f'index.html: no card picture for lesson {n}' for n in lessons if f'<!-- thumb {n} --><figure' not in hub]
if f'T. Pandey, Quantum Error Correction in Practice (2026), {SITE}' not in hub:
    fail.append('index.html: no "How to cite" line for the course')
sitemap = read(QEC.parent / 'sitemap.xml')
fail += [f'sitemap.xml: no {u}' for u in [SITE] + [e['url'] for e in order] if f'<loc>{u}</loc>' not in sitemap]
for f in [QEC / 'index.html', *QEC.glob('lesson-*.html'), *QEC.glob('js/*.js'), QEC.parent / 'sitemap.xml']:
    if re.search(r'lesson\.html\?n=', read(f)):
        fail.append(f'{f.name}: still links to lesson.html?n=')
print('\n'.join(fail) or 'lessons ok')
sys.exit(1 if fail else 0)
