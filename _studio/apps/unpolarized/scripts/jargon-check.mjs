/* Jargon gate for An Unpolarized Life.

   The book's premise is that it works without technical vocabulary. A reader
   who does not know what a qubit is should never feel excluded, so the terms
   below are capped per chapter and forbidden outright inside reflections,
   which are the lines a reader is most likely to carry away and quote.

   The watchlist is informational. Those words are legitimate in this book
   (the Oracle refuses several physics-flavoured comforts by name, and cannot
   do that without naming them), but a reviewer running the framing audit
   wants to know exactly where they appear. Watchlist hits never fail. */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const BOOK = fileURLToPath(new URL('../../../content/unpolarized.json', import.meta.url));
const FRONT = fileURLToPath(new URL('../../../content/front.unpolarized.json', import.meta.url));

/* Hard list: capped per chapter, zero anywhere inside a reflect block. */
const JARGON = [
  'qubit', 'decoherence', 'Hamiltonian', 'fidelity', 'entanglement', 'entangled',
  'superposition', 'eigenstate', 'eigenvalue', 'wavefunction', 'wave function',
  'coherence', 'unitary', 'observable', 'quantum state', 'collapse of the',
];
const CAP = 2;

/* Informational only. */
const WATCH = [
  'quantum', 'physics', 'photon', 'particle', 'atom', 'energy', 'theorem',
  'correlation', 'correlated', 'polarizing', 'polarizer', 'polarized', 'filter',
];

const rx = (term) => new RegExp('\\b' + term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + 's?\\b', 'gi');

const textOf = (block) => {
  if (block.t === 'dlg') return block.text.join(' ');
  if (typeof block.text === 'string') return block.text;
  if (typeof block.html === 'string') return block.html;
  return '';
};

const count = (haystack, terms) => {
  const hits = new Map();
  for (const term of terms) {
    const n = (haystack.match(rx(term)) ?? []).length;
    if (n) hits.set(term, n);
  }
  return hits;
};

const fmt = (hits) => [...hits].map(([t, n]) => t + '×' + n).join(', ');

const book = JSON.parse(readFileSync(BOOK, 'utf8'));
const front = JSON.parse(readFileSync(FRONT, 'utf8'));

const failures = [];
let jargonTotal = 0;

console.log('jargon gate: ' + JARGON.length + ' capped terms, cap ' + CAP +
  ' per chapter, 0 inside reflections\n');

for (const canto of book) {
  const whole = [canto.title, canto.epigraph?.text ?? '', ...canto.blocks.map(textOf)].join('\n');
  const hits = count(whole, JARGON);
  const n = [...hits.values()].reduce((a, b) => a + b, 0);
  jargonTotal += n;

  const reflects = canto.blocks.filter((b) => b.t === 'reflect').map((b) => b.text).join('\n');
  const rHits = count(reflects, JARGON);
  const rN = [...rHits.values()].reduce((a, b) => a + b, 0);

  const watch = count(whole, WATCH);

  const flag = n > CAP || rN > 0 ? 'FAIL' : ' ok ';
  console.log(flag + '  ch ' + String(canto.n).padStart(2) + '  jargon ' + String(n).padStart(2) +
    '  reflect ' + String(rN).padStart(2) + '   ' + canto.title);
  if (hits.size) console.log('        terms: ' + fmt(hits));
  if (watch.size) console.log('        watch: ' + fmt(watch));

  if (n > CAP) failures.push('ch ' + canto.n + ': ' + n + ' capped terms (cap ' + CAP + '): ' + fmt(hits));
  if (rN > 0) failures.push('ch ' + canto.n + ': ' + rN + ' capped terms inside a reflection: ' + fmt(rHits));
}

/* Front matter is held to the same reflection rule for its own reflect block. */
const frontProse = [
  front.cover.title, front.cover.sub, front.invocation.epigraph.text,
  ...front.invocation.paras, front.appendix.intro, ...front.footer.lines,
].join('\n');
const fHits = count(frontProse, JARGON);
const fN = [...fHits.values()].reduce((a, b) => a + b, 0);
const fRefl = count(front.invocation.reflect.text, JARGON);
const fRN = [...fRefl.values()].reduce((a, b) => a + b, 0);

console.log((fN > CAP || fRN > 0 ? 'FAIL' : ' ok ') + '  front matter   jargon ' +
  String(fN).padStart(2) + '  reflect ' + String(fRN).padStart(2));
if (fHits.size) console.log('        terms: ' + fmt(fHits));
const fWatch = count(frontProse, WATCH);
if (fWatch.size) console.log('        watch: ' + fmt(fWatch));

if (fN > CAP) failures.push('front matter: ' + fN + ' capped terms: ' + fmt(fHits));
if (fRN > 0) failures.push('front matter: capped terms inside the reflection: ' + fmt(fRefl));

console.log('\ntotal capped-term occurrences across the book: ' + (jargonTotal + fN));

if (failures.length) {
  console.error('\njargon gate FAILED');
  for (const f of failures) console.error('  ' + f);
  process.exit(1);
}
console.log('jargon gate passed');
