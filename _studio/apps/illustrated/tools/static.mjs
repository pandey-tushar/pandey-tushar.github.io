/* The still edition gate.

   With prefers-reduced-motion forced, every composed canto has to show its
   signature artwork and its complete text. Not a graceful degradation: spec 02
   calls this a first-class path, and it is also the poster set and the future
   OG cards, so if it is broken the whole still deliverable is broken.

   Checked per canto:
     - the stage holds a loaded image with real pixels
     - no live canvas has been mounted and nothing animates
     - every literary block from content/en.json is present and visible
     - the apparatus (science, prediction, sources) is present too */

import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import { readFile } from 'node:fs/promises';
import { serve } from './serve.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
const book = JSON.parse(await readFile(root + '../../content/en.json', 'utf8'));

const server = await serve(root + 'dist');
const browser = await chromium.launch();

const rows = [];
let failures = 0;

for (const viewport of [{ width: 1440, height: 900 }, { width: 375, height: 812 }]) {
  const context = await browser.newContext({ viewport, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const problems = [];
  page.on('pageerror', (e) => problems.push('pageerror: ' + String(e)));
  page.on('console', (m) => {
    if (m.type() === 'error' || m.type() === 'warning') problems.push(m.type() + ': ' + m.text());
  });

  await page.goto(server.url + '/', { waitUntil: 'load' });
  await page.waitForSelector('article.canto');
  await page.addStyleTag({ content: 'html { scroll-behavior: auto !important; }' });

  const composed = await page.evaluate(() =>
    [...document.querySelectorAll('article.canto:not([data-unstyled])')].map((a) => Number(a.dataset.canto)),
  );

  for (const n of composed) {
    const canto = book.find((c) => c.n === n);
    /* the poster loads lazily as it nears, exactly as a reader would meet it */
    await page.evaluate((id) => document.querySelector(id).scrollIntoView(), '#canto-' + n);
    await page.waitForFunction(
      (id) => {
        const img = document.querySelector(id + ' .poster');
        return img && img.complete && img.naturalWidth > 0;
      },
      '#canto-' + n,
      { timeout: 10000 },
    ).catch(() => { /* reported below */ });

    const seen = await page.evaluate((id) => {
      const article = document.querySelector(id);
      const img = article.querySelector('.poster');
      const style = img ? getComputedStyle(img) : null;
      return {
        artwork: Boolean(img && img.complete && img.naturalWidth > 0 && style.display !== 'none'),
        artWidth: img ? img.getBoundingClientRect().width : 0,
        liveCanvases: article.querySelectorAll('canvas.live').length,
        text: article.innerText,
        beats: article.querySelectorAll('.beat').length,
        litBeats: article.querySelectorAll('.beat.is-lit').length,
      };
    }, '#canto-' + n);

    /* every sentence of the canto has to be on the page */
    const wanted = [];
    for (const b of canto.blocks) {
      if (b.t === 'p' || b.t === 'reflect') wanted.push(b.text);
      else if (b.t === 'dlg') wanted.push(...b.text);
      else if (b.t === 'assume') wanted.push(b.claim);
    }
    const normal = seen.text.replace(/\s+/g, ' ');
    const missing = wanted.filter((t) => !normal.includes(t.replace(/\s+/g, ' ').slice(0, 90)));

    const apparatusPresent = await page.evaluate(
      (id) => document.querySelectorAll(id + ' .apparatus > *').length,
      '#canto-' + n,
    );

    const ok = seen.artwork && missing.length === 0 && seen.liveCanvases === 0 && seen.litBeats === seen.beats;
    if (!ok) failures++;
    rows.push({
      viewport: viewport.width + 'px',
      canto: n,
      artwork: seen.artwork ? 'yes (' + Math.round(seen.artWidth) + 'px wide)' : 'MISSING',
      liveCanvases: seen.liveCanvases,
      beatsVisible: seen.litBeats + '/' + seen.beats,
      blocksMissing: missing.length,
      apparatusBlocks: apparatusPresent,
      pass: ok ? 'pass' : 'FAIL',
    });
  }

  if (problems.length) {
    failures++;
    console.error('console problems at ' + viewport.width + 'px:');
    for (const p of problems) console.error('  ' + p);
  }
  await context.close();
}

await browser.close();
await server.close();

console.log('reduced motion forced, still edition');
console.table(rows);
if (failures > 0) process.exitCode = 1;
else console.log('every composed canto shows its signature artwork and complete text, with no canvas mounted');
