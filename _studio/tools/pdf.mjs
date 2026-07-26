/* Print each built edition to a PDF with Playwright.
   Headless Chrome's --print-to-pdf hangs on these pages: they run continuous
   rAF animation, so the renderer never reaches the idle state it waits for.
   Driving the print through CDP instead sidesteps that entirely.
   Usage: node tools/pdf.mjs [name ...]   (default: all) */
import { chromium } from '@playwright/test';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, statSync } from 'node:fs';
import { extname, join, resolve } from 'node:path';

/* the site root: the PDFs the books hub links to are the deliverable */
const OUT = resolve(import.meta.dirname, '..', '..');
const EDITIONS = {
  unpolarized: { dir: 'apps/unpolarized/dist', file: 'an-unpolarized-life.pdf', port: 4311 },
  /* the Hindi edition is not published, so its PDF stays inside _studio,
     which Jekyll never copies into the built site */
  hindi:       { dir: 'apps/hindi/dist', file: '_studio/qubit-dialogues-hindi.pdf', port: 4312 },
  illustrated: { dir: 'apps/illustrated/dist', file: 'illustrated.pdf', port: 4313 },
  book:        { dir: 'apps/book/dist',        file: 'qubit-dialogues.pdf', port: 4314 },
};

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml' };

/* Print-only prose. A few passages in content/ ask the reader to touch
   something. On screen those scenes are live and the instruction is correct,
   so content/ is left exactly as authored; paper has nothing to touch, so the
   sentence is recast here and only here.

   The scene hints ("Drag to steer the qubit around its sphere") need no entry:
   print.css hides every child of .scene, and the illustrated edition drops
   scene blocks outright, so they never reach a page.

   `in` lists the editions the passage belongs to, and each is asserted to
   match exactly once, so a later edit in content/ that drifts past `find`
   fails the run instead of quietly printing the instruction. */
const PRINT_TEXT = [
  {
    in: ['book'],
    find: 'Read slowly. Drag the spheres, break the lattice, take the lock apart.',
    replace: 'Read slowly.',
  },
  {
    in: ['hindi'],
    find: 'धीरे पढ़िए। गोलों को खींचिए, जालक को तोड़िए, ताले को खोलकर देखिए।',
    replace: 'धीरे पढ़िए।',
  },
  {
    /* The sentences on either side describe what each kind of error does to
       the checks, so the instruction is turned into the statement it was
       carrying rather than cut, which would leave "it" without its edge. */
    in: ['book', 'illustrated'],
    find: 'Tap an edge to lay down a bit flip or a phase flip.',
    replace: 'An error on an edge is either a bit flip or a phase flip.',
  },
];

const names = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(EDITIONS);
const browser = await chromium.launch();

for (const name of names) {
  const ed = EDITIONS[name];
  if (!ed) { console.error('unknown edition', name); continue; }
  const root = resolve(ed.dir);
  if (!existsSync(join(root, 'index.html'))) { console.error(`${name}: no build, skipping`); continue; }

  const server = createServer(async (req, res) => {
    const rel = decodeURIComponent(req.url.split('?')[0]).replace(/^\//, '') || 'index.html';
    try {
      const body = await readFile(join(root, rel));
      res.writeHead(200, { 'content-type': TYPES[extname(rel)] || 'application/octet-stream' });
      res.end(body);
    } catch { res.writeHead(404).end('not found'); }
  });
  await new Promise(r => server.listen(ed.port, r));

  /* reducedMotion at context creation, not after load: the editions read
     prefers-reduced-motion once at module init, so setting it later leaves the
     scroll-driven build running. Set here, the illustrated edition boots
     straight into its static cut, mounts no canvases at all, and every beat of
     text is already revealed. */
  const page = await browser.newPage({ viewport: { width: 1280, height: 1600 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  try {
    await page.goto(`http://127.0.0.1:${ed.port}/`, { waitUntil: 'load', timeout: 60000 });
    /* let content render and lazy work settle; networkidle can never fire on an
       animated page, so wait on a real signal plus a bounded pause */
    await page.waitForSelector('#content, main, body > *', { timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(6000);
    /* A print run has no reader, and these builds defer work until one shows
       up: plates load on intersection. Sweep the document once so every lazy
       slot is filled before the snapshot. */
    await page.evaluate(async () => {
      const step = innerHeight;
      for (let y = 0; y < document.documentElement.scrollHeight && y < step * 400; y += step) {
        scrollTo(0, y);
        await new Promise(r => requestAnimationFrame(() => setTimeout(r, 24)));
      }
      scrollTo(0, 0);
    });
    await page.waitForTimeout(1500);
    /* stop animation so the print snapshot is a settled frame */
    await page.emulateMedia({ media: 'print', reducedMotion: 'reduce' });
    await page.waitForTimeout(2500);
    await page.evaluate(() => {
      /* A book has no hyperlinks. Chromium writes a link annotation for every
         live anchor whatever the stylesheet says, so the hrefs come off before
         the snapshot; the text of each one stays exactly where it was. */
      for (const a of document.querySelectorAll('a[href]')) a.removeAttribute('href');
    });
    const edits = PRINT_TEXT.filter((e) => e.in.includes(name));
    const hits = await page.evaluate((es) => {
      const n = es.map(() => 0);
      const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let t = walk.nextNode(); t; t = walk.nextNode()) {
        es.forEach((e, i) => {
          if (!t.nodeValue.includes(e.find)) return;
          t.nodeValue = t.nodeValue.split(e.find).join(e.replace);
          n[i]++;
        });
      }
      return n;
    }, edits);
    const missed = edits.filter((e, i) => hits[i] !== 1);
    if (missed.length > 0) {
      process.exitCode = 1;
      for (const e of missed) console.error(`${name}: print text not applied once: ${e.find}`);
    }
    const out = join(OUT, ed.file);
    await page.pdf({ path: out, format: 'A4', printBackground: true,
      margin: { top: '14mm', bottom: '14mm', left: '14mm', right: '14mm' } });
    const kb = Math.round(statSync(out).size / 1024);
    console.log(`${name.padEnd(12)} -> ${ed.file} (${kb} KB)  print-text ${hits.join(',') || '-'}` +
      `${errors.length ? '  pageerrors: ' + errors.length : ''}`);
  } catch (e) {
    console.error(`${name}: failed`, String(e).split('\n')[0]);
  }
  await page.close();
  server.close();
}
await browser.close();
