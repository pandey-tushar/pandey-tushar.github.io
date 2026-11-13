/* A plain summary of the edition, written into index.html at build time.

   The page is built in the browser, so the HTML a crawler fetches used to be
   an empty body. The prose itself is not repeated here: it is the text of the
   main edition, and two full copies would only compete. This names the book,
   lists its cantos, and points at the text edition. It is the page's one
   <main>, under the site header; main.ts removes it before it builds the page. */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import type { Plugin } from 'vite';
import type { Canto } from '@qubit/content/schema';

const esc = (s: string): string =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const STYLE = '<style>#static-book{max-width:68ch;margin:0 auto;padding:0 1.5rem}' +
  '#static-book>header{min-height:100vh;display:grid;place-content:center;text-align:center}</style>';

export function staticBook(): string {
  const cantos = JSON.parse(
    readFileSync(fileURLToPath(new URL('../../content/en.json', import.meta.url)), 'utf8'),
  ) as Canto[];
  /* the frontispiece lines, as main.ts sets them */
  return '<div id="static-book">' +
    '<header><p>Illustrated edition</p><h1>The Qubit Dialogues</h1>' +
    '<p>Twenty two cantos between a Seeker and an Oracle, set as plates.</p></header>' +
    '<ol>' + cantos.map((c) => '<li>' + esc(c.title) + '</li>').join('') + '</ol>' +
    '<p>The full text, with its mathematics and interactive figures, is in the ' +
    '<a href="../qubit-dialogues.html">text edition</a>.</p></div>';
}

export const staticBookPlugin = (): Plugin => ({
  name: 'static-book',
  transformIndexHtml: (html, ctx) =>
    ctx.path.endsWith('poster.html')
      ? html
      : html.replace('</head>', STYLE + '\n</head>')
        .replace('<!--static-book-->', '<main id="main">' + staticBook() + '</main>'),
});
