/* The build. Renders the page from src/content, compiles content/notes, and
   emits the files a site needs to be found: a page per note, a feed, a sitemap,
   robots. Nothing here runs in the browser. */

import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Plugin } from 'vite';
import * as C from '../src/content/site.ts';
import { body, head, notePage } from '../src/render.ts';
import { readNotes } from './notes.ts';
import type { Note } from '../src/content/types.ts';

export const NOTES_DIR = fileURLToPath(new URL('../content/notes', import.meta.url));

const esc = (s: string): string =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const rfc822 = (iso: string): string => new Date(iso + 'T09:00:00Z').toUTCString();

function feed(notes: Note[]): string {
  return '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n' +
    '<title>' + esc(C.brand.first + ' ' + C.brand.last + ' · Notes') + '</title>\n' +
    '<link>' + C.ORIGIN + '/#writing</link>\n' +
    '<description>' + esc(C.writing.lede) + '</description>\n' +
    '<language>en</language>\n' +
    '<atom:link href="' + C.ORIGIN + '/feed.xml" rel="self" type="application/rss+xml"/>\n' +
    notes.map((n) =>
      '<item>\n<title>' + esc(n.title) + '</title>\n' +
      '<link>' + C.ORIGIN + '/notes/' + n.slug + '/</link>\n' +
      '<guid isPermaLink="true">' + C.ORIGIN + '/notes/' + n.slug + '/</guid>\n' +
      '<pubDate>' + rfc822(n.date) + '</pubDate>\n' +
      '<description>' + esc(n.summary) + '</description>\n</item>\n').join('') +
    '</channel>\n</rss>\n';
}

function sitemap(notes: Note[]): string {
  const urls = [...C.routes, ...notes.map((n) => '/notes/' + n.slug + '/')];
  return '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    urls.map((u) => '<url><loc>' + C.ORIGIN + u + '</loc></url>\n').join('') +
    '</urlset>\n';
}

const robots = (): string =>
  'User-agent: *\nAllow: /\n\nSitemap: ' + C.ORIGIN + '/sitemap.xml\n';

export function sitePlugin(): Plugin {
  let notes: Note[] = [];
  return {
    name: 'qubit-site',
    buildStart() {
      notes = readNotes(NOTES_DIR);
      this.addWatchFile(NOTES_DIR);
    },
    transformIndexHtml: {
      order: 'pre',
      handler(html) {
        return html
          .replace('<!--head-->', head(C.meta))
          .replace('<!--sections-->', body(notes));
      },
    },
    /* writeBundle, not generateBundle: index.html has to exist on disk before
       its stylesheet link can be swapped for the stylesheet itself */
    writeBundle(opts, bundle) {
      const out = opts.dir ?? 'dist';
      const key = (test: (n: string) => boolean): string => Object.keys(bundle).find(test) ?? '';
      const js = key((n) => n.endsWith('.js') && n.includes('index'));
      const cssKey = key((n) => n.endsWith('.css'));
      const css = cssKey ? readFileSync(join(out, cssKey), 'utf8') : '';

      /* one round trip instead of two: 14KB of css is cheaper inline than a
         render blocking request on a slow link, and this page is one page */
      const index = join(out, 'index.html');
      writeFileSync(index, readFileSync(index, 'utf8')
        .replace(/<link rel="stylesheet"[^>]*href="\/assets\/[^"]+\.css"[^>]*>/, '<style>' + css + '</style>'));
      if (cssKey) rmSync(join(out, cssKey), { force: true });

      /* note pages carry the same analytics snippet as the home page */
      const analytics = /<!-- Google Analytics[\s\S]*?<\/script>/.exec(readFileSync(index, 'utf8'))?.[0] ?? '';
      for (const n of notes) {
        const dir = join(out, 'notes', n.slug);
        mkdirSync(dir, { recursive: true });
        writeFileSync(join(dir, 'index.html'), notePage(n, '/' + js, css, analytics));
      }
      writeFileSync(join(out, 'feed.xml'), feed(notes));
      writeFileSync(join(out, 'sitemap.xml'), sitemap(notes));
      writeFileSync(join(out, 'robots.txt'), robots());
      this.info(notes.length + ' note page(s), inlined css, feed, sitemap and robots written');
    },
  };
}
