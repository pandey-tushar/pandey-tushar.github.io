// The quiet extras: the homepage lattice's logical error, the hidden /logical/ page, the console note
// and the footer year. Browser parts need playwright and its chromium from _studio/node_modules; skip otherwise.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { LEVELS, round, restores } from '../../../../logical/logic.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
let chromium = null, why = '';
try {
  ({ chromium } = createRequire(path.join(ROOT, '_studio/package.json'))('playwright'));
  if (!fs.existsSync(chromium.executablePath())) { why = 'playwright chromium not installed'; chromium = null; }
} catch (e) { why = 'playwright not found in _studio/node_modules'; }

// a page with only the site chrome and a footer for the given year
const yearPage = y => `<!doctype html><html lang="en" class="tp-full"><head><meta charset="utf-8">
<link rel="stylesheet" href="/lib/site.css"><script src="/lib/site.js" defer></script></head><body>
<main id="main"><h1>Year</h1></main>
<footer class="tp-foot"><p>&copy; ${y} Tushar Pandey</p></footer></body></html>`;

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.png': 'image/png' };
function serve() {
  const srv = http.createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    const y = p.match(/^\/__year\/(\d{4})$/);
    if (y) { res.writeHead(200, { 'content-type': 'text/html' }); return res.end(yearPage(y[1])); }
    if (p.endsWith('/')) p += 'index.html';
    const f = path.join(ROOT, p);
    if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' });
    fs.createReadStream(f).pipe(res);
  });
  return new Promise(ok => srv.listen(0, '127.0.0.1', () => ok(srv)));
}

const prime = n => { if (n < 2) return false; for (let d = 2; d * d <= n; d++) if (n % d === 0) return false; return true; };
const twin = n => prime(n) && (prime(n - 2) || prime(n + 2));

// the console note: letters on the bits of a repetition code and the checks between them
function solve(text) {
  const lines = text.split('\n');
  const li = lines.findIndex(l => /^\s*([a-z] )+[a-z]\s*$/.test(l));
  assert.ok(li >= 0, 'a row of letters');
  const letters = lines[li], checks = lines[li + 1];
  assert.match(checks, /^\s*([01] )+[01]\s*$/, 'the checks under the letters');
  const at = [...letters].map((c, i) => [c, i]).filter(([c]) => c !== ' ');
  const cs = [...checks].map((c, i) => [c, i]).filter(([c]) => c !== ' ');
  assert.equal(cs.length, at.length - 1);
  cs.forEach(([, col], i) => assert.ok(at[i][1] < col && col < at[i + 1][1], 'each check sits between its two bits'));
  // two explanations of any syndrome on a line: one and its complement; take the lighter
  const e = [0];
  cs.forEach(([c]) => e.push(e[e.length - 1] ^ +c));
  const w = e.reduce((a, b) => a + b, 0);
  assert.notEqual(2 * w, e.length, 'the lighter explanation is unique');
  const flip = 2 * w < e.length ? e : e.map(b => 1 - b);
  return at.filter((_, i) => flip[i]).map(([c]) => c).join('');
}

test('the hidden page is linked only from the lattice and kept out of the index', () => {
  const page = fs.readFileSync(path.join(ROOT, 'logical/index.html'), 'utf8');
  assert.match(page, /<meta name="robots" content="noindex">/);
  assert.ok(!fs.readFileSync(path.join(ROOT, 'sitemap.xml'), 'utf8').includes('logical'));
  const skip = new Set(['_studio', 'node_modules', 'logical', '.git']);
  const found = [];
  (function walk(d) {
    for (const f of fs.readdirSync(d, { withFileTypes: true })) {
      if (skip.has(f.name)) continue;
      const p = path.join(d, f.name);
      if (f.isDirectory()) walk(p);
      else if (/\.(html|js|xml|txt)$/.test(f.name) && fs.readFileSync(p, 'utf8').includes('/logical/')) found.push(path.relative(ROOT, p).replace(/\\/g, '/'));
    }
  })(ROOT);
  assert.deepEqual(found.sort(), ['index.html']);
  assert.equal(fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8'),
    fs.readFileSync(path.join(ROOT, '_studio/prototypes/site-full/index.html'), 'utf8'));
});

let base, srv, browser;
test('in the browser', { skip: chromium ? false : why }, async t => {
  srv = await serve(); base = `http://127.0.0.1:${srv.address().port}`;
  t.after(() => srv.close());
  browser = await chromium.launch();
  t.after(() => browser.close());
  const open = async (url, opts = {}, bare = false) => {
    const page = await browser.newPage({ colorScheme: 'dark', ...opts });
    if (bare) await page.route('**/lib/site.js', r => r.abort());
    const errors = [], logs = [];
    page.on('pageerror', e => errors.push(String(e)));
    page.on('console', m => { if (m.type() !== 'error') logs.push(m); });
    await page.route(u => !u.host.startsWith('127.0.0.1'), r => r.abort());
    await page.goto(base + url);
    return { page, errors, logs };
  };

  await t.test('console: one note per load whose puzzle spells the hidden path', async () => {
    for (const url of ['/', '/books.html', '/logical/']) {
      const { page, logs, errors } = await open(url);
      await page.waitForTimeout(300);
      assert.equal(logs.length, 1, `${url}: ${logs.map(m => m.text())}`);
      assert.equal(logs[0].type(), 'log');
      const text = logs[0].text();
      assert.ok(text.split('\n').length < 8, 'under eight lines');
      assert.ok(!text.includes('%c'), 'no styling');
      assert.match(text, /^[\x20-\x7e\n]+$/, 'ASCII');
      const word = solve(text);
      assert.equal(word, 'logical');
      assert.ok(fs.existsSync(path.join(ROOT, word, 'index.html')));
      assert.deepEqual(errors, []);
      await page.close();
    }
  });

  await t.test('year: an even year becomes a sum of two primes, one of a twin pair, smallest such p', async () => {
    for (let y = 2024; y <= 2040; y++) {
      const { page, errors } = await open(`/__year/${y}`);
      const foot = page.locator('footer.tp-foot p');
      await page.waitForLoadState('load');
      assert.equal((await foot.textContent()).trim(), `© ${y} Tushar Pandey`);
      const b = page.locator('footer.tp-foot p button');
      if (y % 2) { assert.equal(await b.count(), 0, `${y}: odd, nothing to show`); await page.close(); continue; }
      // unchanged to the eye until pressed: the same pixels as the line without site.js
      const bare = await open(`/__year/${y}`, {}, true);
      await bare.page.waitForLoadState('load');
      assert.ok((await foot.screenshot()).equals(await bare.page.locator('footer.tp-foot p').screenshot()), `${y}: the footer looks the same`);
      await bare.page.close();
      assert.match(await b.getAttribute('aria-label'), new RegExp(`^Year ${y}$`));
      await b.click();
      const m = (await b.textContent()).match(/^(\d{4}) = (\d+) \+ (\d+)$/);
      assert.ok(m, `${y}: shows y = p + q`);
      const [Y, p, q] = m.slice(1).map(Number);
      assert.equal(Y, y); assert.equal(p + q, y);
      assert.ok(prime(p) && prime(q) && p <= q, `${y}: ${p} and ${q} prime`);
      assert.ok(twin(p) || twin(q), `${y}: a twin prime among ${p}, ${q}`);
      for (let s = 2; s < p; s++) assert.ok(!(prime(s) && prime(y - s) && (twin(s) || twin(y - s))), `${y}: ${s} is smaller`);
      assert.equal(await b.getAttribute('aria-label'), `Year ${y} = ${p} + ${q}`);
      await b.click();
      assert.equal(await b.textContent(), String(y), 'the next click puts it back');
      await b.focus(); await page.keyboard.press('Enter');
      assert.equal(await b.textContent(), `${y} = ${p} + ${q}`, 'Enter works too');
      assert.deepEqual(errors, []);
      await page.close();
    }
  });

  await t.test('lattice: a logical error, by hand or by the decoder, opens the door; nothing else does', async () => {
    const { page, errors } = await open('/');
    const st = page.locator('#lat-status'), door = st.locator('a[href="/logical/"]');
    const q = n => page.locator(`#lattice .q[data-q="${n}"]`);
    const flipAll = async ns => { for (const n of ns) await q(n).click(); };
    assert.equal(await door.count(), 0, 'not at the start');
    await flipAll([12, 27]);                                   // clear the two starting flips
    await flipAll([0, 1, 3, 10]);                              // one plaquette: closed, contractible
    assert.match(await st.textContent(), /does no harm/);
    assert.equal(await door.count(), 0, 'a harmless loop is not the door');
    await flipAll([1, 3, 10]);                                 // back to h(0,0) alone
    await flipAll([2, 4, 6, 8]);                               // the whole top row: wraps the torus
    assert.match(await st.textContent(), /logical error the checks cannot see\. Something changed anyway\. Try to beat the decoder\.$/);
    assert.equal(await door.textContent(), 'Try to beat the decoder.');
    await q(8).click();
    assert.equal(await door.count(), 0, 'gone once a check lights');
    await q(8).click();
    assert.equal(await door.count(), 1);
    await page.locator('#reset').click();
    assert.equal(await door.count(), 0, 'gone on reset');
    // three in a row; matching closes the loop the short way, round the torus
    await flipAll([12, 27, 0, 2, 4]);
    await page.locator('#fix').click();
    assert.match(await st.textContent(), /a logical error\. The shortest explanation was the wrong one\. Something changed anyway\. Try to beat the decoder\.$/);
    assert.equal(await door.count(), 1);
    // two in a row; matching closes a harmless loop
    await page.locator('#reset').click();
    await flipAll([12, 27, 0, 2]);
    await page.locator('#fix').click();
    assert.match(await st.textContent(), /intact\.$/);
    assert.equal(await door.count(), 0);
    // by keyboard: the link is reachable and goes to the hidden page
    await page.locator('#reset').click();
    await flipAll([12, 27, 0, 2, 4, 6, 8]);
    await door.focus();
    await Promise.all([page.waitForURL(/\/logical\/$/), page.keyboard.press('Enter')]);
    assert.deepEqual(errors, []);
    await page.close();
  });

  await t.test('beat the decoder: engine rounds, judged by the engine, by mouse, touch and keyboard', async () => {
    const { page, errors } = await open('/logical/', { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
    assert.equal(await page.locator('h1').textContent(), 'Beat the decoder');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= 390), 'no sideways scroll at 390px');
    for (const box of await page.locator('#board .q .hit').evaluateAll(es => es.map(e => e.getBoundingClientRect())))
      assert.ok(box.width >= 40 && box.height >= 40, `tap target ${box.width}x${box.height}`);
    const status = page.locator('#status'), tally = page.locator('#tally');
    assert.equal(await status.getAttribute('aria-live'), 'polite');
    const play = async (seed, lv) => {
      await page.locator(`input[name="rate"][value="${lv}"]`).check();
      await page.locator('#seed').fill(String(seed));
      await page.locator('#replay').click();
    };
    // a round the decoder gets wrong at the top rate, then one it gets right
    let bad = 1; while (restores(round(bad, 2).err, round(bad, 2).decoder)) bad++;
    let good = 1; while (!restores(round(good, 2).err, round(good, 2).decoder)) good++;

    await play(bad, 2);
    const r = round(bad, 2);
    assert.equal(await page.locator('#board .zc.on').count(), r.fired.reduce((a, b) => a + b, 0), 'the fired checks');
    assert.equal(await page.locator('#board .q.err').count(), 0, 'errors hidden before Check');
    for (let i = 0; i < 25; i++) if (r.err[i]) await page.locator(`#board .q[data-q="${i}"]`).tap();
    assert.equal(await page.locator('#board .zc.on').count(), 0, 'marking the errors quiets every check');
    await page.locator('#check').click();
    assert.match(await status.textContent(), /Yours restored the stored bit; the decoder's did not\./);
    assert.equal(await tally.textContent(), 'You 1, Decoder 0');
    assert.equal(await page.locator('#board .q.err').count(), r.err.reduce((a, b) => a + b, 0), 'errors shown');
    assert.equal(await page.locator('#board .q.dec').count(), r.decoder.reduce((a, b) => a + b, 0), "decoder's shown");
    assert.ok(await page.locator('#check').isDisabled(), 'one verdict per round');

    // replay the same seed: the same round
    await play(bad, 2);
    assert.equal(await page.locator('#board .zc.on').count(), r.fired.reduce((a, b) => a + b, 0));
    assert.equal(await page.locator('#board .q.err').count(), 0);

    // keyboard only: do nothing, then check
    await play(good, 2);
    await page.locator('#board .q[tabindex="0"]').focus();
    const first = await page.evaluate(() => document.activeElement.getAttribute('data-q'));
    await page.keyboard.press('ArrowRight');
    const second = await page.evaluate(() => document.activeElement.getAttribute('data-q'));
    assert.equal(+second, +first + 1, 'arrow keys move along a row');
    await page.keyboard.press('Enter');
    assert.equal(await page.locator(`#board .q[data-q="${second}"]`).getAttribute('aria-pressed'), 'true');
    await page.keyboard.press(' ');
    assert.equal(await page.locator(`#board .q[data-q="${second}"]`).getAttribute('aria-pressed'), 'false');
    await page.locator('#check').focus(); await page.keyboard.press('Enter');
    assert.match(await status.textContent(), /The decoder's restored the stored bit; yours left \d+ checks? lit\./);
    assert.equal(await tally.textContent(), 'You 1, Decoder 1');

    // a new round draws a fresh seed and clears the verdict
    await page.locator('#new').click();
    assert.notEqual(await page.locator('#seed').inputValue(), String(good));
    assert.ok(await page.locator('#check').isEnabled());
    assert.equal(LEVELS.length, await page.locator('input[name="rate"]').count());
    assert.deepEqual(errors, []);
    await page.close();
  });
});
