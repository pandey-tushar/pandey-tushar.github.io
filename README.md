# pandey-tushar.com

Personal site of Tushar Pandey, served by GitHub Pages from the repo root
(custom domain in `CNAME`). Static files, no build step for the pages at the root.

## Pages

- `index.html`: homepage, with its own inline CSS and theme switch
- `research.html`, `cv.html`, `books.html`: research list, CV, catalogue of the books
- `qubit-dialogues.html`: The Qubit Dialogues, read online
- `life/`, `illustrated/`: An Unpolarized Life and the illustrated edition (built output, see below)
- `qec-in-practice/`: four interactive surface-code lessons
- `404.html`: served by GitHub Pages for any unknown path
- `sitemap.xml`, `robots.txt`, `og-*.png` (share cards), the book and resume PDFs

## lib/

`lib/site.css` and `lib/site.js` are the shared header, footer, theme switch
(`tp-theme`) and tokens every page but the homepage links. The rules are in
`_studio/site-system.md`. `lib/` also holds three.js and KaTeX for the book page.

## The lessons

`qec-in-practice/lesson-1.html` to `lesson-4.html` are generated: edit
`_studio/tools/lesson-template.html` or `qec-in-practice/data/*.json`, then run
`python _studio/tools/build-lessons.py`. It also draws the card pictures in
`qec-in-practice/index.html`. The pages fetch `data/lesson<n>.json` at run time.

## _studio

Source and tooling. Jekyll skips folders that start with an underscore, so
nothing in it is published. The editions are built from `_studio/apps/*`
(`npm run build` in `_studio`). Checks in `_studio/tools`, each exits non-zero on failure:

- `check-site.py`: shared head, header, nav, one main and h1 on every page; prints `site ok`
- `check-lessons.py`: lesson text present without script; prints `lessons ok`
- `check-editions.py`: built editions carry their text; prints `editions ok`
- `check-qd.py`: qubit-dialogues.html loads lib/ and stays small; prints `qd ok`
- `check-perf.py`: homepage idle frame cost on a slowed phone; prints `perf ok`

Other tools: `build-lessons.py`, `og/render.py` (share cards), `compress-pdf.py`,
`pdf.mjs` (print the editions to PDF), `extract-content.mjs`, `deploy.ps1`.

## Preview locally

    python -m http.server 8000

then open http://localhost:8000. Serve from the repo root: links are root-relative,
so file:// does not work. An unknown path shows the server's own 404; open /404.html.

## Deploy

    powershell -File _studio/tools/deploy.ps1

copies the homepage source and the built editions (`_studio/apps/*/dist`) into
the root, then fails if any file the site links to is missing. It never deletes,
commits or pushes: review with `git status` and `git diff`, then commit and push
to `main`; GitHub Pages publishes it.
