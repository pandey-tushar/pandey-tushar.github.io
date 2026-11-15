"""Site icons from the three-circle mark, written to the repo root:

    favicon.svg           light/dark via prefers-color-scheme
    favicon.ico           16, 32, 48 (PNG entries), transparent
    apple-touch-icon.png  180, opaque paper background
    icon-192.png, icon-512.png  opaque, mark inside the maskable safe zone

    python _studio/tools/assets/icons.py
"""
import io, pathlib, struct
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[3]
TEAL, TEAL_DARK, PAPER = '#0b6e7f', '#5fd0de', '#f7f4ed'
CIRCLES = ((12, 7.6), (8.2, 14.2), (15.8, 14.2))


def mark(scale, stroke, colour=None):
    """The mark centred in a 24 box; the circles' bounding box is centred at (12, 10.9)."""
    c = ''.join(f'<circle cx="{x}" cy="{y}" r="5.4"/>' for x, y in CIRCLES)
    col = f' stroke="{colour}"' if colour else ''
    return (f'<g fill="none"{col} stroke-width="{stroke}" '
            f'transform="translate(12 12) scale({scale}) translate(-12 -10.9)">{c}</g>')


def icon_svg(px, stroke, scale, bg=None):
    rect = f'<rect width="24" height="24" fill="{bg}"/>' if bg else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{px}" height="{px}" viewBox="0 0 24 24">'
            f'{rect}{mark(scale, stroke, TEAL)}</svg>')


FAVICON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
               f'<style>g{{stroke:{TEAL}}}@media (prefers-color-scheme:dark){{g{{stroke:{TEAL_DARK}}}}}</style>'
               f'{mark(1.1, 1.7)}</svg>\n')

# (file, px, stroke in 24-box units, scale, background); small sizes get heavier strokes
RASTERS = [
    ('ico16', 16, 2.1, 1.16, None),
    ('ico32', 32, 1.8, 1.14, None),
    ('ico48', 48, 1.7, 1.1, None),
    ('apple-touch-icon.png', 180, 1.25, 0.72, PAPER),
    ('icon-192.png', 192, 1.25, 0.66, PAPER),
    ('icon-512.png', 512, 1.0, 0.66, PAPER),
]


def write_ico(path, pngs):
    head = struct.pack('<HHH', 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries, blobs = b'', b''
    for px, data in pngs:
        entries += struct.pack('<BBBBHHII', px % 256, px % 256, 0, 0, 1, 32, len(data), offset + len(blobs))
        blobs += data
    path.write_bytes(head + entries + blobs)


(ROOT / 'favicon.svg').write_text(FAVICON_SVG, encoding='utf-8')
ico = []
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='chrome')
    page = browser.new_page()
    for name, px, stroke, scale, bg in RASTERS:
        page.set_viewport_size({'width': px, 'height': px})
        page.set_content(f'<html><body style="margin:0;background:transparent">{icon_svg(px, stroke, scale, bg)}</body></html>')
        png = page.screenshot(omit_background=bg is None, clip={'x': 0, 'y': 0, 'width': px, 'height': px})
        im = Image.open(io.BytesIO(png))
        im = im.convert('RGB') if bg else im.convert('RGBA')
        buf = io.BytesIO(); im.save(buf, 'PNG', optimize=True)
        if not name.endswith('.png'):
            ico.append((px, buf.getvalue()))
        else:
            (ROOT / name).write_bytes(buf.getvalue())
    browser.close()
write_ico(ROOT / 'favicon.ico', ico)
for n in ('favicon.svg', 'favicon.ico', 'apple-touch-icon.png', 'icon-192.png', 'icon-512.png'):
    print(n, (ROOT / n).stat().st_size, 'bytes')
