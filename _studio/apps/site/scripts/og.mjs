/* Share cards for every note, rendered from vite/og.ts into dist/og.

   Cards ship as PNG because that is the only format the share crawlers read.
   The rasteriser is the chromium playwright already installs for the test
   suite, so this adds no dependency; with no notes it exits before launching
   anything. Usage: tsx scripts/og.mjs */

import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { ogCard } from '../vite/og.ts';
import { readNotes } from '../vite/notes.ts';

const notes = readNotes(fileURLToPath(new URL('../content/notes', import.meta.url)));
if (!notes.length) {
  console.log('og: no notes, no cards');
  process.exit(0);
}

const dir = fileURLToPath(new URL('../dist/og', import.meta.url));
mkdirSync(dir, { recursive: true });

const { chromium } = await import('playwright-core');
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });

for (const n of notes) {
  const svg = ogCard({ kicker: 'Notes', title: n.title, footer: 'pandey-tushar.com' });
  writeFileSync(dir + '/notes-' + n.slug + '.svg', svg);
  await page.setContent('<style>html,body{margin:0}</style>' + svg);
  await page.screenshot({ path: dir + '/notes-' + n.slug + '.png' });
  console.log('og: notes-' + n.slug + '.png');
}

await browser.close();
