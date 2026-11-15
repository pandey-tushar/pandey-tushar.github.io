"""Typographic book covers in img/covers/ (SVG, viewBox 600x900) plus WebP
rasters at 600x900 and 300x450 rendered with the system Chrome, so the serif
renders the same everywhere the rasters are used.

    python _studio/tools/assets/covers.py

The illustrated edition embeds a square crop of the canto 3 plate
(illustrated/assets/canto-03-*.webp) as base64 WebP.
"""
import base64, glob, io, pathlib, sys
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import figures as F  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / 'img' / 'covers'
SERIF = "'Palatino Linotype', Palatino, 'Book Antiqua', Georgia, serif"
SANS = "'Segoe UI', system-ui, Arial, sans-serif"
FIG = (110, 372, 380)   # x, y, side of the figure square


def mark(P, cx, cy, size):
    s = size / 24
    c = ''.join(f'<circle cx="{F.f(cx + (x - 12) * s)}" cy="{F.f(cy + (y - 10.9) * s)}" r="{F.f(5.4 * s)}"/>'
                for x, y in F.MARK)
    return f'<g fill="none" stroke="{P["accent"]}" stroke-width="1.4">{c}</g>'


def cover(P, title_lines, sub, figure):
    t = ''.join(f'<text x="300" y="{190 + 74 * i}" text-anchor="middle" font-family="{SERIF}" font-size="62" '
                f'fill="{P["ink"]}">{line}</text>' for i, line in enumerate(title_lines))
    y_sub = 190 + 74 * (len(title_lines) - 1) + 60
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="600" height="900" viewBox="0 0 600 900">'
            f'<rect width="600" height="900" fill="{P["paper"]}"/>'
            f'<rect x="28.5" y="28.5" width="543" height="843" fill="none" stroke="{P["hair"]}"/>'
            f'<rect x="276" y="104" width="48" height="3" fill="{P["accent"]}"/>'
            f'{t}'
            f'<text x="300" y="{y_sub}" text-anchor="middle" font-family="{SERIF}" font-style="italic" font-size="24" '
            f'fill="{P["muted"]}">{sub}</text>'
            f'{figure}'
            f'<text x="300" y="806" text-anchor="middle" font-family="{SANS}" font-size="17" letter-spacing="5" '
            f'fill="{P["ink"]}">TUSHAR PANDEY</text>'
            f'{mark(P, 300, 842, 26)}'
            f'</svg>\n')


def line_figure(P, inner):
    x, y, s = FIG
    return f'<svg x="{x}" y="{y}" width="{s}" height="{s}" viewBox="0 0 400 400">{inner}</svg>'


def plate(P):
    src = glob.glob(str(ROOT / 'illustrated' / 'assets' / 'canto-03-*.webp'))[0]
    im = Image.open(src).convert('RGB')            # 1600x1000; the sphere sits left of centre
    im = im.crop((140, 50, 1040, 950)).resize((720, 720), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, 'WEBP', quality=80, method=6)
    b64 = base64.b64encode(buf.getvalue()).decode()
    x, y, s = FIG
    return (f'<image x="{x}" y="{y}" width="{s}" height="{s}" xlink:href="data:image/webp;base64,{b64}" '
            f'href="data:image/webp;base64,{b64}"/>'
            f'<rect x="{x - .5}" y="{y - .5}" width="{s + 1}" height="{s + 1}" fill="none" stroke="{P["hair"]}"/>'
            f'<rect x="{x - 10.5}" y="{y - 10.5}" width="{s + 21}" height="{s + 21}" fill="none" stroke="{P["hair"]}" '
            f'stroke-opacity=".7"/>')


L, D = F.LIGHT, F.DARK
COVERS = {
    'qubit-dialogues': cover(L, ['The Qubit', 'Dialogues'], 'A Book of Possibilities', line_figure(L, F.bloch(L))),
    'qubit-dialogues-illustrated': cover(D, ['The Qubit', 'Dialogues'], 'Illustrated Edition', plate(D)),
    'an-unpolarized-life': cover(L, ['An Unpolarized', 'Life'], 'A Book of Questions', line_figure(L, F.rings(L))),
}

OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='chrome')
    page = browser.new_page(viewport={'width': 600, 'height': 900}, device_scale_factor=2)
    for name, svg in COVERS.items():
        p = OUT / f'{name}.svg'
        p.write_text(svg, encoding='utf-8')
        page.goto(p.as_uri())
        im = Image.open(io.BytesIO(page.screenshot())).convert('RGB')
        for w, suffix in ((600, ''), (300, '-300')):
            q = OUT / f'{name}{suffix}.webp'
            im.resize((w, w * 3 // 2), Image.LANCZOS).save(q, 'WEBP', quality=86, method=6)
        print(name, {s: (OUT / f'{name}{s}').stat().st_size for s in ('.svg', '.webp', '-300.webp')})
    browser.close()
