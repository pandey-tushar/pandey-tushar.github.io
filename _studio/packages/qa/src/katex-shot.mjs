/* Screenshot the maths in apps/book so the KaTeX cascade can be compared
   before and after a change. Usage: node katex-shot.mjs <outdir> */
import { chromium } from '@playwright/test';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join } from 'node:path';
import { mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';

const out = process.argv[2];
if (!out) { console.error('usage: katex-shot.mjs <outdir>'); process.exit(1); }
mkdirSync(out, { recursive: true });

const root = new URL('../../../apps/book/dist/', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.png': 'image/png', '.svg': 'image/svg+xml' };

const server = createServer(async (req, res) => {
  const p = decodeURIComponent(req.url.split('?')[0]);
  const rel = p === '/' ? 'index.html' : p;
  try {
    const body = await readFile(join(root, rel));
    res.writeHead(200, { 'content-type': TYPES[extname(rel)] || 'application/octet-stream' });
    res.end(body);
  } catch { res.writeHead(404).end('nope'); }
});
await new Promise(r => server.listen(4199, r));

const browser = await chromium.launch();
const results = [];
for (const theme of ['dark', 'light']) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  await page.addInitScript(t => { try { localStorage.setItem('qd-theme', t); } catch {} }, theme);
  await page.goto('http://localhost:4199/', { waitUntil: 'networkidle' });
  await page.evaluate(() => document.querySelectorAll('.canto-head')[0].click());
  await page.waitForTimeout(1200);
  await page.evaluate(() => { document.querySelectorAll('canvas').forEach(c => c.remove()); });
  const sci = page.locator('.science').first();
  await sci.scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);
  const file = join(out, `science-${theme}.png`);
  await sci.screenshot({ path: file });
  /* also record the computed values the cascade decides */
  const computed = await page.evaluate(() => {
    const k = document.querySelector('.eqblock .katex') || document.querySelector('.katex');
    if (!k) return null;
    const s = getComputedStyle(k);
    return { font: s.font, lineHeight: s.lineHeight, color: s.color, fontSize: s.fontSize, boxSizing: s.boxSizing };
  });
  const hash = createHash('sha256').update(await readFile(file)).digest('hex').slice(0, 16);
  results.push({ theme, hash, computed });
  await page.close();
}
await browser.close();
server.close();
console.log(JSON.stringify(results, null, 1));
