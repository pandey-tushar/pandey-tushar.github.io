/* One-shot extraction of book data from the live single-file edition.
   Reads only; never writes into the live folder. */
import fs from 'node:fs';
import path from 'node:path';

const SRC = process.env.QD_SOURCE ||
  'C:/Users/thetu/Downloads/pandey-tushar.github.io/qubit-dialogues.html';
const OUT = path.resolve(import.meta.dirname, '..', 'content');

const raw = fs.readFileSync(SRC, 'utf8');

const m = raw.match(/window\.CANTOS = (\[[\s\S]*?\]);<\/script>/);
if (!m) throw new Error('CANTOS blob not found in ' + SRC);
const cantos = JSON.parse(m[1]);
if (cantos.length !== 22) throw new Error('expected 22 cantos, got ' + cantos.length);

fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, 'en.json'), JSON.stringify(cantos, null, 2) + '\n', 'utf8');
console.log('wrote content/en.json', cantos.length, 'cantos');
