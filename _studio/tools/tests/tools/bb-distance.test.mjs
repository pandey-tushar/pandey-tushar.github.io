import { test } from 'node:test';
import assert from 'node:assert/strict';
import { PRESETS, parsePoly, buildCode, packRows, rankGF2 } from '../../../../tools/js/bb-math.js';
import { createSearch } from '../../../../tools/js/bb-distance.js';

const preset = name => {
  const p = PRESETS.find(q => q.name === name);
  return buildCode(p.l, p.m, parsePoly(p.A, p.l, p.m).terms, parsePoly(p.B, p.l, p.m).terms);
};
const dot = (row, s) => row.filter(c => s.has(c)).length % 2;

// z of type Z must commute with every X check (H_X z = 0) and lie outside the row space of H_Z; type X the other way.
function assertLogical(c, best) {
  const s = new Set(best.support);
  assert.equal(s.size, best.weight);
  assert.ok(best.support.every(q => Number.isInteger(q) && q >= 0 && q < c.n));
  const [commuteWith, stab] = best.type === 'Z' ? [c.hx, c.hz] : [c.hz, c.hx];
  assert.ok(commuteWith.every(row => dot(row, s) === 0), 'commutes with every check of the other type');
  const r0 = rankGF2(packRows(stab, c.n)), r1 = rankGF2(packRows([...stab, best.support], c.n));
  assert.equal(r1, r0 + 1, 'not in the stabilizer');
}

test('[[72,12,6]]: the seeded search reaches 6, never reports less, and returns a true logical', () => {
  const c = preset('[[72,12,6]]');
  const s = createSearch(c, 1);
  for (let i = 0; i < 400 && !(s.best && s.best.weight <= 6); i++) s.step(10);
  assert.equal(s.best.weight, 6);
  assert.ok(s.history.every(h => h.weight >= 6));
  assertLogical(c, s.best);
  s.step(200);                       // more work never goes below the true distance
  assert.equal(s.best.weight, 6);
  assertLogical(c, s.best);
  for (const h of s.history) assertLogical(c, h);
});

test('the search is reproducible from its seed', () => {
  const c = preset('[[144,12,12]]');
  const a = createSearch(c, 42), b = createSearch(c, 42), d = createSearch(c, 43);
  a.step(30); b.step(10); b.step(20); d.step(30);
  assert.deepEqual(a.history, b.history);
  assert.equal(a.iterations, 30);
  assert.notDeepEqual(a.history, d.history);
});

test('[[90,8,10]] and [[108,8,10]]: bound reaches the paper value and every record is a logical', () => {
  for (const name of ['[[90,8,10]]', '[[108,8,10]]']) {
    const c = preset(name), s = createSearch(c, 1);
    for (let i = 0; i < 300 && !(s.best && s.best.weight <= 10); i++) s.step(10);
    assert.equal(s.best.weight, 10, name);
    for (const h of s.history) { assert.ok(h.weight >= 10); assertLogical(c, h); }
  }
});

test('a code with k = 0 has no logical to find', () => {
  // A = 1 is invertible, so ker A = 0 and k = 2 dim(ker A cap ker B) = 0
  const c = buildCode(3, 3, parsePoly('1', 3, 3).terms, parsePoly('1 + y', 3, 3).terms);
  const s = createSearch(c, 1);
  assert.equal(s.k, 0);
  s.step(5);
  assert.equal(s.best, null);
});
