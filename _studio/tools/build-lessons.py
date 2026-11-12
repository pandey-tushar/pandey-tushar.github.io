"""Write qec-in-practice/lesson-1.html .. lesson-4.html from lesson-template.html.

Titles and intros come from qec-in-practice/data/lessons.json, the step
captions from each lesson's own data file, so a crawler that runs no script
still reads the lesson.

    python _studio/tools/build-lessons.py
"""
import io, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lesson_text import state_html, plain

QEC = HERE.parents[1] / 'qec-in-practice'
read = lambda p: io.open(p, encoding='utf-8').read()
template = read(HERE / 'lesson-template.html')
lessons = json.loads(read(QEC / 'data' / 'lessons.json'))
last = max(map(int, lessons))

for key, info in lessons.items():
    n = int(key)
    data = json.loads(read(QEC / 'data' / f'lesson{n}.json'))
    phase = {t: p['name'] for p in data['phases'] for t in range(p['t0'], p['t1'] + 1)}
    steps = '\n'.join(
        f'      <li><b>{state_html(phase[int(t)])}.</b> {state_html(text)}</li>'
        for t, text in sorted(data['layer_text'].items(), key=lambda kv: int(kv[0])))
    nav = ''
    if n > 1:
        nav += f' <a id="prev" href="lesson-{n - 1}.html">&larr; Previous</a>'
    if n < last:
        nav += f' <a id="next" href="lesson-{n + 1}.html">Next &rarr;</a>'
    page = template
    for token, value in {
        '{{n}}': str(n), '{{title}}': state_html(info['title']), '{{intro}}': state_html(info['intro']),
        '{{description}}': plain(info['intro'].replace('_L', '')), '{{nav}}': nav, '{{steps}}': steps,
    }.items():
        page = page.replace(token, value)
    io.open(QEC / f'lesson-{n}.html', 'w', encoding='utf-8', newline='\n').write(page)
    print(f'wrote lesson-{n}.html')
