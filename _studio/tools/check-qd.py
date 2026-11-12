"""qubit-dialogues.html must load KaTeX and three.js from lib/, carry no inline
fonts and no loader overlay, and keep the CANTOS blob the tools read.

    python _studio/tools/check-qd.py
"""
import hashlib, io, json, pathlib, re, sys

REPO = pathlib.Path(__file__).resolve().parents[2]
PAGE = REPO / 'qubit-dialogues.html'
LIB = REPO / 'lib'
# sha256 of the three.js r128 script that was inline in the page (license comment + code)
THREE_SHA = '9274bbcec8d96168626c732b5d31c775aa8cfb7eaa0599bec0c175908a2c1ce2'

html = io.open(PAGE, encoding='utf-8').read()
fail = []

if 'data:font' in html:
    fail.append('page: inline data:font still present')
size = PAGE.stat().st_size
if size >= 320000:
    fail.append(f'page: {size} bytes, want under 320000')
if '<link rel="stylesheet" href="lib/katex/katex.min.css">' not in html:
    fail.append('page: no link to lib/katex/katex.min.css')
if '<script defer src="lib/three-r128.min.js"></script>' not in html:
    fail.append('page: no deferred lib/three-r128.min.js')
if re.search(r'id="loader"|#loader', html):
    fail.append('page: loader overlay still present')

# tools/extract-content.mjs and packages/qa/src/parity.ts read this exact pattern
m = re.search(r'window\.CANTOS = (\[[\s\S]*?\]);</script>', html)
if not m:
    fail.append('page: CANTOS blob not found')
elif len(json.loads(m.group(1))) != 22:
    fail.append('page: CANTOS does not hold 22 cantos')

css = LIB / 'katex' / 'katex.min.css'
if not css.exists():
    fail.append('lib: katex/katex.min.css missing')
else:
    for f in re.findall(r'url\((fonts/[^)]+\.woff2)\)', css.read_text(encoding='utf-8')):
        if not (css.parent / f).exists():
            fail.append(f'lib: katex/{f} missing')

three = LIB / 'three-r128.min.js'
if not three.exists():
    fail.append('lib: three-r128.min.js missing')
else:
    b = three.read_bytes()
    if b'"128"' not in b:
        fail.append('lib: three-r128.min.js has no "128" revision marker')
    if hashlib.sha256(b).hexdigest() != THREE_SHA:
        fail.append('lib: three-r128.min.js differs from the script that was inline')

print('\n'.join(fail) or 'qd ok')
sys.exit(1 if fail else 0)
