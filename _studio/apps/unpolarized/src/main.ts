/* An Unpolarized Life. Same reader as apps/book, different data.

   The edition validates at import time, the same contract @qubit/content gives
   en.json, from its own entry point so that neither edition carries the
   other's JSON. */
import { unpolarized, frontUnpolarized } from '@qubit/content/unpolarized';
import { esc, mountReader } from '@qubit/reader';
import { heroElement, liveHero } from '@qubit/reader/hero';
import './life.css';

/* This book has no scene blocks and no science asides, so no scene mounter is
   passed. The reader core never imports the registry, so three.js and the
   scene chunks are not in this app's module graph at all. It calls its parts
   chapters, and says so through `labels` in front.unpolarized.json. */
/* index.html ships the whole text as plain markup, in its <main>, for anything
   that runs no script (see ../static.ts). The reader builds the real page, so
   that copy goes. */
document.getElementById('main')?.remove();
mountReader({ cantos: unpolarized, front: frontUnpolarized });

/* The site header carries the theme switch (/lib/site.js, key tp-theme), so
   the reader's own chip goes, and with it the loading veil. The reader's main
   takes the skip link's target, and its closing colophon stops being a second
   contentinfo landmark. */
document.getElementById('theme-toggle')?.remove();
document.getElementById('loader')?.remove();
const main = document.getElementById('content');
if (main) main.id = 'main';
document.querySelector('#book > footer')?.setAttribute('role', 'none');

/* The reader's cover gives way to the opening window of the homepage's book
   panes: the circles field, the cover lit in it, the title, the subtitle set
   as a title, and the ways in. A contents list opens the book after it. */
const title = (s: string): string => s.toLowerCase().split(' ')
  .map((w, i) => (i > 0 && ['a', 'of', 'and', 'the'].includes(w) ? w : w.charAt(0).toUpperCase() + w.slice(1)))
  .join(' ');

const book = document.getElementById('book');
document.getElementById('cover')?.remove();
if (book) {
  const hero = heroElement({
    tag: 'Book', title: frontUnpolarized.cover.title, line: title(frontUnpolarized.cover.sub), cover: 'an-unpolarized-life',
    start: { href: '#invocation', label: 'Begin reading' },
    more: [{ href: '#contents', label: 'Contents' }, { href: '/an-unpolarized-life.pdf', label: 'PDF' }],
  });
  book.before(hero);
  liveHero(hero, 'polar');

  const items = unpolarized.map((c) =>
    (c.movement ? '<li class="mv">' + esc(c.movement.title) + '</li>' : '') +
    '<li><a href="#canto-' + c.n + '"><span class="n">' + c.n + '</span><span class="t">' +
    esc(c.title) + '</span></a></li>').join('');
  const toc = document.createElement('nav');
  toc.className = 'contents';
  toc.id = 'contents';
  toc.setAttribute('aria-labelledby', 'contents-h');
  toc.innerHTML = '<h2 id="contents-h">Contents</h2><ol>' +
    '<li><a href="#invocation"><span class="n"></span><span class="t">' +
    esc(frontUnpolarized.invocation.title) + '</span></a></li>' + items +
    '<li class="mv">' + esc(frontUnpolarized.appendix.label) + '</li>' +
    '<li><a href="#references"><span class="n"></span><span class="t">' +
    esc(frontUnpolarized.appendix.title) + '</span></a></li></ol>';
  book.prepend(toc);

  /* a chapter entry opens its chapter through its own head, then lands on it */
  toc.addEventListener('click', (e) => {
    const a = (e.target as Element).closest('a[href^="#canto-"]');
    const sec = a && document.getElementById(a.getAttribute('href')!.slice(1));
    const head = sec?.querySelector<HTMLElement>('.canto-head');
    if (!sec || !head) return;
    e.preventDefault();
    if (!sec.classList.contains('expanded')) head.click();
    sec.scrollIntoView();
    head.focus({ preventScroll: true });
    history.replaceState(null, '', '#' + sec.id);
  });
}

/* the edition links and the site footer close the page, after the book */
const end = document.getElementById('end');
if (end) document.body.append(end);
