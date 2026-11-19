import { test } from 'node:test';
import assert from 'node:assert/strict';
import { repetitionCode, surfaceCode } from '../../../../qec-in-practice/js/qec/codes.js';

const overlap = (a, b) => a.filter(i => b.includes(i)).length;
const key = s => [...s].sort((a, b) => a - b).join(',');

test('d=3 surface code supports equal the existing lesson (patch.js lines 3-4)', () => {
  const c = surfaceCode(3);
  assert.deepEqual(c.checks.X, [[0, 1, 3, 4], [4, 5, 7, 8], [2, 5], [3, 6]]);
  assert.deepEqual(c.checks.Z, [[1, 2, 4, 5], [3, 4, 6, 7], [0, 1], [7, 8]]);
  assert.deepEqual(c.logical.X, [0, 1, 2]);
  assert.deepEqual(c.logical.Z, [0, 3, 6]);
});

for (const d of [3, 5, 7]) {
  test(`surface code d=${d}: commutation, counts, logicals, coords`, () => {
    const c = surfaceCode(d);
    assert.equal(c.kind, 'surface');
    assert.equal(c.n, d * d);
    assert.equal(c.checks.X.length, (d * d - 1) / 2);
    assert.equal(c.checks.Z.length, (d * d - 1) / 2);
    for (const x of c.checks.X) for (const z of c.checks.Z) assert.equal(overlap(x, z) % 2, 0);
    for (const z of c.checks.Z) assert.equal(overlap(c.logical.X, z) % 2, 0);
    for (const x of c.checks.X) assert.equal(overlap(c.logical.Z, x) % 2, 0);
    assert.equal(overlap(c.logical.X, c.logical.Z) % 2, 1);
    assert.equal(c.logical.X.length, d);
    assert.equal(c.logical.Z.length, d);
    const all = [...c.checks.X, ...c.checks.Z].map(key);
    assert.equal(new Set(all).size, all.length);
    for (let i = 0; i < c.n; i++) assert.deepEqual(c.coords[i], [i % d, Math.floor(i / d)]);
    for (const t of ['X', 'Z']) {
      assert.equal(c.checkCoords[t].length, c.checks[t].length);
      c.checks[t].forEach((s, k) => {
        const cx = s.reduce((a, i) => a + c.coords[i][0], 0) / s.length;
        const cy = s.reduce((a, i) => a + c.coords[i][1], 0) / s.length;
        const [px, py] = c.checkCoords[t][k];
        assert.ok(Math.abs(px - cx) <= 0.5 && Math.abs(py - cy) <= 0.5);
      });
    }
    // every qubit is in 1 or 2 checks of each type
    for (const t of ['X', 'Z']) for (let q = 0; q < c.n; q++) {
      const k = c.checks[t].filter(s => s.includes(q)).length;
      assert.ok(k === 1 || k === 2);
    }
  });
}

test('repetition code', () => {
  const c = repetitionCode(5);
  assert.equal(c.kind, 'repetition');
  assert.equal(c.n, 5);
  assert.deepEqual(c.checks.Z, [[0, 1], [1, 2], [2, 3], [3, 4]]);
  assert.deepEqual(c.logical.X, [0, 1, 2, 3, 4]);
  assert.deepEqual(c.logical.Z, [0]);
  assert.equal(c.coords.length, 5);
  for (const z of c.checks.Z) assert.equal(overlap(c.logical.X, z) % 2, 0);
});
