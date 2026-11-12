"""The two built editions must carry their text in the HTML itself, before any
script runs. Checks the build output, so build first. Exits non-zero on failure.

    npm run build:unpolarized && npm run build:illustrated
    python _studio/tools/check-editions.py
"""
import io, json, pathlib, sys

STUDIO = pathlib.Path(__file__).resolve().parents[1]
read = lambda p: io.open(p, encoding='utf-8').read()


def esc(s):
    """esc() in packages/reader/src/render.ts."""
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def first_text(block):
    t = block['text']
    return t[0] if isinstance(t, list) else t


def last_text(block):
    t = block['text']
    return t[-1] if isinstance(t, list) else t


fail = []

life = read(STUDIO / 'apps/unpolarized/dist/index.html')
front = json.loads(read(STUDIO / 'content/front.unpolarized.json'))
want = {'cover title': '<h1>' + esc(front['cover']['title']) + '</h1>',
        'invocation': esc(front['invocation']['paras'][0]),
        'book json-ld': '"@type": "Book"'}
for c in json.loads(read(STUDIO / 'content/unpolarized.json')):
    want[f"chapter {c['n']} title"] = '<h2>' + esc(c['title']) + '</h2>'
    want[f"chapter {c['n']} first paragraph"] = esc(first_text(c['blocks'][0]))
    want[f"chapter {c['n']} last paragraph"] = esc(last_text(c['blocks'][-1]))
fail += [f'life: no {k}' for k, v in want.items() if v not in life]

ill = read(STUDIO / 'apps/illustrated/dist/index.html')
want = {'title': '<h1>The Qubit Dialogues</h1>', 'link to the text edition': 'href="../qubit-dialogues.html"'}
for c in json.loads(read(STUDIO / 'content/en.json')):
    want[f"canto {c['n']} title"] = '<li>' + esc(c['title']) + '</li>'
fail += [f'illustrated: no {k}' for k, v in want.items() if v not in ill]
if 'Five of twenty two' in ill:
    fail.append('illustrated: still says five of twenty two cantos are composed')

for name, page in (('life', life), ('illustrated', ill)):
    if page.count('id="static-book"') != 1:
        fail.append(f'{name}: expected exactly one #static-book')

# what is published must be what was built
for app, pub in (('unpolarized', 'life'), ('illustrated', 'illustrated')):
    if read(STUDIO / 'apps' / app / 'dist/index.html') != read(STUDIO.parent / pub / 'index.html'):
        fail.append(f'{pub}/index.html differs from the build: run _studio/tools/deploy.ps1')

print('\n'.join(fail) or 'editions ok')
sys.exit(1 if fail else 0)
