// Pure helpers for the repetition-code and decoding pages, on top of the engine in ./qec/.
import { repetitionCode } from './qec/codes.js';
import { syndrome, detectionEvents, sampleErrors } from './qec/noise.js';
import { buildGraph, decode, logicalFailure } from './qec/decoder.js';

// Probability that more than half of d independent bits flip: the repetition code's
// logical error rate under majority vote (which the union-find decoder equals on a line).
export function repetitionCurve(d, p) {
  let s = 0, c = 1;
  for (let k = 0; k <= d; k++) {
    if (2 * k > d) s += c * p ** k * (1 - p) ** (d - k);
    c = c * (d - k) / (k + 1);
  }
  return s;
}

export const emptyError = code => ({ x: new Uint8Array(code.n), z: new Uint8Array(code.n) });
export const pauliAt = (e, q) => (e.x[q] ? (e.z[q] ? 'Y' : 'X') : (e.z[q] ? 'Z' : 'I'));
const NEXT = { I: [1, 0], X: [0, 1], Z: [1, 1], Y: [0, 0] };

// Names shown on the pages, counted from 0 as in the lessons: q0 on a line, c0 for the check between q0 and q1,
// (row, column) from the top left on a patch, so at d = 3 the qubit at (r, c) is q(3r + c) of lesson 1.
export const qubitName = i => `q${i}`;
export const repCheckName = k => `c${k}`;
export const rcName = (code, q) => `(${code.coords[q][1]}, ${code.coords[q][0]})`;

// Random errors for a decoder figure: drawn again until at least one qubit has an error, so there is something to decode.
export function sampleSomeErrors(code, p, rng, model) {
  for (;;) {
    const e = sampleErrors(code, p, rng, model);
    if (e.x.some(Boolean) || e.z.some(Boolean)) return e;
  }
}

export function cyclePauli(e, q) {
  const [x, z] = NEXT[pauliAt(e, q)], out = { x: e.x.slice(), z: e.z.slice() };
  out.x[q] = x; out.z[q] = z;
  return out;
}

// graphs keyed by error type: X errors are seen by Z checks, Z errors by X checks
export const graphsFor = code => ({ X: buildGraph(code, 'X'), Z: code.checks.X ? buildGraph(code, 'Z') : null });

export function decodeError(code, err, graphs, { trace = false } = {}) {
  const syn = syndrome(code, err), traces = { X: null, Z: null }, correction = emptyError(code);
  for (const [t, part, s] of [['X', 'x', syn.Z], ['Z', 'z', syn.X]]) {
    if (!graphs[t]) continue;
    const r = decode(graphs[t], s, { trace });
    correction[part] = trace ? r.correction : r;
    if (trace) traces[t] = r.steps;
  }
  const residual = { x: err.x.map((b, i) => b ^ correction.x[i]), z: err.z.map((b, i) => b ^ correction.z[i]) };
  return { syndrome: syn, correction, residual, failure: logicalFailure(code, err, correction), traces };
}

// Drawable growth frames. Frame 0 is the syndrome alone; frame k shows the state after growth round k.
// halves: {edge, full} or {edge, full: false, from} for an edge grown halfway out of node `from`.
// clusters: {root, nodes, defects, boundary, neutral}; odd counts clusters still growing.
export function frames(g, defects, steps) {
  const out = [], side = new Int32Array(g.edges.length).fill(-1);
  let prev = new Int32Array(g.N).fill(-1);
  for (let v = 0; v < g.nDet; v++) if (defects[v]) prev[v] = v;
  out.push(summary(g, defects, prev, null, side));
  let last = new Uint8Array(g.edges.length);
  for (const st of steps) {
    const grown = new Set(st.grown);
    for (let e = 0; e < g.edges.length; e++) {
      if (last[e] === 0 && st.support[e] === 1) {
        const u = g.eu[e];
        side[e] = prev[u] >= 0 && grown.has(prev[u]) ? u : g.ev[e];
      }
    }
    out.push(summary(g, defects, st.cluster, st.support, side));
    prev = st.cluster; last = st.support;
  }
  return out;
}

function summary(g, defects, cluster, support, side) {
  const by = new Map();
  for (let v = 0; v < g.N; v++) {
    const r = cluster[v];
    if (r < 0) continue;
    if (!by.has(r)) by.set(r, { root: r, nodes: [], defects: 0, boundary: false });
    const c = by.get(r);
    c.nodes.push(v);
    if (v >= g.nDet) c.boundary = true; else if (defects[v]) c.defects++;
  }
  const clusters = [...by.values()];
  for (const c of clusters) c.neutral = c.boundary || c.defects % 2 === 0;
  const halves = [];
  if (support) for (let e = 0; e < support.length; e++) {
    if (support[e] === 2) halves.push({ edge: e, full: true });
    else if (support[e] === 1) halves.push({ edge: e, full: false, from: side[e] });
  }
  return { clusters, halves, odd: clusters.filter(c => !c.neutral).length };
}

// Position of a graph node in code coordinates: a check at its plaquette centre, a boundary node
// mirrored through the data qubit of its one edge, just outside the code.
export function nodePoint(code, g, v) {
  const t = g.type === 'X' ? 'Z' : 'X';
  if (v < g.nDet) return code.checkCoords[t][g.nodes[v].check];
  const e = g.edges.findIndex(([a, b]) => a === v || b === v);
  const [a, b, q] = g.edges[e], other = a === v ? b : a;
  const c = code.checkCoords[t][g.nodes[other].check], [qx, qy] = code.coords[q];
  return [2 * qx - c[0], 2 * qy - c[1]];
}

// X errors on the left (d+1)/2 qubits of the top row. explore.test.mjs checks that the decoder answers with
// the other (d-1)/2 qubits of that row, so error and correction together are the logical X.
export function foolingPreset(d) {
  return { type: 'X', qubits: [...Array((d + 1) / 2).keys()] };
}

// A five-qubit repetition code measured over four rounds, the last one perfect, with one data error
// (qubit 1, from round 2 on) and/or one wrong reading (check 4 in round 2), decoded on the space-time graph.
export function measurementDemo(which, d = 5, rounds = 4) {
  const code = repetitionCode(d), m = code.checks.Z.length;
  const dataError = new Uint8Array(code.n), measured = [], flips = [];
  for (let t = 0; t < rounds; t++) {
    if (t === 1 && which !== 'measure') dataError[1] = 1;
    const s = syndrome(code, { x: dataError, z: dataError }).Z, f = new Uint8Array(m);
    if (t === 1 && which !== 'data') f[3] = 1;
    for (let c = 0; c < m; c++) s[c] ^= f[c];
    measured.push(s); flips.push(f);
  }
  const events = detectionEvents(measured);
  const correction = decode(buildGraph(code, 'X', rounds), events);
  return { code, rounds, m, measured, flips, events, dataError, correction };
}
