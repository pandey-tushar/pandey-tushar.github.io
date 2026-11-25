// The three book readers (qubit-dialogues.html, life/, illustrated/) in a browser:
// the site bar and footer on the site's column, the end links of life/, the
// illustrated edition's width and rail, and the text edition's equations,
// figure captions and contents control.
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

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2', '.webp': 'image/webp', '.png': 'image/png', '.json': 'application/json' };
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

// the 72rem column of the full-mode pages, whose root is 17px from 40em up
const COLUMN = 72 * 17;
const gut = w => Math.min(72, Math.max(20, 0.05 * w));
const inset = w => Math.max(gut(w), (w - COLUMN) / 2);
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, `${msg}: ${a} vs ${b}`);

test('illustrated metadata says twenty-two', () => {
  for (const f of ['_studio/apps/illustrated/index.html', 'illustrated/index.html']) {
    const head = fs.readFileSync(path.join(ROOT, f), 'utf8').split('</head>')[0];
    assert.ok(!/twenty two/i.test(head), `${f}: "twenty two" in the head`);
  }
});

let base, srv, browser;
test('readers in a browser', { skip: chromium ? false : why }, async t => {
  srv = await serve(); base = `http://127.0.0.1:${srv.address().port}`;
  t.after(() => srv.close());
  browser = await chromium.launch();
  t.after(() => browser.close());

  async function open(url, width, height = 900, opts = {}) {
    const page = await browser.newPage({ viewport: { width, height }, ...opts });
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.route(u => !u.host.startsWith('127.0.0.1'), r => r.abort());
    await page.goto(base + url, { waitUntil: 'load' });
    await page.waitForTimeout(300);
    return { page, errors };
  }

  await t.test('bar and footer sit on the site column', async () => {
    // illustrated/ is night only and has no switch: its bar ends at the nav
    for (const url of ['/qubit-dialogues.html', '/life/', '/illustrated/']) for (const w of [1920, 1440, 1024]) {
      const { page } = await open(url, w);
      const m = await page.evaluate(() => {
        const r = s => document.querySelector(s).getBoundingClientRect();
        const cw = document.documentElement.clientWidth;
        return { cw, mark: r('.tp-mark').left, toggle: r(document.querySelector('.tp-toggle') ? '.tp-toggle' : '.tp-nav').right,
          fl: r('.tp-foot').left, fr: r('.tp-foot').right };
      });
      const x = inset(m.cw);
      near(m.mark, x, 1, `${url} ${w} logo`);
      near(m.toggle, m.cw - x, 1, `${url} ${w} switch`);
      near(m.fl, x, 1, `${url} ${w} footer left`);
      near(m.fr, m.cw - x, 1, `${url} ${w} footer right`);
      await page.close();
    }
  });

  // the three readers open on a window-sized live hero in the homepage's
  // pane system: a TP.live field behind the whole window with the cover lit in
  // it, the title in Geist, one line and a way in; the book keeps its serif
  const HEROES = [
    { url: '/qubit-dialogues.html', title: 'The Qubit Dialogues', cover: 'qubit-dialogues', start: '#invocation',
      line: 'A Book of Possibilities', serif: '#invocation .dlg p', label: '.canto-num', themes: ['dark', 'light'],
      contents: '#contents' },
    { url: '/life/', title: 'An Unpolarized Life', cover: 'an-unpolarized-life', start: '#invocation',
      line: 'A Book of Questions', serif: '#invocation .dlg p', label: '.canto-num', themes: ['dark', 'light'] },
    { url: '/illustrated/', title: 'The Qubit Dialogues', cover: 'qubit-dialogues-illustrated', start: '#canto-1',
      line: 'Twenty two cantos between a Seeker and an Oracle, set as plates.', serif: '#canto-1 .turn p:not(.who)',
      label: '#canto-1 .numeral', themes: ['dark'] },
  ];
  await t.test('the readers: a live hero, Geist chrome, serif text', async () => {
    for (const h of HEROES) for (const theme of h.themes) for (const [w, ht] of [[1440, 900], [390, 844]]) {
      const page = await browser.newPage({ viewport: { width: w, height: ht } });
      const errors = [];
      page.on('pageerror', e => errors.push(String(e)));
      await page.route(u => !u.host.startsWith('127.0.0.1'), r => r.abort());
      await page.addInitScript(th => localStorage.setItem('tp-theme', th), theme);
      await page.goto(base + h.url, { waitUntil: 'load' });
      await page.waitForTimeout(700);
      const at = `${h.url} ${theme} ${w}`;
      const m = await page.evaluate(() => {
        const hero = document.querySelector('.rd-hero.tp-pane');
        if (!hero) return null;
        const r = hero.getBoundingClientRect(), bar = document.querySelector('.tp-bar').getBoundingClientRect();
        const cv = hero.querySelector('.tp-pane-viz > canvas'), img = hero.querySelector('img.tp-pane-cover');
        const px = cv && cv.width ? cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data : [];
        let ink = 0; for (let i = 3; i < px.length; i += 4) if (px[i]) ink++;
        const ff = s => { const e = document.querySelector(s); return e ? getComputedStyle(e).fontFamily : ''; };
        const start = hero.querySelector('a.rd-start');
        return { top: r.top, barBottom: bar.bottom, left: r.left, width: r.width, height: r.height,
          cw: document.documentElement.clientWidth, sw: document.documentElement.scrollWidth, vh: innerHeight,
          h1s: document.querySelectorAll('h1').length, h1: hero.querySelector('h1')?.textContent,
          line: hero.querySelector('.tp-pane-line')?.textContent, tag: hero.querySelector('.tp-pane-tag')?.textContent,
          ink, live: !!(window.TP && TP.live),
          cover: img ? { src: img.currentSrc || img.src, vis: getComputedStyle(img).visibility, ok: img.complete && img.naturalWidth > 0,
            in: (b => b.left >= r.left && b.right <= r.right + 1 && b.top >= r.top - 1 && b.bottom <= r.bottom + 1)(img.getBoundingClientRect()) } : null,
          start: start && { href: start.getAttribute('href'), text: start.textContent.trim() },
          fName: ff('.rd-hero h1'), fTag: ff('.rd-hero .tp-pane-tag'), fNav: ff('.tp-nav a') };
      });
      assert.ok(m, `${at}: no .rd-hero.tp-pane`);
      near(m.top, m.barBottom, 1, `${at} hero starts under the bar`);
      near(m.left, 0, 0.5, `${at} hero left edge`);
      near(m.width, m.cw, 0.5, `${at} hero is full-bleed`);
      near(m.height, Math.max(m.vh - m.barBottom, 34 * 16), 2, `${at} hero is the window under the bar`);
      assert.ok(m.sw <= m.cw, `${at}: scrolls sideways ${m.sw} vs ${m.cw}`);
      assert.equal(m.h1s, 1, `${at}: one h1`);
      assert.equal(m.h1, h.title);
      assert.equal(m.line, h.line);
      assert.ok(m.tag && m.tag.length > 0, `${at}: no tag`);
      assert.ok(m.live, `${at}: TP.live missing`);
      assert.ok(m.ink > 1000, `${at}: the hero canvas is blank (${m.ink} painted pixels)`);
      assert.ok(m.cover && m.cover.src.includes('/img/covers/' + h.cover) && m.cover.ok && m.cover.vis === 'visible' && m.cover.in,
        `${at}: the cover is not lit inside the hero: ${JSON.stringify(m.cover)}`);
      assert.deepEqual(m.start, { href: h.start, text: 'Begin reading' }, `${at}: start-reading link`);
      if (h.contents) assert.equal(await page.locator(`.rd-hero .rd-actions a[href="${h.contents}"]`).textContent(), 'Contents', `${at}: contents link`);
      assert.match(m.fName, /^"?Geist"?,/, `${at}: title font ${m.fName}`);
      assert.match(m.fTag, /^"?Geist Mono"?,/, `${at}: tag font ${m.fTag}`);
      assert.match(m.fNav, /^"?Geist"?,/, `${at}: nav font ${m.fNav}`);
      await page.locator('.rd-hero a.rd-start').click();
      await page.waitForTimeout(900);
      const landed = await page.evaluate(s => {
        const r = document.querySelector(s).getBoundingClientRect();
        return { top: r.top, bar: document.querySelector('.tp-bar').getBoundingClientRect().bottom };
      }, h.start);
      assert.ok(landed.top >= landed.bar - 2 && landed.top < landed.bar + 140, `${at}: Begin reading lands at ${landed.top}`);
      const f = await page.evaluate(([a, b]) => [a, b].map(s => { const e = document.querySelector(s); return e ? getComputedStyle(e).fontFamily : ''; }), [h.serif, h.label]);
      assert.match(f[0], /Iowan Old Style/, `${at}: book text is not the serif: ${f[0]}`);
      assert.match(f[1], /^"?Geist Mono"?,/, `${at}: reader label font ${f[1]}`);
      assert.deepEqual(errors, [], at);
      await page.close();
    }
  });

  await t.test('life/ and qubit-dialogues.html: the contents list is set in Geist', async () => {
    for (const url of ['/life/', '/qubit-dialogues.html']) {
    const { page } = await open(url, 1440);
    const f = await page.evaluate(() => ['.contents h2', '.contents a .t', '.contents a .n'].map(s => getComputedStyle(document.querySelector(s)).fontFamily));
    assert.match(f[0], /^"?Geist Mono"?,/);
    assert.match(f[1], /^"?Geist"?,/);
    assert.match(f[2], /^"?Geist Mono"?,/);
    await page.close();
    }
  });

  await t.test('heroes animate only while motion is allowed', async () => {
    for (const url of ['/life/', '/illustrated/', '/qubit-dialogues.html']) for (const rm of ['no-preference', 'reduce']) {
      const { page } = await open(url, 1440, 900, { reducedMotion: rm });
      const snap = () => page.evaluate(() => document.querySelector('.rd-hero canvas').toDataURL());
      const a = await snap(); await page.waitForTimeout(800); const b = await snap();
      if (rm === 'reduce') assert.equal(a, b, `${url}: moves under reduced motion`);
      else assert.notEqual(a, b, `${url}: the hero is not live`);
      await page.close();
    }
  });

  await t.test('life/: the end links share the text column and are centred', async () => {
    for (const w of [1440, 768, 390]) {
      const { page } = await open('/life/', w);
      const m = await page.evaluate(() => {
        const box = s => { const e = document.querySelector(s), b = e.getBoundingClientRect(), c = getComputedStyle(e);
          return [b.left + parseFloat(c.paddingLeft), b.right - parseFloat(c.paddingRight)]; };
        const lis = [...document.querySelectorAll('.editions li')].map(li => li.getBoundingClientRect());
        return { text: box('#book'), ed: box('.editions'),
          links: [Math.min(...lis.map(b => b.left)), Math.max(...lis.map(b => b.right))] };
      });
      near(m.ed[0], m.text[0], 1, `${w} editions left`);
      near(m.ed[1], m.text[1], 1, `${w} editions right`);
      near((m.links[0] + m.links[1]) / 2, (m.text[0] + m.text[1]) / 2, 2, `${w} links centred`);
      await page.close();
    }
  });

  await t.test('illustrated/: nothing reaches past the right edge, even where body overflow is ignored', async () => {
    for (const w of [721, 768, 900, 1024, 1440]) {
      const { page } = await open('/illustrated/', w);
      const m = await page.evaluate(() => {
        document.body.style.overflowX = 'visible';
        const d = document.documentElement;
        return { sw: d.scrollWidth, cw: d.clientWidth };
      });
      assert.equal(m.sw, m.cw, `${w}: scrollWidth ${m.sw} vs clientWidth ${m.cw}`);
      await page.close();
    }
  });

  await t.test('illustrated/: rail marks are real targets, clear of the frame, drawn as before', async () => {
    for (const [w, h] of [[1440, 900], [1024, 768], [768, 1024]]) {
      const { page } = await open('/illustrated/', w, h);
      const m = await page.evaluate(() => {
        const marks = [...document.querySelectorAll('.rail .mark')];
        const rail = document.querySelector('.rail').getBoundingClientRect();
        const frame = document.querySelector('.stage-inner').getBoundingClientRect();
        const bar = getComputedStyle(marks[0], '::before');
        return { n: marks.length, minH: Math.min(...marks.map(a => a.getBoundingClientRect().height)),
          railL: rail.left, railR: rail.right, frameR: frame.right, barH: bar.height, barW: bar.width,
          bottom: rail.bottom, vh: innerHeight };
      });
      assert.equal(m.n, 22);
      assert.ok(m.minH >= 24, `${w}: mark height ${m.minH}`);
      assert.equal(m.barH, '2px', `${w}: visible bar`);
      assert.equal(m.barW, '12px', `${w}: visible bar`);
      assert.ok(m.railR <= m.frameR - 4, `${w}: rail ${m.railL}-${m.railR} on the frame line ${m.frameR}`);
      assert.ok(m.bottom <= m.vh, `${w}: rail runs off the bottom`);
      await page.close();
    }
  });

  await t.test('qubit-dialogues.html: contents control, find-in-page, captions, equations', async () => {
    const { page, errors } = await open('/qubit-dialogues.html', 1440);
    const toggle = page.locator('#contents button.open-all');
    assert.equal((await toggle.textContent()).trim(), 'Open all');
    const openCount = () => page.evaluate(() => [...document.querySelectorAll('section.canto.acc')].filter(s => s.classList.contains('expanded')).length);
    assert.equal(await openCount(), 1, 'one canto open on load');
    assert.equal(await page.locator('.canto-wrap[hidden="until-found"]').count(), 21, 'closed cantos findable');

    await toggle.click();
    assert.equal(await openCount(), 22, 'open all');
    assert.equal((await toggle.textContent()).trim(), 'Close all');
    assert.equal(await page.locator('.canto-wrap[hidden]').count(), 0);
    await page.evaluate(() => document.getElementById('canto-10').scrollIntoView());
    await page.waitForTimeout(500);
    assert.equal(await openCount(), 22, 'scrolling does not close cantos while all are open');

    // every display equation fits at 1440 once laid out
    const eq = await page.evaluate(() => [...document.querySelectorAll('.eqblock')]
      .filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.closest('section').id));
    assert.deepEqual(eq, [], 'equations scroll sideways at 1440');

    // captions: numbered in order, full sentences
    const caps = await page.evaluate(() => [...document.querySelectorAll('.scene .hint')].map(h => {
      const b = h.querySelector('b');
      return [b ? b.textContent : '', h.textContent.slice(b ? b.textContent.length : 0).trim()];
    }));
    assert.equal(caps.length, 9);
    caps.forEach(([num, c], i) => {
      assert.equal(num, `Fig. ${i + 1}`);
      assert.match(c, /^[A-Z].*\.$/, c);
    });

    await page.evaluate(() => scrollTo(0, 0));
    await toggle.click();
    assert.equal(await openCount(), 0, 'close all');
    assert.equal((await toggle.textContent()).trim(), 'Open all');
    await page.waitForTimeout(300);
    assert.equal(await page.locator('.canto-wrap[hidden="until-found"]').count(), 22);

    // find-in-page: a text fragment into a closed canto opens it
    const phrase = await page.evaluate(() => {
      const b = CANTOS[9].blocks.find(b => b.t === 'dlg');
      return b.text[0].split(/\s+/).slice(0, 6).join(' ').replace(/[^\w\s']/g, '').trim();
    });
    await page.goto(base + '/qubit-dialogues.html#:~:text=' + encodeURIComponent(phrase), { waitUntil: 'load' });
    await page.waitForTimeout(800);
    assert.ok(await page.evaluate(() => document.getElementById('canto-10').classList.contains('expanded')),
      'find opens canto 10: ' + phrase);
    assert.deepEqual(errors, []);
    await page.close();
  });

  await t.test('qubit-dialogues.html at 390: the page never scrolls sideways', async () => {
    const { page } = await open('/qubit-dialogues.html', 390, 844);
    await page.locator('#contents button.open-all').click();
    await page.waitForTimeout(500);
    const m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
    assert.ok(m.sw <= m.cw, `${m.sw} vs ${m.cw}`);
    await page.close();
  });
});
