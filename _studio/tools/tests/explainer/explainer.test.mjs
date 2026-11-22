// why-error-correction.html: the plain-language front door. Fixes the page contract (head, shell, Article
// JSON-LD), the text rules (no kets or formulas, no em dashes, 450 to 800 words of prose), the figure logic
// against the course engine on real engine runs, and keyboard operation of the figure in a browser.
// The browser part needs playwright and its chromium from _studio/node_modules; it skips otherwise.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { mulberry32 } from '../../../../qec-in-practice/js/stabsim.js';
import { repetitionCode } from '../../../../qec-in-practice/js/qec/codes.js';
import { sampleErrors, syndrome } from '../../../../qec-in-practice/js/qec/noise.js';
import { majorityDecode } from '../../../../qec-in-practice/js/qec/decoder.js';
import { estimate } from '../../../../qec-in-practice/js/qec/montecarlo.js';
import { repetitionCurve } from '../../../../qec-in-practice/js/explore-logic.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const PAGE = path.join(ROOT, 'why-error-correction.html');
const URL_ = 'https://pandey-tushar.com/why-error-correction.html';
const html = fs.existsSync(PAGE) ? fs.readFileSync(PAGE, 'utf8') : '';
const head = html.split('</head>')[0];
const logic = await import('../../../../explainer/explainer-logic.js').catch(() => null);

const ENT = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', middot: '·', rsquo: '’', lsquo: '‘', ldquo: '“', rdquo: '”', mdash: '—', ndash: '–', hellip: '…', rang: '⟩', lang: '⟨', minus: '−', times: '×', sum: '∑', copy: '©' };
const decode = s => s.replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
  .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(+d)).replace(/&(\w+);/g, (m, n) => ENT[n] ?? m);
const visible = s => decode(s.replace(/<script[\s\S]*?<\/script>/g, ' ').replace(/<style[\s\S]*?<\/style>/g, ' ')
  .replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim();
const mainHtml = (html.match(/<main[\s\S]*?<\/main>/) || [''])[0];
const prose = visible(mainHtml.replace(/<figure[\s\S]*?<\/figure>/g, ' '));
// kets, brackets, operators and maths symbols; em dashes; tags that set formulas
const FORBIDDEN = /[|⟨⟩=+^∑√≈×÷<>−≤≥—]/;

test('page exists with the site shell and its meta', () => {
  assert.ok(html, 'why-error-correction.html is missing');
  assert.match(html, /<html lang="en" class="tp-full">/);
  assert.deepEqual(head.match(/<meta name="theme-color" content="[^"]*">/g), ['<meta name="theme-color" content="#0d1320">']);
  assert.match(head, /getItem\(\s*"tp-theme"\s*\)/);
  for (const s of ['<link rel="icon" href="/favicon.ico" sizes="16x16 32x32 48x48">', '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
    '<link rel="apple-touch-icon" href="/apple-touch-icon.png">', '<link rel="stylesheet" href="/lib/site.css">', '<script src="/lib/site.js" defer></script>',
    `<link rel="canonical" href="${URL_}">`, `<meta property="og:url" content="${URL_}">`,
    '<meta property="og:image" content="https://pandey-tushar.com/og-qec.png">', '<meta property="og:image:width" content="1200">',
    '<meta property="og:image:height" content="630">', '<meta name="twitter:image" content="https://pandey-tushar.com/og-qec.png">',
    '<meta property="og:type" content="article">'])
    assert.ok(head.includes(s), `head lacks ${s}`);
  assert.match(head, /<title>Why quantum computers need error correction/);
  assert.match(head, /<meta name="description" content="[^"]{60,}">/);
  assert.match(head, /<meta property="og:title" content="[^"]+">/);
  assert.match(head, /<meta property="og:description" content="[^"]+">/);
  assert.ok(!/fonts\.googleapis|background-clip:\s*text|backdrop-filter|gradient\(/.test(html), 'web fonts or gradients');
  assert.ok(!/qd-theme/.test(html));
  assert.equal((html.match(/<h1[\s>]/g) || []).length, 1);
  assert.equal((html.match(/<main[\s>]/g) || []).length, 1);
  assert.match(html, /<a class="tp-skip" href="#main">/);
  assert.match(html, /<main id="main">/);
  assert.match(html, /<header class="tp-bar">/);
  assert.match(html, /<footer class="tp-foot">/);
});

test('Article JSON-LD agrees with the visible page', () => {
  const ld = [...head.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map(m => JSON.parse(m[1]));
  const a = ld.find(x => x['@type'] === 'Article');
  assert.ok(a, 'no Article');
  const h1 = visible((html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/) || ['', ''])[1]);
  assert.equal(a.headline, h1);
  assert.equal(a.url, URL_);
  assert.equal(a.image, 'https://pandey-tushar.com/og-qec.png');
  assert.equal(a.author && a.author.name, 'Tushar Pandey');
  assert.equal(a.inLanguage, 'en');
});

test('links: the course, the books, the research page', () => {
  for (const h of ['/qec-in-practice/', '/qubit-dialogues.html', '/life/', '/research.html'])
    assert.ok(mainHtml.includes(`href="${h}"`), `main does not link ${h}`);
});

test('text: no kets, formulas or em dashes; ASCII source; 450 to 800 words', () => {
  const vis = visible(mainHtml);
  const bad = vis.match(FORBIDDEN);
  assert.equal(bad, null, `forbidden character ${bad && JSON.stringify(bad[0])} in: ${bad && vis.slice(Math.max(0, bad.index - 40), bad.index + 40)}`);
  assert.ok(!/<(sub|sup|math)[\s>]/.test(mainHtml), 'sub, sup or math markup');
  const nonAscii = [...html].filter(c => c.charCodeAt(0) > 126);
  assert.deepEqual(nonAscii, [], 'non-ASCII in the source (use entities)');
  const words = prose.split(/\s+/).filter(w => /[A-Za-z0-9]/.test(w)).length;
  assert.ok(words >= 450 && words <= 800, `${words} words of prose`);
});

// ---- the figure logic against the engine ----
const L = logic || {};
const need = {}; // a missing logic module fails every test below, it never skips
const bitsOf = (n, m) => Uint8Array.from({ length: n }, (_, i) => (m >> i) & 1);
const weight = a => a.reduce((s, b) => s + b, 0);

test('majority vote over n qubits fails exactly when more than half flip (every pattern, n = 3, 5, 7)', need, () => {
  assert.ok(logic, 'explainer/explainer-logic.js missing');
  for (const n of [3, 5, 7]) {
    const row = L.makeRow(n);
    for (let m = 0; m < 2 ** n; m++) {
      row.err = { x: bitsOf(n, m), z: new Uint8Array(n) };
      const r = L.correct(row), k = weight(row.err.x);
      assert.equal(r.survived, 2 * k < n, `n=${n} pattern ${m}`);
      // the correction is the engine's majority decoder read from the checks alone
      assert.deepEqual([...r.correction], [...majorityDecode(row.code, syndrome(row.code, row.err).Z)]);
      assert.equal(weight(r.correction), Math.min(k, n - k), 'the fewest flips that explain the checks');
      // after the correction every qubit agrees, and every check is quiet
      assert.ok(r.after.x.every(b => b === r.after.x[0]));
      assert.equal(r.after.x[0], r.survived ? 0 : 1);
    }
  }
});

test('five qubits survive any two flips and lose the bit to any three', need, () => {
  const row = L.makeRow(5);
  for (let m = 0; m < 32; m++) {
    row.err = { x: bitsOf(5, m), z: new Uint8Array(5) };
    assert.equal(L.correct(row).survived, weight(row.err.x) <= 2);
  }
});

test('checks light where neighbours disagree, from the engine syndrome, on engine-sampled errors', need, () => {
  const rng = mulberry32(7);
  for (const n of [3, 5, 7]) {
    const row = L.makeRow(n);
    for (let s = 0; s < 400; s++) {
      row.err = sampleErrors(row.code, 0.3, rng);
      const lit = L.checksLit(row);
      assert.equal(lit.length, n - 1);
      for (let k = 0; k < n - 1; k++) assert.equal(lit[k], row.err.x[k] ^ row.err.x[k + 1]);
      assert.deepEqual([...lit], [...syndrome(row.code, row.err).Z]);
      assert.equal(L.correct(row).survived, 2 * weight(row.err.x) < n);
    }
  }
});

test('loss table: 1, 3, 5, 7 qubits from the exact formula, matching engine Monte Carlo', need, () => {
  assert.deepEqual(L.SIZES, [1, 3, 5, 7]);
  let seed = 41;
  for (const p of [0.05, 0.2, 0.7]) {
    const t = L.lossTable(p);
    assert.deepEqual(t.map(r => r.n), [1, 3, 5, 7]);
    for (const r of t) {
      assert.equal(r.lost, repetitionCurve(r.n, p));
      const shots = 20000, mc = estimate({ kind: 'repetition', d: r.n, p, shots, seed: seed++ });
      const sig = Math.sqrt(r.lost * (1 - r.lost) / shots);
      assert.ok(Math.abs(mc.rate - r.lost) <= 4 * sig + 1e-9, `n=${r.n} p=${p}: ${mc.rate} vs ${r.lost}`);
    }
  }
});

test('threshold at one half: more qubits help below it, hurt above it, no change at it', need, () => {
  for (let i = 1; i < 100; i++) {
    const p = i / 100, lost = L.lossTable(p).map(r => r.lost);
    for (let j = 1; j < lost.length; j++) {
      if (p < 0.5) assert.ok(lost[j] < lost[j - 1], `p=${p}`);
      else if (p > 0.5) assert.ok(lost[j] > lost[j - 1], `p=${p}`);
      else assert.ok(Math.abs(lost[j] - lost[j - 1]) < 1e-12);
    }
    assert.equal(L.trend(p), p < 0.5 ? 'help' : p > 0.5 ? 'hurt' : 'same');
  }
});

test('chances read in plain words', need, () => {
  assert.equal(L.formatChance(0), 'never');
  assert.equal(L.formatChance(0.1), '10%');
  assert.equal(L.formatChance(0.028), '2.8%');
  assert.equal(L.formatChance(0.5), '50%');
  assert.equal(L.formatChance(repetitionCurve(5, 0.1)), '1 in 120');
  assert.equal(L.formatChance(repetitionCurve(7, 0.01)), '1 in 2,900,000');
  assert.equal(L.formatChance(0.9997), 'over 99.9%');
  for (let i = 1; i < 100; i++) for (const r of L.lossTable(i / 100))
    assert.equal(L.formatChance(r.lost).match(FORBIDDEN), null);
});

// ---- the page in a browser: keyboard operation, live status, touch targets ----
let chromium = null, why = '';
try {
  ({ chromium } = createRequire(path.join(ROOT, '_studio/package.json'))('playwright'));
  if (!fs.existsSync(chromium.executablePath())) { why = 'playwright chromium not installed'; chromium = null; }
} catch (e) { why = 'playwright not found in _studio/node_modules'; }

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon' };
function serve() {
  const srv = http.createServer((req, res) => {
    const f = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
    if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' });
    fs.createReadStream(f).pipe(res);
  });
  return new Promise(ok => srv.listen(0, '127.0.0.1', () => ok(srv)));
}

test('figure is keyboard operable with a live status', { skip: chromium ? false : why }, async t => {
  const srv = await serve(), base = `http://127.0.0.1:${srv.address().port}`;
  t.after(() => srv.close());
  const browser = await chromium.launch();
  t.after(() => browser.close());
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error' && (m.location().url || '').startsWith(base)) errors.push(m.text()); });
  await page.route(u => u.hostname !== '127.0.0.1', r => r.abort());
  await page.goto(`${base}/why-error-correction.html`);
  const fig = page.locator('#fig-vote');
  const qubits = fig.locator('button[data-q]');
  await qubits.first().waitFor();
  assert.equal(await qubits.count(), 5);
  const status = fig.locator('[aria-live]').first();
  assert.ok((await status.getAttribute('aria-live')) === 'polite');
  const lit = () => fig.locator('[data-check].lit').count();
  assert.equal(await fig.locator('[data-check]').count(), 4);

  // Tab reaches the first qubit; Enter and Space flip, aria-pressed follows
  await page.locator('h1').click();
  let hops = 0;
  while (!(await page.evaluate(() => document.activeElement && document.activeElement.hasAttribute('data-q'))) && hops++ < 60) await page.keyboard.press('Tab');
  assert.ok(hops < 60, 'Tab never reached a qubit');
  const focused = page.locator(':focus');
  assert.equal(await focused.getAttribute('data-q'), '0');
  const ring = await focused.evaluate(e => getComputedStyle(e).outlineStyle);
  assert.notEqual(ring, 'none', 'no visible focus ring');
  await page.keyboard.press('Tab'); // second qubit
  await page.keyboard.press('Enter');
  assert.equal(await qubits.nth(1).getAttribute('aria-pressed'), 'true');
  assert.equal(await lit(), 2, 'a flip in the middle lights the two checks beside it');
  assert.match(await status.textContent(), /Qubit 2/);
  await page.keyboard.press('Tab'); await page.keyboard.press('Tab');
  await page.keyboard.press(' ');
  assert.equal(await qubits.nth(3).getAttribute('aria-pressed'), 'true');

  // Correct by keyboard: two flips of five, the bit survives and the row is clean
  const correct = fig.locator('button[data-correct]');
  await correct.focus(); await page.keyboard.press('Enter');
  assert.match(await status.textContent(), /survived/i);
  assert.equal(await fig.locator('button[data-q][aria-pressed="true"]').count(), 0);
  assert.equal(await lit(), 0);

  // three flips lose it
  for (const i of [0, 2, 4]) { await qubits.nth(i).focus(); await page.keyboard.press('Enter'); }
  await correct.focus(); await page.keyboard.press('Enter');
  assert.match(await status.textContent(), /lost/i);

  // slider by arrow keys updates the loss table
  const slider = fig.locator('input[type=range]');
  assert.ok(await page.locator(`label[for="${await slider.getAttribute('id')}"]`).count() || await slider.getAttribute('aria-label'), 'slider has no label');
  const table = () => fig.locator('[data-loss]').innerText();
  const before = await table();
  await slider.focus();
  for (let i = 0; i < 50; i++) await page.keyboard.press('ArrowRight');
  assert.notEqual(await table(), before);
  assert.ok(+(await slider.inputValue()) > 0.5);
  assert.match(await fig.locator('[data-trend]').textContent(), /worse|hurt/i);

  // Random errors by keyboard
  await fig.locator('button[data-random]').focus(); await page.keyboard.press('Enter');
  assert.match(await status.textContent(), /Random errors/);
  await fig.locator('button[data-clear]').focus(); await page.keyboard.press('Space');
  assert.equal(await fig.locator('button[data-q][aria-pressed="true"]').count(), 0);

  // the text the scripts write follows the same rules
  const bad = (await page.locator('main').innerText()).match(FORBIDDEN);
  assert.equal(bad, null, `forbidden character in rendered text: ${bad && bad[0]}`);
  assert.deepEqual(errors, []);

  // touch: every control is at least 40px
  const phone = await browser.newPage({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  await phone.route(u => u.hostname !== '127.0.0.1', r => r.abort());
  await phone.goto(`${base}/why-error-correction.html`);
  await phone.locator('#fig-vote button[data-q]').first().waitFor();
  const small = await phone.evaluate(() => [...document.querySelectorAll('#fig-vote button, #fig-vote input')]
    .map(e => [e.outerHTML.slice(0, 50), e.getBoundingClientRect()]).filter(([, r]) => r.width < 40 || r.height < 40).map(([h]) => h));
  assert.deepEqual(small, []);
  const overflow = await phone.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  assert.ok(overflow <= 0, `page scrolls sideways by ${overflow}px on a phone`);
  await phone.close();
});
