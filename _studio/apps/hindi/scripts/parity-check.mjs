#!/usr/bin/env node
/* Structural parity of content/hi.json against content/en.json.

   The Hindi edition is re-authored, not translated, so the prose is expected
   to differ. Its skeleton is not. This checks, for every canto present in
   hi.json:

     same block count, same block types in the same order
     same speaker on every dialogue turn, same paragraph count per turn
     same scene kinds, same prediction class and confidence
     same movement and epigraph presence
     every KaTeX chunk byte-identical to en.json
     every number identical, as a multiset
     every citation name present, in Latin or in its declared Devanagari form

   content/en.json is read only. */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const at = (p) => fileURLToPath(new URL(p, import.meta.url));
const read = (p) => JSON.parse(readFileSync(at(p), 'utf8'));

const en = read('../../../content/en.json');
const hi = read('../../../content/hi.json');
const glossary = read('../../../content/glossary-hi.json');

/** Names written in Devanagari when they appear in prose rather than a citation.
    Declared here so the check can accept either form and so the list is visible. */
const NAMES_IN_PROSE = {
  Minev: 'मिनेव', Braginsky: 'ब्रगिंस्की', Bohr: 'बोर', Bell: 'बेल',
  Einstein: 'आइंस्टाइन', Yale: 'येल', Raussendorf: 'राउसेनडोर्फ', Briegel: 'ब्रीगल',
  Ramsey: 'रैमज़े', Bloch: 'ब्लॉक', Zlatko: 'ज़्लाट्को',
};

const problems = [];
const say = (s) => problems.push(s);

/* ---------- KaTeX chunk extraction ---------- */
function eqChunks(html) {
  const out = [];
  const re = /<span class="(?:eqi|eqblock)">/g;
  let m;
  while ((m = re.exec(html))) {
    let depth = 0, end = html.length;
    const tag = /<span\b[^>]*>|<\/span>/g;
    tag.lastIndex = m.index;
    let t;
    while ((t = tag.exec(html))) {
      depth += t[0].startsWith('</') ? -1 : 1;
      if (depth === 0) { end = t.index + t[0].length; break; }
    }
    out.push(html.slice(m.index, end));
    re.lastIndex = end;
  }
  return out;
}

/** All authored markup on a block, concatenated. */
function markup(b) {
  return [b.html, b.counter, b.claim, b.text, b.controls, b.hint, b.head]
    .flat()
    .filter((v) => typeof v === 'string')
    .join('\n');
}

/** Readable text: KaTeX removed, tags stripped. */
function prose(s) {
  let out = s;
  for (const chunk of eqChunks(out)) out = out.split(chunk).join(' ');
  return out.replace(/<[^>]*>/g, ' ');
}

const numbers = (s) => (prose(s).match(/\d[\d,.]*\d|\d/g) ?? [])
  .map((n) => n.replace(/[.,]$/, ''))
  .sort();

/* citation tokens: capitalised proper nouns the glossary declares Latin */
const CITE = new Set();
for (const key of ['people', 'organisations', 'machines', 'venues']) {
  for (const entry of glossary.latinAllowed[key]) {
    for (const w of entry.split(/\s+/)) if (/^[A-Z][A-Za-z-]{2,}$/.test(w)) CITE.add(w);
  }
}

/** Citation contexts only: a whole note block, or a parenthesised span.
    Scanning free prose instead would flag every sentence that happens to open
    with "Quantum" or "Science". */
function citations(block, s) {
  const text = prose(s);
  const scope = block.t === 'note' ? [text] : (text.match(/\([^)]*\)/g) ?? []);
  const found = new Set();
  for (const span of scope) {
    for (const w of span.split(/[^A-Za-z-]+/)) if (CITE.has(w)) found.add(w);
  }
  return found;
}

/* ---------- compare ---------- */
const byN = new Map(en.map((c) => [c.n, c]));
let blocksChecked = 0, eqChecked = 0, numChecked = 0, citeChecked = 0;

for (const h of hi) {
  const e = byN.get(h.n);
  const at_ = 'canto ' + h.n;
  if (!e) { say(at_ + ': no such canto in en.json'); continue; }

  if (h.blocks.length !== e.blocks.length) {
    say(at_ + ' block count: en ' + e.blocks.length + ', hi ' + h.blocks.length);
    continue;
  }
  const et = e.blocks.map((b) => b.t).join(',');
  const ht = h.blocks.map((b) => b.t).join(',');
  if (et !== ht) say(at_ + ' block types differ\n    en: ' + et + '\n    hi: ' + ht);

  if (!!e.movement !== !!h.movement) say(at_ + ': movement present in only one edition');
  if (!!e.epigraph !== !!h.epigraph) say(at_ + ': epigraph present in only one edition');

  for (let i = 0; i < e.blocks.length; i++) {
    const a = e.blocks[i], b = h.blocks[i];
    const bat = at_ + ' block[' + i + '] (' + a.t + ')';
    blocksChecked++;

    if (a.t === 'dlg') {
      if (a.who !== b.who) say(bat + ' speaker: en ' + a.who + ', hi ' + b.who);
      if (a.text.length !== b.text.length) {
        say(bat + ' paragraph count: en ' + a.text.length + ', hi ' + b.text.length);
      }
    }
    if (a.t === 'scene' && a.kind !== b.kind) say(bat + ' scene kind: en ' + a.kind + ', hi ' + b.kind);
    if (a.t === 'pred') {
      if (a.tagc !== b.tagc) say(bat + ' tag class: en ' + a.tagc + ', hi ' + b.tagc);
      if (a.conf !== b.conf) say(bat + ' confidence: en ' + a.conf + ', hi ' + b.conf);
    }
    if (a.t === 'science' && (a.head === undefined) !== (b.head === undefined)) {
      say(bat + ': science head present in only one edition');
    }

    const ma = markup(a), mb = markup(b);

    const ea = eqChunks(ma), eb = eqChunks(mb);
    if (ea.length !== eb.length) {
      say(bat + ' equation count: en ' + ea.length + ', hi ' + eb.length);
    } else {
      for (let k = 0; k < ea.length; k++) {
        eqChecked++;
        if (ea[k] !== eb[k]) say(bat + ' equation[' + k + '] is not byte-identical to en.json');
      }
    }

    const na = numbers(ma), nb = numbers(mb);
    numChecked += na.length;
    if (na.join(' ') !== nb.join(' ')) {
      say(bat + ' numbers differ\n    en: [' + na.join(' ') + ']\n    hi: [' + nb.join(' ') + ']');
    }

    const ca = citations(a, ma), cb = citations(b, mb);
    for (const name of ca) {
      citeChecked++;
      if (cb.has(name)) continue;
      const deva = NAMES_IN_PROSE[name];
      if (deva && prose(mb).includes(deva)) continue;
      say(bat + ' citation "' + name + '" is missing from the Hindi block');
    }
  }
}

console.log('parity-check  hi.json against en.json');
console.log('  cantos compared  : ' + hi.map((c) => c.n).join(', ') + '  (of ' + en.length + ' in en.json)');
console.log('  blocks compared  : ' + blocksChecked);
console.log('  per-canto blocks : en ' + hi.map((c) => byN.get(c.n)?.blocks.length ?? '?').join(',') +
  '  |  hi ' + hi.map((c) => c.blocks.length).join(','));
console.log('  KaTeX chunks     : ' + eqChecked + ' compared byte-for-byte');
console.log('  numbers          : ' + numChecked + ' compared');
console.log('  citation names   : ' + citeChecked + ' compared');

if (problems.length) {
  console.error('\nPARITY FAILED (' + problems.length + ')');
  for (const p of problems) console.error('  ' + p);
  process.exit(1);
}
console.log('\nparity ok: same skeleton, same equations, same numbers, same citations');
