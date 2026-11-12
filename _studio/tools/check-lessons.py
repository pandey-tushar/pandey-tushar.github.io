"""Each lesson page must carry its title, intro and step captions in the raw
HTML, with no script run. Exits non-zero on the first failure.

    python _studio/tools/check-lessons.py
"""
import io, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lesson_text import state_html, plain

QEC = pathlib.Path(__file__).resolve().parents[2] / 'qec-in-practice'
read = lambda p: io.open(p, encoding='utf-8').read()
fail = []
lessons = json.loads(read(QEC / 'data' / 'lessons.json'))
for n in ('1', '2', '3', '4'):
    page = QEC / f'lesson-{n}.html'
    if not page.exists():
        fail.append(f'{page.name}: missing'); continue
    html = read(page)
    title = f"Lesson {n}: {lessons[n]['title']}"
    steps = json.loads(read(QEC / 'data' / f'lesson{n}.json'))['layer_text']
    want = {'title tag': f'<title>{title}', 'h1': f'<h1 id="lesson-title">{title}</h1>',
            'intro': state_html(lessons[n]['intro']),
            'canonical': f'<link rel="canonical" href="https://pandey-tushar.com/qec-in-practice/lesson-{n}.html">',
            'lesson number': f'data-lesson="{n}"',
            'description': '<meta name="description" content="' + plain(lessons[n]['intro'].replace('_L', '')) + '">'}
    want.update({f'step {k}': state_html(v) for k, v in steps.items()})
    fail += [f'{page.name}: no {k}' for k, v in want.items() if v not in html]
    if any(ord(c) < 32 and c not in '\n\t' for c in html):
        fail.append(f'{page.name}: control character in the page')
for f in [QEC / 'index.html', *QEC.glob('lesson-*.html'), *QEC.glob('js/*.js'), QEC.parent / 'sitemap.xml']:
    if re.search(r'lesson\.html\?n=', read(f)):
        fail.append(f'{f.name}: still links to lesson.html?n=')
print('\n'.join(fail) or 'lessons ok')
sys.exit(1 if fail else 0)
