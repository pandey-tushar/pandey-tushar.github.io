/* Parity gate: the built page against the page that is live right now.

   Anything a visitor or a crawler can already reach must survive the rebuild.
   That is every heading, every link target, every meta name or property, every
   script source, and the files at the deploy root that the live page points at.
   Items the rebuild adds are reported but never fail; items it loses do.

   The live folder is read only here. This script never writes to it.
   Usage: node scripts/parity.mjs [--live <path>] [--dist <path>] */

import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const arg = (flag, fallback) => {
  const i = process.argv.indexOf(flag);
  return i > -1 && process.argv[i + 1] ? resolve(process.argv[i + 1]) : fallback;
};
const LIVE = arg('--live', process.env.SITE_LIVE
  ? resolve(process.env.SITE_LIVE)
  : 'C:/Users/thetu/Downloads/pandey-tushar.github.io/index.html');
const MINE = arg('--dist', fileURLToPath(new URL('../dist/index.html', import.meta.url)));

for (const p of [LIVE, MINE]) {
  if (!existsSync(p)) { console.error('parity: missing ' + p); process.exit(1); }
}
const live = readFileSync(LIVE, 'utf8');
const mine = readFileSync(MINE, 'utf8');

/* ---- the smallest html reader that answers these four questions ---- */
const ENT = {
  amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ',
  rsquo: '\u2019', lsquo: '\u2018', rdquo: '\u201d', ldquo: '\u201c', hellip: '\u2026',
  middot: '\u00b7', times: '\u00d7', deg: '\u00b0', copy: '\u00a9',
};
const decode = (s) => s
  .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(+d))
  .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
  .replace(/&([a-z]+);/gi, (m, n) => ENT[n.toLowerCase()] ?? m);
const text = (html) => decode(html.replace(/<[^>]*>/g, '')).replace(/\s+/g, ' ').trim();
const attr = (tag, name) => {
  const m = new RegExp(name + '\\s*=\\s*"([^"]*)"', 'i').exec(tag) ||
    new RegExp(name + "\\s*=\\s*'([^']*)'", 'i').exec(tag);
  return m ? decode(m[1]) : null;
};

const headings = (html) => [...html.matchAll(/<(h[1-6])\b[^>]*>([\s\S]*?)<\/\1>/gi)]
  .map((m) => m[1].toLowerCase() + ': ' + text(m[2])).filter((h) => h.split(': ')[1]);

const titles = (html) => [...html.matchAll(/<title>([\s\S]*?)<\/title>/gi)].map((m) => 'title: ' + text(m[1]));

const links = (html) => [...html.matchAll(/<a\b[^>]*>/gi)]
  .map((m) => attr(m[0], 'href')).filter(Boolean);

const sheets = (html) => [...html.matchAll(/<link\b[^>]*>/gi)]
  .map((m) => attr(m[0], 'href')).filter(Boolean);

const scripts = (html) => [...html.matchAll(/<script\b[^>]*\ssrc\s*=\s*["'][^"']*["'][^>]*>/gi)]
  .map((m) => attr(m[0], 'src')).filter(Boolean);

const metas = (html) => [...html.matchAll(/<meta\b[^>]*>/gi)].map((m) => {
  const key = attr(m[0], 'name') ?? attr(m[0], 'property') ?? attr(m[0], 'http-equiv') ??
    (attr(m[0], 'charset') !== null ? 'charset' : null);
  return key ? { key, content: attr(m[0], 'content') ?? attr(m[0], 'charset') ?? '' } : null;
}).filter(Boolean);

/* Things the live page carries that the rebuild deliberately drops, each with
   the reason. Anything not on this list and not in the build is a regression. */
const REPLACED = new Map([
  ['https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js',
    'three.js is now a bundled chunk imported after first paint (assets/scene-*.js)'],
  ['https://www.googletagmanager.com/gtag/js?id=G-DVPGC1C44Z',
    'gtag.js is 470KB, so the same tag is appended on load and idle instead; the ' +
    'dataLayer queue and the config call are unchanged, and the id check below proves it'],
]);

/* Receipts that must survive whatever the markup does: the analytics property,
   the canonical host, and the pages people already have links to. */
const RECEIPTS = [
  ['GA4 measurement id', /G-DVPGC1C44Z/],
  ['GA4 config call', /gtag\(\s*['"]config['"]\s*,\s*['"]G-DVPGC1C44Z['"]/],
  ['canonical url', /rel="canonical"[^>]*https:\/\/pandey-tushar\.com\//],
  ['og image', /og:image[^>]*og-home\.png/],
  ['cv link', /href="cv\.html"/],
  ['book link', /href="qubit-dialogues\.html"/],
];

/* ---- compare ---- */
let failed = 0;
const report = (label, liveList, mineList) => {
  const mineSet = new Set(mineList);
  const gone = [...new Set(liveList)].filter((x) => !mineSet.has(x));
  const missing = gone.filter((x) => !REPLACED.has(x));
  const replaced = gone.filter((x) => REPLACED.has(x));
  const added = [...new Set(mineList)].filter((x) => !new Set(liveList).has(x));
  const flag = missing.length ? 'MISSING ' + missing.length : 'ok';
  console.log(
    label.padEnd(12) + 'live ' + String(liveList.length).padEnd(4) +
    'mine ' + String(mineList.length).padEnd(4) + flag,
  );
  for (const m of missing) console.log('  lost     ' + m);
  for (const r of replaced) console.log('  replaced ' + r + '\n             ' + REPLACED.get(r));
  for (const a of added) console.log('  added    ' + a);
  failed += missing.length;
};

console.log('parity');
console.log('  live  ' + LIVE);
console.log('  mine  ' + MINE);
console.log('');

report('headings', [...titles(live), ...headings(live)], [...titles(mine), ...headings(mine)]);
report('links', links(live), links(mine));
report('head links', sheets(live), sheets(mine));
report('scripts', scripts(live), scripts(mine));

/* meta compares on the name or property, then warns when the value moved */
const lm = metas(live), mm = metas(mine);
report('meta', lm.map((m) => m.key), mm.map((m) => m.key));
for (const m of lm) {
  const match = mm.find((x) => x.key === m.key);
  if (match && match.content !== m.content) {
    console.log('  value  ' + m.key + '\n           live ' + m.content + '\n           mine ' + match.content);
  }
}

/* ---- the files the live page links to at the deploy root ---- */
const liveRoot = dirname(LIVE);
const distRoot = dirname(MINE);
const rootFiles = [...new Set([...links(live), ...sheets(live)])]
  .filter((h) => !/^(#|https?:|mailto:|data:|\/\/)/.test(h))
  .concat(['og-home.png', 'og-book.png', 'Tushar_Pandey_Resume_AI.pdf', 'Tushar_Pandey_Resume_Quantum.pdf']);
console.log('');
console.log('deploy root files the live page depends on');
for (const f of [...new Set(rootFiles)]) {
  const inDist = existsSync(join(distRoot, f));
  const atLive = existsSync(join(liveRoot, f));
  const where = inDist ? 'built' : atLive ? 'carried by the deploy root' : 'NOT FOUND';
  if (!inDist && !atLive) failed++;
  console.log('  ' + f.padEnd(34) + where);
}

console.log('');
console.log('receipts that must not move');
for (const [label, re] of RECEIPTS) {
  const ok = re.test(mine);
  if (!ok) failed++;
  console.log('  ' + label.padEnd(34) + (ok ? 'present' : 'MISSING'));
}

console.log('');
if (failed) { console.error('PARITY FAILED: ' + failed + ' item(s) lost'); process.exit(1); }
console.log('PARITY OK: nothing the live page carries is missing from the build');
