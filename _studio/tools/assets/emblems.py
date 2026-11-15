"""Research-area emblems in img/figures/ (viewBox 120x120, strokes only).
Ink is currentColor; highlights use var(--tp-acc) and var(--tp-warm) through
style attributes, so the files work inlined or as <img>.

    python _studio/tools/assets/emblems.py
"""
import math, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import figures as F  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / 'img' / 'figures'
ACC, WARM = 'var(--tp-acc, #0b6e7f)', 'var(--tp-warm, #b4541a)'
f = F.f


def doc(title, body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'role="img" aria-label="{title}"><title>{title}</title>{body}</svg>\n')


def qec():
    """Toric-code lattice; one flipped qubit on a horizontal edge lights the two plaquettes either side."""
    L = (15, 45, 75, 105)
    out = [f'<rect x="45" y="15" width="30" height="30" style="fill:{ACC};fill-opacity:.22;stroke:none"/>',
           f'<rect x="45" y="45" width="30" height="30" style="fill:{ACC};fill-opacity:.22;stroke:none"/>']
    out.append('<path d="' + ''.join(f'M{v},7V113M7,{v}H113' for v in L) + '"/>')
    out.append(f'<path d="M45,15H75V75H45Z" style="stroke:{ACC}" stroke-width="2.6"/>')
    out.append(f'<path d="M45,45H75" style="stroke:{ACC}" stroke-width="2.6"/>')
    out.append(f'<circle cx="60" cy="45" r="5.5" style="fill:{WARM};stroke:{WARM}"/>')
    return doc('Toric code lattice with one error and its two syndrome checks', ''.join(out))


def reasoning():
    """A thought graph that branches into three, merges two branches, prunes one and concludes."""
    N = dict(A=(18, 60), B=(48, 26), C=(48, 60), D=(48, 94), E=(78, 43), F=(78, 94), G=(104, 60))
    r = 6.5
    edges = [('A', 'B', 0), ('A', 'C', 1), ('A', 'D', 0), ('B', 'E', 0), ('C', 'E', 1),
             ('D', 'F', 2), ('E', 'G', 1)]
    out = []
    for a, b, kind in edges:
        (x1, y1), (x2, y2) = N[a], N[b]
        dx, dy = x2 - x1, y2 - y1
        d = (dx * dx + dy * dy) ** .5
        sx, sy, ex, ey = x1 + dx / d * r, y1 + dy / d * r, x2 - dx / d * r, y2 - dy / d * r
        st = f' style="stroke:{ACC}"' if kind == 1 else (' stroke-dasharray="3 4" opacity=".55"' if kind == 2 else '')
        out.append(f'<line x1="{f(sx)}" y1="{f(sy)}" x2="{f(ex)}" y2="{f(ey)}"{st}/>')
    for k, (x, y) in N.items():
        if k == 'G':
            st = f' style="fill:{WARM};stroke:{WARM}"'
        elif k == 'E':
            st = f' style="fill:{ACC};fill-opacity:.25;stroke:{ACC}"'
        elif k == 'F':
            st = ' stroke-dasharray="3 3" opacity=".55"'
        elif k in 'AC':
            st = f' style="stroke:{ACC}"'
        else:
            st = ''
        out.append(f'<circle cx="{x}" cy="{y}" r="{r}"{st}/>')
    return doc('A graph of thoughts that branches, merges and prunes', ''.join(out))


def inference():
    """Requests queue into a batch of decode slots; the next request takes the free slot."""
    out = ['<rect x="54" y="18" width="56" height="84" rx="4"/>']
    fills = (0.72, 0.42, None, 0.86)
    for i, fr in enumerate(fills):
        y = 26 + i * 18
        out.append(f'<rect x="61" y="{y}" width="42" height="12" rx="2" stroke-width="1.6"/>')
        if fr:
            out.append(f'<rect x="61" y="{y}" width="{f(42 * fr)}" height="12" rx="2" '
                       f'style="fill:{ACC};fill-opacity:.3;stroke:{ACC}" stroke-width="1.6"/>')
    y = 26 + 2 * 18
    for k, x in enumerate((8, 21)):
        out.append(f'<rect x="{x}" y="{y}" width="9" height="12" rx="2" stroke-width="1.6"/>')
    out.append(f'<rect x="34" y="{y}" width="9" height="12" rx="2" style="fill:{WARM};fill-opacity:.85;stroke:{WARM}" stroke-width="1.6"/>')
    out.append(f'<path d="M46,{y + 6}H57M53,{y + 2.5}L57,{y + 6}L53,{y + 9.5}" style="stroke:{WARM}"/>')
    return doc('Requests queued into the free slot of a running batch', ''.join(out))


# The figure-eight knot drawn as the twist knot with two half-twists: a clasp
# above, the twist below. A closed Catmull-Rom curve through these points has
# four crossings; taking them over and under in turn along the curve gives an
# alternating diagram of determinant 5, which is 4_1.
EIGHT = [(40, 56), (35, 42), (39, 28), (50, 21), (61, 28), (65, 42), (60, 56), (50, 66), (40, 77),
         (50, 88), (60, 99), (70, 108), (84, 110), (96, 96), (99, 70), (93, 47), (79, 37), (50, 36),
         (21, 37), (7, 47), (1, 70), (4, 96), (16, 110), (30, 108), (40, 99), (50, 88), (60, 77), (50, 66)]


def figure_eight(size, pad=10, gap=4.5, sub=40):
    """SVG path data for the figure-eight knot in a size x size box, the
    under-strand cut back by `gap` (in the units of EIGHT) at each crossing."""
    n0, pts = len(EIGHT), []
    for i in range(n0):
        p0, p1, p2, p3 = EIGHT[i - 1], EIGHT[i], EIGHT[(i + 1) % n0], EIGHT[(i + 2) % n0]
        for k in range(sub):
            t = k / sub
            pts.append(tuple(.5 * (2 * p1[j] + (p2[j] - p0[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                   + (3 * p1[j] - p0[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    n = len(pts)
    L = [0.0]
    for i in range(1, n + 1):
        L.append(L[-1] + math.dist(pts[i - 1], pts[i % n]))
    hits = []  # (arc length, crossing) for both passes through each crossing
    for i in range(n):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
        for j in range(i + 2, n - (i == 0)):
            (x3, y3), (x4, y4) = pts[j], pts[(j + 1) % n]
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if not den:
                continue
            a = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            b = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / den
            if 0 <= a < 1 and 0 <= b < 1:
                c = len(hits) // 2
                hits += [(L[i] + a * (L[i + 1] - L[i]), c), (L[j] + b * (L[j + 1] - L[j]), c)]
    assert len(hits) == 8, 'the figure-eight diagram should have four crossings'
    under = [s for k, (s, _) in enumerate(sorted(hits)) if k % 2]
    tot = L[-1]
    cut = [any(min(abs(L[i] - u), tot - abs(L[i] - u)) < gap for u in under) for i in range(n)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    sc = (size - 2 * pad) / max(max(xs) - min(xs), max(ys) - min(ys))
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    start = next(i for i in range(n) if cut[i] and not cut[(i + 1) % n])
    runs, cur = [], []
    for k in range(1, n + 1):
        i = (start + k) % n
        if cut[i]:
            if cur:
                runs.append(cur); cur = []
        else:
            cur.append(pts[i])
    if cur:
        runs.append(cur)
    return ''.join('M' + 'L'.join(f'{f(size / 2 + (x - cx) * sc)} {f(size / 2 + (y - cy) * sc)}'
                                  for x, y in r[::8] + [r[-1]]) for r in runs)


def topology():
    """The figure-eight knot, whose complement the volume-conjecture paper treats."""
    return doc('Figure-eight knot diagram', f'<path d="{figure_eight(120, pad=8)}" stroke-width="3"/>')


def circuit():
    """Three qubit wires: two single-qubit gates, then two CNOTs entangling them in a ladder."""
    out = ['<path d="M8,30H112M8,60H112M8,90H112" opacity=".55"/>',
           '<rect x="19" y="19" width="22" height="22" rx="2" style="fill:var(--tp-void2, #fffdf8)"/>',
           '<rect x="19" y="79" width="22" height="22" rx="2" style="fill:var(--tp-void2, #fffdf8)"/>']
    for x, c, t in ((62, 30, 60), (90, 60, 90)):
        out.append(f'<path d="M{x},{c}V{t + 9.5}"/>')
        out.append(f'<circle cx="{x}" cy="{c}" r="4.5" style="fill:currentColor"/>')
        out.append(f'<circle cx="{x}" cy="{t}" r="9.5" style="fill:var(--tp-void2, #fffdf8);stroke:{ACC}"/>')
        out.append(f'<path d="M{x - 9.5},{t}H{x + 9.5}M{x},{t - 9.5}V{t + 9.5}" style="stroke:{ACC}"/>')
    return doc('A three-qubit circuit: two gates, then two CNOTs', ''.join(out))


def primes():
    """The numbers 1 to 49 in rows of seven: primes as dots, twin primes ringed."""
    p = [n for n in range(2, 50) if all(n % d for d in range(2, int(n ** .5) + 1))]
    twin = {n for n in p if n - 2 in p or n + 2 in p}
    out = []
    for n in range(1, 50):
        x, y = 15 + 15 * ((n - 1) % 7), 15 + 15 * ((n - 1) // 7)
        if n in twin:
            out.append(f'<circle cx="{x}" cy="{y}" r="6" style="stroke:{ACC}"/>')
        if n in p:
            out.append(f'<circle cx="{x}" cy="{y}" r="3" style="fill:currentColor;stroke:none"/>')
        else:
            out.append(f'<circle cx="{x}" cy="{y}" r="1.4" style="fill:currentColor;stroke:none" opacity=".4"/>')
    return doc('The numbers 1 to 49: primes marked, twin primes ringed', ''.join(out))


OUT.mkdir(parents=True, exist_ok=True)
for name, fn in (('qec', qec), ('reasoning', reasoning), ('inference', inference), ('topology', topology),
                 ('circuit', circuit), ('primes', primes)):
    p = OUT / f'{name}.svg'
    p.write_text(fn(), encoding='utf-8')
    print(p.name, p.stat().st_size, 'bytes')
