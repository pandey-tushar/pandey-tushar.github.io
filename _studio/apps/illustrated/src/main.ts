import '@qubit/tokens/tokens.css';
/* No KaTeX here. This cut strips the mathematics in content.ts (see demath), so
   the 1.2 MB of KaTeX font files never enter the bundle. The text edition keeps
   the equations and the stylesheet that sets them. */
import './styles/illustrated.css';
/* after the edition's own sheet, so the paper overrides win */
import './styles/print.css';

import { en } from '@qubit/content';
import type { Canto } from '@qubit/content/schema';
import { artFor, type CantoArt } from './cantos/index.js';
import { apparatus, beatsOf, blockHtml, romanNumeral } from './content.js';
import { posterDataUrl, SceneDirector, type SceneHost } from './stage.js';

/* Built posters, if tools/posters.mjs has been run. The WebP set is the web
   layer; the full resolution PNGs stay the deliverable and the print masters.
   Anything missing is generated at runtime from the same renderer, so the page
   is never without its still frame either way. */
const built = import.meta.glob('../posters/web/*.webp', {
  eager: true, query: '?url', import: 'default',
}) as Record<string, string>;

const posterFile = new Map<number, string>();
for (const [path, url] of Object.entries(built)) {
  const m = /canto-(\d+)\.webp$/.exec(path);
  if (m) posterFile.set(Number(m[1]), url);
}

const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
document.documentElement.setAttribute('data-theme', 'dark');
document.documentElement.dataset.motion = reduced ? 'reduce' : 'full';

const el = <K extends keyof HTMLElementTagNameMap>(
  tag: K, cls?: string, html?: string,
): HTMLElementTagNameMap[K] => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html !== undefined) n.innerHTML = html;
  return n;
};

const hosts: SceneHost[] = [];
const posterSlots: Array<{ img: HTMLImageElement; art: CantoArt; canto: number }> = [];

/** A pinned stage plus its poster. The poster is in the DOM before any script
    decides whether a live canvas is coming. */
function makeStage(canto: number, art: CantoArt, track: HTMLElement): HTMLElement {
  const stage = el('div', 'stage');
  const inner = el('div', 'stage-inner');
  const img = el('img', 'poster');
  img.alt = '';
  img.decoding = 'async';
  img.setAttribute('aria-hidden', 'true');
  inner.append(img);
  stage.append(inner);
  posterSlots.push({ img, art, canto });
  hosts.push({ canto, art, track, stage: inner });
  return stage;
}

/* ---------- frontispiece ---------- */

const front = el('header', 'front');
const frontTrack = el('div', 'track front-track');
const frontArt = artFor(0);
if (frontArt) frontTrack.append(makeStage(0, frontArt, frontTrack));
frontTrack.append(el('div', 'front-type',
  '<p class="kicker">Illustrated edition</p>' +
  '<h1>The Qubit Dialogues</h1>' +
  '<p class="sub">Twenty two cantos between a Seeker and an Oracle, set as plates.</p>' +
  '<p class="cue">Scroll</p>',
));
front.append(frontTrack);
if (frontArt) front.append(el('p', 'legend', frontArt.legend));

/* ---------- cantos ---------- */

const book = el('main', 'book');
book.id = 'book';

function buildCanto(c: Canto): HTMLElement {
  const art = artFor(c.n);
  const article = el('article', 'canto');
  article.id = 'canto-' + String(c.n);
  article.dataset.canto = String(c.n);
  if (!art) article.dataset.unstyled = 'true';

  /* the title sits on the plate, the way a plate carries its own caption */
  const head =
    '<div class="canto-head">' +
    '<p class="numeral">Canto ' + romanNumeral(c.n) + '</p>' +
    '<h2>' + c.title + '</h2>' +
    (c.epigraph
      ? '<blockquote class="epigraph"><p>' + c.epigraph.text + '</p>' +
        '<cite>' + c.epigraph.attr + '</cite></blockquote>'
      : '') +
    '</div>';

  const track = el('div', 'track');
  track.dataset.canto = String(c.n);
  if (art) track.append(makeStage(c.n, art, track));

  const beats = el('div', 'beats');
  const groups = beatsOf(c, art?.beats);
  track.dataset.beats = String(groups.length);
  groups.forEach((blocks, i) => {
    const beat = el('section', 'beat');
    beat.dataset.beat = String(i + 1);
    const column = el('div', 'column');
    column.innerHTML = (i === 0 ? head : '') + blocks.map(blockHtml).join('');
    beat.append(column);
    beats.append(beat);
  });
  track.append(beats);

  if (c.movement) {
    article.append(el('div', 'movement-rule',
      '<p class="label">' + c.movement.label + '</p>' +
      '<p class="title">' + c.movement.title + '</p>',
    ));
  }
  article.append(track);
  if (art) article.append(el('p', 'legend', art.legend));

  const rest = apparatus(c);
  if (rest.length > 0) {
    const notes = el('section', 'apparatus');
    notes.innerHTML = rest.map(blockHtml).join('');
    article.append(notes);
  }
  return article;
}

for (const c of en) book.append(buildCanto(c));

/* ---------- rail ---------- */

const rail = el('nav', 'rail');
rail.setAttribute('aria-label', 'Cantos');
rail.innerHTML = en
  .map((c) => {
    const marked = artFor(c.n) ? ' is-composed' : '';
    return '<a class="mark' + marked + '" href="#canto-' + String(c.n) + '">' +
      '<span class="sr">' + romanNumeral(c.n) + '. ' + c.title + '</span></a>';
  })
  .join('');

const footer = el('footer', 'foot',
  '<p>The Qubit Dialogues, illustrated edition. Text by Tushar Pandey. ' +
  'Every plate is generated from a seed; the same seed draws the same picture on every machine.</p>' +
  '<p class="quiet">Local preview. Not published, not indexed.</p>',
);

const skip = el('a', 'skip', 'Skip to the first canto');
skip.href = '#canto-1';

document.body.append(skip, rail, front, book, footer);

/* ---------- posters ---------- */

function fillPoster(slot: { img: HTMLImageElement; art: CantoArt; canto: number }): void {
  if (slot.img.dataset.filled) return;
  slot.img.dataset.filled = '1';
  const file = posterFile.get(slot.canto);
  slot.img.src = file ?? posterDataUrl(slot.art);
}

/* the first two are needed on the first paint; the rest arrive as they near */
posterSlots.slice(0, 2).forEach(fillPoster);
const posterIo = new IntersectionObserver(
  (entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      const slot = posterSlots.find((s) => s.img === e.target);
      if (slot) fillPoster(slot);
      posterIo.unobserve(e.target);
    }
  },
  { rootMargin: '250% 0px 250% 0px' },
);
for (const slot of posterSlots) posterIo.observe(slot.img);

/* ---------- beats ---------- */

const beatEls = [...document.querySelectorAll<HTMLElement>('.beat')];
if (reduced) {
  for (const b of beatEls) b.classList.add('is-lit');
} else {
  const beatIo = new IntersectionObserver(
    (entries) => {
      for (const e of entries) e.target.classList.toggle('is-lit', e.isIntersecting);
    },
    { rootMargin: '-22% 0px -22% 0px', threshold: 0 },
  );
  for (const b of beatEls) beatIo.observe(b);
}

/* ---------- rail state ---------- */

const marks = [...rail.querySelectorAll<HTMLElement>('.mark')];
const railIo = new IntersectionObserver(
  (entries) => {
    for (const e of entries) {
      const n = Number((e.target as HTMLElement).dataset.canto);
      const mark = marks[n - 1];
      if (mark) mark.classList.toggle('is-here', e.isIntersecting);
    }
  },
  { rootMargin: '-45% 0px -45% 0px', threshold: 0 },
);
for (const a of book.querySelectorAll<HTMLElement>('article.canto')) railIo.observe(a);

/* ---------- scenes ---------- */

/* The reduced motion edition is complete and static: every composed canto
   shows its signature frame as an image and every beat of text is visible.
   No canvas is mounted, no scroll listener runs, nothing animates. */
declare global {
  interface Window { __illustrated?: { director: SceneDirector | null; reduced: boolean } }
}

const director = reduced ? null : new SceneDirector(hosts, 3);
window.__illustrated = { director, reduced };
