"""Write qec-in-practice/lesson-1.html .. lesson-4.html from lesson-template.html,
and the course list between the <!-- course --> markers of
qec-in-practice/index.html, with a static picture per card (between
<!-- thumb n --> and <!-- /thumb -->).

The course order, the card texts and the titles of the hand-written pages come
from qec-in-practice/data/course.json; titles, intros and the narrative of
lessons 1 to 4 from qec-in-practice/data/lessons.json; the step captions from
each lesson's own data file, so a crawler that runs no script still reads the
lesson.

    python _studio/tools/build-lessons.py
"""
import io, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lesson_text import state_html, plain, course, phase_label

QEC = HERE.parents[1] / 'qec-in-practice'
read = lambda p: io.open(p, encoding='utf-8').read()
template = read(HERE / 'lesson-template.html')
lessons = json.loads(read(QEC / 'data' / 'lessons.json'))
order = course(QEC)

# The geometry of qec-in-practice/js/patch.js, drawn once as a still.
X_STABS = [[0, 1, 3, 4], [4, 5, 7, 8], [2, 5], [3, 6]]
Z_STABS = [[1, 2, 4, 5], [3, 4, 6, 7], [0, 1], [7, 8]]
SHAPE = {'2,5': 'right', '3,6': 'left', '0,1': 'top', '7,8': 'bottom'}
S, R, M = 60, 30, 48
TIGHT = {4: (3.2, 36)}  # lesson: (patch spacing in units of S, side margin) for the card picture
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
    # three patches at the lesson's own spacing would draw each one a third smaller than on the other cards,
    # so the lesson 4 still sets them closer, with a narrower side margin
    step, mx = TIGHT.get(n, (None, M))
    blocks = [dict(b, x0=k * step) if step else b for k, b in enumerate(data['blocks'])]
    W = (max(b['x0'] for b in blocks) + 2) * S + 2 * mx
    H = 2 * S + 2 * M
    out = [f'<svg viewBox="0 0 {num(W)} {num(H)}" aria-hidden="true" focusable="false">']
    if gates:
        out.append(f'<defs><marker id="th-ah-{n}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" class="th-head"/></marker></defs>')
    pos = {}
    for bi, b in enumerate(blocks):
        x0, y0 = mx + b['x0'] * S, M + b['y0'] * S
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


# Pictures for the hand-written pages, in the same inks as the lesson thumbs.

def face(pts, side=None):
    """A check drawn as in patch.js: a square on four qubits, a half-disc outside the patch on two."""
    if len(pts) == 4:
        x, y = min(pts)
        return f'M{num(x)},{num(y)}h{S}v{S}h{-S}Z'
    (ax, ay), (bx, by) = sorted(pts)
    sweep = 1 if side in ('top', 'right') else 0
    return f'M{num(ax)},{num(ay)}A{R},{R} 0 0 {sweep} {num(bx)},{num(by)}Z'


def surface(d):
    """The rotated surface code of qec-in-practice/js/qec/codes.js (surfaceCode): qubit i at
    column i % d, row i // d; plaquette (r, c) is X when r + c is even. Yields (type, qubits, side)."""
    def add(r, c, side=None):
        q = [i * d + j for i, j in ((r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1)) if 0 <= i < d and 0 <= j < d]
        return ('X' if (r + c) % 2 == 0 else 'Z', q, side)
    out = [add(r, c) for r in range(d - 1) for c in range(d - 1)]
    out += [add(r, d - 1, 'right') for r in range(d - 1) if (r + d - 1) % 2 == 0]
    out += [add(r, -1, 'left') for r in range(d - 1) if (r - 1) % 2 == 0]
    out += [add(-1, c, 'top') for c in range(d - 1) if c % 2 == 0]
    out += [add(d - 1, c, 'bottom') for c in range(d - 1) if (d - 1 + c) % 2 == 1]
    return out


def svg(w, h, body):
    return f'<svg viewBox="0 0 {num(w)} {num(h)}" aria-hidden="true" focusable="false">{"".join(body)}</svg>'


def repetition():
    """d = 5: Z Z checks between neighbours (codes.js repetitionCode); an X error on q2 fires the two beside it."""
    d, hit, h = 5, 2, 15
    x = lambda i: M + S * i
    out = [f'<line x1="{num(x(0))}" y1="{num(M)}" x2="{num(x(d - 1))}" y2="{num(M)}" class="th-rep"/>']
    for i in range(1, d):
        # a diamond between neighbours, as qec-draw.js draws the checks on the page
        state = 'fire' if hit in (i - 1, i) else 'z'
        cx = x(i) - S / 2
        out.append(f'<path d="M{num(cx)},{num(M - h)}L{num(cx + h)},{num(M)}L{num(cx)},{num(M + h)}L{num(cx - h)},{num(M)}Z" class="th-f th-{state} th-sz"/>')
    out += [f'<circle cx="{num(x(i))}" cy="{num(M)}" r="12" class="qdot{" hit" if i == hit else ""}"/>' for i in range(d)]
    out.append(f'<circle cx="{num(x(hit))}" cy="{num(M)}" r="19" class="th-err"/>')
    return svg(2 * M + S * (d - 1), 2 * M, out), 'An X error on q2 fires the two checks beside it'


def cluster():
    """d = 5: X errors on two vertical neighbours fire the two Z checks at the ends of the chain;
    one union-find cluster covers both."""
    d, hits = 5, (7, 12)
    xy = lambda i: (M + S * (i % d), M + S * (i // d))
    out, fired = [], []
    for typ, q, side in surface(d):
        on = typ == 'Z' and sum(h in q for h in hits) % 2 == 1
        if on:
            fired.append(q)
        out.append(f'<path d="{face([xy(i) for i in q], side)}" class="th-f th-{"fire" if on else typ.lower()} th-s{typ.lower()}"/>')
    cx = [sum(xy(i)[0] for i in q) / len(q) for q in fired] + [xy(h)[0] for h in hits]
    cy = [sum(xy(i)[1] for i in q) / len(q) for q in fired] + [xy(h)[1] for h in hits]
    x0, x1, y0, y1 = min(cx) - 24, max(cx) + 24, min(cy) - 24, max(cy) + 24
    out.append(f'<rect x="{num(x0)}" y="{num(y0)}" width="{num(x1 - x0)}" height="{num(y1 - y0)}" rx="24" class="th-cluster"/>')
    out += [f'<circle cx="{num(x)}" cy="{num(y)}" r="12" class="qdot{" hit" if i in hits else ""}"/>'
            for i, (x, y) in enumerate(map(xy, range(d * d)))]
    out += [f'<circle cx="{num(xy(h)[0])}" cy="{num(xy(h)[1])}" r="19" class="th-err"/>' for h in hits]
    return svg(2 * M + S * (d - 1), 2 * M + S * (d - 1), out), 'Two X errors fire two Z checks; one cluster joins them'


def curves():
    """Logical against physical error rate on log-log axes: p_L = A (p / p_th)^((d+1)/2) is a line
    of slope (d+1)/2, so the lines for d = 3, 5, 7 cross at p_th, the steepest lowest below it."""
    W, H, L, B, T = 336, 216, 40, 180, 24
    px, py = 180, 102
    out = [f'<path d="M{L},{T}V{B}H{W - 16}" class="th-axis"/>',
           f'<line x1="{px}" y1="{T}" x2="{px}" y2="{B}" class="th-tick"/>']
    for d in (3, 5, 7):
        k = (d + 1) / 2 * 0.3
        xa, xb = L + 8, W - 24
        ya, yb = py + k * (px - xa), py - k * (xb - px)
        if ya > B:
            xa, ya = px - (B - py) / k, B
        if yb < T:
            xb, yb = px + (py - T) / k, T
        out.append(f'<line x1="{xa:.0f}" y1="{ya:.0f}" x2="{xb:.0f}" y2="{yb:.0f}" class="th-curve th-d{d}"/>')
    out.append(f'<circle cx="{px}" cy="{py}" r="7" class="th-cross"/>')
    out.append(f'<text x="{L - 8}" y="{T + 14}" class="th-lab" text-anchor="end">p<tspan font-size="0.7em" dy="5">L</tspan></text>')
    out.append(f'<text x="{W - 16}" y="{B + 28}" class="th-lab" text-anchor="end">p</text>')
    return svg(W, H, out), 'Logical against physical error rate: d = 3, 5, 7 cross at the threshold'


def seam():
    """The merged grid of qec-in-practice/js/surgery.js: A in columns 0..2, the seam qubits 18..20
    in column 3, B in columns 4..6; the facing X edges are gone and the seam checks join the patches."""
    col = {**{i: (i % 3, i // 3) for i in range(9)}, **{9 + i: (4 + i % 3, i // 3) for i in range(9)},
           **{18 + r: (3, r) for r in range(3)}}
    xy = lambda i: (M + S * col[i][0], M + S * col[i][1])
    checks = []
    for off in (0, 9):
        for typ, stabs in (('Z', Z_STABS), ('X', X_STABS)):
            for q in stabs:
                if (off, q) not in ((0, [2, 5]), (9, [3, 6])):
                    checks.append((typ, [i + off for i in q], SHAPE.get(','.join(map(str, q)))))
    checks += [('Z', [2, 18], 'top'), ('X', [2, 18, 5, 19], None), ('Z', [5, 19, 8, 20], None),
               ('Z', [18, 9, 19, 12], None), ('X', [19, 12, 20, 15], None), ('Z', [20, 15], 'bottom')]
    out = [f'<path d="{face([xy(i) for i in q], side)}" class="th-f th-{typ.lower()} th-s{typ.lower()}"/>' for typ, q, side in checks]
    out += [f'<circle cx="{num(xy(i)[0])}" cy="{num(xy(i)[1])}" r="12" class="qdot{" seam" if i >= 18 else ""}"/>' for i in col]
    return svg(2 * M + 6 * S, 2 * M + 2 * S, out), 'Merged: three seam qubits and their checks join A and B'


PICTURES = {'repetition': repetition, 'cluster': cluster, 'curves': curves, 'seam': seam}


def figure(art):
    body, caption = art
    return f'<figure class="tp-plate thumb">{body}<figcaption>{caption}</figcaption></figure>'


def link(e, rel):
    """The top nav link: the full title, cut to Previous or Next on a phone (css/site.css .nav-long)."""
    t = state_html(e['title'])
    text = f'&larr; Previous<span class="nav-long">: {t}</span>' if rel == 'prev' else f'Next<span class="nav-long">: {t}</span>&nbsp;&rarr;'
    return f'<a id="{rel}" href="{e["page"]}">{text}</a>'


def endlink(e, rel):
    t = state_html(e['title'])
    return f'<a href="{e["page"]}">' + (f'&larr; Previous: {t}' if rel == 'prev' else f'Next: {t} &rarr;') + '</a>'


# the line under a page's title in its hero: the course and the part the page belongs to, as the course list numbers them
PARTS = list(dict.fromkeys(e['part'] for e in order))
part_line = lambda e: f"Quantum Error Correction in Practice, part {PARTS.index(e['part']) + 1}: {state_html(e['part'])}"

thumbs = {}
for i, e in enumerate(order):
    if 'lesson' not in e:
        thumbs[e['page']] = (e['page'].removesuffix('.html'), figure(PICTURES[e['picture']]()))
        continue
    n = e['lesson']
    info = lessons[str(n)]
    data = json.loads(read(QEC / 'data' / f'lesson{n}.json'))
    thumbs[e['page']] = (str(n), thumb(n, data))
    phase = {t: p['name'] for p in data['phases'] for t in range(p['t0'], p['t1'] + 1)}
    steps = '\n'.join(
        f'      <li><b>{state_html(phase_label(phase[int(t)]))}.</b> {state_html(text)}</li>'
        for t, text in sorted(data['layer_text'].items(), key=lambda kv: int(kv[0])))
    near = ([(order[i - 1], 'prev')] if i > 0 else []) + ([(order[i + 1], 'next')] if i < len(order) - 1 else [])
    page = template
    for token, value in {
        '{{n}}': str(n), '{{title}}': state_html(info['title']), '{{plaintitle}}': plain(info['title']),
        '{{intro}}': state_html(info['intro']),
        '{{description}}': plain(info['intro'].replace('_L', '')), '{{steps}}': steps,
        '{{nav}}': ''.join(' ' + link(o, rel) for o, rel in near),
        '{{endnav}}': ' '.join(endlink(o, rel) for o, rel in near),
        '{{stepof}}': f'Step {i + 1} of {len(order)}', '{{part}}': part_line(e), '{{plain}}': state_html(info['plain']),
        '{{results_note}}': '\n'.join(f'      <p>{state_html(p)}</p>' for p in info['results_note']),
        '{{shows}}': '\n'.join(f'    <p>{state_html(p)}</p>' for p in info['shows']),
        '{{try}}': '\n'.join(f'      <li>{state_html(p)}</li>' for p in info['try']),
    }.items():
        page = page.replace(token, value)
    io.open(QEC / f'lesson-{n}.html', 'w', encoding='utf-8', newline='\n').write(page)
    print(f'wrote lesson-{n}.html')

# The course index: one window-sized pane per page of the course, in order, tagged with its
# part, its card picture's caption as the line, opening into a sheet with the picture, the
# card text and the link (lib/site.css tp-pane, tp-rail, tp-sheet; the figures are TP.live.fig)
FIGS = {'repetition-code.html': 'rep', 'lesson-1.html': 'surface', 'decoding.html': 'toric', 'threshold.html': 'crossing',
        'lesson-2.html': 'circuit', 'lesson-3.html': 'bloch', 'lesson-4.html': 'bell', 'lattice-surgery.html': 'seam'}
PLACES = ['', ' tp-pane-mid', ' tp-pane-end', ' tp-pane-top']
panes, rail, sheets = [], [], []
for k, e in enumerate(order, 1):
    key, fig = thumbs[e['page']]
    sid, live = e['page'].removesuffix('.html'), FIGS[e['page']]
    cap = re.search(r'<figcaption>(.*?)</figcaption>', fig).group(1)
    # the step is the place in the course; a numbered lesson keeps its number next to it
    step, title = (f'Step {k}, Lesson {e["lesson"]}', lessons[str(e['lesson'])]['title']) if 'lesson' in e else (f'Step {k}', e['title'])
    t, part = state_html(title), state_html(e['part'])
    go = 'Open the lesson' if 'lesson' in e else 'Open the essay'
    panes.append(f'''    <article class="tp-pane{PLACES[(k - 1) % 4]}" id="pane-{sid}" aria-labelledby="pane-{sid}-t">
      <div class="tp-pane-viz"><canvas data-fig="{live}" aria-hidden="true"></canvas></div>
      <div class="tp-pane-in tp-wrap">
        <div class="tp-pane-text">
          <p class="tp-pane-tag">{part}</p>
          <h2 class="tp-pane-name" id="pane-{sid}-t">{t}</h2>
          <p class="tp-pane-line">{cap}</p>
          <a class="tp-pane-open" href="#{sid}" aria-haspopup="dialog" aria-label="Open {plain(title)}">Open<i aria-hidden="true"></i></a>
        </div>
      </div>
    </article>''')
    rail.append(f'    <a href="#pane-{sid}"><span>{plain(title)}</span></a>')
    sheets.append(f'''  <dialog class="tp-sheet" id="{sid}" aria-labelledby="{sid}-t">
    <div class="tp-sheet-bar"><span class="tp-sheet-tag">{part}</span><button class="tp-sheet-close" type="button" aria-label="Close">Close <kbd>Esc</kbd></button></div>
    <div class="tp-sheet-in tp-wrap">
      <div class="tp-sheet-media lesson-fig"><!-- thumb {key} -->{fig}<!-- /thumb --></div>
      <div class="tp-sheet-body">
        <h2 id="{sid}-t">{t}</h2>
        <p class="tp-sheet-sub">{step}</p>
        <p>{state_html(e["card"])}</p>
        <ul class="tp-sheet-links">
          <li><a class="lesson-go" href="{e["page"]}">{go}</a></li>
        </ul>
      </div>
    </div>
  </dialog>''')
parts = [f'  <section id="course" class="tp-panes" aria-label="The course">\n' + '\n\n'.join(panes) + '\n  </section>\n\n'
         + '  <nav class="tp-rail" aria-label="Panes">\n' + '\n'.join(rail) + '\n  </nav>\n\n' + '\n\n'.join(sheets)]
hub_path = QEC / 'index.html'
hub, found = re.subn(r'(<!-- course -->).*?(\n *<!-- /course -->)',
                     lambda m: m.group(1) + '\n' + '\n'.join(parts) + m.group(2), read(hub_path), flags=re.S)
if not found:
    sys.exit('index.html: no <!-- course --> marker')
io.open(hub_path, 'w', encoding='utf-8', newline='\n').write(hub)
print('wrote the course list in index.html')
