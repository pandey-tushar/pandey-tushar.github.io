import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mulberry32 } from '../../../../qec-in-practice/js/stabsim.js';
import { repetitionCode, surfaceCode } from '../../../../qec-in-practice/js/qec/codes.js';
import { sampleErrors, syndrome } from '../../../../qec-in-practice/js/qec/noise.js';
import { buildGraph } from '../../../../qec-in-practice/js/qec/decoder.js';
import { estimate } from '../../../../qec-in-practice/js/qec/montecarlo.js';
import {
  repetitionCurve, pauliAt, cyclePauli, graphsFor, decodeError, frames, nodePoint,
  foolingPreset, measurementDemo, emptyError,
} from '../../../../qec-in-practice/js/explore-logic.js';

const zeros = a => a.every(b => b === 0);

test('repetition curve: closed form values', () => {
  assert.equal(repetitionCurve(1, 0.3), 0.3);
  assert.ok(Math.abs(repetitionCurve(3, 0.1) - 0.028) < 1e-12);
  for (const d of [1, 3, 5, 7]) {
    assert.ok(Math.abs(repetitionCurve(d, 0.5) - 0.5) < 1e-12);
    assert.equal(repetitionCurve(d, 0), 0);
    assert.ok(Math.abs(repetitionCurve(d, 1) - 1) < 1e-12);
  }
  // below 1/2 more qubits help, above it they hurt
  assert.ok(repetitionCurve(7, 0.2) < repetitionCurve(5, 0.2) && repetitionCurve(5, 0.2) < repetitionCurve(3, 0.2));
  assert.ok(repetitionCurve(7, 0.7) > repetitionCurve(5, 0.7));
});

test('repetition curve matches the engine Monte Carlo within sampling error', () => {
  let i = 0;
  for (const d of [1, 3, 5, 7]) for (const p of [0.05, 0.2, 0.45, 0.7]) {
    const shots = 20000, r = estimate({ kind: 'repetition', d, p, shots, seed: 101 + i++ });
    const a = repetitionCurve(d, p), sig = Math.sqrt(a * (1 - a) / shots);
    assert.ok(Math.abs(r.rate - a) <= 4 * sig + 1e-9, `d=${d} p=${p}: ${r.rate} vs ${a}`);
  }
});

test('Pauli cycle I -> X -> Z -> Y -> I, one qubit at a time', () => {
  const c = surfaceCode(3);
  let e = emptyError(c);
  const seen = [];
  for (let k = 0; k < 5; k++) { seen.push(pauliAt(e, 4)); e = cyclePauli(e, 4); }
  assert.deepEqual(seen, ['I', 'X', 'Z', 'Y', 'I']);
  e = cyclePauli(cyclePauli(emptyError(c), 2), 2);
  assert.equal(pauliAt(e, 2), 'Z');
  for (let q = 0; q < c.n; q++) if (q !== 2) assert.equal(pauliAt(e, q), 'I');
});

test('after the decoder correction the syndrome is always empty', () => {
  const rng = mulberry32(3);
  for (const d of [3, 5, 7]) {
    const c = surfaceCode(d), gs = graphsFor(c);
    for (let s = 0; s < 1500; s++) {
      const e = sampleErrors(c, 0.03 + 0.25 * rng(), rng, s % 2 ? 'depolarizing' : 'bitflip');
      const r = decodeError(c, e, gs, { trace: s % 10 === 0 });
      const syn = syndrome(c, r.residual);
      assert.ok(zeros(syn.X) && zeros(syn.Z), `surface d=${d} sample ${s}`);
    }
  }
  for (const d of [3, 5, 7]) {
    const c = repetitionCode(d), gs = graphsFor(c);
    assert.equal(gs.Z, null);
    for (let m = 0; m < 2 ** d; m++) {
      const e = emptyError(c);
      for (let i = 0; i < d; i++) e.x[i] = (m >> i) & 1;
      const r = decodeError(c, e, gs);
      assert.ok(zeros(syndrome(c, r.residual).Z));
      // the residual is all zeros or all ones: the logical bit kept or flipped
      const w = r.residual.x.reduce((a, b) => a + b, 0);
      assert.ok(w === 0 || w === d);
      assert.equal(r.failure.x, w === d);
      // majority: fails exactly when more than half are flipped
      const k = e.x.reduce((a, b) => a + b, 0);
      assert.equal(r.failure.x, 2 * k > d, `rep d=${d} pattern ${m}`);
    }
  }
});

test('residual is a stabilizer or a logical, and failure says which', () => {
  const rng = mulberry32(8);
  const c = surfaceCode(5), gs = graphsFor(c);
  for (let s = 0; s < 500; s++) {
    const e = sampleErrors(c, 0.15, rng, 'depolarizing');
    const r = decodeError(c, e, gs);
    let ox = 0, oz = 0;
    for (const i of c.logical.Z) ox ^= r.residual.x[i];
    for (const i of c.logical.X) oz ^= r.residual.z[i];
    assert.equal(r.failure.x, ox === 1);
    assert.equal(r.failure.z, oz === 1);
  }
});

test('fooling presets: weight (d+1)/2 on one row, and the decoder completes them into a logical X', () => {
  for (const d of [3, 5, 7]) {
    const c = surfaceCode(d), pre = foolingPreset(d);
    assert.equal(pre.type, 'X');
    assert.equal(pre.qubits.length, (d + 1) / 2);
    const row = Math.floor(pre.qubits[0] / d);
    assert.ok(pre.qubits.every(q => Math.floor(q / d) === row));
    const e = emptyError(c);
    for (const q of pre.qubits) e.x[q] = 1;
    const r = decodeError(c, e, graphsFor(c), { trace: true });
    assert.equal(r.failure.x, true, `d=${d}`);
    assert.equal(r.failure.z, false);
    // the guess is the rest of the row: lighter than the true error, same syndrome
    const guess = [...r.correction.x.keys()].filter(i => r.correction.x[i]);
    const rest = [...Array(d).keys()].map(j => row * d + j).filter(q => !pre.qubits.includes(q));
    assert.deepEqual(guess, rest);
    assert.ok(guess.length < pre.qubits.length);
    assert.deepEqual([...syndrome(c, { x: r.correction.x, z: r.correction.z }).Z], [...syndrome(c, e).Z]);
  }
});

test('trace frames: half-edges add up to the support, clusters end neutral', () => {
  const rng = mulberry32(21);
  for (const d of [3, 5, 7]) {
    const c = surfaceCode(d), gs = graphsFor(c);
    for (let s = 0; s < 300; s++) {
      const e = sampleErrors(c, 0.12, rng, 'depolarizing');
      const r = decodeError(c, e, gs, { trace: true });
      for (const t of ['X', 'Z']) {
        const g = gs[t], syn = syndrome(c, e)[t === 'X' ? 'Z' : 'X'];
        const fr = frames(g, syn, r.traces[t]);
        assert.equal(fr.length, r.traces[t].length + 1);
        // frame 0: each defect is its own odd cluster, nothing grown
        assert.equal(fr[0].halves.length, 0);
        assert.equal(fr[0].clusters.length, syn.reduce((a, b) => a + b, 0));
        fr.forEach((f, k) => {
          const sup = k ? r.traces[t][k - 1].support : new Uint8Array(g.edges.length);
          let want = 0; for (const v of sup) want += v;
          let got = 0; for (const h of f.halves) got += h.full ? 2 : 1;
          assert.equal(got, want);
          for (const h of f.halves) if (!h.full) {
            const [u, v] = g.edges[h.edge];
            assert.ok(h.from === u || h.from === v);
            assert.ok(h.from < g.nDet, 'a half-edge grows from a check, never from the boundary');
          }
        });
        const last = fr[fr.length - 1];
        assert.equal(last.odd, 0);
        assert.ok(last.clusters.every(cl => cl.neutral && (cl.defects % 2 === 0 || cl.boundary)));
        if (fr.length > 1) assert.ok(fr[fr.length - 2].odd > 0);
      }
    }
  }
});

test('node points: checks at plaquette centres, boundary nodes mirrored through their qubit', () => {
  const c = surfaceCode(3), g = buildGraph(c, 'X');
  for (const [u, v, q] of g.edges) {
    const a = nodePoint(c, g, u), b = nodePoint(c, g, v), [qx, qy] = c.coords[q];
    assert.ok(Math.abs((a[0] + b[0]) / 2 - qx) < 1e-12 && Math.abs((a[1] + b[1]) / 2 - qy) < 1e-12);
  }
  assert.deepEqual(nodePoint(c, g, 0), c.checkCoords.Z[0]);
  const r = repetitionCode(5), gr = buildGraph(r, 'X');
  for (const [u, v, q] of gr.edges) assert.equal((nodePoint(r, gr, u)[0] + nodePoint(r, gr, v)[0]) / 2, q);
});

test('measurement demo: a data error is two events in space, a measurement error two events in time', () => {
  const data = measurementDemo('data'), meas = measurementDemo('measure'), both = measurementDemo('both');
  const m = data.m, ev = x => [...x.events.keys()].filter(i => x.events[i]).map(i => [Math.floor(i / m), i % m]);
  const d1 = ev(data), m1 = ev(meas);
  assert.equal(d1.length, 2);
  assert.equal(d1[0][0], d1[1][0]);
  assert.equal(Math.abs(d1[0][1] - d1[1][1]), 1);
  assert.equal(m1.length, 2);
  assert.equal(m1[0][1], m1[1][1]);
  assert.equal(m1[1][0] - m1[0][0], 1);
  assert.ok(zeros(meas.correction), 'a lone measurement error needs no data correction');
  assert.deepEqual([...data.correction], [...data.dataError]);
  assert.equal(ev(both).length, 4);
  for (const x of [data, meas, both]) {
    assert.ok(x.measured.length === x.rounds);
    assert.ok(zeros(x.flips[x.rounds - 1]), 'the last round is read perfectly');
    const res = x.dataError.map((b, i) => b ^ x.correction[i]);
    assert.ok(zeros(syndrome(x.code, { x: res, z: res }).Z));
  }
});
