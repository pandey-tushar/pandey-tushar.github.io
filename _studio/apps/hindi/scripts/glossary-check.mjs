#!/usr/bin/env node
/* Glossary consistency and script hygiene for the Hindi edition.

   Terminology drift across 25,000 words is invisible to a reader and obvious
   to a script. This is that script. It fails the build on:

     1. a rejected rendering of a glossary term appearing anywhere
     2. a string that is not in Unicode NFC
     3. a single token mixing Devanagari and Latin
     4. a Latin token in prose that is not a declared name, venue or symbol
     5. an em-dash or en-dash, in any script
     6. Devanagari digits in content (canto numbers are the renderer's job)

   KaTeX chunks are excluded from every text scan; they are carried verbatim
   from en.json and are checked byte-for-byte by parity-check.mjs instead.
   So are the {n} {total} {title} placeholders in front matter labels and in
   scene readout strings: the renderer substitutes them, they are never read. */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const at = (p) => fileURLToPath(new URL(p, import.meta.url));
const read = (p) => JSON.parse(readFileSync(at(p), 'utf8'));

const glossary = read('../../../content/glossary-hi.json');
const book = read('../../../content/hi.json');
const front = read('../../../content/front.hi.json');

const DEVA = /[ऀ-ॿ꣠-ꣿ]/;
const LATIN = /[A-Za-z]/;
const DEVA_DIGIT = /[०-९]/;

/** Strip the KaTeX chunks, then all markup, leaving readable text. */
function prose(html) {
  let s = String(html);
  /* balanced-span removal of every eqi / eqblock */
  for (;;) {
    const m = /<span class="(?:eqi|eqblock)">/.exec(s);
    if (!m) break;
    let depth = 0, end = s.length;
    const tag = /<span\b[^>]*>|<\/span>/g;
    tag.lastIndex = m.index;
    let t;
    while ((t = tag.exec(s))) {
      depth += t[0].startsWith('</') ? -1 : 1;
      if (depth === 0) { end = t.index + t[0].length; break; }
    }
    s = s.slice(0, m.index) + ' ' + s.slice(end);
  }
  return s.replace(/<[^>]*>/g, ' ').replace(/&[a-z]+;/g, ' ').replace(/\{\w+\}/g, ' ');
}

/* Machine values, not prose: block discriminators, speaker ids, scene ids, the
   CSS class that colours a prediction tag, and the ten-character numeral table
   that lets the renderer print canto numbers in Devanagari. */
const NOT_PROSE = new Set(['t', 'who', 'kind', 'tagc', 'n', 'conf', 'digits']);

/** Every authored string, with its path. `raw` keeps markup for NFC checks. */
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

const SPLIT = /[\s।॥.,;:!?()[\]{}"'“”‘’·…|/<>=+*%&@#$~^\\→∝↑↓⟩∣-]+/;
const tokensOf = (text) => text.split(SPLIT).filter(Boolean);

const strings = [
  ...collect(book, 'hi.json', []),
  ...collect(front, 'front.hi.json', []),
].map((s) => {
  const text = prose(s.raw);
  return { ...s, text, tokens: tokensOf(text) };
});

/** Word-level, not substring. डिकपलिंग must not read as कपलिंग, फ़रवरी must
    not read as रव, and the postposition की must not read as the noun key. */
function hasPhrase(s, phrase) {
  const want = tokensOf(phrase);
  if (want.length === 1) return s.tokens.includes(want[0]);
  for (let i = 0; i + want.length <= s.tokens.length; i++) {
    if (want.every((w, k) => s.tokens[i + k] === w)) return true;
  }
  return false;
}

const fails = [];
const warns = [];
const fail = (s) => fails.push(s);

/* ---------- 2. NFC ---------- */
let nfcBad = 0;
for (const s of strings) {
  if (s.raw.normalize('NFC') !== s.raw) { nfcBad++; fail('NFC: ' + s.path + ' is not normalised'); }
}

/* ---------- 5. dashes ---------- */
for (const s of strings) {
  if (/[—–]/.test(s.raw)) fail('dash: ' + s.path + ' contains an em-dash or en-dash');
}

/* ---------- 6. Devanagari digits in content ---------- */
for (const s of strings) {
  if (DEVA_DIGIT.test(s.raw)) fail('numerals: ' + s.path + ' contains Devanagari digits');
}

/* ---------- 1. rejected renderings ---------- */
let avoidChecked = 0;
for (const term of glossary.terms) {
  for (const bad of term.avoid ?? []) {
    avoidChecked++;
    for (const s of strings) {
      if (hasPhrase(s, bad)) {
        fail('glossary: "' + bad + '" is a rejected rendering of "' + term.en +
          '" (approved: ' + term.hi + ') at ' + s.path);
      }
    }
  }
}

/* ---------- 3. mixed-script tokens ---------- */
for (const s of strings) {
  for (const tok of s.tokens) {
    if (DEVA.test(tok) && LATIN.test(tok)) {
      fail('mixed script: "' + tok + '" at ' + s.path);
    }
  }
}

/* ---------- 4. stray Latin ---------- */
const allowed = new Set();
for (const group of Object.values(glossary.latinAllowed)) {
  if (!Array.isArray(group)) continue;
  for (const entry of group) for (const word of entry.split(/[\s-]+/)) allowed.add(word.toLowerCase());
}
/* terms whose approved rendering is itself Latin */
for (const term of glossary.terms) {
  if (term.latinToken) allowed.add(term.latinToken.toLowerCase());
  if (term.policy === 'latin') for (const w of term.hi.split(/[\s/-]+/)) allowed.add(w.toLowerCase());
}
/* CSS hooks and markup fragments that survive tag stripping in no case, plus
   the mathematical symbols KaTeX leaves behind */
for (const w of ['s', 'e', 'i', 'n', 'd', 'p', 'x', 'z', 'a', 'b', 'k']) allowed.add(w);

const strayCounts = new Map();
for (const s of strings) {
  for (const tok of s.tokens) {
    if (!LATIN.test(tok)) continue;
    const bare = tok.replace(/[^A-Za-z0-9-]/g, '');
    if (!bare || !LATIN.test(bare)) continue;
    if (allowed.has(bare.toLowerCase())) continue;
    if (allowed.has(bare.replace(/\d+$/, '').toLowerCase())) continue;
    const key = bare + '  @ ' + s.path;
    strayCounts.set(key, (strayCounts.get(key) ?? 0) + 1);
  }
}
for (const key of strayCounts.keys()) fail('stray Latin: ' + key);

/* ---------- attestation report ---------- */
const allText = strings.map((s) => s.text).join('\n');
let attested = 0;
const missing = [];
for (const term of glossary.terms) {
  const forms = [term.hi, ...(term.forms ?? [])].flatMap((f) => f.split(' / '));
  if (forms.some((f) => allText.includes(f))) attested++;
  else missing.push(term.en);
}

/* reserved senses cannot be judged by machine; they are reported for a human */
for (const r of glossary.reservedSense ?? []) {
  let n = 0;
  for (const s of strings) for (const tok of s.tokens) if (tok === r.word) n++;
  warns.push('reserved sense: "' + r.word + '" occurs ' + n + ' times as a whole word, ' +
    'every one of which must mean ' + r.reservedFor.split('(')[0].trim());
}

/* ---------- output ---------- */
const cantos = book.map((c) => c.n).join(', ');
console.log('glossary-check');
console.log('  edition        : content/hi.json (cantos ' + cantos + ') + content/front.hi.json');
console.log('  strings scanned: ' + strings.length);
console.log('  glossary terms : ' + glossary.terms.length + ', rejected renderings checked: ' + avoidChecked);
console.log('  terms attested : ' + attested + ' / ' + glossary.terms.length +
  ' (' + missing.length + ' belong to cantos not yet written)');
console.log('  NFC            : ' + (nfcBad === 0 ? 'all ' + strings.length + ' strings normalised' : nfcBad + ' NOT normalised'));
for (const w of warns) console.log('  ' + w);

if (fails.length) {
  console.error('\nFAIL (' + fails.length + ')');
  for (const f of fails) console.error('  ' + f);
  process.exit(1);
}
console.log('\nok: no rejected renderings, no mixed-script tokens, no stray Latin, no dashes, NFC clean');
