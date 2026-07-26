/* The 375 pixel gate.

   This edition regressed on horizontal overflow once already, when display
   mathematics set SVG paths wider than the viewport, and a page that scrolls
   sideways on a phone is not a page anyone reads. Nothing in the existing
   gates measured it, so a plate whose region reaches past the stage, or a
   legend that will not wrap, could ship again unnoticed.

   Checked at 375 pixels, in both motion modes, for the document and for every
   canto article and every one of its descendants:

     document.scrollWidth must not exceed the viewport
     no element's right edge may sit outside the viewport

   Run: node tools/overflow.mjs */

import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import { serve } from './serve.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
const W = 375;

const server = await serve(root + 'dist');
const browser = await chromium.launch();

const rows = [];
let failures = 0;

for (const motion of ['no-preference', 'reduce']) {
  const context = await browser.newContext({
    viewport: { width: W, height: 812 },
    reducedMotion: motion === 'reduce' ? 'reduce' : 'no-preference',
  });
  const page = await context.newPage();
  const problems = [];
  page.on('pageerror', (e) => problems.push('pageerror: ' + String(e)));
  page.on('console', (m) => {
    if (m.type() === 'error' || m.type() === 'warning') problems.push(m.type() + ': ' + m.text());
  });

  await page.goto(server.url + '/', { waitUntil: 'load' });
  await page.waitForSelector('article.canto');
  await page.addStyleTag({ content: 'html { scroll-behavior: auto !important; }' });

  const cantos = await page.evaluate(() =>
    [...document.querySelectorAll('article.canto')].map((a) => Number(a.dataset.canto)),
  );

  for (const n of cantos) {
    /* walk it the way a reader does, so lazily filled posters are in place */
    await page.evaluate((id) => document.querySelector(id).scrollIntoView(), '#canto-' + n);
    await page.waitForTimeout(60);
    const seen = await page.evaluate(({ id, w }) => {
      const article = document.querySelector(id);
      let worst = 0;
      let culprit = '';
      for (const el of article.querySelectorAll('*')) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) continue;
        if (r.right > worst) {
          worst = r.right;
          culprit = el.className || el.tagName;
        }
      }
      return {
        docScroll: document.documentElement.scrollWidth,
        bodyScroll: document.body.scrollWidth,
        widest: Math.round(worst),
        culprit: String(culprit).slice(0, 40),
        over: worst > w + 0.5,
      };
    }, { id: '#canto-' + n, w: W });

    const ok = !seen.over && seen.docScroll <= W && seen.bodyScroll <= W;
    if (!ok) failures++;
    rows.push({
      motion, canto: n,
      docScrollWidth: seen.docScroll,
      widestRightEdge: seen.widest,
      widestElement: seen.culprit,
      pass: ok ? 'pass' : 'OVERFLOW',
    });
  }

  if (problems.length) {
    failures++;
    console.error('console problems, motion ' + motion + ':');
    for (const p of problems) console.error('  ' + p);
  }
  await context.close();
}

await browser.close();
await server.close();

console.log('horizontal overflow at ' + W + 'px, both motion modes');
console.table(rows);
if (failures > 0) {
  console.error(failures + ' overflow failure(s)');
  process.exitCode = 1;
} else {
  console.log('no horizontal overflow in ' + rows.length + ' canto checks');
}
