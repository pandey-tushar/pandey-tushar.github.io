// The article pages open on a window-sized live hero (lib/article.css, lib/article.js): a canvas figure run by
// TP.live behind a small mono tag, the page's one h1 and one line, and a scroll cue to the text below. The body
// keeps its content and its own tests; this file holds the shared shell. The browser part needs playwright and
// its chromium from _studio/node_modules; it skips otherwise.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const read = p => fs.readFileSync(path.join(ROOT, p), 'utf8');

// page: the figure behind its title
const PAGES = {
  'papers/adaptive-graph-of-thoughts.html': 'graph',
  'papers/bb-erasure-baselines.html': 'erasure',
  'papers/lifted-surgery.html': 'surgery',
  'notes/crossing-is-not-the-threshold.html': 'curves',
  'why-error-correction.html': 'rep',
  'qec-in-practice/repetition-code.html': 'rep',
  'qec-in-practice/lesson-1.html': 'patch',
  'qec-in-practice/decoding.html': 'uf',
  'qec-in-practice/threshold.html': 'curves',
  'qec-in-practice/lesson-2.html': 'patch',
  'qec-in-practice/lesson-3.html': 'patch',
  'qec-in-practice/lesson-4.html': 'patch',
  'qec-in-practice/lattice-surgery.html': 'surgery',
  'qec-in-practice/glossary.html': 'patch',
  'logical/index.html': 'patch',
  'tools/bb-codes.html': 'bb',
};
const js = read('lib/article.js'), css = read('lib/article.css');
const makers = new Set([...js.matchAll(/^\s{2}(\w+): function\(hero\)/gm)].map(m => m[1]));
const hero = html => (html.match(/<header class="ar-hero[^"]*" data-art="(\w+)">([\s\S]*?)<\/header>/) || []);
const visible = s => s.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();

for (const [page, art] of Object.entries(PAGES)) {
  test(`${page}: a live hero holds the one h1, its tag, one line and a cue`, () => {
    const html = read(page), head = html.split('</head>')[0];
    assert.ok(head.includes('<link rel="stylesheet" href="/lib/article.css">'), 'no /lib/article.css');
    assert.ok(head.includes('<script src="/lib/article.js" defer></script>'), 'no /lib/article.js');
    assert.ok(head.lastIndexOf('<link rel="stylesheet" href="/lib/article.css">') > Math.max(head.lastIndexOf('<style'), ...[...head.matchAll(/<link rel="stylesheet" href="([^"]+)">/g)].filter(m => m[1] !== '/lib/article.css').map(m => m.index)),
      'article.css is not the last stylesheet, so the page CSS would override it');
    const [, kind, body] = hero(html);
    assert.equal(kind, art, 'the figure');
    assert.ok(makers.has(kind), `article.js has no maker ${kind}`);
    assert.equal((html.match(/<header class="ar-hero/g) || []).length, 1);
    assert.match(body, /^\s*<canvas class="ar-viz" aria-hidden="true"><\/canvas>/);
    assert.match(body, /<div class="ar-text">\s*<p class="tp-lbl[^"]*">[^<]+<\/p>\s*<h1[\s>][\s\S]*?<\/h1>\s*<p class="[^"]*\bar-line\b[^"]*">/);
    assert.equal((html.match(/<h1[\s>]/g) || []).length, 1);
    const cue = body.match(/<a class="ar-cue" href="#([\w-]+)">([^<]+)<i aria-hidden="true"><\/i><\/a>/);
    assert.ok(cue, 'no scroll cue');
    assert.ok(html.includes(`id="${cue[1]}"`), `the cue's #${cue[1]} does not resolve`);
    const words = visible(body);
    assert.doesNotMatch(words, /[^\x00-\x7f]|&mdash;/, 'non-ASCII or an em dash in the hero');
  });
}

test('lesson-template.html carries the hero the build fills in', () => {
  const t = read('_studio/tools/lesson-template.html');
  assert.match(t, /<header class="ar-hero" data-art="patch">/);
  assert.match(t, /<p class="ar-line">\{\{part\}\}<\/p>/);
  assert.match(t, /<link rel="stylesheet" href="\/lib\/article\.css">/);
});

test('article.css and article.js: shared, quiet, and never the site files', () => {
  assert.doesNotMatch(css + js, /backdrop-filter|background-clip:\s*text|NVIDIA|Dynamo/);
  assert.match(css, /prefers-reduced-motion/);
  assert.match(css, /@media print/);
  assert.match(js, /TP\.live/);
  assert.ok(!js.includes('/logical/'), 'only the homepage may link the hidden page');
  for (const k of new Set(Object.values(PAGES))) assert.ok(makers.has(k), `no maker ${k}`);
});

let chromium = null, why = '';
try {
  ({ chromium } = createRequire(path.join(ROOT, '_studio/package.json'))('playwright'));
  if (!fs.existsSync(chromium.executablePath())) { why = 'playwright chromium not installed'; chromium = null; }
} catch (e) { why = 'playwright not found in _studio/node_modules'; }

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
  '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.webp': 'image/webp', '.png': 'image/png', '.json': 'application/json' };
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

test('the heroes in a browser', { skip: chromium ? false : why }, async t => {
  const srv = await serve(), base = `http://127.0.0.1:${srv.address().port}/`;
  t.after(() => srv.close());
  const browser = await chromium.launch();
  t.after(() => browser.close());
  for (const [w, h, mobile] of [[1440, 900, false], [390, 844, true]]) {
    for (const theme of ['dark', 'light']) {
      await t.test(`${w}px, ${theme}`, async () => {
        for (const page of Object.keys(PAGES)) {
          const p = await browser.newPage({ viewport: { width: w, height: h }, isMobile: mobile, hasTouch: mobile, colorScheme: theme });
          const errors = [];
          p.on('pageerror', e => errors.push(String(e)));
          p.on('console', m => { if (m.type() === 'error' && (m.location().url || '').startsWith(base)) errors.push(m.text()); });
          await p.route(u => !u.host.startsWith('127.0.0.1'), r => r.abort());
          await p.goto(base + page, { waitUntil: 'load' });
          await p.waitForTimeout(250);
          const m = await p.evaluate(() => {
            const hero = document.querySelector('.ar-hero'), cv = hero.querySelector('canvas.ar-viz');
            const r = hero.getBoundingClientRect(), bar = document.querySelector('.tp-bar').getBoundingClientRect();
            const h1 = document.querySelector('h1').getBoundingClientRect(), logo = document.querySelector('.tp-mark').getBoundingClientRect();
            const px = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
            let ink = 0; for (let i = 3; i < px.length; i += 4 * 97) ink += px[i] > 0;
            return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, barB: bar.bottom, h1l: h1.left, logo: logo.left,
              inHero: hero.contains(document.querySelector('h1')), cw: cv.width, ink, theme: document.documentElement.dataset.theme,
              sw: document.documentElement.scrollWidth, vw: document.documentElement.clientWidth,
              font: getComputedStyle(document.querySelector('h1')).fontFamily };
          });
          assert.equal(m.theme, theme, page);
          assert.ok(m.inHero, `${page}: the h1 is not in the hero`);
          assert.ok(Math.abs(m.top - m.barB) <= 1, `${page}: the hero does not start under the header (${m.top} vs ${m.barB})`);
          assert.ok(m.bottom - m.top >= Math.min(h - m.barB, 544) - 2, `${page}: the hero is ${m.bottom - m.top}px, not the window`);
          assert.ok(Math.abs(m.left) <= 1 && Math.abs(m.right - m.vw) <= 1, `${page}: the hero is not full-bleed (${m.left}, ${m.right}, ${m.vw})`);
          assert.ok(Math.abs(m.h1l - (w > 600 ? m.logo : m.h1l)) <= 2, `${page}: h1 left ${m.h1l} vs logo ${m.logo}`);
          assert.ok(m.cw > 0 && m.ink > 20, `${page}: the canvas is blank`);
          assert.ok(m.sw <= m.vw, `${page}: scrolls sideways (${m.sw} vs ${m.vw})`);
          assert.match(m.font, /^"?Geist/, `${page}: h1 is not in Geist`);
          assert.deepEqual(errors, [], page);
          await p.close();
        }
      });
    }
  }
});
