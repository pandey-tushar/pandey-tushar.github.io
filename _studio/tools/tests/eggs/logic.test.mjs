// logical/logic.js: the rounds of "Beat the decoder", drawn and judged by the engine in qec-in-practice/js/qec/.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mulberry32 } from '../../../../qec-in-practice/js/stabsim.js';
import { surfaceCode } from '../../../../qec-in-practice/js/qec/codes.js';
import { sampleErrors, syndrome } from '../../../../qec-in-practice/js/qec/noise.js';
import { buildGraph, decode, logicalFailure } from '../../../../qec-in-practice/js/qec/decoder.js';
import { LEVELS, code, round, restores, unexplained } from '../../../../logical/logic.js';

const ref = surfaceCode(5), g = buildGraph(ref, 'X');
const none = () => new Uint8Array(ref.n);
const xor = (a, b) => a.map((v, i) => v ^ b[i]);
const zero = s => s.every(b => b === 0);

test('a distance 5 surface code and three error rates, low to high', () => {
  assert.equal(code.d, 5);
  assert.deepEqual(code.checks, ref.checks);
  assert.equal(LEVELS.length, 3);
  for (let i = 1; i < 3; i++) assert.ok(LEVELS[i].p > LEVELS[i - 1].p);
  for (const l of LEVELS) assert.match(l.label, /^\d+%$/);
});

test('a round is the engine sample for its seed, so it replays', () => {
  for (let lv = 0; lv < 3; lv++) for (let seed = 1; seed <= 300; seed++) {
    const r = round(seed, lv), again = round(seed, lv);
    assert.deepEqual(r.err, again.err);
    // the engine draw: bit flips at rate p from mulberry32(seed), drawn again until a check fires
    const rng = mulberry32(seed);
    let e;
    do e = sampleErrors(ref, LEVELS[lv].p, rng); while (zero(syndrome(ref, e).Z));
    assert.deepEqual(r.err, e.x);
    assert.deepEqual(r.fired, syndrome(ref, e).Z);
    assert.deepEqual(r.decoder, decode(g, syndrome(ref, e).Z));
  }
  assert.notDeepEqual(round(1, 2).err, round(2, 2).err);
});

test('restores: no check left lit and the logical bit unchanged, as the engine judges', () => {
  let decoderFailed = 0, rounds = 0;
  for (let lv = 0; lv < 3; lv++) for (let seed = 1; seed <= 400; seed++) {
    const { err, decoder } = round(seed, lv);
    const e = { x: err, z: none() };
    rounds++;
    assert.ok(zero(syndrome(ref, { x: xor(err, decoder), z: none() }).Z));
    assert.equal(restores(err, decoder), !logicalFailure(ref, e, { x: decoder }).x);
    if (!restores(err, decoder)) decoderFailed++;
    assert.equal(restores(err, err), true, 'undoing the errors exactly restores');
    // the errors times a logical X: every check quiet, the stored bit flipped
    const wrong = err.slice();
    for (const q of ref.logical.X) wrong[q] ^= 1;
    assert.ok(zero(syndrome(ref, { x: xor(err, wrong), z: none() }).Z));
    assert.equal(restores(err, wrong), false);
    assert.equal(restores(err, none()), false, 'doing nothing leaves the fired checks lit');
  }
  assert.ok(decoderFailed > 0 && decoderFailed < rounds, `decoder failed ${decoderFailed} of ${rounds}`);
});

test('unexplained: the checks still lit once the marked qubits are flipped back', () => {
  for (let seed = 1; seed <= 50; seed++) {
    const { err, fired } = round(seed, 1);
    assert.deepEqual(unexplained(fired, none()), fired);
    assert.ok(zero(unexplained(fired, err)));
    const one = none(); one[12] = 1;
    assert.deepEqual(unexplained(fired, one), xor(fired, syndrome(ref, { x: one, z: none() }).Z));
  }
});
