// qubit-dialogues.html: under prefers-reduced-motion the 3D figures draw a
// still frame and redraw only when the reader does something.
// Needs playwright and its chromium from _studio/node_modules; skips otherwise.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
let chromium = null, why = '';
try {
  ({ chromium } = createRequire(path.join(ROOT, '_studio/package.json'))('playwright'));
  if (!fs.existsSync(chromium.executablePath())) { why = 'playwright chromium not installed'; chromium = null; }
} catch (e) { why = 'playwright not found in _studio/node_modules'; }

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' };
function serve() {
  const srv = http.createServer((req, res) => {
    const f = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
    if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' });
    fs.createReadStream(f).pipe(res);
  });
  return new Promise(ok => srv.listen(0, '127.0.0.1', () => ok(srv)));
}

// count WebGL draw calls per canvas
const HOOK = () => {
  window.__draws = new Map();
  for (const P of [WebGLRenderingContext.prototype, WebGL2RenderingContext.prototype])
    for (const k of ['drawArrays', 'drawElements']) {
      const f = P[k];
      P[k] = function (...a) { window.__draws.set(this.canvas, (window.__draws.get(this.canvas) || 0) + 1); return f.apply(this, a); };
    }
};

async function open(browser, reducedMotion, n) {
  const page = await browser.newPage({ reducedMotion });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.route(u => !u.host.startsWith('127.0.0.1'), r => r.abort());
  await page.addInitScript(HOOK);
  await page.goto(`${base}/qubit-dialogues.html#canto-${n}`);
  const scene = page.locator(`#canto-${n} .scene canvas`);
  await scene.waitFor();
  await scene.scrollIntoViewIfNeeded();
  await page.waitForTimeout(600);
  const draws = () => scene.evaluate(c => window.__draws.get(c) || 0);
  const over = async (ms, act) => { const a = await draws(); if (act) await act(); await page.waitForTimeout(ms); return (await draws()) - a; };
  return { page, scene, draws, over, errors };
}

let base, srv;
test('reduced motion: figures hold a still frame and redraw on reader actions', { skip: chromium ? false : why }, async t => {
  srv = await serve(); base = `http://127.0.0.1:${srv.address().port}`;
  t.after(() => srv.close());
  const browser = await chromium.launch();
  t.after(() => browser.close());

  await t.test('without the setting the figure animates', async () => {
    const { page, over, errors } = await open(browser, 'no-preference', 4);
    assert.ok(await over(1000) > 20, 'expected continuous frames');
    assert.deepEqual(errors, []);
    await page.close();
  });

  await t.test('with reduce: a still frame, then nothing; controls, theme and resize redraw', async () => {
    const { page, scene, draws, over, errors } = await open(browser, 'reduce', 4);
    assert.ok(await draws() > 0, 'still frame drawn once the figure is live');
    assert.ok(await over(1000) <= 1, 'no continuous animation');
    const slider = page.locator('#canto-4 .scene input[type=range]');
    assert.ok(await over(300, () => slider.fill('80')) >= 1, 'slider redraws');
    assert.ok(await over(1000) <= 1, 'quiet again after the slider');
    assert.ok(await over(300, () => page.evaluate(() => {
      const d = document.documentElement; d.dataset.theme = d.dataset.theme === 'light' ? 'dark' : 'light';
      document.dispatchEvent(new CustomEvent('tp-theme'));
    })) >= 1, 'theme change redraws');
    assert.ok(await over(300, () => page.setViewportSize({ width: 900, height: 700 })) >= 1, 'resize redraws');
    assert.ok(await over(1000) <= 1, 'quiet again');
    // expanding another canto draws its figure
    const toric = page.locator('#canto-5 .scene canvas');
    await page.locator('#canto-5 .canto-head').click();
    await toric.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    const td = () => toric.evaluate(c => window.__draws.get(c) || 0);
    const t0 = await td();
    assert.ok(t0 > 0, 'expanded canto draws its still');
    await toric.click({ position: { x: 5, y: 5 } });
    await page.locator('#canto-5 [data-act=clear]').click();
    await page.waitForTimeout(300);
    assert.ok(await td() > t0, 'button press redraws');
    // the setting changes while the page is open
    await page.locator('#canto-4 .canto-head').click();
    await scene.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    assert.ok(await over(1000) > 20, 'animates once the setting is off');
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.waitForTimeout(200);
    assert.ok(await over(1000) <= 1, 'stops once the setting is back on');
    assert.deepEqual(errors, []);
    await page.close();
  });
});
