#!/usr/bin/env node
/* Structural parity and script hygiene for आधा उजाला.

   This edition is composed in Hindi rather than translated, so the prose is
   expected to differ from content/unpolarized.json in every sentence. Its
   skeleton is not. Two jobs, one script, because there is no glossary to
   enforce here: An Unpolarized Life carries almost no technical vocabulary,
   so content/glossary-hi.json has nothing to say about it and is not read.

   PARITY, against content/unpolarized.json:
     same chapter set and count
     same block count, same block types in the same order
     same speaker on every dialogue turn, same paragraph count per turn
     same movement and epigraph presence
     every number identical, as a multiset, per block

   HYGIENE, over both the book and its front matter:
     every string in Unicode NFC
     no token mixing Devanagari and Latin
     no Latin word in prose
     no em-dash or en-dash, in any script
     no Devanagari digit in content (the canto numbering is the renderer's
     job, via the `digits` table in front matter, which is exempt)

   content/unpolarized.json is read only. */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const at = (p) => fileURLToPath(new URL(p, import.meta.url));
const read = (p) => JSON.parse(readFileSync(at(p), 'utf8'));

const en = read('../../../content/unpolarized.json');
const hi = read('../../../content/hi-unpolarized.json');
const front = read('../../../content/front.hi-unpolarized.json');

const problems = [];
const say = (s) => problems.push(s);

/* ---------- parity ---------- */

/** All authored strings on a block, concatenated. */
const markup = (b) =>
  [b.html, b.counter, b.claim, b.text, b.controls, b.hint, b.head]
    .flat()
    .filter((v) => typeof v === 'string')
    .join('\n');

const prose = (s) => s.replace(/<[^>]*>/g, ' ');

const numbers = (s) =>
  (prose(s).match(/\d[\d,.]*\d|\d/g) ?? []).map((n) => n.replace(/[.,]$/, '')).sort();

const byN = new Map(en.map((c) => [c.n, c]));
let blocksChecked = 0;
let numChecked = 0;

if (hi.length !== en.length) {
  say('chapter count: en ' + en.length + ', hi ' + hi.length);
}

for (const h of hi) {
  const e = byN.get(h.n);
  const where = 'chapter ' + h.n;
  if (!e) { say(where + ': no such chapter in unpolarized.json'); continue; }

  if (h.blocks.length !== e.blocks.length) {
    say(where + ' block count: en ' + e.blocks.length + ', hi ' + h.blocks.length);
    continue;
  }
  const et = e.blocks.map((b) => b.t).join(',');
  const ht = h.blocks.map((b) => b.t).join(',');
  if (et !== ht) say(where + ' block types differ\n    en: ' + et + '\n    hi: ' + ht);

  if (!!e.movement !== !!h.movement) say(where + ': movement present in only one edition');
  if (!!e.epigraph !== !!h.epigraph) say(where + ': epigraph present in only one edition');

  for (let i = 0; i < e.blocks.length; i++) {
    const a = e.blocks[i], b = h.blocks[i];
    const bat = where + ' block[' + i + '] (' + a.t + ')';
    blocksChecked++;

    if (a.t === 'dlg') {
      if (a.who !== b.who) say(bat + ' speaker: en ' + a.who + ', hi ' + b.who);
      if (a.text.length !== b.text.length) {
        say(bat + ' paragraph count: en ' + a.text.length + ', hi ' + b.text.length);
      }
    }

    const na = numbers(markup(a)), nb = numbers(markup(b));
    numChecked += na.length;
    if (na.join(' ') !== nb.join(' ')) {
      say(bat + ' numbers differ\n    en: [' + na.join(' ') + ']\n    hi: [' + nb.join(' ') + ']');
    }
  }
}

/* ---------- hygiene ---------- */

const DEVA = /[ऀ-ॿ꣠-ꣿ]/;
const LATIN = /[A-Za-z]/;
const DEVA_DIGIT = /[०-९]/;

/* Machine values, not prose: the block discriminator, the speaker id, the
   chapter number, and the ten-character numeral table that lets the renderer
   print chapter numbers in Devanagari. */
const NOT_PROSE = new Set(['t', 'who', 'n', 'digits']);

/** Every authored string, with its path. */
function collect(node, path, out) {
  if (typeof node === 'string') { out.push({ path, raw: node }); return out; }
  if (Array.isArray(node)) { node.forEach((v, i) => collect(v, path + '[' + i + ']', out)); return out; }
  if (node && typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      if (NOT_PROSE.has(k)) continue;
      collect(v, path + '.' + k, out);
    }
  }
  return out;
}

/* `{n}` `{total}` `{title}` are substituted by the renderer and never read. */
const readable = (s) => prose(s).replace(/&[a-z]+;/g, ' ').replace(/\{\w+\}/g, ' ');

const SPLIT = /[\s।॥.,;:!?()[\]{}"'“”‘’·…|/<>=+*%&@#$~^\\▾©-]+/;

const strings = [
  ...collect(hi, 'hi-unpolarized.json', []),
  ...collect(front, 'front.hi-unpolarized.json', []),
].map((s) => {
  const text = readable(s.raw);
  return { ...s, text, tokens: text.split(SPLIT).filter(Boolean) };
});

let nfcBad = 0;
for (const s of strings) {
  if (s.raw.normalize('NFC') !== s.raw) { nfcBad++; say('NFC: ' + s.path + ' is not normalised'); }
  if (/[—–]/.test(s.raw)) say('dash: ' + s.path + ' contains an em-dash or en-dash');
  if (DEVA_DIGIT.test(s.raw)) say('numerals: ' + s.path + ' contains Devanagari digits');
  for (const tok of s.tokens) {
    if (DEVA.test(tok) && LATIN.test(tok)) say('mixed script: "' + tok + '" at ' + s.path);
    if (LATIN.test(tok)) say('stray Latin: "' + tok + '" at ' + s.path);
  }
}

/* ---------- report ---------- */
console.log('parity + hygiene  hi-unpolarized.json against unpolarized.json');
console.log('  chapters compared: ' + hi.map((c) => c.n).join(', ') + '  (of ' + en.length + ' in English)');
console.log('  blocks compared  : ' + blocksChecked);
console.log('  per-chapter blocks: en ' + en.map((c) => c.blocks.length).join(',') +
  '\n                    : hi ' + hi.map((c) => c.blocks.length).join(','));
console.log('  numbers compared : ' + numChecked);
console.log('  strings scanned  : ' + strings.length);
console.log('  NFC              : ' + (nfcBad === 0 ? 'all ' + strings.length + ' normalised' : nfcBad + ' NOT normalised'));

if (problems.length) {
  console.error('\nFAILED (' + problems.length + ')');
  for (const p of problems) console.error('  ' + p);
  process.exit(1);
}
console.log('\nok: same skeleton, same numbers, NFC clean, no mixed script, no stray Latin, no dashes');
