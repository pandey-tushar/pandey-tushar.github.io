// Lattice surgery layout and simulation (qec-in-practice/js/surgery.js).
//   node --test _studio/tools/tests/surgery/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  N, A, B, SEAM, COORD, PATCH_CHECKS, MERGE_CHECKS, SPLIT_CHECKS, PARITY_CHECKS, LOGICAL,
  commute, runShot, runShots, INPUTS,
} from '../../../../qec-in-practice/js/surgery.js';

const sym = (s, t) => new Set([...s].filter((x) => !t.has(x)).concat([...t].filter((x) => !s.has(x))));
const supp = (c) => ({ X: new Set(c.type === 'X' ? c.q : []), Z: new Set(c.type === 'Z' ? c.q : []) });
const ZA = { type: 'Z', q: LOGICAL.ZA }, ZB = { type: 'Z', q: LOGICAL.ZB };
const XA = { type: 'X', q: LOGICAL.XA }, XB = { type: 'X', q: LOGICAL.XB };
const SIGN = { 0: 1, 1: -1, '+': 1, '-': -1 };
const ref = JSON.parse(readFileSync(new URL('./reference.json', import.meta.url), 'utf8'));

// GF(2) rank of Pauli supports (as 2N-bit rows).
function rank(checks) {
  const rows = checks.map((c) => {
    let v = 0n;
    for (const q of c.q) v |= 1n << BigInt(c.type === 'X' ? q : N + q);
    return v;
  });
  let r = 0;
  for (let bit = 0; bit < 2 * N; bit++) {
    const m = 1n << BigInt(bit);
    const p = rows.findIndex((v, i) => i >= r && (v & m));
    if (p < 0) continue;
    [rows[r], rows[p]] = [rows[p], rows[r]];
    for (let i = 0; i < rows.length; i++) if (i !== r && (rows[i] & m)) rows[i] ^= rows[r];
    r++;
  }
  return r;
}

test('layout: 21 qubits, 9 per patch and a seam column of 3 between them', () => {
  assert.equal(N, 21);
  assert.deepEqual(A, [0, 1, 2, 3, 4, 5, 6, 7, 8]);
  assert.deepEqual(B, [9, 10, 11, 12, 13, 14, 15, 16, 17]);
  assert.deepEqual(SEAM, [18, 19, 20]);
  assert.equal(COORD.length, N);
  for (const q of SEAM) assert.equal(COORD[q][0], 3);
  // every 4-body check sits on a unit square of the grid, every 2-body one on an edge
  for (const c of [...PATCH_CHECKS, ...MERGE_CHECKS]) {
    const xs = c.q.map((q) => COORD[q][0]), ys = c.q.map((q) => COORD[q][1]);
    assert.ok(Math.max(...xs) - Math.min(...xs) <= 1 && Math.max(...ys) - Math.min(...ys) <= 1, c.id);
  }
});

for (const [name, checks, n] of [['start', PATCH_CHECKS, 16], ['merge', MERGE_CHECKS, 20], ['split', SPLIT_CHECKS, 16]]) {
  test(`${name}: ${n} independent checks that commute pairwise`, () => {
    assert.equal(checks.length, n);
    for (const c of checks) for (const d of checks) assert.ok(commute(c, d), `${c.id} vs ${d.id}`);
    assert.equal(rank(checks), n);
  });
}

test('the original patch checks are 4 X and 4 Z per patch, as in patch.js', () => {
  assert.deepEqual(PATCH_CHECKS.filter((c) => c.q.every((q) => q < 9)).map((c) => `${c.type}${c.q}`).sort(),
    ['X0,1,3,4', 'X2,5', 'X3,6', 'X4,5,7,8', 'Z0,1', 'Z1,2,4,5', 'Z3,4,6,7', 'Z7,8']);
  assert.deepEqual(SPLIT_CHECKS.map((c) => c.id), PATCH_CHECKS.map((c) => c.id));
});

test('merge drops the two facing X boundary checks and adds six seam checks', () => {
  const ids = new Set(MERGE_CHECKS.map((c) => c.id));
  const dropped = PATCH_CHECKS.filter((c) => !ids.has(c.id)).map((c) => `${c.type}${c.q}`);
  assert.deepEqual(dropped.sort(), ['X12,15', 'X2,5']);
  const seam = MERGE_CHECKS.filter((c) => c.q.some((q) => q >= 18));
  assert.equal(seam.length, 6);
});

test('merged checks commute with Z_L(A) Z_L(B); X_L(A) X_L(B) survives only with X on the top seam qubit', () => {
  for (const c of MERGE_CHECKS) assert.ok(commute(c, { type: 'Z', q: [...LOGICAL.ZA, ...LOGICAL.ZB] }), c.id);
  // X_L(A) X_L(B) alone does not survive the merge; with the top seam qubit it does
  const xx = { type: 'X', q: [...LOGICAL.XA, ...LOGICAL.XB] };
  assert.ok(MERGE_CHECKS.some((c) => !commute(c, xx)));
  const xxs = { type: 'X', q: [...LOGICAL.XA, SEAM[0], ...LOGICAL.XB] };
  for (const c of MERGE_CHECKS) assert.ok(commute(c, xxs), c.id);
});

test('product of the four seam Z checks = Z_L(A) Z_L(B) times the four Z checks of A (GF(2) supports)', () => {
  const named = MERGE_CHECKS.filter((c) => PARITY_CHECKS.includes(c.id));
  assert.equal(named.length, 4);
  assert.ok(named.every((c) => c.type === 'Z' && c.q.some((q) => SEAM.includes(q))));
  let lhs = new Set();
  for (const c of named) lhs = sym(lhs, new Set(c.q));
  let rhs = sym(new Set(LOGICAL.ZA), new Set(LOGICAL.ZB));
  for (const c of PATCH_CHECKS.filter((c) => c.type === 'Z' && c.q.every((q) => q < 9))) rhs = sym(rhs, new Set(c.q));
  assert.deepEqual([...lhs].sort((a, b) => a - b), [...rhs].sort((a, b) => a - b));
  assert.deepEqual([...lhs].sort((a, b) => a - b), [2, 5, 8, 9, 12, 15]);
});

test('any column carries Z_L: B right column = Z_L(B) times the four Z checks of B (the figure draws it there)', () => {
  let s = new Set(LOGICAL.ZB);
  for (const c of PATCH_CHECKS.filter((c) => c.patch === 'B' && c.type === 'Z')) s = sym(s, new Set(c.q));
  assert.deepEqual([...s].sort((a, b) => a - b), [11, 14, 17]);
});

test('the dual merge (essay claim): stacking A above B with a seam row in |0> measures X_L(A) X_L(B)', () => {
  // A rows 0..2, seam row 3 (18, 19, 20), B rows 4..6; A's bottom and B's top Z edges face each other.
  const X = (...q) => ({ type: 'X', q }), Z = (...q) => ({ type: 'Z', q });
  const facing = ['Z7,8', 'Z9,10'];
  const kept = PATCH_CHECKS.filter((c) => !facing.includes(`${c.type}${c.q}`));
  assert.equal(kept.length, 14);
  const seamX = [X(6, 7, 18, 19), X(19, 20, 10, 11), X(18, 9), X(8, 20)];
  const seamZ = [Z(7, 8, 19, 20), Z(18, 19, 9, 10)];
  const merged = [...kept, ...seamX, ...seamZ];
  for (const c of merged) for (const d of merged) assert.ok(commute(c, d));
  assert.equal(rank(merged), 20);
  let lhs = new Set();
  for (const c of seamX) lhs = sym(lhs, new Set(c.q));
  let rhs = sym(new Set(LOGICAL.XA), new Set(LOGICAL.XB));
  for (const c of PATCH_CHECKS.filter((c) => c.patch === 'A' && c.type === 'X')) rhs = sym(rhs, new Set(c.q));
  assert.deepEqual([...lhs].sort((a, b) => a - b), [...rhs].sort((a, b) => a - b));
  // with the seam in |0>, each seam X check is random, the seam Z checks are old edge checks times Z on the seam
  for (const c of seamX) assert.ok(c.q.some((q) => q >= 18));
});

test('after the merge of |+>|+>: neither Z_L has a value, their product does', () => {
  for (let seed = 1; seed <= 20; seed++) {
    const s = runShot({ a: '+', b: '+', basis: 'Z', seed });
    const L = s.stages[1].logicals;
    assert.equal(L.ZA, 0);
    assert.equal(L.ZB, 0);
    assert.equal(L.ZZ, s.parity);
    assert.equal(s.stages[0].logicals.ZZ, 0);
    assert.equal(s.stages[0].logicals.XX, 1);
    assert.equal(s.stages[3].logicals.XX, 1);
  }
});

test('logical operators commute with their own patch checks and anticommute in pairs', () => {
  for (const L of [ZA, ZB, XA, XB]) for (const c of PATCH_CHECKS) assert.ok(commute(L, c));
  assert.ok(!commute(ZA, XA) && !commute(ZB, XB) && commute(ZA, XB) && commute(XA, ZB));
});

test('one shot is reproducible from its seed', () => {
  const a = runShot({ a: '+', b: '+', basis: 'Z', seed: 7 });
  const b = runShot({ a: '+', b: '+', basis: 'Z', seed: 7 });
  assert.deepEqual(a, b);
  assert.equal(a.stages.length, 4);
  assert.deepEqual(a.stages.map((s) => s.name), ['start', 'merge', 'split', 'readout']);
});

test('start: every patch check holds; merge: patch Z checks still hold, seam X checks hold', () => {
  for (const seed of [1, 2, 3, 4, 5]) {
    const s = runShot({ a: '+', b: '0', basis: 'Z', seed });
    assert.ok(s.stages[0].checks.every((c) => c.value === 1));
    const m = s.stages[1].checks;
    for (const c of m) {
      if (PARITY_CHECKS.includes(c.id)) assert.ok(c.value === 1 || c.value === -1);
      else assert.equal(c.value, 1, c.id);
    }
    // readout stage, after the frame: every check holds again
    assert.ok(s.stages[3].checks.every((c) => c.value === 1));
  }
});

test('split: the restored edge checks read what the frame rule predicts from the seam outcomes', () => {
  let flips = 0;
  for (let seed = 1; seed <= 300; seed++) {
    const s = runShot({ a: '+', b: '1', basis: 'Z', seed });
    const v = Object.fromEntries(s.stages[2].checks.map((c) => [c.id, c.value]));
    assert.equal(v['A.X(A2,A5)'], s.frame.aEdge);
    assert.equal(v['B.X(B3,B6)'], s.frame.bEdge);
    for (const c of s.stages[2].checks) if (!['A.X(A2,A5)', 'B.X(B3,B6)'].includes(c.id)) assert.equal(c.value, 1, c.id);
    if (s.frame.aEdge === -1) flips++;
  }
  assert.ok(flips > 100 && flips < 200, `${flips}`);
});

for (const basis of ['Z', 'X']) {
  test(`2000 shots for all 16 input pairs, read out in ${basis}`, () => {
    for (const a of INPUTS) for (const b of INPUTS) {
      let plus = 0;
      for (let seed = 1; seed <= 2000; seed++) {
        const s = runShot({ a, b, basis, seed: seed * 7919 + 13, snapshots: false });
        if (s.parity === 1) plus++;
        if (basis === 'Z') {
          // the readout always agrees with the reported parity
          assert.equal(s.readout.A * s.readout.B, s.parity, `${a}${b} seed ${seed}`);
          if ('01'.includes(a)) assert.equal(s.readout.A, SIGN[a]);
          if ('01'.includes(b)) assert.equal(s.readout.B, SIGN[b]);
        } else if ('+-'.includes(a) && '+-'.includes(b)) {
          // X_L(A) X_L(B) commutes with the measured Z_L(A) Z_L(B): with the frame it is kept
          assert.equal(s.readout.A * s.readout.B, SIGN[a] * SIGN[b], `${a}${b} seed ${seed}`);
        }
      }
      if ('01'.includes(a) && '01'.includes(b)) assert.equal(plus, SIGN[a] * SIGN[b] === 1 ? 2000 : 0, `${a}${b}`);
      else assert.ok(plus > 900 && plus < 1100, `${a}${b}: ${plus} of 2000 gave +1`);
    }
  });
}

test('without the frame, X_L(A) X_L(B) is wrong in about half the shots (the frame is needed)', () => {
  let bad = 0;
  for (let seed = 1; seed <= 2000; seed++) {
    const s = runShot({ a: '+', b: '+', basis: 'X', seed, frame: false, snapshots: false });
    if (s.readout.A * s.readout.B !== 1) bad++;
  }
  assert.ok(bad > 900 && bad < 1100, `${bad}`);
});

test('|+>|+> : the ZZ outcome is 50/50 and the two Z readouts always agree with it (a Bell pair)', () => {
  const t = runShots({ a: '+', b: '+', basis: 'Z', shots: 2000, seed: 99 });
  assert.equal(t.shots, 2000);
  assert.equal(t.agree, 2000);
  assert.ok(t.table['+1']['+1'] > 900 && t.table['-1']['-1'] > 900);
  assert.equal(t.table['+1']['-1'] + t.table['-1']['+1'], 0);
  const x = runShots({ a: '+', b: '+', basis: 'X', shots: 2000, seed: 99 });
  assert.equal(x.table['+1']['-1'] + x.table['-1']['-1'], 0);
});

test('agrees with the stim reference on every deterministic outcome', () => {
  assert.equal(ref.cases.length, 16);
  for (const r of ref.cases) {
    const det = '01'.includes(r.a) && '01'.includes(r.b);
    assert.equal(r.parity_deterministic, det ? SIGN[r.a] * SIGN[r.b] : null, `${r.a}${r.b}`);
    assert.equal(r.z_readout_agrees, 1);
    if ('+-'.includes(r.a) && '+-'.includes(r.b)) assert.equal(r.xx_after, SIGN[r.a] * SIGN[r.b]);
    for (let seed = 1; seed <= 50; seed++) {
      const s = runShot({ a: r.a, b: r.b, basis: 'Z', seed, snapshots: false });
      if (r.parity_deterministic !== null) assert.equal(s.parity, r.parity_deterministic);
    }
  }
});
