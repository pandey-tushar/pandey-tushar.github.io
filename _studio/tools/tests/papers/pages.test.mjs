// The static HTML, CSS and status text of the three paper companion pages (papers/*.html): the right rail with
// "In plain words" and "On this page", consistent BibTeX, and the text fixes of the November 2026 review.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = p => readFileSync(new URL(`../../../../${p}`, import.meta.url), 'utf8');
const PAGES = { 'bb-erasure-baselines': '2603.19062', 'lifted-surgery': '2610.05307', 'adaptive-graph-of-thoughts': '2502.05078' };
const css = read('papers/paper.css');

for (const [slug, id] of Object.entries(PAGES)) {
  const html = read(`papers/${slug}.html`);
  test(`${slug}: a rail with In plain words and a contents list of every essay heading`, () => {
    assert.match(html, /<div class="tp-wrap pc-cols">/);
    assert.match(html, /<\/header>\s*<aside class="pc-rail"/, 'the rail follows the header, so it sits under it on narrow screens');
    const rail = html.match(/<aside class="pc-rail"[\s\S]*?<\/aside>/)[0];
    assert.match(rail, /In plain words<\/h2>\s*<p>[^<]{80,}/);
    const toc = rail.match(/<nav class="pc-toc" aria-label="On this page">[\s\S]*?<\/nav>/);
    assert.ok(toc, 'no On this page nav');
    const hrefs = [...toc[0].matchAll(/href="#([\w-]+)"/g)].map(m => m[1]);
    const essayH2 = [...html.matchAll(/<article class="pc-essay">([\s\S]*?)<\/article>/g)].flatMap(a => [...a[1].matchAll(/<h2([^>]*)>/g)].map(m => m[1]));
    assert.ok(essayH2.length >= 4);
    for (const attrs of essayH2) {
      const m = attrs.match(/id="([\w-]+)"/);
      assert.ok(m, `an essay h2 has no id: <h2${attrs}>`);
      assert.ok(hrefs.includes(m[1]), `#${m[1]} is not in the contents list`);
    }
    for (const h of hrefs) assert.ok(html.includes(`id="${h}"`), `#${h} does not resolve`);
    assert.match(rail, new RegExp(`href="https://arxiv.org/abs/${id.replace('.', '\\.')}"`));
  });
  test(`${slug}: BibTeX author is Surname, Given and the entry has its arXiv url`, () => {
    const bib = html.match(/<pre class="pc-bib" id="bib">([\s\S]*?)<\/pre>/)[1];
    assert.match(bib, /author\s+= \{Pandey, Tushar(\}| and)/);
    assert.match(bib, new RegExp(`url\\s+= \\{https://arxiv\\.org/abs/${id.replace('.', '\\.')}\\}`));
  });
}

test('paper.css: the figure status rule is scoped to figures; head, citation and figures share one width', () => {
  assert.doesNotMatch(css, /^\.pc-status\s*\{[^}]*border/m, 'an unscoped .pc-status rule draws a rule above header meta lines');
  assert.match(css, /^\.pc-fig \.pc-status\s*\{[^}]*border-top/m);
  assert.doesNotMatch(css, /^\.pc-head\s*\{[^}]*max-width/m);
  assert.doesNotMatch(css, /^\.pc-cite\s*\{[^}]*max-width/m);
  assert.match(css, /\.pc-cols > \.pc-rail\s*\{[^}]*position: sticky/);
});

test('bb-erasure-baselines: status text uses the symbols of the slider labels; fit-window sentence follows Sec. 2.5', () => {
  const js = read('papers/js/bb-erasure-baselines.js');
  const words = js.match(/function collapseWords[\s\S]*?\n}/)[0];
  assert.doesNotMatch(words.replace(/state\.nu\b|&nu;/g, ''), /p-star-infinity|\bnu\b/);
  assert.match(words, /p\*<sub>&infin;<\/sub> = \$\{state\.ps\.toFixed\(3\)\}, &nu; = \$\{state\.nu\.toFixed\(2\)\}/);
  assert.match(js, /\$\('fss-status'\)\.innerHTML = text/);
  const html = read('papers/bb-erasure-baselines.html');
  assert.doesNotMatch(html, /suggests &lsim;/);
  assert.match(html, /windows of 0\.04 and 0\.08 shifts p\*<sub>&infin;<\/sub> by &lsim;&nbsp;0\.004, consistent with its stated systematic uncertainty of &lsim;&nbsp;0\.005\./);
});

test('lifted-surgery: the lesson link is its own sentence; the status line writes groups with subscripts', () => {
  const html = read('papers/lifted-surgery.html');
  assert.doesNotMatch(html, /\(<a [^>]*lattice-surgery\.html/);
  assert.match(html, /<a class="tp-link" href="\/qec-in-practice\/lattice-surgery\.html">[^<]+<\/a>[^<]*\.<\/p>/);
  const js = read('papers/js/lifted-surgery.js');
  assert.match(js, /\$\('ls-status'\)\.innerHTML = text/);
  assert.match(js.match(/function words[\s\S]*?\n}/)[0], /parseGroup\(c\.group\)\.html/);
  assert.match(js, /familyHTML\(state\.family\)/);
});

test('adaptive-graph-of-thoughts: the figure opens on gpt-4o-mini and the plot fills its plate', () => {
  const js = read('papers/js/adaptive-graph-of-thoughts.js');
  assert.match(js, /const state = \{ dataset: 'GPQA_S', model: 'gpt-4o-mini'/);
  assert.doesNotMatch(read('papers/adaptive-graph-of-thoughts.html'), /\.agot-plot \{ max-width/);
});
