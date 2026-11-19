// Pure figure logic for the paper companion pages: papers/js/fss.js (scaling collapse) and papers/js/plot.js
// (scales and ticks). The real-data tests read papers/data/bb-erasure-baselines.json.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { scaled, fitPoly, collapse, wilson } from '../../../../papers/js/fss.js';
import { linScale, logScale, niceTicks, logTicks } from '../../../../papers/js/plot.js';

const DATA = JSON.parse(readFileSync(new URL('../../../../papers/data/bb-erasure-baselines.json', import.meta.url), 'utf8'));
const close = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, `${msg ?? ''} ${a} vs ${b}`);

test('scaled is (p - p*) N^(1/nu)', () => {
  close(scaled(0.5, 100, 0.4, 2), 0.1 * 10, 1e-12);
  close(scaled(0.4, 1296, 0.4, 1.18), 0, 1e-12);
  assert.ok(scaled(0.3, 144, 0.4, 1) < 0);
});

test('fitPoly recovers an exact cubic and has zero residual', () => {
  const xs = [-3, -1, 0, 0.5, 2, 4, 7], f = x => 0.4 - 0.2 * x + 0.03 * x * x + 0.001 * x ** 3;
  const fit = fitPoly(xs, xs.map(f), 3);
  close(fit.rss, 0, 1e-18);
  for (const x of [-2, 1, 5]) close(fit.evaluate(x), f(x), 1e-12);
});

test('fitPoly is stable at large x and weights count as repeated rows', () => {
  const xs = [1e4, 2e4, 3e4, 4e4, 5e4, 6e4], ys = [0.01, 0.05, 0.02, 0.2, 0.15, 0.3];
  const rep = fitPoly([...xs, xs[1], xs[1]], [...ys, ys[1], ys[1]], 3);
  const w = fitPoly(xs, ys, 3, [1, 3, 1, 1, 1, 1]);
  close(w.rss, rep.rss, 1e-12);
  assert.ok(Number.isFinite(w.rss) && w.rss > 0);
});

test('wilson interval brackets the rate and stays in [0, 1]', () => {
  const [lo, hi] = wilson(20000, 200000);
  assert.ok(lo < 0.1 && hi > 0.1 && hi - lo < 0.003);
  const [z0, z1] = wilson(0, 200000);
  assert.equal(z0, 0); assert.ok(z1 > 0 && z1 < 3e-5);
});

test('collapse keeps only points within the window of each size centre', () => {
  const sizes = [{ N: 100, center: 0.4, points: [{ p: 0.3, fails: 1, shots: 10 }, { p: 0.41, fails: 2, shots: 10 }, { p: 0.46, fails: 5, shots: 10 }] }];
  const c = collapse(sizes, 0.4, 1, 0.06, 1);
  assert.deepEqual(c.points.map(q => q.p), [0.41, 0.46]);
  close(c.points[0].x, 0.01 * 100, 1e-9);
});

test('real data: the fit recorded in fss_results.json gives the residual recorded there', () => {
  const f = DATA.fss_fit;
  const c = collapse(DATA.bb, f.p_star_inf, f.nu, f.p_window, f.poly_degree);
  close(c.rss, f.residual_ss, 1e-9, 'residual');
  assert.equal(c.points.reduce((t, q) => t + q.w, 0), 55);
});

test("real data: the paper's fit collapses better than clearly wrong parameters", () => {
  const { p_star_inf: ps, nu } = DATA.paper_fit, w = DATA.fss_fit.p_window;
  const at = collapse(DATA.bb, ps, nu, w, 3).rss;
  for (const [a, b] of [[0.46, nu], [0.52, nu], [ps, 0.7], [ps, 2.2], [0.47, 2.0]])
    assert.ok(collapse(DATA.bb, a, b, w, 3).rss > 1.5 * at, `p*=${a}, nu=${b}`);
});

test('linScale and logScale map the domain ends to the range ends', () => {
  const l = linScale([0, 0.3], [50, 350]);
  close(l(0), 50, 1e-12); close(l(0.3), 350, 1e-9); close(l(0.15), 200, 1e-9);
  const g = logScale([1e-5, 1], [400, 0]);
  close(g(1e-5), 400, 1e-9); close(g(1), 0, 1e-9); close(g(1e-3), 240, 1e-9);
});

test('niceTicks are 1, 2 or 5 times a power of ten, inside the domain, about the asked count', () => {
  for (const [a, b] of [[0, 0.3], [0.29, 0.51], [-41.7, 63.2], [-3000, 12000]]) {
    const t = niceTicks(a, b, 5);
    assert.ok(t.length >= 3 && t.length <= 9, `${a}..${b}: ${t}`);
    assert.ok(t.every(v => v >= a - 1e-12 && v <= b + 1e-12));
    const step = t[1] - t[0], m = step / 10 ** Math.floor(Math.log10(step) + 1e-9);
    assert.ok([1, 2, 5].some(k => Math.abs(m - k) < 1e-6), `step ${step}`);
  }
});

test('logTicks gives the decades in the domain', () => {
  assert.deepEqual(logTicks(1e-5, 1), [1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1]);
});
