"""Render the 1200x630 share cards at the repo root from card.html, with
Python Playwright and the system Chrome:

    og-home.png og-research.png og-cv.png og-book.png og-life.png og-qec.png

    python _studio/tools/og/render.py            # all cards
    python _studio/tools/og/render.py og-cv.png  # just one

The figures come from _studio/tools/assets/figures.py; og-cv.png uses
img/tushar-pandey-b.webp (run _studio/tools/assets/portrait.py first).
"""
import base64, pathlib, sys
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / 'assets'))
import figures as F  # noqa: E402

P = F.LIGHT


def fig(inner, box=400, size=420):
    return F.svg(inner, box, size)


def portrait(size=400):
    b64 = base64.b64encode((ROOT / 'img' / 'tushar-pandey-b.webp').read_bytes()).decode()
    r = size / 2
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<defs><clipPath id="pc"><circle cx="{r}" cy="{r}" r="{r - 16}"/></clipPath></defs>'
            f'<image href="data:image/webp;base64,{b64}" x="16" y="16" width="{size - 32}" height="{size - 32}" clip-path="url(#pc)"/>'
            f'<circle cx="{r}" cy="{r}" r="{r - 16}" fill="none" stroke="{P["ink"]}" stroke-width="2"/>'
            f'<circle cx="{r}" cy="{r}" r="{r - 4}" fill="none" stroke="{P["hair"]}" stroke-width="1.5"/></svg>')


CARDS = {
    'og-home.png': dict(
        title='Tushar Pandey',
        sub='Senior Software Engineer at DataRobot. Researcher in quantum error correction. Ph.D. in mathematics.',
        foot='pandey-tushar.com', art=lambda: fig(F.toric(P))),
    'og-research.png': dict(
        title='Research',
        sub='Papers and preprints in quantum error correction, quantum algorithms, LLM reasoning and quantum topology.',
        foot='pandey-tushar.com/research', art=lambda: fig(F.trefoil(P, width=9), size=400)),
    'og-cv.png': dict(
        title='Curriculum Vitae', sub='Tushar Pandey, Ph.D.',
        foot='pandey-tushar.com/cv', art=lambda: portrait(400)),
    'og-book.png': dict(
        title='The Qubit Dialogues', sub='A book of possibilities.',
        foot='pandey-tushar.com/qubit-dialogues', art=lambda: fig(F.bloch(P))),
    'og-life.png': dict(
        title='An Unpolarized Life', sub='A book of questions.',
        foot='pandey-tushar.com/life', art=lambda: fig(F.rings(P))),
    'og-qec.png': dict(
        title='Quantum error correction in practice',
        sub='Eight interactive lessons, from the repetition code to lattice surgery.',
        foot='pandey-tushar.com/qec-in-practice', art=lambda: fig(F.surface(P)), size='64px'),
}

only = set(sys.argv[1:])
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='chrome')
    page = browser.new_page(viewport={'width': 1200, 'height': 630})
    for name, card in CARDS.items():
        if only and name not in only:
            continue
        page.goto((HERE / 'card.html').as_uri())
        card = {k: (v() if callable(v) else v) for k, v in card.items()}
        size = card.pop('size', None)
        page.evaluate('c => { for (const k in c) document.getElementById(k).innerHTML = c[k]; }', card)
        if size:
            page.evaluate('s => document.getElementById("title").style.fontSize = s', size)
        clipped = page.evaluate('''() => [...document.querySelectorAll('h1,.sub,.foot span')]
            .some(e => e.scrollWidth > e.clientWidth + 1 || e.getBoundingClientRect().right > 1200 - 470)''')
        out = ROOT / name
        page.screenshot(path=str(out))
        # octree keeps the few exact brand colours that median cut drifts
        Image.open(out).convert('RGB').quantize(colors=256, method=Image.Quantize.FASTOCTREE,
                                                dither=Image.Dither.FLOYDSTEINBERG).save(out, optimize=True)
        print(f'{name}: {out.stat().st_size} bytes' + ('  WARNING: text runs into the figure' if clipped else ''))
    browser.close()
