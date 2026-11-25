# pandey-tushar.com

Personal site of Tushar Pandey, served by GitHub Pages from the repo root
(custom domain in `CNAME`). Static files, no build step for the pages at the root.

## Pages

- `index.html`: homepage, published from `_studio/prototypes/site-full/index.html`
- `research.html`, `cv.html`, `books.html`: research list, CV, catalogue of the books; the paper
  lists in the first two are generated from `_studio/content/papers.json` by `build-research.py`
- `qubit-dialogues.html`: The Qubit Dialogues, read online
- `life/`, `illustrated/`: An Unpolarized Life and the illustrated edition (built output, see below)
- `qec-in-practice/`: Quantum Error Correction in Practice, a course of eight interactive lessons
- `papers/`: paper companion pages, one per paper (see below)
- `tools/`: interactive tools (see below)
- `notes/`: short notes with an RSS feed (see below); not in the primary nav
- `404.html`: served by GitHub Pages for any unknown path
- `sitemap.xml`, `robots.txt`, `og-*.png` (share cards, 1200x630), the book and resume PDFs
- `favicon.ico`, `favicon.svg`, `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`: the site icons
- `img/`: the portrait, the book covers (`img/covers/`) and the research-area emblems
  (`img/figures/`), drawn by the scripts in `_studio/tools/assets/`

## lib/

`lib/site.css` and `lib/site.js` are the shared header, footer, theme switch
(`tp-theme`) and tokens every page links. The rules are in
`_studio/site-system.md`. `lib/` also holds three.js and KaTeX for the book page.

## The lessons

The course order, its two parts and the card texts live in one place,
`qec-in-practice/data/course.json`; the generator and check-lessons.py read it.
Eight pages: `repetition-code.html`, `lesson-1.html`, `decoding.html`, `threshold.html`,
`lesson-2.html` to `lesson-4.html`, `lattice-surgery.html`.

`lesson-1.html` to `lesson-4.html` are generated: edit `_studio/tools/lesson-template.html`,
`qec-in-practice/data/lessons.json` (titles, intros, the narrative) or `data/lesson<n>.json`
(the run data each page fetches), then run `python _studio/tools/build-lessons.py`. It also
writes the course list and its card pictures in `qec-in-practice/index.html` (between
`<!-- course -->` and `<!-- /course -->`) and each lesson's previous and next links. The
other four pages are hand-written; their back and next links are kept to the course order by hand.
The error-correction engine (codes, noise, union-find decoder, Monte Carlo, worker) is in
`qec-in-practice/js/qec/`; its tests are `_studio/tools/tests/**/*.test.mjs`.

## Paper companion pages

One page per paper, worth linking from arXiv, GitHub and talks: a plain-language essay, one
interactive figure from the paper's own data, a BibTeX block and links. The first is
`papers/bb-erasure-baselines.html`; copy it for the next one.

- `papers/<slug>.html`: hand-written, full mode, head, header and footer as on `research.html`,
  canonical `https://pandey-tushar.com/papers/<slug>.html`, og image `og-research.png`,
  `ScholarlyArticle` JSON-LD with the shared Person `@id`. Header block: title, authors, venue
  and year from papers.json, buttons arXiv, PDF, Code, All papers. Every factual sentence in the
  essay must trace to a line of the paper or a results file.
- `papers/paper.css`: the shared styles (`pc-` classes). `papers/js/plot.js`: shared SVG
  helpers (scales, ticks, markers). Page logic goes in `papers/js/<slug>.js`, pure maths in a
  module of its own with tests in `_studio/tools/tests/papers/`.
- `papers/data/<slug>.json`: the figure's data, written only by
  `_studio/tools/papers/extract_<slug>.py` from a clone of the paper's repository. It records
  the source files, the clone's commit and the extraction date; the page never holds hand-typed
  data points. A test in `_studio/tools/tests/papers/` compares the JSON with the source files
  (and skips, saying so, when the clone is absent; set the clone path in the env variable the test names).
- Figure rules: controls `hidden` until the script runs, a "needs JavaScript" line and a static
  sentence with the main result, "Show data as table", `aria-live` status, markers that differ
  by shape, both themes, no idle animation, no sideways scroll at 360px.
- In `_studio/content/papers.json` the paper's entry gets `"page": "/papers/<slug>.html"` and,
  if it names a code repository, `"code": "<url>"`; `build-research.py` then adds Companion page
  and Code links to its `research.html` entry. `check-research.py` fails if a declared page is
  missing, lacks its canonical, the arXiv link or a BibTeX `<pre>` with the arXiv id, has no link
  to `/research.html` inside `<main>`, or is not linked from `research.html`.
- Also add the page to `PAGES`, `FULL` and `OG` in `check-site.py`, to `sitemap.xml`, and its
  files to the must-exist list in `deploy.ps1`.

## Tools

`tools/bb-codes.html`, the bivariate bicycle code explorer: type l, m, A and B and it computes n, k, the check
weights and the Tanner graph's components, draws the layout, searches for an upper bound on the distance in a
worker, and exports H_X and H_Z; the code is kept in the query string. Hand-written, full mode, head, header and
footer as on `research.html`. The maths is in `tools/js/bb-math.js` (parsing, matrices, ranks; the presets from
Table 3 of arXiv:2308.07915) and `tools/js/bb-distance.js` (the search), with `bb-worker.js` and the page script
`bb-page.js`; the tests are `_studio/tools/tests/tools/`. They compare against `bb-reference.json`, written by
`make_bb_reference.py` there with numpy and ldpc. A new tool gets the same: `PAGES`, `FULL` and `OG` in
`check-site.py`, `sitemap.xml`, and its files in the must-exist list of `deploy.ps1`.

## Notes

`notes/<slug>.html`, the list `notes/index.html` and the RSS feed `notes/feed.xml` are generated:
add the note to `_studio/content/notes.json` (slug, title, date, description, body file, and an
optional data file) with its body in `_studio/content/notes/<slug>.md`, then run
`python _studio/tools/build-notes.py`. The body is a small subset of markdown (one h1, h2 headings,
paragraphs, inline links, one pipe table, reference lines `[1]` ...); anything else stops the build.
A note's table is rendered from its data file and the build fails if the markdown table disagrees.
The first note's data is written by `_studio/tools/notes/crossings.mjs` (fixed seeds, about 90 s).
Styles: `papers/paper.css` plus `notes/notes.css`. A new note also needs its page in `sitemap.xml`,
in `PAGES`, `FULL` and `OG` of `check-site.py`, and in the must-exist list of `deploy.ps1`.

## _studio

Source and tooling. Jekyll skips folders that start with an underscore, so
nothing in it is published. The editions are built from `_studio/apps/*`
(`npm run build` in `_studio`). Checks in `_studio/tools`, each exits non-zero on failure:

- `check-site.py`: shared head, icons, header, nav, one main and h1 on every page, share cards
  on disk at 1200x630, covers, portrait and emblems where they belong; prints `site ok`
- `check-research.py`: research.html and cv.html in step with papers.json, and each declared
  companion page in place; prints `research ok`
- `check-lessons.py`: lesson text, narrative and course links present without script, every course page
  with canonical, h1, cite line, a link back and the end-of-lesson link row, the index and sitemap in course order; prints `lessons ok`
- `check-notes.py`: each note page, the notes list and the RSS feed in step with notes.json and a
  fresh build, tables equal to their data, links resolving, the sitemap; prints `notes ok`
- `check-editions.py`: built editions carry their text; prints `editions ok`
- `check-qd.py`: qubit-dialogues.html loads lib/, stays small and its animation driver honours
  reduced motion (behaviour in `tests/qd/reduced-motion.test.mjs`); prints `qd ok`

`python _studio/tools/run-tests.py` runs all of them and every `tests/**/*.test.mjs` with
`node --test`, one line per suite.

Other tools: `build-lessons.py`, `build-research.py`, `build-notes.py`, `notes/crossings.mjs`, `og/render.py` (share cards),
`assets/*.py` (icons, covers, emblems, portrait), `compress-pdf.py`,
`pdf.mjs` (print the editions to PDF), `extract-content.mjs`, `papers/extract_*.py`
(companion page data), `deploy.ps1`.

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
