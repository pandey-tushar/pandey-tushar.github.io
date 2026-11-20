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

Headings: the serif stack ("Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua", Georgia), weight 400. Body: the system sans stack. No web fonts. Running text is held to a 60 to 72 character measure. Monospace (`--tp-mono`, or class `tp-id`) only for real identifiers: arXiv ids, DOIs, code, gate labels in the lessons. Eyebrow labels (`tp-lbl`) are sans, uppercase, 600, 0.07em tracking, and used sparingly: one per block at most. No gradient text, no glow, no starfield or grid wash, no backdrop blur, no violet-to-pink ramps; check-site.py rejects gradient text, backdrop-filter and the old lattice wash on full-mode pages.

## Figures

Crisp line art in inline SVG: strokes about 1.25px (`vector-effect:non-scaling-stroke` keeps them crisp at any size), ink for the drawing, the accent for what the eye should follow, warm only for the one highlighted thing (an error, a lit check, the expanded node). Every figure depicts something true about the work it sits beside, and carries a caption in the manner of a paper, led by its number: `<figcaption><b>Fig. 2</b>What it shows.</figcaption>` (the full stop after the number is added by CSS). A figure that animates does so only in response to the reader, never while idle, and not at all under `prefers-reduced-motion`.

## Classes

`tp-skip`, `tp-bar`, `tp-mark`, `tp-nav`, `tp-toggle`, `tp-foot` (chrome). `tp-wrap` (the centred 72rem column). `tp-lbl` (eyebrow label). `tp-btn` (a quiet bordered button on the surface colour). `tp-link` (accent link in running text, underlined). `tp-id` (an identifier in mono). `tp-plate` (a figure on a raised panel with a hairline and a paper caption); add `tp-plate-open` for art that stands on the page without the panel.

Images: book covers in `img/covers/` (`<slug>-300.webp` with a 600w `<slug>.webp` in srcset, on a hairline); research-area emblems in `img/figures/` (viewBox 120, ink in currentColor, `var(--tp-acc)` and `var(--tp-warm)` for the highlight), inlined by build-research.py so they follow the theme; the portrait `img/tushar-pandey-b.webp` (640) and `-b-320.webp`. All are drawn by the scripts in `_studio/tools/assets/`.

## Canvases and scripted figures

```js
document.addEventListener("tp-theme", function(e){ repaint(e.detail.theme); }); // detail: {theme: "light"|"dark", pref: "auto"|"light"|"dark"}
```
Read the initial theme from `document.documentElement.dataset.theme`. The event fires on every toggle click and on system changes while on auto. SVG figures styled with the tokens need no repaint.

## Page checklist

Skip link to `#main`; one `<main id="main">`; exactly one `<h1>` in the static HTML; the header and footer above; the head snippet (pre-paint, the three icon links, site.css, site.js); og:title, og:description, og:url, og:image (a 1200x630 PNG in the repo, with og:image:width, og:image:height and twitter:image) and canonical; theme key tp-theme only; no Google Fonts; no text under 12px. Then `python _studio/tools/check-site.py`, and for the homepage `python _studio/tools/check-perf.py` (main-thread time under 300 ms/s idle, scrolling and working the lattice figure; nothing animating while idle).
