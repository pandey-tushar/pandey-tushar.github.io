/* Tell census: a regex sweep for the fingerprints of machine-written prose.
   Prints counts per file. `--check` compares against census-baseline.json and
   fails when any count grows; `--bless` rewrites the baseline.

   Watch for false positives when adding patterns: word boundaries matter,
   "abundance" and "redundancy" both contain "danc". */
import { readFileSync, writeFileSync, existsSync, readdirSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('../../..', import.meta.url));
const BASELINE = fileURLToPath(new URL('../census-baseline.json', import.meta.url));

interface Pattern { id: string; re: RegExp }

const PATTERNS: Pattern[] = [
  { id: 'em-dash', re: /—/g },
  { id: 'en-dash', re: /–/g },
  { id: 'not-x-but-y', re: /\bnot\s+(?:only\s+)?[^.;!?]{2,60}?,?\s+but\s+(?:rather|also|instead)?\b/gi },
  { id: 'it-is-not-only', re: /[.;]\s+It is (?:not|only|the)\b/g },
  { id: 'quietly', re: /\bquietly\b/gi },
  { id: 'simply', re: /\bsimply\b/gi },
  { id: 'whisper', re: /\bwhispers?(?:ed|ing)?\b/gi },
  { id: 'delve', re: /\bdelv(?:e|es|ed|ing)\b/gi },
  { id: 'tapestry', re: /\btapestr(?:y|ies)\b/gi },
  { id: 'testament', re: /\btestament\b/gi },
  { id: 'elegant', re: /\belegant(?:ly)?\b/gi },
  { id: 'here-is-the', re: /\bHere is the\b/g },
  /* three parallel short items in one clause: "a, b, and c" */
  { id: 'triadic-run', re: /\b[\w'-]+(?:\s+[\w'-]+){0,2},\s+[\w'-]+(?:\s+[\w'-]+){0,2},\s+and\s+[\w'-]+/g },
  /* three -ly adverbs in a row is the loudest form of the same tic */
  { id: 'triadic-adverbs', re: /\b\w+ly,\s+\w+ly,?\s+and\s+\w+ly\b/gi },
];

const stripTags = (s: string) => s.replace(/<[^>]*>/g, ' ');

/** Pulls every string out of a JSON value, markup stripped. */
function proseOf(value: unknown, out: string[] = []): string[] {
  if (typeof value === 'string') out.push(stripTags(value));
  else if (Array.isArray(value)) for (const v of value) proseOf(v, out);
  else if (value && typeof value === 'object') for (const v of Object.values(value)) proseOf(v, out);
  return out;
}

function proseFromFile(path: string): string {
  const raw = readFileSync(path, 'utf8');
  if (path.endsWith('.json')) {
    try { return proseOf(JSON.parse(raw)).join('\n'); } catch { return raw; }
  }
  return stripTags(raw);
}

const SKIP = new Set(['package.json', 'package-lock.json', 'tsconfig.json']);

function targets(): string[] {
  const dir = join(ROOT, 'content');
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((f) => f.endsWith('.json') && !SKIP.has(f))
    .map((f) => join(dir, f))
    .sort();
}

const files = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const list = files.length ? files.map((f) => join(ROOT, f)) : targets();
const mode = process.argv.includes('--check') ? 'check'
  : process.argv.includes('--bless') ? 'bless' : 'print';

const report: Record<string, Record<string, number>> = {};
for (const path of list) {
  const prose = proseFromFile(path);
  const counts: Record<string, number> = {};
  for (const p of PATTERNS) counts[p.id] = (prose.match(p.re) ?? []).length;
  report[relative(ROOT, path).replace(/\\/g, '/')] = counts;
}

for (const [file, counts] of Object.entries(report)) {
  const hits = Object.entries(counts).filter(([, n]) => n > 0);
  const total = hits.reduce((n, [, v]) => n + v, 0);
  console.log(file + '  (' + total + ' hits)');
  if (!hits.length) console.log('  clean');
  for (const [id, n] of hits.sort((a, b) => b[1] - a[1])) {
    console.log('  ' + id.padEnd(18) + String(n).padStart(5));
  }
}

if (mode === 'bless') {
  writeFileSync(BASELINE, JSON.stringify(report, null, 2) + '\n', 'utf8');
  console.log('\nbaseline written to ' + relative(ROOT, BASELINE).replace(/\\/g, '/'));
} else if (mode === 'check') {
  if (!existsSync(BASELINE)) {
    console.error('\nno baseline; run: npm run census:bless -w @qubit/qa');
    process.exit(1);
  }
  const base = JSON.parse(readFileSync(BASELINE, 'utf8')) as typeof report;
  const regressions: string[] = [];
  for (const [file, counts] of Object.entries(report)) {
    for (const [id, n] of Object.entries(counts)) {
      const was = base[file]?.[id] ?? 0;
      if (n > was) regressions.push(file + ' ' + id + ': ' + was + ' -> ' + n);
    }
  }
  if (regressions.length) {
    console.error('\ncensus regressions:');
    for (const r of regressions) console.error('  ' + r);
    process.exit(1);
  }
  console.log('\nno regressions against baseline');
}
