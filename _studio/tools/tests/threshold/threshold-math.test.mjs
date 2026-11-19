import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { estimate } from '../../../../qec-in-practice/js/qec/montecarlo.js';
import {
  binomialError, crossing, fitLambda, logScale, linScale, logTicks, linTicks, logSpace, planQueue,
} from '../../../../qec-in-practice/js/threshold-math.js';

const ROOT = new URL('../../../../', import.meta.url);

test('the served reference copy is byte-identical to the test fixture', () => {
  const a = readFileSync(new URL('_studio/tools/tests/qec/reference.json', ROOT));
  const b = readFileSync(new URL('qec-in-practice/data/qec-reference.json', ROOT));
  assert.ok(a.equals(b));
});

test('binomial error bars', () => {
  const e = binomialError(25, 1000);
  assert.equal(e.rate, 0.025);
  assert.ok(Math.abs(e.stderr - Math.sqrt(0.025 * 0.975 / 1000)) < 1e-15);
  assert.ok(Math.abs(e.lo - (0.025 - e.stderr)) < 1e-15);
  assert.ok(Math.abs(e.hi - (0.025 + e.stderr)) < 1e-15);
  const z = binomialError(0, 2000);
  assert.deepEqual([z.rate, z.stderr, z.lo], [0, 0, 0]);
  assert.equal(z.upper95, 3 / 2000);
  const big = binomialError(1, 2);
  assert.ok(big.lo >= 0 && big.hi <= 1);
  assert.equal(binomialError(0, 0).rate, null);
});

// Synthetic curves r_d(p) = A (p / pth)^((d + 1) / 2) all meet at pth, and ln r_5 - ln r_3 is linear in ln p,
// so interpolation in ln p must return pth exactly.
const synth = (d, pth, ps, shots = 1e7) =>
  ps.map(p => ({ p, shots, failures: Math.round(shots * 0.05 * (p / pth) ** ((d + 1) / 2)) }));

test('crossing recovers a known crossing from synthetic curves', () => {
  const ps = logSpace(0.04, 0.16, 9);
  const c = crossing(synth(3, 0.0912, ps), synth(5, 0.0912, ps));
  assert.equal(c.status, 'found');
  assert.ok(Math.abs(c.p - 0.0912) < 2e-4, `${c.p}`);
  assert.ok(c.lo <= c.p && c.p <= c.hi && c.hi - c.lo < 0.01);
});

test('crossing reports when the curves do not cross inside the range', () => {
  const ps = [0.01, 0.02, 0.03];
  assert.equal(crossing(synth(3, 0.1, ps), synth(5, 0.1, ps)).status, 'above');
  const hi = [0.2, 0.3, 0.4];
  assert.equal(crossing(synth(3, 0.1, hi), synth(5, 0.1, hi)).status, 'below');
  assert.equal(crossing([{ p: 0.1, shots: 10, failures: 1 }], [{ p: 0.1, shots: 10, failures: 2 }]).status, 'none');
});

test('crossing range widens with fewer shots', () => {
  const ps = logSpace(0.04, 0.16, 9);
  const wide = crossing(synth(3, 0.1, ps, 2000), synth(5, 0.1, ps, 2000));
  const tight = crossing(synth(3, 0.1, ps, 1e7), synth(5, 0.1, ps, 1e7));
  assert.ok(wide.hi - wide.lo > tight.hi - tight.lo);
});

// Real engine output, surface code, bit-flip noise, perfect measurement, union-find decoder.
// Band: the stim + pymatching reference (reference.json, 200,000 shots) has rates that fall with d at p = 0.08
// (0.0832, 0.0770, 0.0699 for d = 3, 5, 7) and rise at p = 0.10 (0.1200, 0.1247, 0.1262), so matching crosses in
// (0.08, 0.10). Union-find is a faster approximation to matching and is not expected to beat it, so its crossing
// sits at or below 0.10. The lower edge 0.06 is checked directly below: there the union-find rates fall clearly
// with d, so the crossing cannot be lower.
const ps = [0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11];
const curve = (d, opts = {}) => ps.map((p, i) => ({ p, ...estimate({ kind: 'surface', d, p, shots: 20000, seed: 500 + 10 * d + i, ...opts }) }));
const c3 = curve(3), c5 = curve(5), c7 = curve(7);

test('union-find code-capacity rates fall with d at p = 0.06 and rise at p = 0.10', () => {
  const at = (c, p) => c.find(r => r.p === p).rate;
  assert.ok(at(c3, 0.06) > at(c5, 0.06) && at(c5, 0.06) > at(c7, 0.06));
  assert.ok(at(c3, 0.10) < at(c5, 0.10) && at(c5, 0.10) < at(c7, 0.10));
});

test('crossing estimate on real engine output lies in (0.06, 0.10)', () => {
  for (const [a, b] of [[c3, c5], [c5, c7]]) {
    const c = crossing(a, b);
    assert.equal(c.status, 'found');
    assert.ok(c.p > 0.06 && c.p < 0.10, `${c.p}`);
    assert.ok(c.lo <= c.p && c.p <= c.hi);
  }
});

test('Lambda on real engine output at p = 0.03 is greater than 1', () => {
  const pts = [3, 5, 7].map(d => ({ d, ...estimate({ kind: 'surface', d, p: 0.03, shots: 20000, seed: 900 + d }) }));
  const f = fitLambda(pts);
  assert.ok(f.lambda > 1 && f.lo > 1, JSON.stringify(f));
  assert.ok(f.lo <= f.lambda && f.lambda <= f.hi);
});

test('Lambda fit recovers an exact exponential and skips zero-failure points', () => {
  const pts = [3, 5, 7, 9].map(d => ({ d, shots: 1e9, failures: Math.round(1e9 * 0.1 / 4 ** ((d - 3) / 2)) }));
  assert.ok(Math.abs(fitLambda(pts).lambda - 4) < 1e-3);
  const f = fitLambda([...pts.slice(0, 2), { d: 7, shots: 1000, failures: 0 }]);
  assert.deepEqual(f.used, [3, 5]);
  assert.equal(fitLambda([{ d: 3, shots: 10, failures: 1 }]), null);
});

test('scales and ticks', () => {
  const s = logScale([0.01, 1], [0, 200]);
  assert.equal(s(0.01), 0);
  assert.ok(Math.abs(s(0.1) - 100) < 1e-9);
  assert.ok(Math.abs(s.invert(100) - 0.1) < 1e-12);
  const l = linScale([0, 10], [100, 0]);
  assert.equal(l(5), 50);
  const t = logTicks(0.003, 0.2);
  assert.deepEqual(t.major, [0.01, 0.1]);
  assert.ok(t.minor.includes(0.005) && t.minor.includes(0.2) && t.minor.includes(0.02));
  assert.ok(t.minor.every(v => v >= 0.003 && v <= 0.2));
  assert.deepEqual(linTicks(0, 1, 5), [0, 0.2, 0.4, 0.6, 0.8, 1]);
  assert.deepEqual(logSpace(0.01, 0.1, 3), [0.01, 0.0316, 0.1]);
});

test('run queue: every point gets its shots, seeds are distinct, the first pass covers every point', () => {
  const jobs = planQueue({ ps: [0.05, 0.1], ds: [3, 5, 7], shots: 10000, passes: [0.2, 0.8], seed: 7 });
  const tot = {};
  for (const j of jobs) tot[`${j.d}:${j.p}`] = (tot[`${j.d}:${j.p}`] || 0) + j.shots;
  assert.equal(Object.keys(tot).length, 6);
  assert.ok(Object.values(tot).every(v => v === 10000));
  assert.equal(new Set(jobs.map(j => j.seed)).size, jobs.length);
  assert.deepEqual(jobs.slice(0, 6).map(j => j.shots), Array(6).fill(2000));
  assert.deepEqual(new Set(jobs.slice(0, 6).map(j => `${j.d}:${j.p}`)).size, 6);
  assert.equal(planQueue({ ps: [0.1], ds: [3], shots: 3, passes: [0.2, 0.8] }).reduce((a, j) => a + j.shots, 0), 3);
});
