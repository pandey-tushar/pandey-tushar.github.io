/* Seed determinism gate.

   Renders every registered plate's signature frame twice, in two browser
   contexts that share nothing, and compares a SHA-256 of the raw pixels. Any
   drift means an unseeded random is loose somewhere in packages/motifs, and no
   amount of care in review will find it faster than this will.

   The hash covers (seed, params, size, dpr). Changing any of those is supposed
   to change the picture; changing none of them and getting a different hash is
   the bug this exists to catch. */

import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import { serve } from './serve.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
const W = 900;
const H = 563;

const server = await serve(root + 'dist');
const browser = await chromium.launch();

async function hashOnce(canto) {
  /* a fresh context every time: new renderer process state, new caches */
  const context = await browser.newContext({ viewport: { width: 1000, height: 700 } });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(server.url + '/poster.html?canto=' + canto + '&w=' + W + '&h=' + H);
  await page.waitForSelector('html[data-poster-ready]');
  const info = await page.evaluate(() => window.__poster);
  await context.close();
  if (errors.length) throw new Error('canto ' + canto + ': ' + errors.join('; '));
  return info.hash;
}

const probe = await browser.newContext();
const probePage = await probe.newPage();
await probePage.goto(server.url + '/poster.html?canto=1&w=64&h=40');
await probePage.waitForFunction(() => Array.isArray(window.__cantos));
const cantos = await probePage.evaluate(() => window.__cantos);
await probe.close();

const rows = [];
let drift = 0;
for (const canto of cantos) {
  const a = await hashOnce(canto);
  const b = await hashOnce(canto);
  const same = a === b;
  if (!same) drift++;
  rows.push({ canto, run1: a.slice(0, 24), run2: b.slice(0, 24), match: same ? 'yes' : 'DRIFT' });
}

await browser.close();
await server.close();

console.log('seed determinism: ' + W + 'x' + H + ' at dpr 1, two fresh contexts each');
console.table(rows);
if (drift > 0) {
  console.error(drift + ' plate(s) drifted. An unseeded random is loose.');
  process.exitCode = 1;
} else {
  console.log('all ' + rows.length + ' plates identical across fresh contexts');
}
