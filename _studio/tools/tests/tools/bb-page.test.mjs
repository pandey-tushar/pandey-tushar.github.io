// Checks of the explorer page (tools/bb-codes.html, bb-codes.css, js/bb-page.js): one width for the tool
// section and Fig. 2 in one column, a plain-words card by Fig. 1, a visible message when a link does not give
// a valid code, and in a browser the right rail from 70em, which fills the column beside the tool.
// The browser checks need playwright and its chromium from _studio/node_modules; they skip otherwise.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const read = p => readFileSync(new URL(`../../../../tools/${p}`, import.meta.url), 'utf8');
const css = read('bb-codes.css'), html = read('bb-codes.html'), js = read('js/bb-page.js');
const rule = sel => (css.match(new RegExp(`^${sel.replace(/[.#]/g, '\\$&')}\\s*\\{([^}]*)\\}`, 'm')) || [])[1] || '';

test('form, parameters, status and Fig. 2 share one right edge', () => {
  for (const sel of ['.bb-form', '.bb-params', '.bb-status', '.bb-dist'])
    assert.match(rule(sel), /max-width: var\(--tp-measure\)/, `${sel} is not held to the measure`);
  assert.doesNotMatch(css.replace(/^\.bb-head \{[^}]*\}/m, ''), /max-width: (52|60)rem/);
  assert.match(html, /<figure class="tp-plate bb-fig bb-dist" id="fig-dist">/);
});

test('Fig. 1 has a line a reader without the background can follow', () => {
  assert.match(html, /<aside class="bb-rail"[^>]*>\s*<section class="bb-plainwords"[^>]*>\s*<h2[^>]*>In plain words<\/h2>\s*<p>[^<]*two qubits and two checks[^<]*<\/p>/);
  assert.match(html, /<\/aside>\s*<figure class="tp-plate bb-fig" id="fig-layout">/);
});

test('a link that does not give a valid code says so and loads the default', () => {
  assert.match(js, /linkState\(location\.search\)/);
  assert.match(js, /The link did not give a valid code, so the default code was loaded\./);
});

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
let chromium = null, why = '';
try {
  ({ chromium } = createRequire(path.join(ROOT, '_studio/package.json'))('playwright'));
  if (!fs.existsSync(chromium.executablePath())) { why = 'playwright chromium not installed'; chromium = null; }
} catch (e) { why = 'playwright not found in _studio/node_modules'; }

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.ico': 'image/x-icon' };
function serve() {
  const srv = http.createServer((req, res) => {
    let f = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
    if (f.startsWith(ROOT) && fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
    if (!f.startsWith(ROOT) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' });
    fs.createReadStream(f).pipe(res);
  });
  return new Promise(ok => srv.listen(0, '127.0.0.1', () => ok(srv)));
}

test('the explorer in a browser', { skip: chromium ? false : why }, async t => {
  const srv = await serve(), base = `http://127.0.0.1:${srv.address().port}`;
  t.after(() => srv.close());
  const browser = await chromium.launch();
  t.after(() => browser.close());

  async function open(width, height = 900) {
    const page = await browser.newPage({ viewport: { width, height } });
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.route(u => !u.host.startsWith('127.0.0.1'), r => r.abort());
    await page.goto(base + '/tools/bb-codes.html', { waitUntil: 'load' });
    await page.waitForFunction(() => !document.getElementById('bb-results').hidden);
    await page.waitForTimeout(300);
    return { page, errors };
  }

  await t.test('1440: a rail with the plain words and the contents, and no blank beside the tool', async () => {
    const { page, errors } = await open(1440);
    const m = await page.evaluate(() => {
      const r = e => (typeof e === 'string' ? document.querySelector(e) : e).getBoundingClientRect();
      const rail = document.querySelector('.bb-rail');
      if (!rail) return { rail: false };
      const toc = [...rail.querySelectorAll('.bb-toc a')];
      const tool = ['#bb-form', '#bb-params', '#bb-status'].map(r);
      return { rail: true, railL: r(rail).left, railW: r(rail).width,
        plain: rail.querySelector('.bb-plainwords')?.textContent || '',
        toc: toc.map(a => a.getAttribute('href')), tocShown: toc.length && r(toc[0]).height > 0,
        missing: toc.map(a => a.getAttribute('href')).filter(h => !document.querySelector(h)),
        toolR: Math.max(...tool.map(b => b.right)), formR: tool[0].right, paramsL: tool[1].left,
        formTop: tool[0].top, paramsTop: tool[1].top };
    });
    assert.ok(m.rail, 'no .bb-rail');
    assert.match(m.plain, /two qubits and two checks/);
    assert.ok(m.tocShown && m.toc.length >= 5, `contents list: ${m.toc}`);
    assert.deepEqual(m.missing, [], 'contents links without a target');
    assert.ok(m.railL - m.toolR < 80, `blank right of the tool: ${m.railL - m.toolR}px`);
    assert.ok(m.paramsL > m.formR, `parameters beside the form: ${m.paramsL} vs ${m.formR}`);
    assert.deepEqual(errors, []);
    await page.close();
  });

  await t.test('1440x700: the rail never overlaps a figure or the footer while scrolling', async () => {
    const { page } = await open(1440, 700);
    const hits = await page.evaluate(async () => {
      const out = [], rail = document.querySelector('.bb-rail');
      if (!rail) return ['no .bb-rail'];
      const cut = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
      const max = document.documentElement.scrollHeight - innerHeight;
      for (let y = 0; y <= max + 100; y += 100) {
        scrollTo(0, Math.min(y, max));
        await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
        const a = rail.getBoundingClientRect();
        for (const e of document.querySelectorAll('figure, .tp-foot'))
          if (cut(a, e.getBoundingClientRect())) out.push(`${scrollY}: ${e.id || e.className}`);
      }
      return out;
    });
    assert.deepEqual(hits, []);
    await page.close();
  });

  await t.test('below 70em one column with the plain words above Fig. 1, no sideways scroll at 390', async () => {
    for (const w of [1024, 390]) {
      const { page } = await open(w, 844);
      const m = await page.evaluate(() => {
        const d = document.documentElement, r = s => document.querySelector(s).getBoundingClientRect();
        return { sw: d.scrollWidth, cw: d.clientWidth, plain: r('.bb-plainwords'), fig: r('#fig-layout'),
          toc: getComputedStyle(document.querySelector('.bb-toc')).display };
      });
      assert.ok(m.sw <= m.cw, `${w}: ${m.sw} vs ${m.cw}`);
      assert.ok(m.plain.bottom <= m.fig.top, `${w}: plain words not above Fig. 1`);
      assert.ok(Math.abs(m.plain.left - m.fig.left) <= 8, `${w}: plain words off the column`);
      assert.equal(m.toc, 'none', `${w}: contents list shown in one column`);
      await page.close();
    }
  });

  await t.test('1440: every preset loads and the controls still work', async () => {
    const { page, errors } = await open(1440);
    const names = await page.$$eval('#in-preset option', os => os.map(o => o.value).filter(Boolean));
    assert.ok(names.length >= 5, `presets: ${names}`);
    const seen = new Set();
    for (const name of names) {
      await page.selectOption('#in-preset', name);
      await page.waitForTimeout(250);
      const p = await page.evaluate(() => ({ text: document.getElementById('bb-params').textContent,
        err: [...document.querySelectorAll('.bb-err')].map(e => e.textContent).join('') }));
      assert.equal(p.err, '', `${name}: ${p.err}`);
      seen.add(p.text);
    }
    assert.equal(seen.size, names.length, 'each preset gives its own parameters');

    await page.fill('#in-l', '6'); await page.fill('#in-m', '6');
    await page.fill('#in-A', 'x^3 + y + y^2'); await page.fill('#in-B', 'y^3 + x + x^2');
    await page.waitForTimeout(600);
    assert.match(await page.textContent('#bb-params'), /72/, 'typed code gives n = 72');

    await page.selectOption('#lay-kind', 'Z');
    await page.fill('#lay-i', '1'); await page.fill('#lay-j', '2');
    await page.waitForTimeout(200);
    assert.ok(await page.locator('#lay-plot .sel').count() > 0, 'selected node drawn');
    assert.ok(await page.locator('#lay-plot .bb-edge').count() > 0, 'edges drawn');
    const hit = page.locator('#lay-plot .bb-hit').nth(5);
    await hit.evaluate(e => e.scrollIntoView({ block: 'center', behavior: 'instant' }));  // the page scrolls smoothly
    const b = await hit.boundingBox();  // the node drawn over the hit area takes the click
    await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
    await page.waitForTimeout(150);
    assert.ok(await page.locator('#lay-plot .sel').count() > 0, 'click selects a node');

    await page.click('#dist-run');
    await page.waitForFunction(() => /\d/.test(document.getElementById('dist-readout').textContent), null, { timeout: 15000 });
    await page.evaluate(() => document.getElementById('dist-stop').click());  // a small code may already be done
    assert.match(await page.textContent('#dist-readout'), /\d/);
    assert.deepEqual(errors, []);
    await page.close();
  });
});
