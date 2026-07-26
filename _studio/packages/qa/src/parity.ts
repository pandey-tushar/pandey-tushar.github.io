/* Content parity: content/en.json against the CANTOS blob in the shipped
   single-file edition. Any difference is a bug in the extraction.

   The live folder is read-only here. Never write to it. */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const LIVE = process.env.QD_SOURCE ??
  'C:/Users/thetu/Downloads/pandey-tushar.github.io/qubit-dialogues.html';
const MINE = fileURLToPath(new URL('../../../content/en.json', import.meta.url));

interface Block { t: string; [k: string]: unknown }
interface Canto { n: number; title: string; blocks: Block[]; [k: string]: unknown }

const raw = readFileSync(LIVE, 'utf8');
const m = raw.match(/window\.CANTOS = (\[[\s\S]*?\]);<\/script>/);
if (!m) { console.error('parity: CANTOS blob not found in ' + LIVE); process.exit(1); }

const live = JSON.parse(m[1]) as Canto[];
const mine = JSON.parse(readFileSync(MINE, 'utf8')) as Canto[];

const problems: string[] = [];
const say = (s: string) => problems.push(s);

if (live.length !== mine.length) say('canto count: live ' + live.length + ', mine ' + mine.length);

const n = Math.min(live.length, mine.length);
for (let i = 0; i < n; i++) {
  const a = live[i], b = mine[i];
  const at = 'canto[' + i + ']';
  if (a.n !== b.n) say(at + '.n: ' + a.n + ' vs ' + b.n);
  if (a.title !== b.title) say(at + '.title differs');
  if (a.blocks.length !== b.blocks.length) {
    say(at + ' (canto ' + a.n + ') block count: live ' + a.blocks.length + ', mine ' + b.blocks.length);
    continue;
  }
  for (let j = 0; j < a.blocks.length; j++) {
    const x = a.blocks[j], y = b.blocks[j];
    if (x.t !== y.t) say(at + '.blocks[' + j + '].t: ' + x.t + ' vs ' + y.t);
    if (JSON.stringify(x) !== JSON.stringify(y)) say(at + '.blocks[' + j + '] (' + x.t + ') content differs');
  }
}

/* a whole-tree byte check on the canonical serialisation */
const same = JSON.stringify(live) === JSON.stringify(mine);

const liveBlocks = live.reduce((t, c) => t + c.blocks.length, 0);
const mineBlocks = mine.reduce((t, c) => t + c.blocks.length, 0);
console.log('live: ' + live.length + ' cantos, ' + liveBlocks + ' blocks');
console.log('mine: ' + mine.length + ' cantos, ' + mineBlocks + ' blocks');
console.log('per-canto blocks live: ' + live.map((c) => c.blocks.length).join(','));
console.log('per-canto blocks mine: ' + mine.map((c) => c.blocks.length).join(','));
console.log('canonical JSON identical: ' + same);

if (problems.length || !same) {
  console.error('\nPARITY FAILED');
  for (const p of problems.slice(0, 40)) console.error('  ' + p);
  if (problems.length > 40) console.error('  ... and ' + (problems.length - 40) + ' more');
  process.exit(1);
}
console.log('\nparity ok: content/en.json is byte-faithful to the shipped edition');
