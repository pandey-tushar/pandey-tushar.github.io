/* Renders every composed canto's signature frame to a PNG.

   Spec 02's forcing function: each of these has to work standing alone as a
   poster. If a frame only reads as background texture, that canto's art is not
   done, and the honest move is to say so rather than ship filler.

   The PNGs are also the poster-first layer the edition loads before any canvas
   mounts, and they are what the OG cards would be cut from if this edition is
   ever published.

   Usage: node tools/posters.mjs [--width 1600] */

import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { serve } from './serve.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
const widthArg = process.argv.indexOf('--width');
const WIDTH = widthArg > -1 ? Number(process.argv[widthArg + 1]) : 1600;
const HEIGHT = Math.round(WIDTH * 0.625);

const server = await serve(root + 'dist');
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

const problems = [];
page.on('pageerror', (e) => problems.push(String(e)));
page.on('console', (m) => { if (m.type() === 'error') problems.push(m.text()); });

await page.goto(server.url + '/poster.html?canto=1&w=64');
await page.waitForFunction(() => Array.isArray(window.__cantos));
const cantos = await page.evaluate(() => window.__cantos);

await mkdir(root + 'posters', { recursive: true });
await mkdir(root + 'posters/web', { recursive: true });
const out = [];

for (const canto of cantos) {
  await page.goto(
    server.url + '/poster.html?canto=' + canto + '&w=' + WIDTH + '&h=' + HEIGHT,
  );
  await page.waitForSelector('html[data-poster-ready]');
  /* two files from one render: the full resolution PNG is the deliverable the
     poster test judges, and the WebP is the poster-first layer the edition
     actually loads. A 1.8 MB PNG decoded on the main thread as a canto nears
     is a long task, and it would be one paid on every canto. */
  const info = await page.evaluate(() => ({
    ...window.__poster,
    png: document.querySelector('canvas').toDataURL('image/png'),
    webp: document.querySelector('canvas').toDataURL('image/webp', 0.82),
  }));
  const stem = 'canto-' + String(canto).padStart(2, '0');
  const bytes = Buffer.from(info.png.split(',')[1], 'base64');
  await writeFile(root + 'posters/' + stem + '.png', bytes);
  let webKb = 0;
  if (info.webp.startsWith('data:image/webp')) {
    const web = Buffer.from(info.webp.split(',')[1], 'base64');
    await writeFile(root + 'posters/web/' + stem + '.webp', web);
    webKb = Math.round(web.length / 1024);
  }
  out.push({
    canto, name: stem + '.png', kb: Math.round(bytes.length / 1024), webKb,
    progress: info.progress, hash: info.hash.slice(0, 16),
  });
}

await browser.close();
await server.close();

console.log('posters at ' + WIDTH + 'x' + HEIGHT + ', written to apps/illustrated/posters/');
console.table(out);
if (problems.length) {
  console.error('console problems during poster export:');
  for (const p of problems) console.error('  ' + p);
  process.exitCode = 1;
}
