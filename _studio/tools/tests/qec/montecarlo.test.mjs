import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { surfaceCode, repetitionCode } from '../../../../qec-in-practice/js/qec/codes.js';
import { estimate, estimateChunks } from '../../../../qec-in-practice/js/qec/montecarlo.js';

const ref = JSON.parse(readFileSync(new URL('./reference.json', import.meta.url)));

test('reference fixture uses the same checks and logical as codes.js', () => {
  for (const r of ref.rows) {
    const c = r.kind === 'repetition' ? repetitionCode(r.d) : surfaceCode(r.d);
    assert.deepEqual(r.zChecks, c.checks.Z);
    assert.deepEqual(r.logicalZ, c.logical.Z);
  }
});

test('chunks are cumulative and match estimate', () => {
  const o = { kind: 'surface', d: 3, p: 0.08, shots: 2500, seed: 4 };
  const all = [...estimateChunks(o, 1000)];
  assert.deepEqual(all.map(s => s.shots), [1000, 2000, 2500]);
  assert.deepEqual(all.map(s => s.done), [false, false, true]);
  const e = estimate(o);
  assert.equal(e.failures, all[2].failures);
  assert.equal(e.rate, e.failures / 2500);
  assert.ok(Math.abs(e.stderr - Math.sqrt(e.rate * (1 - e.rate) / 2500)) < 1e-12);
});

test('depolarizing at p: each Pauli part is bitflip at 2p/3, so r <= rate <= 2r', () => {
  const r = estimate({ kind: 'surface', d: 5, p: 0.1 * 2 / 3, shots: 20000, seed: 1, model: 'bitflip' }).rate;
  const dp = estimate({ kind: 'surface', d: 5, p: 0.1, shots: 20000, seed: 2, model: 'depolarizing' });
  assert.ok(dp.rate > r + 4 * dp.stderr && dp.rate < 2 * r, `${dp.rate} vs ${r}`);
});

const JS_SHOTS = { repetition: 200000, surface: 60000 };
const table = [];

test('JS union-find vs stim + pymatching reference', () => {
  for (const [i, r] of ref.rows.entries()) {
    const shots = r.rounds > 1 ? 30000 : JS_SHOTS[r.kind];
    const js = estimate({ kind: r.kind, d: r.d, p: r.p, model: r.model, shots, seed: 77 + i, rounds: r.rounds });
    const pool = (js.failures + r.failures) / (shots + r.shots);
    const sig = Math.sqrt(pool * (1 - pool) * (1 / shots + 1 / r.shots));
    const sJ = Math.sqrt(js.rate * (1 - js.rate) / shots + r.rate * (1 - r.rate) / r.shots);
    table.push([r.kind, r.d, r.p, r.rounds, r.rate, js.rate, r.rate ? js.rate / r.rate : NaN, sig ? (js.rate - r.rate) / sig : 0]);
    if (r.kind === 'repetition') assert.ok(Math.abs(js.rate - r.rate) <= 4 * sig, `rep d=${r.d} p=${r.p}: ${js.rate} vs ${r.rate}`);
    else {
      assert.ok(js.rate >= r.rate - 4 * sJ, `surface d=${r.d} p=${r.p} R=${r.rounds}: ${js.rate} below ${r.rate}`);
      assert.ok(js.rate <= { 3: 1.3, 5: 1.7, 7: 2.5 }[r.d] * r.rate + 2 * sJ, `surface d=${r.d} p=${r.p} R=${r.rounds}: ${js.rate} vs ${r.rate}`);
    }
  }
  console.log('kind d p rounds ref js ratio z');
  for (const t of table) console.log(t.map(v => typeof v === 'number' ? +v.toPrecision(4) : v).join(' '));
});

test('threshold sanity: falls with d at p=0.05, rises at p=0.15', () => {
  const at = (p, d) => estimate({ kind: 'surface', d, p, shots: 40000, seed: d }).rate;
  const lo = [3, 5, 7].map(d => at(0.05, d)), hi = [3, 5, 7].map(d => at(0.15, d));
  console.log('p=0.05', lo, 'p=0.15', hi);
  assert.ok(lo[0] > lo[1] && lo[1] > lo[2]);
  assert.ok(hi[0] < hi[1] && hi[1] < hi[2]);
});

test('performance: d=7 code capacity, 20000 shots', () => {
  estimate({ kind: 'surface', d: 7, p: 0.05, shots: 2000, seed: 1 });
  const t0 = performance.now();
  estimate({ kind: 'surface', d: 7, p: 0.05, shots: 20000, seed: 2 });
  const ms = performance.now() - t0;
  console.log(`d=7 20000 shots: ${ms.toFixed(0)} ms`);
  assert.ok(ms < 1500);
});

test('worker posts cumulative progress', async () => {
  const msgs = [];
  globalThis.self = { postMessage: m => msgs.push(m) };
  await import('../../../../qec-in-practice/js/qec/worker.js');
  self.onmessage({ data: { id: 'a', kind: 'repetition', d: 3, p: 0.1, model: 'bitflip', shots: 2500, seed: 1, rounds: 1, chunk: 1000 } });
  assert.deepEqual(msgs.map(m => [m.id, m.shots, m.done]), [['a', 1000, false], ['a', 2000, false], ['a', 2500, true]]);
  assert.equal(msgs[2].failures, estimate({ kind: 'repetition', d: 3, p: 0.1, shots: 2500, seed: 1 }).failures);
  delete globalThis.self;
});
