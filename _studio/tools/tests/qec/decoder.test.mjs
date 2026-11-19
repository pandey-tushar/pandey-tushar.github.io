import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mulberry32 } from '../../../../qec-in-practice/js/stabsim.js';
import { surfaceCode, repetitionCode } from '../../../../qec-in-practice/js/qec/codes.js';
import { sampleErrors, syndrome, sampleMeasurementFlips, detectionEvents } from '../../../../qec-in-practice/js/qec/noise.js';
import { majorityDecode, buildGraph, decode, logicalFailure } from '../../../../qec-in-practice/js/qec/decoder.js';

const SYN = { X: 'Z', Z: 'X' }, PART = { X: 'x', Z: 'z' };
const zeros = s => s.every(b => b === 0);

function bits(n, ones) { const a = new Uint8Array(n); for (const i of ones) a[i] = 1; return a; }
function errOf(code, type, ones) {
  const e = { x: new Uint8Array(code.n), z: new Uint8Array(code.n) };
  e[PART[type]] = bits(code.n, ones);
  return e;
}
function* combos(n, k, start = 0, pre = []) {
  if (k === 0) { yield pre; return; }
  for (let i = start; i < n; i++) yield* combos(n, k - 1, i + 1, [...pre, i]);
}
// decode one type at code capacity; returns failure for that type after asserting zero residual syndrome
function run(code, g, type, e) {
  const corr = decode(g, syndrome(code, e)[SYN[type]]);
  const fix = { x: new Uint8Array(code.n), z: new Uint8Array(code.n) };
  fix[PART[type]] = corr;
  const res = { x: e.x.map((b, i) => b ^ fix.x[i]), z: e.z.map((b, i) => b ^ fix.z[i]) };
  assert.ok(zeros(syndrome(code, res)[SYN[type]]), 'residual syndrome must be zero');
  return logicalFailure(code, e, fix)[PART[type]];
}

for (const d of [3, 5]) test(`repetition d=${d}: majority equals union-find on all ${2 ** d} patterns`, () => {
  const c = repetitionCode(d), g = buildGraph(c, 'X');
  for (let m = 0; m < 2 ** d; m++) {
    const x = bits(d, [...Array(d).keys()].filter(i => (m >> i) & 1));
    const s = syndrome(c, { x, z: new Uint8Array(d) }).Z;
    assert.deepEqual([...decode(g, s)], [...majorityDecode(c, s)], `pattern ${m}`);
  }
});

test('surface d=3: every pattern clears the syndrome, every weight <= 1 corrected', () => {
  const c = surfaceCode(3);
  for (const type of ['X', 'Z']) {
    const g = buildGraph(c, type);
    for (let m = 0; m < 512; m++) {
      const ones = [...Array(9).keys()].filter(i => (m >> i) & 1);
      const fail = run(c, g, type, errOf(c, type, ones));
      if (ones.length <= 1) assert.equal(fail, false, `${type} ${ones}`);
    }
  }
});

test('surface d=5: every weight <= 2 corrected', () => {
  const c = surfaceCode(5);
  for (const type of ['X', 'Z']) {
    const g = buildGraph(c, type);
    for (let k = 0; k <= 2; k++) for (const ones of combos(25, k)) assert.equal(run(c, g, type, errOf(c, type, ones)), false, `${type} ${ones}`);
  }
});

test('surface d=7: sampled weight 3 corrected', () => {
  const c = surfaceCode(7), rng = mulberry32(7);
  for (const type of ['X', 'Z']) {
    const g = buildGraph(c, type);
    for (let s = 0; s < 3000; s++) {
      const ones = new Set();
      while (ones.size < 3) ones.add(Math.floor(rng() * 49));
      assert.equal(run(c, g, type, errOf(c, type, [...ones])), false, `${type} ${[...ones]}`);
    }
  }
});

test('random depolarizing samples at code capacity clear both syndromes', () => {
  const rng = mulberry32(11);
  for (const d of [3, 5, 7]) {
    const c = surfaceCode(d), gx = buildGraph(c, 'X'), gz = buildGraph(c, 'Z');
    for (let s = 0; s < 2000; s++) {
      const e = sampleErrors(c, 0.15, rng, 'depolarizing');
      run(c, gx, 'X', e);
      run(c, gz, 'Z', e);
    }
  }
});

function phenom(code, type, p, q, R, rng) {
  const acc = new Uint8Array(code.n), meas = [];
  for (let t = 0; t < R; t++) {
    const e = sampleErrors(code, p, rng, 'bitflip');
    for (let i = 0; i < code.n; i++) acc[i] ^= e.x[i];
    const s = syndrome(code, { x: acc, z: acc })[SYN[type]];
    if (t < R - 1) { const f = sampleMeasurementFlips(code, q, rng)[SYN[type]]; for (let k = 0; k < s.length; k++) s[k] ^= f[k]; }
    meas.push(s);
  }
  return { acc, events: detectionEvents(meas) };
}

test('space-time graph: projected correction clears the final syndrome', () => {
  const rng = mulberry32(5);
  for (const [code, type] of [[repetitionCode(5), 'X'], [surfaceCode(3), 'X'], [surfaceCode(5), 'Z'], [surfaceCode(7), 'X']]) {
    const R = code.d, g = buildGraph(code, type, R);
    assert.equal(g.nDet, R * code.checks[SYN[type]].length);
    for (let s = 0; s < 2000; s++) {
      const { acc, events } = phenom(code, type, 0.04, 0.04, R, rng);
      const corr = decode(g, events);
      const res = acc.map((b, i) => b ^ corr[i]);
      assert.ok(zeros(syndrome(code, { x: res, z: res })[SYN[type]]));
    }
  }
});

test('space-time graph: a lone measurement error needs no data correction', () => {
  const c = surfaceCode(5), g = buildGraph(c, 'X', 5), m = c.checks.Z.length;
  const ev = new Uint8Array(g.nDet);
  ev[1 * m + 3] = 1; ev[2 * m + 3] = 1;
  assert.ok(zeros(decode(g, ev)));
});

test('trace lists growth steps and does not change the correction', () => {
  const c = surfaceCode(5), g = buildGraph(c, 'X'), rng = mulberry32(9);
  for (let s = 0; s < 200; s++) {
    const syn = syndrome(c, sampleErrors(c, 0.12, rng, 'bitflip')).Z;
    const plain = decode(g, syn), t = decode(g, syn, { trace: true });
    assert.deepEqual([...t.correction], [...plain]);
    if (!zeros(syn)) assert.ok(t.steps.length >= 1);
    for (const st of t.steps) {
      assert.equal(st.cluster.length, g.N);
      assert.equal(st.support.length, g.edges.length);
      assert.ok(st.support.every(v => v >= 0 && v <= 2));
    }
  }
});
