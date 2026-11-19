import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mulberry32 } from '../../../../qec-in-practice/js/stabsim.js';
import { surfaceCode, repetitionCode } from '../../../../qec-in-practice/js/qec/codes.js';
import { sampleErrors, syndrome, sampleMeasurementFlips, detectionEvents } from '../../../../qec-in-practice/js/qec/noise.js';

test('bitflip rate and no z part', () => {
  const c = surfaceCode(5), rng = mulberry32(1);
  let nx = 0, nz = 0;
  for (let s = 0; s < 4000; s++) {
    const e = sampleErrors(c, 0.1, rng, 'bitflip');
    assert.equal(e.x.length, 25);
    for (let i = 0; i < 25; i++) { nx += e.x[i]; nz += e.z[i]; }
  }
  assert.equal(nz, 0);
  assert.ok(Math.abs(nx / 1e5 - 0.1) < 0.005);
});

test('depolarizing: X, Y, Z each p/3', () => {
  const c = surfaceCode(5), rng = mulberry32(2);
  const cnt = [0, 0, 0, 0];
  for (let s = 0; s < 8000; s++) {
    const e = sampleErrors(c, 0.3, rng, 'depolarizing');
    for (let i = 0; i < 25; i++) cnt[e.x[i] + 2 * e.z[i]]++;
  }
  const N = 2e5;
  for (const k of [1, 2, 3]) assert.ok(Math.abs(cnt[k] / N - 0.1) < 0.004, `${k}: ${cnt[k] / N}`);
});

test('syndrome: Z checks see x part, X checks see z part', () => {
  const c = surfaceCode(3);
  const x = new Uint8Array(9), z = new Uint8Array(9);
  x[4] = 1;
  let s = syndrome(c, { x, z });
  assert.deepEqual([...s.Z], [1, 1, 0, 0]);
  assert.deepEqual([...s.X], [0, 0, 0, 0]);
  x[4] = 0; z[0] = 1;
  s = syndrome(c, { x, z });
  assert.deepEqual([...s.X], [1, 0, 0, 0]);
  assert.deepEqual([...s.Z], [0, 0, 0, 0]);
  const r = repetitionCode(3);
  s = syndrome(r, { x: Uint8Array.of(0, 1, 0), z: new Uint8Array(3) });
  assert.deepEqual([...s.Z], [1, 1]);
  assert.equal(s.X.length, 0);
});

test('measurement flips rate', () => {
  const c = surfaceCode(5), rng = mulberry32(3);
  let k = 0;
  for (let s = 0; s < 5000; s++) { const f = sampleMeasurementFlips(c, 0.2, rng); for (const b of f.Z) k += b; assert.equal(f.X.length, 12); }
  assert.ok(Math.abs(k / 60000 - 0.2) < 0.008);
});

test('detection events are differences of consecutive rounds', () => {
  const ev = detectionEvents([Uint8Array.of(1, 0), Uint8Array.of(1, 1), Uint8Array.of(0, 1)]);
  assert.deepEqual([...ev], [1, 0, 0, 1, 1, 0]);
});
