"""Write qec-in-practice/lesson-1.html .. lesson-4.html from lesson-template.html,
and the static card pictures between the <!-- thumb n --> markers of
qec-in-practice/index.html.

Titles and intros come from qec-in-practice/data/lessons.json, the step
captions from each lesson's own data file, so a crawler that runs no script
still reads the lesson.

    python _studio/tools/build-lessons.py
"""
import io, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lesson_text import state_html, plain

QEC = HERE.parents[1] / 'qec-in-practice'
read = lambda p: io.open(p, encoding='utf-8').read()
template = read(HERE / 'lesson-template.html')
lessons = json.loads(read(QEC / 'data' / 'lessons.json'))
last = max(map(int, lessons))

# The geometry of qec-in-practice/js/patch.js, drawn once as a still.
X_STABS = [[0, 1, 3, 4], [4, 5, 7, 8], [2, 5], [3, 6]]
Z_STABS = [[1, 2, 4, 5], [3, 4, 6, 7], [0, 1], [7, 8]]
SHAPE = {'2,5': 'right', '3,6': 'left', '0,1': 'top', '7,8': 'bottom'}
S, R, M = 60, 30, 48
num = lambda v: f'{v:g}'

# lesson: (time slice of the checks, gate layer drawn, inject variant, caption)
THUMB = {
    1: (None, None, 'X4', 'An X error on q4 fires two Z checks'),
    2: (4, 3, None, 'Nine CNOTs, A to B, make a Bell pair'),
    3: (3, None, None, 'All checks hold, neither logical does'),
    4: (8, 7, None, 'Logical CNOT A to B, before the readout'),
}


def outline(q, x0, y0):
    p = lambda i: (x0 + S * (i % 3), y0 + S * (i // 3))
    x, y = p(q[0])
    if len(q) == 4:
        return f'M{num(x)},{num(y)}h{S}v{S}h{-S}Z'
    bx, by = p(q[1])
    side = SHAPE[','.join(map(str, q))]
    sweep = 1 if side in ('top', 'right') else 0
    return f'M{num(x)},{num(y)}A{R},{R} 0 0 {sweep} {num(bx)},{num(by)}Z'


def thumb(n, data):
    t, layer, variant, caption = THUMB[n]
    src = data['inject_variants'][variant] if variant else data
    ops = src['ops']
    inj = next((o for o in ops if o.get('role') == 'inject'), None)
    if inj:
        t = inj['t'] + 1
    checks, logicals = src['checks'][t], src['logicals'][t]
    gates = [o for o in ops if o['t'] == layer] if layer is not None else []
    blocks = data['blocks']
    W = (max(b['x0'] for b in blocks) + 2) * S + 2 * M
    H = 2 * S + 2 * M
    out = [f'<svg viewBox="0 0 {num(W)} {num(H)}" aria-hidden="true" focusable="false">']
    if gates:
        out.append(f'<defs><marker id="th-ah-{n}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" class="th-head"/></marker></defs>')
    pos = {}
    for bi, b in enumerate(blocks):
        x0, y0 = M + b['x0'] * S, M + b['y0'] * S
        for i, qid in enumerate(b['data']):
            pos[qid] = (x0 + S * (i % 3), y0 + S * (i // 3))
        for typ, stabs in (('Z', Z_STABS), ('X', X_STABS)):
            for k, q in enumerate(stabs):
                v = checks[bi][typ][k]
                state = {1: typ.lower(), -1: 'fire', 0: 'und'}[v]
                out.append(f'<path d="{outline(q, x0, y0)}" class="th-f th-{state} th-s{typ.lower()}"/>')
        for typ, x1, y1, x2, y2 in (('X', x0, y0 - 6, x0 + 2 * S, y0 - 6), ('Z', x0 - 6, y0, x0 - 6, y0 + 2 * S)):
            v = logicals[bi][typ]
            cls = {1: f'logline-on {typ.lower()}', -1: 'logline-bad', 0: 'logline'}[v]
            out.append(f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" class="{cls}"/>')
    for qid, (x, y) in pos.items():
        hit = ' hit' if inj and qid == inj['q'][0] else ''
        out.append(f'<circle cx="{num(x)}" cy="{num(y)}" r="12" class="qdot{hit}"/>')
    for o in gates:
        if o['gate'] != 'cx':
            continue
        (ax, ay), (bx, by) = pos[o['q'][0]], pos[o['q'][1]]
        dx, dy = bx - ax, by - ay
        L = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / L, dy / L
        sx, sy, ex, ey = ax + ux * 16, ay + uy * 16, bx - ux * 15, by - uy * 15
        bend = min(0.18 * L, 40)
        cx, cy = (sx + ex) / 2 + uy * bend, (sy + ey) / 2 - ux * bend
        out.append(f'<path d="M{sx:.0f},{sy:.0f} Q{cx:.0f},{cy:.0f} {ex:.0f},{ey:.0f}" class="cxarrow" marker-end="url(#th-ah-{n})"/>')
    if inj:
        x, y = pos[inj['q'][0]]
        out.append(f'<circle cx="{num(x)}" cy="{num(y)}" r="19" class="th-err"/>')
    out.append('</svg>')
    svg = ''.join(out)
    return f'<figure class="tp-plate thumb">{svg}<figcaption>{caption}</figcaption></figure>'


hub_path = QEC / 'index.html'
hub = read(hub_path)
for key, info in lessons.items():
    n = int(key)
    data = json.loads(read(QEC / 'data' / f'lesson{n}.json'))
    phase = {t: p['name'] for p in data['phases'] for t in range(p['t0'], p['t1'] + 1)}
    steps = '\n'.join(
        f'      <li><b>{state_html(phase[int(t)])}.</b> {state_html(text)}</li>'
        for t, text in sorted(data['layer_text'].items(), key=lambda kv: int(kv[0])))
    nav = ''
    if n > 1:
        nav += f' <a id="prev" href="lesson-{n - 1}.html">&larr; Lesson {n - 1}</a>'
    if n < last:
        nav += f' <a id="next" href="lesson-{n + 1}.html">Lesson {n + 1} &rarr;</a>'
    page = template
    for token, value in {
        '{{n}}': str(n), '{{title}}': state_html(info['title']), '{{plaintitle}}': plain(info['title']),
        '{{intro}}': state_html(info['intro']),
        '{{description}}': plain(info['intro'].replace('_L', '')), '{{nav}}': nav, '{{steps}}': steps,
    }.items():
        page = page.replace(token, value)
    io.open(QEC / f'lesson-{n}.html', 'w', encoding='utf-8', newline='\n').write(page)
    print(f'wrote lesson-{n}.html')
    hub, found = re.subn(rf'(<!-- thumb {n} -->).*?(<!-- /thumb -->)',
                         lambda m: m.group(1) + thumb(n, data) + m.group(2), hub, flags=re.S)
    if not found:
        sys.exit(f'index.html: no <!-- thumb {n} --> marker')
io.open(hub_path, 'w', encoding='utf-8', newline='\n').write(hub)
print('wrote the card pictures in index.html')
