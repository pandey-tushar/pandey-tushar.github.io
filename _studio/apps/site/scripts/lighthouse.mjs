/* Lighthouse against the served build. Starts the static server itself so the
   numbers include gzip and cache headers.
   Usage: tsx scripts/lighthouse.mjs [url] [--desktop] */

import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import lighthouse from 'lighthouse';
import * as chromeLauncher from 'chrome-launcher';

const url = process.argv.find((a) => a.startsWith('http')) || 'http://localhost:4320/';
const desktop = process.argv.includes('--desktop');
const port = Number(new URL(url).port || 80);

const server = spawn(process.execPath, [fileURLToPath(new URL('./serve.mjs', import.meta.url)), String(port)], {
  stdio: 'ignore',
});
const stop = () => { try { server.kill(); } catch { /* already gone */ } };
process.on('exit', stop);

/* wait for the port rather than sleeping at it, then prove it is this build:
   another app in the monorepo on the same port would silently be measured */
let served = '';
for (let i = 0; i < 60; i++) {
  try { served = await (await fetch(url)).text(); break; } catch { await new Promise((r) => setTimeout(r, 250)); }
}
if (!served.includes('Ph.D. Mathematics')) {
  stop();
  console.error('lighthouse: ' + url + ' is not this build; something else holds the port');
  process.exit(1);
}

const chrome = await chromeLauncher.launch({ chromeFlags: ['--headless=new', '--no-sandbox'] });
const result = await lighthouse(url, {
  port: chrome.port,
  output: 'json',
  logLevel: 'error',
  formFactor: desktop ? 'desktop' : 'mobile',
  screenEmulation: desktop
    ? { mobile: false, width: 1350, height: 940, deviceScaleFactor: 1, disabled: false }
    : undefined,
  throttling: desktop ? { rttMs: 40, throughputKbps: 10240, cpuSlowdownMultiplier: 1 } : undefined,
});
await chrome.kill();
stop();

const lhr = result.lhr;
const pct = (id) => Math.round((lhr.categories[id]?.score ?? 0) * 100);
const metric = (id) => (lhr.audits[id]?.displayValue ?? 'n/a') +
  '  (' + Math.round(lhr.audits[id]?.numericValue ?? 0) + ')';

console.log('lighthouse ' + (desktop ? 'desktop' : 'mobile') + '  ' + url);
console.log('  performance     ' + pct('performance'));
console.log('  accessibility   ' + pct('accessibility'));
console.log('  best-practices  ' + pct('best-practices'));
console.log('  seo             ' + pct('seo'));
console.log('  LCP             ' + metric('largest-contentful-paint'));
console.log('  FCP             ' + metric('first-contentful-paint'));
console.log('  TBT             ' + metric('total-blocking-time'));
console.log('  CLS             ' + metric('cumulative-layout-shift'));
console.log('  Speed Index     ' + metric('speed-index'));
const lcpEl = lhr.audits['largest-contentful-paint-element'];
const node = lcpEl?.details?.items?.[0]?.items?.[0]?.node;
if (node) console.log('  LCP element     ' + (node.nodeLabel || node.snippet));
const total = lhr.audits['total-byte-weight'];
if (total) console.log('  total bytes     ' + total.displayValue);

for (const id of ['performance', 'accessibility', 'best-practices', 'seo']) {
  const fails = (lhr.categories[id]?.auditRefs ?? [])
    .map((r) => lhr.audits[r.id])
    .filter((a) => a && a.score !== null && a.score < 1 && a.scoreDisplayMode !== 'informative');
  if (!fails.length) continue;
  console.log('\n  ' + id + ' audits below 1:');
  for (const a of fails) console.log('    ' + a.id + '  ' + (a.displayValue || a.title));
}
