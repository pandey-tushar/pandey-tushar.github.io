/* Build-time HTML. Runs in node during `vite build`, never in the browser, so
   the shipped page carries real headings and real links instead of waiting for
   a script. Fields named `rich` are trusted markup from src/content; every
   other string is escaped. */

import type { Cta, Note, NavLink, PageMeta } from './content/types.ts';
import * as C from './content/site.ts';

const esc = (s: string): string =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const ext = (e?: boolean): string => (e ? ' target="_blank" rel="noopener"' : '');

const link = (l: NavLink | Cta, cls?: string): string =>
  '<a' + (cls ? ' class="' + cls + '"' : '') + ' href="' + esc(l.href) + '"' + ext(l.external) + '>' +
  esc(l.label) + '</a>';

/** heading split so the second half takes the gradient italic */
const split = ([a, b]: [string, string]): string => esc(a) + '<em>' + esc(b) + '</em>';

/** the caption line this section hands to the scene, as data attributes */
const actAttr = (a?: string, at?: number): string =>
  a ? ' data-act="' + esc(a) + '" data-act-at="' + (at ?? 0.45) + '"' : '';

export function head(m: PageMeta): string {
  return [
    '<title>' + esc(m.title) + '</title>',
    '<meta name="description" content="' + esc(m.description) + '" />',
    '<link rel="canonical" href="' + esc(m.canonical) + '" />',
    '<meta property="og:title" content="' + esc(m.ogTitle) + '" />',
    '<meta property="og:description" content="' + esc(m.ogDescription) + '" />',
    '<meta property="og:type" content="website" />',
    '<meta property="og:url" content="' + esc(m.canonical) + '" />',
    '<meta property="og:image" content="' + esc(m.ogImage) + '" />',
    '<meta property="og:image:width" content="1200" />',
    '<meta property="og:image:height" content="630" />',
    '<meta name="twitter:card" content="summary_large_image" />',
    '<meta name="twitter:image" content="' + esc(m.ogImage) + '" />',
  ].join('\n');
}

function header(): string {
  return '<header id="hdr"><nav>' +
    '<a class="brand" href="#top">' + esc(C.brand.first) + ' <span>' + esc(C.brand.last) + '</span></a>' +
    '<div class="nav-right">' +
    '<div class="navlinks" id="navlinks">' + C.nav.map((l) => link(l)).join('') + '</div>' +
    /* the chip stays outside the collapsible list so it is reachable on a phone */
    '<button class="theme-btn" id="themeBtn" type="button" aria-label="Switch to the paper theme">' +
    esc(C.theme.toLight) + '</button>' +
    '<button class="menu-btn" id="menuBtn" type="button" aria-label="Toggle menu" aria-expanded="false" aria-controls="navlinks">menu</button>' +
    '</div></nav></header>';
}

function hero(): string {
  const h = C.hero;
  return '<section class="hero" id="top">' +
    '<picture><source srcset="/hero-poster-narrow.svg" media="(max-width: 899px)" width="800" height="1400" />' +
    '<img id="poster" src="/hero-poster.svg" alt="" width="1600" height="900" fetchpriority="high" decoding="sync" /></picture>' +
    '<div class="wrap">' +
    '<p class="hero-eyebrow">' + esc(h.eyebrow) + '</p>' +
    '<h1>' + esc(h.name[0]) + '<br><em>' + esc(h.name[1]) + '</em></h1>' +
    '<p class="lede">' + esc(h.lede) + '</p>' +
    '<p class="hero-whisper">' + esc(h.whisper.text) + ' <b>' + esc(h.whisper.strong) + '</b></p>' +
    '<div class="meta-row">' +
    h.facts.map((f) => '<span><b>' + esc(f.key) + '</b> &nbsp;' + esc(f.value) + '</span>').join('') +
    '</div>' +
    '<div class="cta-row">' +
    h.ctas.map((c) => link(c, 'btn' + (c.primary ? ' primary' : ''))).join('') +
    '</div></div>' +
    '<div class="hint">' + esc(h.hint) + '</div>' +
    '<div class="scroll-cue">' + esc(h.scrollCue) + '</div>' +
    '</section>';
}

function chapters(): string {
  return C.chapters.map((c) =>
    '<section class="chapter" id="' + c.id + '"' + actAttr(c.act, c.actAt) + '><div class="wrap">' +
    '<div class="box' + (c.side === 'right' ? ' right' : '') + ' reveal">' +
    '<div class="ghost" aria-hidden="true">' + esc(c.ghost) + '</div>' +
    '<p class="ch-eyebrow">' + esc(c.eyebrow) + '</p>' +
    '<h2>' + split(c.heading) + '</h2>' +
    '<p class="ch-lede">' + c.lede + '</p>' +
    (c.more ? link(c.more, 'ch-more') : '') +
    '</div></div></section>').join('');
}

const dateLabel = (iso: string): string =>
  new Date(iso + 'T00:00:00Z').toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC',
  });

function writing(notes: Note[]): string {
  const w = C.writing;
  const list = notes.length
    ? '<ul class="notes">' + notes.map((n) =>
        '<li><a href="notes/' + esc(n.slug) + '/">' +
        '<span class="note-date"><time datetime="' + esc(n.date) + '">' + esc(dateLabel(n.date)) + '</time></span>' +
        '<span class="note-title">' + esc(n.title) + '</span>' +
        '<span class="note-sum">' + esc(n.summary) + '</span></a></li>').join('') + '</ul>'
    : '<p class="note-empty">' + esc(w.empty) + '</p>';
  return '<section class="writing" id="' + w.id + '"><div class="wrap">' +
    '<div class="box reveal">' +
    '<div class="ghost" aria-hidden="true">' + esc(w.ghost) + '</div>' +
    '<p class="ch-eyebrow">' + esc(w.eyebrow) + '</p>' +
    '<h2>' + split(w.heading) + '</h2>' +
    '<p class="ch-lede">' + esc(w.lede) + '</p>' + list +
    link({ label: w.feed.label, href: w.feed.href }, 'ch-more') +
    '</div></div></section>';
}

function namesBand(): string {
  return '<section class="names reveal" id="wins"><div class="wrap">' +
    C.names.map((n) => '<span>' + esc(n) + '</span>').join('') +
    '</div></section>';
}

function contact(): string {
  const c = C.contact;
  return '<section class="contact" id="' + c.id + '"' + actAttr(c.act, c.actAt) + '><div class="wrap"><div class="inner">' +
    '<div class="pitch">' +
    '<p class="ch-eyebrow reveal">' + esc(c.eyebrow) + '</p>' +
    '<h2 class="reveal">' + split(c.heading) + '</h2>' +
    '<p class="receipt reveal">' + c.receipt + '</p>' +
    '</div><div class="contact-links reveal">' +
    C.contactLinks.map((l) =>
      '<a href="' + esc(l.href) + '"' + ext(l.external) + '>' +
      '<span class="lbl">' + esc(l.label) + '</span> ' + esc(l.text) + '</a>').join('') +
    '</div></div></div></section>';
}

function foot(): string {
  return '<footer><div class="wrap">' +
    '<span>© <span id="yr">' + new Date().getFullYear() + '</span> ' +
    esc(C.brand.first + ' ' + C.brand.last) + '</span>' +
    '<span>' + esc(C.footer.colophon) + '</span>' +
    '</div></footer>';
}

/** The whole home page body, minus the module script vite appends. */
export function body(notes: Note[]): string {
  return '<div id="act" aria-hidden="true">' + esc(C.intro.sub) + '</div>' +
    header() + '<main>' + hero() + chapters() + writing(notes) + namesBand() + contact() + '</main>' +
    foot();
}

/** A single note page. Reuses the site shell so a post is never a fork. */
export function notePage(n: Note, script: string, css: string, analytics: string): string {
  const m: PageMeta = {
    title: n.title + ' · ' + C.brand.first + ' ' + C.brand.last,
    description: n.summary,
    canonical: C.ORIGIN + '/notes/' + n.slug + '/',
    ogTitle: n.title,
    ogDescription: n.summary,
    ogImage: C.ORIGIN + '/og/notes-' + n.slug + '.png',
  };
  return '<!DOCTYPE html>\n<html lang="en" data-theme="dark">\n<head>\n' +
    '<meta charset="UTF-8" />\n' +
    '<meta name="viewport" content="width=device-width, initial-scale=1" />\n' +
    "<script>try{var t=localStorage.getItem('qd-theme');" +
    "document.documentElement.setAttribute('data-theme',t==='light'?'light':'dark');}catch(e){}</script>\n" +
    analytics + '\n' +
    head(m) + '\n' +
    '<link rel="alternate" type="application/rss+xml" title="Tushar Pandey · Notes" href="/feed.xml" />\n' +
    '<link rel="preconnect" href="https://fonts.googleapis.com" />\n' +
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n' +
    '<link rel="stylesheet" href="' + esc(C.fonts) + '" media="print" onload="this.media=\'all\'" />\n' +
    '<style>' + css + '</style>\n' +
    '</head>\n<body class="note-body">\n' +
    header() +
    '<main class="note wrap"><article>' +
    '<p class="ch-eyebrow"><time datetime="' + esc(n.date) + '">' + esc(dateLabel(n.date)) + '</time> · ' +
    n.minutes + ' min</p>' +
    '<h1>' + esc(n.title) + '</h1>' + n.html +
    '</article><p class="note-back"><a class="ch-more" href="/#writing">back to notes →</a></p></main>' +
    foot() +
    '<script type="module" src="' + script + '"></script>\n</body>\n</html>\n';
}
