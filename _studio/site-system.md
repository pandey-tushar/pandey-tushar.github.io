# Site system

One identity for every published page, taken from the homepage. `lib/site.css` mirrors index.html's tokens (index.html keeps its own inline copy); `lib/site.js` runs the theme switch and marks the current nav item. `python _studio/tools/check-site.py` enforces this; books.html is the reference page.

## Head (paste first in `<head>`, after charset and viewport)

```html
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#0b1122">
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
<link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%3E%3Crect%20width='24'%20height='24'%20fill='%23070a14'/%3E%3Cg%20fill='none'%20stroke='%2352d6e6'%20stroke-width='1.4'%3E%3Ccircle%20cx='12'%20cy='7.6'%20r='5.4'/%3E%3Ccircle%20cx='8.2'%20cy='14.2'%20r='5.4'/%3E%3Ccircle%20cx='15.8'%20cy='14.2'%20r='5.4'/%3E%3C/g%3E%3C/svg%3E">
<link rel="stylesheet" href="/lib/site.css">
<script src="/lib/site.js" defer></script>
```

The pre-paint script is index.html's own, unchanged. Never write `qd-theme`; site.js moves an old qd-theme value onto tp-theme once and deletes it.

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

Do not set aria-current by hand; site.js does it (a link ending in `/` also marks every page under it). The nav is the same on every page. The homepage's in-page links (Quantum, AI, Writing) are not in it: with them the row cannot fit a 390px phone, and they are sections of one page, not places. On index.html, `#contact` stands for `/#contact`.

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

Pages in subfolders paste the same snippets: every URL is root-relative, so they resolve from any depth on the site and under `python -m http.server` at the repo root (not from file://). A Vite-built edition (life/, illustrated/) must keep `/lib/site.css` and `/lib/site.js` as literal URLs in its built index.html, not bundled copies; edit the source in `_studio/apps/*`, rebuild, deploy, then run check-editions.py.

## Two modes

Chrome-only (default, for qubit-dialogues.html, life/, illustrated/): link the stylesheet and paste the snippets. Only `tp-` classes are styled; tokens are `--tp-*` so the page's own `:root` variables, body and element rules are untouched. The page drops its own theme toggle and reads `html[data-theme]`, which it already does.

Full (books, cv, research, lessons, 404): also put `class="tp-full"` on `<html>`. The page then takes the homepage ground (night washes, paper in light), system sans body at .92rem, serif display h1 to h3, focus rings, selection, and `a` reset. Page CSS should then use `--tp-*` tokens, not its own colours.

## Classes

`tp-skip`, `tp-bar`, `tp-mark`, `tp-nav`, `tp-toggle`, `tp-foot` (chrome). `tp-wrap` (centred column on the header's gutter). `tp-lbl` (mono 12px caps label). `tp-btn` (homepage button with cut corners). `tp-link` (link in running text). `tp-lattice` (faint surface-code grid behind a block; uses the block's `::before`, so not on an element that has its own). `tp-plate` (figure in a thin ruled frame with cut corners, mono caption, `<figcaption><b>Plate I</b>Subject</figcaption>`); add `tp-plate-open` when the art draws its own frame.

## Tokens (`--tp-` + name; dark / light, equal to index.html)

| name | dark | light |
|---|---|---|
| void (ground) | #0b1122 | #eef1f8 |
| void2 | #16203f | #dbe2f0 |
| bar | #0d1428 | #e8ecf6 |
| ink | #e6ecff | #101828 |
| acc, cyan | #52d6e6 | #0a6f80 |
| violet | #9b7bff | #5233c4 |
| mag | #f06ab0 | #a8226a |
| dim | #8891b8 | #57617d |
| a08 a14 a22 a40 a70 | acc at .08 .15 .24 .42 .74 | acc at .09 .17 .27 .45 .78 |
| head (h1-h3) | #f4f7ff | #0b1220 |
| text (body copy) | ink at .9 | ink at .9 |
| sans, mono, serif | system stacks; serif is Iowan Old Style, Palatino Linotype, Palatino, Georgia | |

Also `--tp-gut`, `--tp-barh`, `--tp-t-display`, `--tp-t-h2`, `--tp-t-body`, `--tp-t-small`, `--tp-t-app` (12px). Contrast on the ground: body 13.0 / 12.1, dim 6.1 / 5.4, accent 10.9 / 5.2.

## Canvases

```js
document.addEventListener("tp-theme", function(e){ repaint(e.detail.theme); }); // detail: {theme: "light"|"dark", pref: "auto"|"light"|"dark"}
```
Read the initial theme from `document.documentElement.dataset.theme`. The event fires on every toggle click and on system changes while on auto.

## Page checklist

Skip link to `#main`; one `<main id="main">`; exactly one `<h1>` in the static HTML; the header and footer above; the head snippet (pre-paint, favicon, site.css, site.js); og:title, og:description, og:url, og:image and canonical; theme key tp-theme only; no Google Fonts; no text under 12px. Then `python _studio/tools/check-site.py`.
