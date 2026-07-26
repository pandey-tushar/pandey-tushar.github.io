/* Runs the schema validator over every edition on disk. */
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { validateBook, validateFront, SchemaError, BLOCK_TYPES } from './schema.js';

const here = import.meta.dirname;
const SKIP = new Set(['package.json', 'package-lock.json', 'tsconfig.json']);
/* hyphens are allowed so that a two-word edition id (hi-unpolarized) is found */
const editions = readdirSync(here).filter((f) => /^[a-z][a-z-]*\.json$/.test(f) && !SKIP.has(f));
const fronts = readdirSync(here).filter((f) => /^front\.[a-z][a-z-]*\.json$/.test(f));

let failed = false;

for (const file of editions) {
  try {
    const book = validateBook(JSON.parse(readFileSync(join(here, file), 'utf8')), file);
    const blocks = book.reduce((n, c) => n + c.blocks.length, 0);
    const counts = new Map<string, number>();
    for (const c of book) for (const b of c.blocks) counts.set(b.t, (counts.get(b.t) ?? 0) + 1);
    const shape = BLOCK_TYPES.map((t) => t + '=' + (counts.get(t) ?? 0)).join(' ');
    console.log('ok   ' + file + ': ' + book.length + ' cantos, ' + blocks + ' blocks (' + shape + ')');
  } catch (e) {
    failed = true;
    console.error('FAIL ' + file + ': ' + (e instanceof SchemaError ? e.message : String(e)));
  }
}

for (const file of fronts) {
  try {
    validateFront(JSON.parse(readFileSync(join(here, file), 'utf8')), file);
    console.log('ok   ' + file);
  } catch (e) {
    failed = true;
    console.error('FAIL ' + file + ': ' + (e instanceof SchemaError ? e.message : String(e)));
  }
}

if (failed) process.exit(1);
