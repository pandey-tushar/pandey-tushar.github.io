"""Line figures shared by the share cards, book covers and emblems.

Every function returns SVG markup (no outer <svg>) for a square box of side
`box`, drawn with the palette `P` (a dict with ink, muted, hair, accent, warm,
paper, raised). Colours may be CSS expressions such as currentColor.
"""
import math

LIGHT = dict(paper='#f7f4ed', raised='#fffdf8', ink='#16202e', muted='#5a6472',
             hair='#d9d3c4', accent='#0b6e7f', warm='#b4541a', tint='#ebe5d6')
DARK = dict(paper='#0d1320', raised='#131b2c', ink='#e9eef5', muted='#9aa6b6',
            hair='#2a3447', accent='#5fd0de', warm='#f0a35e', tint='#1a2336')

MARK = ((12, 7.6), (8.2, 14.2), (15.8, 14.2))
MARK_R = 5.4


def f(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')


def rings(P, box=400, width=2.5, fill_core=True):
    """The site mark: three overlapping circles, scaled to the box, with the
    common region of all three lightly tinted."""
    s = box / 24 * 0.98
    cx0, cy0 = 12, (7.6 + 14.2 + 14.2) / 3
    pts = [(box / 2 + (x - cx0) * s, box / 2 + (y - cy0) * s) for x, y in MARK]
    r = MARK_R * s
    out = []
    if fill_core:
        ids = [f'mk{i}' for i in range(3)]
        out.append('<defs>' + ''.join(
            f'<clipPath id="{ids[i]}"><circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}"/></clipPath>'
            for i, (x, y) in enumerate(pts)) + '</defs>')
        x, y = pts[0]
        out.append(f'<g clip-path="url(#{ids[1]})"><g clip-path="url(#{ids[2]})">'
                   f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{P["accent"]}" fill-opacity=".16"/></g></g>')
    out.append(f'<g fill="none" stroke="{P["ink"]}" stroke-width="{width}">' + ''.join(
        f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}"/>' for x, y in pts) + '</g>')
    return ''.join(out)


def toric(P, box=400, n=4, width=2):
    """A patch of the toric code: qubits on edges, vertex (star) and plaquette
    checks. Two X errors on neighbouring vertical edges in one row; the
    plaquette they share is flipped twice and stays quiet, the two outer
    plaquettes fire."""
    m = box * 0.14
    s = (box - 2 * m) / n
    X = lambda i: m + i * s
    stub = s * 0.42
    row = n // 2 - 1 if n > 2 else 0
    err = [(1, row), (2, row)]                # vertical edges (x index, y cell)
    lit = [(0, row), (2, row)]                # plaquettes (x cell, y cell)
    out = []
    for cx, cy in lit:
        out.append(f'<rect x="{f(X(cx))}" y="{f(X(cy))}" width="{f(s)}" height="{f(s)}" '
                   f'fill="{P["accent"]}" fill-opacity=".22"/>')
    # lattice lines, continuing past the patch to suggest the torus
    g = []
    for i in range(n + 1):
        g.append(f'M{f(X(i))},{f(m - stub)}V{f(X(n) + stub)}')
        g.append(f'M{f(m - stub)},{f(X(i))}H{f(X(n) + stub)}')
    out.append(f'<path d="{"".join(g)}" fill="none" stroke="{P["ink"]}" stroke-width="{width}"/>')
    # fade the stubs into the paper
    for d in (f'M0,0H{box}V{f(m - stub * .35)}H0Z', f'M0,{f(X(n) + stub * .35)}H{box}V{box}H0Z',
              f'M0,0V{box}H{f(m - stub * .35)}V0Z', f'M{f(X(n) + stub * .35)},0V{box}H{box}V0Z'):
        out.append(f'<path d="{d}" fill="{P["paper"]}" fill-opacity=".55"/>')
    for cx, cy in lit:
        out.append(f'<rect x="{f(X(cx))}" y="{f(X(cy))}" width="{f(s)}" height="{f(s)}" '
                   f'fill="none" stroke="{P["accent"]}" stroke-width="{width * 1.6}"/>')
    # dual string through the two errors
    y = X(row) + s / 2
    out.append(f'<path d="M{f(X(0) + s / 2)},{f(y)}H{f(X(2) + s / 2)}" stroke="{P["warm"]}" '
               f'stroke-width="{width}" stroke-dasharray="{f(width * 2.5)} {f(width * 2.5)}" fill="none"/>')
    # vertices
    for i in range(n + 1):
        for j in range(n + 1):
            out.append(f'<circle cx="{f(X(i))}" cy="{f(X(j))}" r="{f(width * 1.6)}" fill="{P["ink"]}"/>')
    # qubits on edge midpoints
    q = s * 0.12
    for i in range(n + 1):
        for j in range(n):
            for (x, y, key) in ((X(i), X(j) + s / 2, ('v', i, j)), (X(j) + s / 2, X(i), ('h', j, i))):
                hit = key[0] == 'v' and (key[1], key[2]) in err
                out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(q)}" fill="{P["warm"] if hit else P["raised"]}" '
                           f'stroke="{P["warm"] if hit else P["ink"]}" stroke-width="{width}"/>')
    return ''.join(out)


SURFACE_X = [[0, 1, 3, 4], [4, 5, 7, 8], [2, 5], [3, 6]]
SURFACE_Z = [[1, 2, 4, 5], [3, 4, 6, 7], [0, 1], [7, 8]]
SIDE = {(2, 5): 1, (3, 6): 0, (0, 1): 1, (7, 8): 0}


def surface(P, box=400, width=2, labels=True):
    """Distance 3 rotated surface code (the patch of qec-in-practice): data
    qubits on the vertices, alternating X and Z plaquettes, weight two checks
    on the boundary. An X error on the centre qubit fires the two Z checks
    that contain it."""
    S = box / 4
    M = (box - 2 * S) / 2
    R = S / 2
    p = lambda i: (M + S * (i % 3), M + S * (i // 3))
    err = 4
    out = []
    for typ, stabs in (('X', SURFACE_X), ('Z', SURFACE_Z)):
        for q in stabs:
            fire = typ == 'Z' and err in q
            x, y = p(q[0])
            if len(q) == 4:
                d = f'M{f(x)},{f(y)}h{f(S)}v{f(S)}h{f(-S)}Z'
            else:
                bx, by = p(q[1])
                d = f'M{f(x)},{f(y)}A{f(R)},{f(R)} 0 0 {SIDE[tuple(q)]} {f(bx)},{f(by)}Z'
            if fire:
                fill, op = P['accent'], '.24'
            else:
                fill, op = (P['tint'], '1') if typ == 'X' else (P['raised'], '1')
            out.append(f'<path d="{d}" fill="{fill}" fill-opacity="{op}" stroke="{P["ink"]}" '
                       f'stroke-width="{width}" stroke-linejoin="round"/>')
            if fire:
                out.append(f'<path d="{d}" fill="none" stroke="{P["accent"]}" stroke-width="{width * 1.8}" '
                           f'stroke-linejoin="round"/>')
            if labels and len(q) == 4:
                cx, cy = x + S / 2, y + S / 2
                out.append(f'<text x="{f(cx)}" y="{f(cy + S * .09)}" text-anchor="middle" '
                           f'font-family="Palatino Linotype,Palatino,Georgia,serif" font-style="italic" '
                           f'font-size="{f(S * .26)}" fill="{P["accent"] if fire else P["muted"]}">{typ}</text>')
    for i in range(9):
        x, y = p(i)
        hit = i == err
        out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(S * .12)}" fill="{P["warm"] if hit else P["raised"]}" '
                   f'stroke="{P["warm"] if hit else P["ink"]}" stroke-width="{width}"/>')
    return ''.join(out)


def _bloch_proj(e=math.radians(18), a=math.radians(-35)):
    ca, sa, ce, se = math.cos(a), math.sin(a), math.cos(e), math.sin(e)

    def proj(x, y, z):
        xp = x * ca - y * sa
        yp = x * sa + y * ca
        return xp, yp * se + z * ce, -yp * ce + z * se   # screen x, screen up, depth
    return proj


def bloch(P, box=400, width=2, theta=math.radians(52), phi=math.radians(-5)):
    """Bloch sphere as an engraving: outline, equator and two parallels,
    three meridians (back halves dashed), z axis, and one state vector."""
    proj = _bloch_proj()
    c = box / 2
    R = box * 0.34
    S = lambda x, y, z: (c + R * proj(x, y, z)[0], c - R * proj(x, y, z)[1], proj(x, y, z)[2])
    out = []

    def curve(pts, sw, colour, back_dash=True):
        front, back, cur, side = [], [], [], None
        for x, y, d in pts:
            sd = d >= 0
            if side is not None and sd != side:
                (front if side else back).append(cur)
                cur = [cur[-1]]
            cur.append((x, y))
            side = sd
        (front if side else back).append(cur)
        for seg in back:
            if len(seg) > 1:
                out.append(f'<polyline points="{" ".join(f"{f(x)},{f(y)}" for x, y in seg)}" fill="none" '
                           f'stroke="{P["muted"]}" stroke-width="{sw * .7}" stroke-dasharray="{f(sw * 2)} {f(sw * 2.5)}" '
                           f'stroke-opacity=".7"/>')
        for seg in front:
            if len(seg) > 1:
                out.append(f'<polyline points="{" ".join(f"{f(x)},{f(y)}" for x, y in seg)}" fill="none" '
                           f'stroke="{colour}" stroke-width="{sw}" stroke-linecap="round"/>')

    N = 240
    for lat in (-45, 0, 45):
        z = math.sin(math.radians(lat)); rr = math.cos(math.radians(lat))
        curve([S(rr * math.cos(t), rr * math.sin(t), z) for t in (2 * math.pi * k / N for k in range(N + 1))],
              width * (0.9 if lat == 0 else .6), P['ink'] if lat == 0 else P['muted'])
    for lon in (0, 60, 120):
        l = math.radians(lon)
        curve([S(math.sin(t) * math.cos(l), math.sin(t) * math.sin(l), math.cos(t))
               for t in (2 * math.pi * k / N for k in range(N + 1))], width * .6, P['muted'])
    out.append(f'<circle cx="{f(c)}" cy="{f(c)}" r="{f(R)}" fill="none" stroke="{P["ink"]}" stroke-width="{width * 1.1}"/>')
    # z axis
    n0, s0 = S(0, 0, 1.22), S(0, 0, -1.22)
    out.append(f'<line x1="{f(s0[0])}" y1="{f(s0[1])}" x2="{f(n0[0])}" y2="{f(n0[1])}" stroke="{P["ink"]}" '
               f'stroke-width="{width * .7}" stroke-dasharray="{f(width * 3)} {f(width * 2)}"/>')
    for z in (1, -1):
        x, y, _ = S(0, 0, z)
        out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(width * 1.7)}" fill="{P["ink"]}"/>')
    font = 'font-family="Palatino Linotype,Palatino,Georgia,serif" font-style="italic"'
    out.append(f'<text x="{f(n0[0] + box * .03)}" y="{f(n0[1] + box * .01)}" {font} font-size="{f(box * .055)}" '
               f'fill="{P["ink"]}">|0&#x27E9;</text>')
    out.append(f'<text x="{f(s0[0] + box * .03)}" y="{f(s0[1] + box * .03)}" {font} font-size="{f(box * .055)}" '
               f'fill="{P["ink"]}">|1&#x27E9;</text>')
    # state vector and its projection onto the equatorial plane
    v = (math.sin(theta) * math.cos(phi), math.sin(theta) * math.sin(phi), math.cos(theta))
    o, tip, foot = S(0, 0, 0), S(*v), S(v[0], v[1], 0)
    dot = f'stroke="{P["muted"]}" stroke-width="{width * .7}" stroke-dasharray="{f(width)} {f(width * 1.8)}"'
    out.append(f'<line x1="{f(o[0])}" y1="{f(o[1])}" x2="{f(foot[0])}" y2="{f(foot[1])}" {dot}/>')
    out.append(f'<line x1="{f(tip[0])}" y1="{f(tip[1])}" x2="{f(foot[0])}" y2="{f(foot[1])}" {dot}/>')
    ang = math.atan2(tip[1] - o[1], tip[0] - o[0])
    L = width * 6
    back = (tip[0] - L * math.cos(ang), tip[1] - L * math.sin(ang))
    out.append(f'<line x1="{f(o[0])}" y1="{f(o[1])}" x2="{f(back[0])}" y2="{f(back[1])}" stroke="{P["warm"]}" '
               f'stroke-width="{width * 1.4}" stroke-linecap="round"/>')
    head = [tip, (back[0] + L * .45 * math.sin(ang), back[1] - L * .45 * math.cos(ang)),
            (back[0] - L * .45 * math.sin(ang), back[1] + L * .45 * math.cos(ang))]
    out.append(f'<polygon points="{" ".join(f"{f(p[0])},{f(p[1])}" for p in head)}" fill="{P["warm"]}"/>')
    out.append(f'<circle cx="{f(o[0])}" cy="{f(o[1])}" r="{f(width * 1.5)}" fill="{P["ink"]}"/>')
    out.append(f'<text x="{f(tip[0] - box * .025)}" y="{f(tip[1] - box * .03)}" text-anchor="end" {font} font-size="{f(box * .055)}" '
               f'fill="{P["warm"]}">|&#x03C8;&#x27E9;</text>')
    return ''.join(out)


def _trefoil_arcs(box, gap):
    """Projection of the trefoil x = sin t + 2 sin 2t, y = cos t - 2 cos 2t,
    z = -sin 3t, cut at its three under-crossings. Returns the three arcs of
    the diagram as point lists (each runs from one under-crossing to the next)."""
    N = 1500
    s = box / 2 / 3.35
    T = [2 * math.pi * k / N for k in range(N)]
    P3 = [(box / 2 + s * (math.sin(t) + 2 * math.sin(2 * t)),
           box / 2 + s * 0.08 + s * (math.cos(t) - 2 * math.cos(2 * t)),
           -math.sin(3 * t)) for t in T]
    unders = []
    for i in range(N):
        a, b = P3[i], P3[(i + 1) % N]
        for j in range(i + 2, N):
            if (j + 1) % N == i:
                continue
            c, d = P3[j], P3[(j + 1) % N]
            den = (b[0] - a[0]) * (d[1] - c[1]) - (b[1] - a[1]) * (d[0] - c[0])
            if abs(den) < 1e-12:
                continue
            u = ((c[0] - a[0]) * (d[1] - c[1]) - (c[1] - a[1]) * (d[0] - c[0])) / den
            w = ((c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0])) / den
            if 0 <= u < 1 and 0 <= w < 1:
                unders.append(i if a[2] < c[2] else j)
    assert len(unders) == 3, unders
    # arc length along the curve
    L = [0.0]
    for i in range(1, N + 1):
        p, q = P3[i - 1], P3[i % N]
        L.append(L[-1] + math.hypot(q[0] - p[0], q[1] - p[1]))
    total = L[-1]
    hidden = [any(min(abs(L[i] - L[u]), total - abs(L[i] - L[u])) < gap for u in unders) for i in range(N)]
    start = next(i for i in range(N) if hidden[i] and not hidden[(i + 1) % N]) + 1
    arcs, cur = [], []
    for k in range(N):
        i = (start + k) % N
        if hidden[i]:
            if cur:
                arcs.append(cur); cur = []
        else:
            cur.append(P3[i][:2])
    if cur:
        arcs.append(cur)
    assert len(arcs) == 3, len(arcs)
    return arcs


def trefoil(P, box=400, width=7, colours=None):
    """Trefoil knot diagram with gaps at the under-crossings. Its three arcs
    are tricoloured (ink, accent, warm): at every crossing all three meet."""
    colours = colours or (P['ink'], P['accent'], P['warm'])
    out = []
    for arc, col in zip(_trefoil_arcs(box, gap=width * 1.9), colours):
        pts = ' '.join(f'{f(x)},{f(y)}' for x, y in arc[::4] + [arc[-1]])
        out.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{width}" '
                   f'stroke-linecap="round" stroke-linejoin="round"/>')
    return ''.join(out)


def svg(inner, box=400, size=None, extra=''):
    size = size or box
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {box} {box}"{extra}>{inner}</svg>')
