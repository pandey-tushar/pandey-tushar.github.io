"""Render the share cards og-life.png and og-qec.png (1200x630) at the repo
root from card.html, with Python Playwright and the system Chrome.

    python _studio/tools/og/render.py
"""
import io, json, pathlib
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
front = json.load(io.open(ROOT / '_studio' / 'content' / 'front.unpolarized.json', encoding='utf-8'))


def rings(size, colours, width):
    c = ''.join(f'<circle cx="{x}" cy="{y}" r="5.4" stroke="{col}"/>'
                for (x, y), col in zip(((12, 7.6), (8.2, 14.2), (15.8, 14.2)), colours))
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" style="overflow:visible">'
            f'<g fill="none" stroke-width="{width}" opacity=".85">{c}</g></svg>')


def patch(size):
    # the distance 3 patch of qec-in-practice/js/patch.js: X checks amber, Z checks blue, an X error on q4 firing two Z checks
    S, R, M = 60, 30, 48
    X = [[0, 1, 3, 4], [4, 5, 7, 8], [2, 5], [3, 6]]
    Z = [[1, 2, 4, 5], [3, 4, 6, 7], [0, 1], [7, 8]]
    side = {'2,5': 1, '3,6': 0, '0,1': 1, '7,8': 0}
    p = lambda i: (M + S * (i % 3), M + S * (i // 3))
    out = []
    for typ, stabs, col in (('Z', Z, '#4f9cff'), ('X', X, '#e0a040')):
        for k, q in enumerate(stabs):
            x, y = p(q[0])
            if len(q) == 4:
                d = f'M{x},{y}h{S}v{S}h{-S}Z'
            else:
                bx, by = p(q[1])
                d = f'M{x},{y}A{R},{R} 0 0 {side[",".join(map(str, q))]} {bx},{by}Z'
            fire = typ == 'Z' and k in (0, 1)
            fill = '#ff5c5c' if fire else col
            out.append(f'<path d="{d}" fill="{fill}" fill-opacity="{.75 if fire else .2}" stroke="{col}" stroke-width="2"/>')
    for i in range(9):
        x, y = p(i)
        out.append(f'<circle cx="{x}" cy="{y}" r="11" fill="{"#ff5c5c" if i == 4 else "#111a33"}" stroke="#e6ecff" stroke-width="2"/>')
    x, y = p(4)
    out.append(f'<circle cx="{x}" cy="{y}" r="19" fill="none" stroke="#ff5c5c" stroke-width="3"/>')
    out.append(f'<line x1="{M}" y1="{M - 8}" x2="{M + 2 * S}" y2="{M - 8}" stroke="#52d6e6" stroke-width="4" stroke-linecap="round"/>')
    out.append(f'<line x1="{M - 8}" y1="{M}" x2="{M - 8}" y2="{M + 2 * S}" stroke="#9b7bff" stroke-width="4" stroke-linecap="round"/>')
    return f'<svg width="{size}" height="{size}" viewBox="0 0 216 216" style="opacity:.92">{"".join(out)}</svg>'


CARDS = {
    'og-life.png': {
        'eyebrow': 'Tushar Pandey &middot; a book',
        'title': front['cover']['title'].replace('Unpolarized', '<i>Unpolarized</i>'),
        'sub': front['cover']['sub'].capitalize() + '.',
        'foot': 'pandey-tushar.com/life',
        'art': rings(300, ('#52d6e6', '#9b7bff', '#52d6e6'), .32),
    },
    'og-qec.png': {
        'eyebrow': 'Four interactive lessons',
        'title': 'Quantum error correction <i>in practice</i>',
        'sub': 'From one surface code patch to a teleported T state.',
        'foot': 'pandey-tushar.com/qec-in-practice',
        'art': patch(270),
    },
}

with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='chrome')
    page = browser.new_page(viewport={'width': 1200, 'height': 630})
    for name, card in CARDS.items():
        page.goto((HERE / 'card.html').as_uri())
        page.evaluate('c => { for (const k in c) document.getElementById(k).innerHTML = c[k]; }', card)
        out = ROOT / name
        page.screenshot(path=str(out))
        img = Image.open(out).convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
        img.save(out, optimize=True)
        print(f'{name}: {out.stat().st_size // 1024} KB')
    browser.close()
