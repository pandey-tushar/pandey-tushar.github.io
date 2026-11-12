/* The book as plain markup, written into index.html at build time.

   The reader builds the page in the browser, so the HTML a crawler fetches
   used to be an empty body. This puts the whole text there first. main.ts
   removes the block before the reader mounts, so a reader with scripts sees
   exactly what they saw before.

   Every string comes through the reader's own builders, from the same JSON the
   reader loads, so the two cannot drift. */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import type { Plugin } from 'vite';
import type { Canto, FrontMatter } from '@qubit/content/schema';
import { blockHtml, esc, fill, invocationHtml, numeral, resolveLabels } from '../../packages/reader/src/render';

const json = <T>(p: string): T =>
  JSON.parse(readFileSync(fileURLToPath(new URL(p, import.meta.url)), 'utf8')) as T;

/* The first screen is the cover in both states, so nothing jumps when the
   reader takes over. */
const STYLE = '<style>#static-book{max-width:68ch;margin:0 auto;padding:0 1.5rem}' +
  '#static-book>header{min-height:100vh;display:grid;place-content:center;text-align:center}</style>';

export function staticBook(): string {
  const cantos = json<Canto[]>('../../content/unpolarized.json');
  const front = json<FrontMatter>('../../content/front.unpolarized.json');
  const labels = resolveLabels(front);
  const chapters = cantos.map((c) => {
    const num = fill(labels.canto, {
      n: numeral(c.n, labels.digits), total: numeral(cantos.length, labels.digits),
    });
    const epigraph = c.epigraph
      ? '<div class="epigraph">' + esc(c.epigraph.text) + '<span class="attr">' + esc(c.epigraph.attr) + '</span></div>'
      : '';
    return '<article><p>' + esc(num) + '</p><h2>' + esc(c.title) + '</h2>' + epigraph +
      c.blocks.map((b) => blockHtml(b, labels)).join('') + '</article>';
  });
  return '<div id="static-book">' +
    '<header><h1>' + esc(front.cover.title) + '</h1><p>' + esc(front.cover.sub) + '</p></header>' +
    '<section>' + invocationHtml(front) + '</section>' +
    chapters.join('') + '</div>';
}

export const staticBookPlugin = (): Plugin => ({
  name: 'static-book',
  transformIndexHtml: (html) =>
    html.replace('</head>', STYLE + '\n</head>').replace('<body>', '<body>\n' + staticBook()),
});
