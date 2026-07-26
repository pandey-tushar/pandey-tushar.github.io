/* Frame budget, memory, and the mobile gate.

   Three things are measured, all of them things this design fails at by
   default rather than by accident:

   1. Frame timing while scrolling each composed canto. Art-led pages are fine
      until the reader moves.
   2. Heap and canvas backing store after a full scroll down and back. Three
      mounted scenes is the whole budget; a scene that does not dispose shows
      up here as backing store that never comes back down.
   3. The same run at 375 pixels wide. This edition dies on phones if it is not
      measured there constantly.

   Usage: node tools/perf.mjs [--mobile] */

import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import { serve } from './serve.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
const mobileOnly = process.argv.includes('--mobile');
const desktopOnly = process.argv.includes('--desktop');

const PROFILES = [
  { name: 'desktop 1440x900', viewport: { width: 1440, height: 900 }, dpr: 1, step: 42 },
  { name: 'mobile 375x812', viewport: { width: 375, height: 812 }, dpr: 2, step: 26 },
];

const server = await serve(root + 'dist');
const browser = await chromium.launch();

const median = (xs) => {
  if (xs.length === 0) return 0;
  const s = [...xs].sort((a, b) => a - b);
  return s[Math.floor(s.length / 2)];
};
const pct = (xs, p) => {
  if (xs.length === 0) return 0;
  const s = [...xs].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.floor(s.length * p))];
};
const mb = (bytes) => Math.round((bytes / 1048576) * 10) / 10;

async function heapOf(cdp) {
  await cdp.send('HeapProfiler.collectGarbage');
  const { metrics } = await cdp.send('Performance.getMetrics');
  const hit = metrics.find((m) => m.name === 'JSHeapUsedSize');
  return hit ? hit.value : 0;
}

const report = [];

for (const profile of PROFILES) {
  if (mobileOnly && !profile.name.startsWith('mobile')) continue;
  if (desktopOnly && !profile.name.startsWith('desktop')) continue;

  const context = await browser.newContext({
    viewport: profile.viewport,
    deviceScaleFactor: profile.dpr,
  });
  const page = await context.newPage();
  const problems = [];
  page.on('pageerror', (e) => problems.push('pageerror: ' + String(e)));
  page.on('console', (m) => {
    if (m.type() === 'error' || m.type() === 'warning') problems.push(m.type() + ': ' + m.text());
  });

  await page.goto(server.url + '/', { waitUntil: 'load' });
  await page.waitForSelector('article.canto');
  /* the page sets scroll-behavior: smooth for anchor jumps. Leaving it on
     would animate every programmatic scroll and make these numbers fiction. */
  await page.addStyleTag({ content: 'html { scroll-behavior: auto !important; }' });

  const cdp = await context.newCDPSession(page);
  await cdp.send('Performance.enable');
  await cdp.send('HeapProfiler.enable');

  const baselineHeap = await heapOf(cdp);
  const baselineCanvas = await page.evaluate(() => {
    const cs = [...document.querySelectorAll('canvas')];
    return { count: cs.length, bytes: cs.reduce((n, c) => n + c.width * c.height * 4, 0) };
  });

  const composed = await page.evaluate(() =>
    [...document.querySelectorAll('article.canto:not([data-unstyled])')].map((a) => Number(a.dataset.canto)),
  );

  /* per canto scroll pass */
  const perCanto = [];
  for (const canto of composed) {
    const stats = await page.evaluate(async ({ canto, step }) => {
      const track = document.querySelector('#canto-' + canto + ' .track');
      const start = track.getBoundingClientRect().top + scrollY;
      const end = start + track.getBoundingClientRect().height;
      scrollTo(0, start);
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));

      const frames = [];
      let maxLive = 0;
      await new Promise((done) => {
        let last = performance.now();
        const tick = (t) => {
          frames.push(t - last);
          last = t;
          maxLive = Math.max(maxLive, document.querySelectorAll('canvas.live').length);
          if (scrollY >= end - innerHeight || scrollY + innerHeight >= document.body.scrollHeight - 2) {
            done();
            return;
          }
          scrollBy(0, step);
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      });
      /* the first sample is the gap since the previous idle frame, not a cost */
      return { frames: frames.slice(2), maxLive };
    }, { canto, step: profile.step });

    perCanto.push({
      canto,
      frames: stats.frames.length,
      median: Math.round(median(stats.frames) * 100) / 100,
      p95: Math.round(pct(stats.frames, 0.95) * 100) / 100,
      worst: Math.round(Math.max(...stats.frames, 0) * 100) / 100,
      over50ms: stats.frames.filter((f) => f > 50).length,
      maxLiveCanvases: stats.maxLive,
    });
  }

  /* full document, down and back, for the memory check */
  await page.evaluate(async () => {
    const step = Math.round(innerHeight * 0.6);
    const bottom = document.body.scrollHeight;
    for (let y = 0; y < bottom; y += step) {
      scrollTo(0, y);
      await new Promise((r) => requestAnimationFrame(r));
    }
    for (let y = bottom; y > 0; y -= step) {
      scrollTo(0, y);
      await new Promise((r) => requestAnimationFrame(r));
    }
    scrollTo(0, 0);
    await new Promise((r) => setTimeout(r, 400));
  });

  const afterHeap = await heapOf(cdp);
  const afterCanvas = await page.evaluate(() => {
    const cs = [...document.querySelectorAll('canvas')];
    return { count: cs.length, bytes: cs.reduce((n, c) => n + c.width * c.height * 4, 0) };
  });

  const all = perCanto.flatMap((c) => [c.median]);
  report.push({
    profile: profile.name,
    perCanto,
    overallMedianOfMedians: Math.round(median(all) * 100) / 100,
    worstFrame: Math.max(...perCanto.map((c) => c.worst)),
    longTasksOver50ms: perCanto.reduce((n, c) => n + c.over50ms, 0),
    maxLiveCanvases: Math.max(...perCanto.map((c) => c.maxLiveCanvases)),
    heapBaselineMB: mb(baselineHeap),
    heapAfterMB: mb(afterHeap),
    heapDeltaMB: Math.round((mb(afterHeap) - mb(baselineHeap)) * 10) / 10,
    canvasBaseline: baselineCanvas.count + ' canvases, ' + mb(baselineCanvas.bytes) + ' MB',
    canvasAfter: afterCanvas.count + ' canvases, ' + mb(afterCanvas.bytes) + ' MB',
    problems,
  });

  await context.close();
}

await browser.close();
await server.close();

for (const r of report) {
  console.log('\n=== ' + r.profile + ' ===');
  console.table(r.perCanto);
  console.log('median of per canto medians : ' + r.overallMedianOfMedians + ' ms');
  console.log('worst single frame          : ' + r.worstFrame + ' ms');
  console.log('frames over 50 ms           : ' + r.longTasksOver50ms);
  console.log('most live canvases at once  : ' + r.maxLiveCanvases + ' (budget 3)');
  console.log('heap before / after         : ' + r.heapBaselineMB + ' MB / ' + r.heapAfterMB +
    ' MB (delta ' + r.heapDeltaMB + ' MB)');
  console.log('canvas store before / after : ' + r.canvasBaseline + '  ->  ' + r.canvasAfter);
  console.log('console errors and warnings : ' + (r.problems.length === 0 ? 'none' : r.problems.length));
  for (const p of r.problems) console.log('   ' + p);
}

if (report.some((r) => r.problems.length > 0)) process.exitCode = 1;
