// Helpers behind the course pages' text, the fault count the lesson results notes rest on, and the course layout
// in a browser (needs playwright and its chromium from _studio/node_modules; that part skips otherwise).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { Tableau, mulberry32 } from '../../../../qec-in-practice/js/stabsim.js';
import { stateHTML } from '../../../../qec-in-practice/js/patch.js';
import { phaseLabel, shortPhase, whereText } from '../../../../qec-in-practice/js/strip.js';
import { surfaceCode, repetitionCode } from '../../../../qec-in-practice/js/qec/codes.js';
import { qubitName, rcName, repCheckName, sampleSomeErrors } from '../../../../qec-in-practice/js/explore-logic.js';

const lesson = (n) => JSON.parse(readFileSync(new URL(`../../../../qec-in-practice/data/lesson${n}.json`, import.meta.url), 'utf8'));

test('a subscript L is joined to what it follows by a word joiner, never a zero-width space', () => {
  assert.equal(stateHTML('|T>_L'), '|T&#10217;&#8288;<sub>L</sub>');
  assert.equal(stateHTML('X_L of A'), 'X&#8288;<sub>L</sub> of A');
  assert.ok(!stateHTML('|+>_L and Z_L').includes('&#8203;'));
});

test('the readout rotation has one name in the strip, the step list and the step label', () => {
  assert.equal(phaseLabel('readout rotation A (X)'), 'H on A');
  assert.equal(phaseLabel('readout rotation C (X)'), 'H on C');
  assert.equal(shortPhase('readout rotation A (X)'), 'H on A');
  assert.equal(phaseLabel('encode A'), 'encode A');
});

test('the player labels its starting view Start, not step 1', () => {
  assert.equal(whereText(0, 8, 'encode A'), 'Start: before step 1 of 9');
  assert.equal(whereText(0.99, 8, 'encode A'), 'Step 1 of 9: encode A');
  assert.equal(whereText(9, 8, 'measure'), 'All 9 steps done');
  assert.equal(whereText(8.5, 8, 'readout rotation A (X)'), 'Step 9 of 9: H on A');
});

test('qubits are named from 0: q0 on a line, (row, column) from (0, 0) on a patch, matching lesson 1 at d = 3', () => {
  assert.equal(qubitName(0), 'q0');
  assert.equal(repCheckName(0), 'c0');
  const c = surfaceCode(3);
  for (let q = 0; q < 9; q++) assert.equal(rcName(c, q), `(${Math.floor(q / 3)}, ${q % 3})`);
  assert.equal(rcName(surfaceCode(5), 7), '(1, 2)');
});

test('random errors for the decoder figure always include at least one error', () => {
  for (const code of [surfaceCode(3), repetitionCode(5)]) {
    const rng = mulberry32(7);
    for (let s = 0; s < 200; s++) {
      const e = sampleSomeErrors(code, 0.02, rng, 'bitflip');
      assert.ok(e.x.some(Boolean) || e.z.some(Boolean));
    }
  }
});

// The results notes say the lesson 1 encoder is not fault tolerant. Each of its 12 CNOTs, followed by each of the
// 15 two-qubit Paulis, is run through the stabilizer simulator; the data qubits are read in Z and decoded with the
// single-error table of js/lesson.js. 44 of the 180 single faults end in a wrong logical readout; none is discarded.
test('one faulty CNOT in the lesson 1 encoder can flip the logical readout after correction', () => {
  const D = lesson(1);
  const Z_STABS = [[1, 2, 4, 5], [3, 4, 6, 7], [0, 1], [7, 8]];
  const Z_TABLE = { '0000': -1, '0010': 0, '1010': 1, '1000': 2, '0100': 3, '1100': 4, '0101': 7, '0001': 8 };
  const gates = D.ops.filter((o) => o.gate !== 'measure').map((o, i) => ({ ...o, i })).sort((a, b) => a.t - b.t || a.i - b.i);
  const run = (k, pa, pb) => {
    const tab = new Tableau(9, () => 0.3);
    gates.forEach((g, j) => {
      tab[g.gate](...g.q);
      if (j === k) { if (pa !== 'i') tab[pa](g.q[0]); if (pb !== 'i') tab[pb](g.q[1]); }
    });
    const bits = [...Array(9).keys()].map((q) => tab.measureZ(q));
    const key = Z_STABS.map((s) => s.reduce((a, i) => a ^ bits[i], 0)).join('');
    if (!(key in Z_TABLE)) return 'discard';
    if (Z_TABLE[key] >= 0) bits[Z_TABLE[key]] ^= 1;
    return bits[0] ^ bits[3] ^ bits[6] ? 'fail' : 'ok';
  };
  assert.equal(run(-1), 'ok');
  const tally = { ok: 0, fail: 0, discard: 0 };
  let cnots = 0;
  gates.forEach((g, k) => {
    if (g.gate !== 'cx') return;
    cnots++;
    for (const a of 'ixyz') for (const b of 'ixyz') if (a !== 'i' || b !== 'i') tally[run(k, a, b)]++;
  });
  assert.equal(cnots, 12);
  assert.deepEqual(tally, { ok: 136, fail: 44, discard: 0 });
});

// What the results columns count, read off the stored data: every shot is clean (no check fired), corrected
// (a fired pattern found in the table) or discarded (a pattern not in the table), and the rates are over those counts.
test('stored results: clean + corrected + discarded = all shots, and a bare row has no checks', () => {
  for (const n of [1, 2, 3, 4]) for (const r of lesson(n).results) {
    assert.equal(r.n_clean + r.n_corrected + r.n_discarded, r.n_total);
    assert.equal(r.n_kept, r.n_total - r.n_discarded);
    assert.ok(Math.abs(r.correct_fraction - r.n_corrected / r.n_total) < 1e-9);
    assert.ok(Math.abs(r.discard_fraction - r.n_discarded / r.n_total) < 1e-9);
    if (r.kind === 'bare') assert.equal(r.blocks.length, 0);
  }
});

// The course pages in a browser. The five essay pages share the site column's left edge with the header and the
// lessons; from 70em a sticky right rail holds "In plain words" and an "On this page" list, clear of the figures
// and the footer. Below 70em the plain-words box sits under the title and the list is hidden. Nothing scrolls
// sideways on a phone, the top course row is one line at 1440, and every plain-words box has the same card look.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
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

const ESSAYS = ['repetition-code', 'decoding', 'threshold', 'lattice-surgery', 'glossary'];
const LESSONS = ['lesson-1', 'lesson-2', 'lesson-3', 'lesson-4'];
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, `${msg}: ${a} vs ${b}`);
const overlap = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

test('course layout in a browser', { skip: chromium ? false : why }, async t => {
  const srv = await serve();
  const base = `http://127.0.0.1:${srv.address().port}/qec-in-practice/`;
  t.after(() => srv.close());
  const browser = await chromium.launch();
  t.after(() => browser.close());
  async function open(name, width, height = 900) {
    const page = await browser.newPage({ viewport: { width, height } });
    await page.route(u => !u.host.startsWith('127.0.0.1'), r => r.abort());
    await page.goto(`${base}${name}.html`, { waitUntil: 'load' });
    await page.waitForTimeout(200);
    return page;
  }

  await t.test('at 1440 every course page starts on the header logo, and the top course row is one line', async () => {
    for (const name of [...ESSAYS, ...LESSONS]) {
      const page = await open(name, 1440);
      const m = await page.evaluate(() => ({
        h1: document.querySelector('main h1').getBoundingClientRect().left,
        logo: document.querySelector('.tp-mark').getBoundingClientRect().left,
        tops: [...document.querySelectorAll('nav.secnav:not(.endnav) a')].map(a => a.getBoundingClientRect().top),
      }));
      near(m.h1, m.logo, 2, `${name} h1 left vs logo left`);
      assert.ok(Math.max(...m.tops) - Math.min(...m.tops) < 2, `${name}: the top course row wraps (${m.tops})`);
      await page.close();
    }
  });

  await t.test('at 1440 the essay rail lists every h2 and figure and stays clear of figures and footer', async () => {
    for (const name of ESSAYS) {
      const page = await open(name, 1440, 700);
      const m = await page.evaluate(() => {
        const rail = document.querySelector('main .course-rail');
        const toc = rail && rail.querySelector('nav.course-toc');
        if (!toc || getComputedStyle(toc).display === 'none') return { missing: true };
        const targets = [...document.querySelectorAll('main h2, main figure, main dt')]
          .filter(e => !rail.contains(e) && !e.closest('.course-end')).map(e => e.id);
        const links = [...toc.querySelectorAll('a')].map(a => a.getAttribute('href').slice(1));
        const h1 = document.querySelector('main h1').getBoundingClientRect();
        const box = r => { const b = r.getBoundingClientRect(); return { left: b.left, right: b.right, top: b.top, bottom: b.bottom }; };
        const hits = [];
        const max = document.documentElement.scrollHeight - innerHeight;
        for (let k = 0; k <= 24; k++) {
          scrollTo(0, max * k / 24);
          const r = box(rail);
          for (const f of [...document.querySelectorAll('main figure, .tp-foot')]) if (!rail.contains(f)) {
            const b = box(f);
            if (b.left < r.right && r.left < b.right && b.top < r.bottom && r.top < b.bottom) hits.push(`${f.id || f.className} at ${k}/24`);
          }
          if (k === 12 && (r.bottom <= 0 || r.top >= innerHeight)) hits.push('rail out of view mid-page');
        }
        return { targets, links, hits, railLeft: box(rail).left, h1Right: h1.right };
      });
      assert.ok(!m.missing, `${name}: no visible .course-rail with nav.course-toc at 1440`);
      assert.ok(m.targets.every(Boolean), `${name}: an h2, figure or term has no id`);
      assert.deepEqual(m.links, m.targets, `${name}: the contents list is not every h2 and figure in order`);
      assert.deepEqual(m.hits, [], `${name}: the rail overlaps`);
      await page.close();
    }
  });

  await t.test('below 70em the plain-words box sits under the title and the contents list is hidden', async () => {
    for (const name of ESSAYS.filter(n => n !== 'glossary')) {
      const page = await open(name, 1024);
      const m = await page.evaluate(() => {
        const h1 = document.querySelector('main h1').getBoundingClientRect();
        const plain = document.querySelector('main .plain').getBoundingClientRect();
        const toc = document.querySelector('main .course-toc');
        return { h1b: h1.bottom, h1l: h1.left, pt: plain.top, pl: plain.left, toc: toc ? getComputedStyle(toc).display : 'none' };
      });
      assert.ok(m.pt >= m.h1b, `${name}: plain box above the title`);
      near(m.pl, m.h1l, 1, `${name}: plain box left vs title left`);
      assert.equal(m.toc, 'none', `${name}: contents list shown below 70em`);
      await page.close();
    }
  });

  await t.test('nothing scrolls sideways at 390', async () => {
    for (const name of [...ESSAYS, ...LESSONS]) {
      const page = await open(name, 390, 844);
      const m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
      assert.ok(m.sw <= m.cw, `${name}: scrollWidth ${m.sw} vs clientWidth ${m.cw}`);
      await page.close();
    }
  });

  await t.test('every plain-words box has the rail card look', async () => {
    const look = async name => {
      const page = await open(name, 1440);
      const s = await page.evaluate(() => {
        const c = getComputedStyle(document.querySelector('main .plain'));
        const l = getComputedStyle(document.querySelector('main .plain .tp-lbl'));
        return [c.borderTopWidth, c.borderLeftWidth, c.borderTopStyle, c.borderTopColor, c.backgroundColor, c.borderRadius, c.padding,
          l.fontSize, l.textTransform, l.color, l.marginBottom].join(' ');
      });
      await page.close();
      return s;
    };
    const want = await look('threshold');
    assert.match(want, /^1px 1px solid /, 'threshold: the plain box is not a 1px bordered card');
    for (const name of [...ESSAYS.filter(n => n !== 'glossary'), ...LESSONS]) assert.equal(await look(name), want, `${name}: plain box look`);
  });
});
