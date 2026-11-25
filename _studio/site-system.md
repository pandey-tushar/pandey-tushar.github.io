# Site system

One identity for every published page: figures from a well-typeset paper. Paper and ink, one accent for links and figure highlights, a warm second ink only for the highlighted thing in a figure. `lib/site.css` holds every token and shared class; `lib/site.js` runs the theme switch and marks the current nav item. Every page, the homepage included, links both. `python _studio/tools/check-site.py` enforces this file: the token table below is the source of truth for the values in `lib/site.css`, and the check fails if they drift or if any text colour falls under WCAG AA on either ground.

## Head (paste first in `<head>`, after charset and viewport)

```html
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#0d1320">
<script>
(function(){
  var d = document.documentElement;
  try{
    var pref = localStorage.getItem("tp-theme");
    if (pref !== "light" && pref !== "dark") pref = "auto";
    d.dataset.pref = pref;
    d.dataset.theme =
      (pref === "auto" ? matchMedia("(prefers-color-scheme: light)").matches : pref === "light")
        ? "light" : "dark";
  }catch(e){ d.dataset.pref = "auto"; d.dataset.theme = "dark"; }
})();
</script>
<link rel="icon" href="/favicon.ico" sizes="16x16 32x32 48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/lib/site.css">
<script src="/lib/site.js" defer></script>
```

The pre-paint script settles the theme before first paint. Never write `qd-theme`; site.js moves an old qd-theme value onto tp-theme once and deletes it. site.js also keeps `theme-color` in step (paper or night ground): the static value is the dark `void`, the pre-paint fallback, and site.js swaps it for the light `void` on the paper theme, so a page carries exactly one theme-color meta. The icons are files at the root, drawn by `_studio/tools/assets/icons.py`; favicon.svg follows the system scheme on its own.

## Header (first thing in `<body>`)

```html
<a class="tp-skip" href="#main">Skip to content</a>
<header class="tp-bar">
  <a class="tp-mark" href="/" aria-label="Tushar Pandey, home">
    <svg width="19" height="19" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <g fill="none" stroke="#52d6e6" stroke-width="1.05" opacity=".9">
        <circle cx="12" cy="7.6" r="5.4"/><circle cx="8.2" cy="14.2" r="5.4"/><circle cx="15.8" cy="14.2" r="5.4"/>
      </g>
    </svg>
    <span>Tushar Pandey</span>
  </a>
  <nav class="tp-nav" aria-label="Primary">
    <a href="/research.html">Research</a>
    <a href="/books.html">Books</a>
    <a href="/qec-in-practice/">Lessons</a>
    <a href="/cv.html">CV</a>
    <a href="/#contact">Contact</a>
  </nav>
  <button class="tp-toggle" type="button" aria-label="Switch theme"><b aria-hidden="true">&#9680;</b><span>Auto</span></button>
</header>
```

The mark's stroke in the markup is overridden by the accent in site.css. Do not set aria-current by hand; site.js does it (a link ending in `/` also marks every page under it). The nav is the same on every page and fits a 390px phone as one row that scrolls sideways; on the homepage `/#contact` is its own section.

## Footer (last thing in `<body>`)

```html
<footer class="tp-foot">
  <ul>
    <li><a href="/">Home</a></li>
    <li><a href="/research.html">Research</a></li>
    <li><a href="/books.html">Books</a></li>
    <li><a href="/qec-in-practice/">Lessons</a></li>
    <li><a href="/cv.html">CV</a></li>
    <li><a href="https://github.com/pandey-tushar" rel="noopener">GitHub</a></li>
    <li><a href="mailto:wtatushar@gmail.com">Email</a></li>
  </ul>
  <p>&copy; 2026 Tushar Pandey</p>
</footer>
```

Every URL is root-relative, so the snippets work from any depth on the site and under `python -m http.server` at the repo root (not from file://). A Vite-built edition (life/, illustrated/) keeps `/lib/site.css` and `/lib/site.js` as literal URLs in its built index.html; edit the source in `_studio/apps/*`, rebuild, deploy, then run check-editions.py. The homepage source is `_studio/prototypes/site-full/index.html`; `_studio/tools/deploy.ps1` copies it to the root and check-site.py fails if the two differ.

## Two modes

Chrome-only (default, for qubit-dialogues.html, life/, illustrated/): link the stylesheet and paste the snippets. Only `tp-` classes are styled; the page's own `:root` variables, body and element rules are untouched. The page reads `html[data-theme]` and has no toggle of its own.

Full (home, books, cv, research, lessons, notes, 404): also put `class="tp-full"` on `<html>`. The page then takes the plain paper ground (no washes, no grid), body type, serif h1 to h3, focus rings, selection and the `a` reset, and the header and footer sit on the `.tp-wrap` column. Page CSS uses `--tp-*` tokens, never its own colours, except a section's own figure inks (the lessons' X and Z checks).

## Tokens (`--tp-` + name)

| token | role | dark | light |
|---|---|---|---|
| `void` | paper, the page ground | #0d1320 | #f7f4ed |
| `void2` | raised surface: figure panels, buttons | #131b2b | #fffdf8 |
| `bar` | header ground | #0d1320 | #f7f4ed |
| `ink` | headings, strong text, figure line | #e9eef5 | #16202e |
| `head` | h1 to h3 | #e9eef5 | #16202e |
| `text` | running text | #d3dbe6 | #253040 |
| `dim` | muted text, labels, captions | #97a3b4 | #5a6472 |
| `rule` | hairlines and borders | #263247 | #d9d3c4 |
| `acc` | links, figure highlights | #5fd0de | #0b6e7f |
| `cyan` | old name for `acc` | #5fd0de | #0b6e7f |
| `warm` | the highlighted thing in a figure: errors, syndromes | #f0a35e | #b4541a |

`a08 a14 a22 a40 a70` are the accent at those alphas, for tints and link underlines. Contrast (WCAG, computed by check-site.py): on paper, light ink 14.9, text 12.1, dim 5.5, acc 5.4, warm 4.5; dark ink 15.9, text 13.3, dim 7.3, acc 10.2, warm 8.9. Warm in light is the closest to the 4.5 floor, so it stays out of small running text except as a figure's status word.

Also `--tp-gut`, `--tp-barh`, `--tp-measure` (68ch), `--tp-t-display`, `--tp-t-h2`, `--tp-t-body` (1rem: 17px on a desktop, 16px on a phone), `--tp-t-small`, `--tp-t-app` (eyebrow labels, about 13px). No text under 12px anywhere.

## Type

Headings: the serif stack ("Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua", Georgia), weight 400. Body: the system sans stack. The only web fonts are Geist and Geist Mono, self-hosted in `lib/fonts/` and declared by `@font-face` in site.css for every page; a page fetches them only if its CSS names them (the homepage sets `--tp-sans` and `--tp-mono` to them). No Google Fonts. Running text is held to a 60 to 72 character measure. Monospace (`--tp-mono`, or class `tp-id`) only for real identifiers: arXiv ids, DOIs, code, gate labels in the lessons. Eyebrow labels (`tp-lbl`) are sans, uppercase, 600, 0.07em tracking, and used sparingly: one per block at most. No gradient text, no glow, no starfield or grid wash, no backdrop blur, no violet-to-pink ramps; check-site.py rejects gradient text, backdrop-filter and the old lattice wash on full-mode pages.

## Figures

Crisp line art in inline SVG: strokes about 1.25px (`vector-effect:non-scaling-stroke` keeps them crisp at any size), ink for the drawing, the accent for what the eye should follow, warm only for the one highlighted thing (an error, a lit check, the expanded node). Every figure depicts something true about the work it sits beside, and carries a caption in the manner of a paper, led by its number: `<figcaption><b>Fig. 2</b>What it shows.</figcaption>` (the full stop after the number is added by CSS). A figure that animates does so only in response to the reader, never while idle, and not at all under `prefers-reduced-motion`; the exception is a canvas run by `TP.live` (below), which keeps to its frame budget.

## Classes

`tp-skip`, `tp-bar`, `tp-mark`, `tp-nav`, `tp-toggle`, `tp-foot` (chrome). `tp-wrap` (the centred 72rem column). `tp-lbl` (eyebrow label). `tp-btn` (a quiet bordered button on the surface colour). `tp-link` (accent link in running text, underlined). `tp-id` (an identifier in mono). `tp-plate` (a figure on a raised panel with a hairline and a paper caption); add `tp-plate-open` for art that stands on the page without the panel. `tp-pane`, `tp-rail` and `tp-sheet` with their parts (see Panes, rail and sheet below). `tp-geist`, `tp-hero`, `tp-coda` and `tp-print-sheets` (see Hero, coda and Geist).

Images: book covers in `img/covers/` (`<slug>-300.webp` with a 600w `<slug>.webp` in srcset, on a hairline); research-area emblems in `img/figures/` (viewBox 120, ink in currentColor, `var(--tp-acc)` and `var(--tp-warm)` for the highlight), inlined by build-research.py so they follow the theme; the portrait `img/tushar-pandey-b.webp` (640) and `-b-320.webp`. All are drawn by the scripts in `_studio/tools/assets/`.

## Canvases and scripted figures

```js
document.addEventListener("tp-theme", function(e){ repaint(e.detail.theme); }); // detail: {theme: "light"|"dark", pref: "auto"|"light"|"dark"}
```
Read the initial theme from `document.documentElement.dataset.theme`. The event fires on every toggle click and on system changes while on auto. SVG figures styled with the tokens need no repaint.

`TP.live.fig` (site.js) holds the shared figure fields, so every page draws from one vocabulary: a `<canvas data-fig="name" aria-hidden="true">` is mounted on load, as a field over the whole box quieted near the words when it sits in a `tp-hero` or a `tp-pane`, and drawn plainly anywhere else (a sheet). The fields: `lattice` (a toric code with errors corrected, lit near the pointer; a hero), `toric` (the same, past the edges), `tokens` (three tenants' requests streaming through a grid), `semion` (errors paired on a honeycomb), `graph` (a thought branching down a graph), `knot` (one Lissajous knot diagram, crossings drifting), `bloch` (Bloch spheres precessing), `polar` (three circles and their common region), `plate` (engraved spheres under a moving light), `rep` (repetition codes, a flip and its two checks), `circuit` (wires and gates, a run to a measurement), `primes` (the integers in rows, a twin pair joined), `prose` (lines of dialogue in two voices, one read to its question), `crossing` (three code distances' lines crossing at one point), `surface` (a rotated surface code, an error and its checks), `seam` (the same, two patches merged along a column of checks), `bell` (Bell pairs, a state teleported along one) and `timeline` (lanes of spans, one drawn to its milestone). A canvas[data-live] is left to the page's own script (the homepage keeps its own copies). `TP.live.kit` exposes the helpers (words, calm, room, cover, layer, mask, hush, lit, drawEvent, walk, segs) for a page's own figure. Never name a scene property `g`, `cv`, `t`, `w`, `h`, `d` or `on`: `TP.live` owns them.

`TP.live` (site.js) runs canvas figures so a page can feel live and stay light. `TP.live.add(canvas, scene)` takes a scene `{still, dpr, setup(w, h), step(dt), draw(g, w, h, t)}`; one loop at about 30 fps paints only scenes on screen (so a pane scrolled away keeps its last frame), stops in a hidden tab, runs only the scenes inside an open sheet while one is open, and under reduced motion paints each once at `t = still`. A full-window canvas should set `dpr` to 1.5. `TP.live.C` holds the token colours (kept current on `tp-theme`), `TP.live.rgba(hex, a)` tints one, `TP.live.clamp` and `TP.live.ss` (smoothstep) are there for easing. Register scenes on `DOMContentLoaded`, since site.js is deferred. Draw on a transparent canvas: cut gaps with `destination-out` rather than painting the ground colour, so the figure sits on any surface.

## Panes, rail and sheet

`tp-pane` is one entry the size of the window under the header (`100svh` less `--tp-barh`, at least 34rem), in a run the reader scrolls through. First `tp-pane-viz`, the pane's background: a canvas run by `TP.live` filling the whole pane, and optionally an `img.tp-pane-cover` (a book's cover, which the page's script stands in the room the words leave by setting `--x`, `--y` and `--h`; it stays hidden until placed). Then, laid over it, `tp-pane-in tp-wrap` holding `tp-pane-text` with `tp-pane-tag` (a small mono category), `h2.tp-pane-name` (the entry's name, Geist 600, large), `tp-pane-line` (one short phrase, never a second sentence) and one `a.tp-pane-open` ("Open", with an `aria-label` naming the entry, usually `href="#slug"` to a sheet; it covers the whole pane, so a click anywhere opens it). A soft scrim from the words' corner (`tp-pane-viz::after`) and a figure drawn quiet near the words keep them legible; no boxes behind text. Every pane's figure is one kind of field: dim structure running past every edge at one density, quieted near the words, with warm for the highlighted thing, the accent for paths and ink for the rest, all at the same calm pace; never an object set in the room the words leave (only a cover is). Vary where the words sit so a run has rhythm, never the same place twice in a row: bottom left (default), centre left (`tp-pane-mid`), bottom right (`tp-pane-end`) or top left (`tp-pane-top`). On a phone the words always sit at the bottom. A page with panes gets `scroll-padding-top` for the header and a gentle `scroll-snap-type: y proximity` (never mandatory), off under reduced motion; give the top of the page and the footer their own snap alignment so the snap never holds the reader back from them. No heading above a run.

`tp-rail` is a `<nav class="tp-rail" aria-label="Panes">` of links, one per pane, each `<a href="#pane-id"><span>Name</span></a>`: thin ticks at the right edge, the current one longer and in the accent, the name shown on hover or focus. site.js marks the pane that holds the middle of the window with `aria-current` and shows the rail while any pane does; it stays reachable by Tab throughout, and is hidden on a phone.

`tp-sheet` is a full-screen `<dialog class="tp-sheet" id="slug" aria-labelledby="slug-t">` holding the detail: `tp-sheet-bar` (with `tp-sheet-tag` and a `button.tp-sheet-close`), then `tp-sheet-in tp-wrap` with `tp-sheet-media` (a canvas, an svg, or `tp-sheet-cover` with a cover image) and `tp-sheet-body` (an h2, `tp-sheet-sub`, the text, and `tp-sheet-links`: one link per row, a `<small>` after the label naming where it goes). `TP.sheet` (site.js) needs no setup: any link to `#slug` opens the sheet, grown out of the link; the hash names the open sheet, so it can be linked, and the back button, Esc and the close button close it, returning focus to the link. `TP.sheet.open(id)` and `TP.sheet.close()` do the same from script; the dialog fires `tp-sheet-open` and `tp-sheet-close`. An id inside a sheet works as a link too: `#entry` opens the sheet that holds it, scrolled to it, so an entry folded into a sheet keeps its old address (research.html#paper-id, cv.html#h-experience). A sheet holding several entries gives each a `tp-sheet-item` (an `article` with an `h3`, a `tp-sheet-spec` `dl` of short facts and its own `tp-sheet-links`), or lists rows in `tp-sheet-rows` (`li` with a `tp-sheet-when` first); its media stays in view beside them on a wide screen. `<html class=".. tp-print-sheets">` prints the sheets in place as a plain document instead of the panes (the CV, research). The markup of all three is in the comments in site.css; the homepage is the reference use.

## Hero, coda and Geist (every page with panes)

`<html class="tp-full tp-geist">` gives a page the homepage's type: Geist for the body and headings (weight 500), Geist Mono for tags and labels. `tp-hero` opens such a page: a `<section class="tp-hero" aria-label="Introduction">` holding a `canvas[data-fig]` that fills it (the window under the header, as the homepage's), then `tp-hero-in tp-wrap` with `tp-hero-text`: `tp-hero-tag` (a short mono tag after the lattice-edge mark), the page's one `h1`, `tp-hero-lede`, optional `tp-hero-note` lines and `tp-hero-actions` (`tp-btn`, the first `pri`). A soft scrim from the words' corner keeps them legible. Then the run of panes, its rail and sheets, and, when something belongs to the whole page (a note on sources, how to cite), a short `tp-coda` band before the footer. Contact appears only on the homepage, or where a page already carries it (the CV). The hubs (research, books, CV, notes, the course, 404) are built this way; each pane names one entry (a research area, a book, a CV section, a note, a page of the course), with one line taken from the entry itself.

## Page checklist

Skip link to `#main`; one `<main id="main">`; exactly one `<h1>` in the static HTML; the header and footer above; the head snippet (pre-paint, the three icon links, site.css, site.js); og:title, og:description, og:url, og:image (a 1200x630 PNG in the repo, with og:image:width, og:image:height and twitter:image) and canonical; theme key tp-theme only; no Google Fonts; no text under 12px. Then `python _studio/tools/check-site.py`.
