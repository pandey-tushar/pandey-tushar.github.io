// Lesson 2 live: logical CNOT A->B between two rotated [[9,1,3]] patches, tableau-simulated.
// Check k of a round: patch b = k >> 3; (k & 7) < 4 is X_STABS[k & 3], else Z_STABS[k & 3].
import { Tableau, mulberry32 } from './stabsim.js';

export const X_STABS = [[0, 1, 3, 4], [4, 5, 7, 8], [2, 5], [3, 6]];
export const Z_STABS = [[1, 2, 4, 5], [3, 4, 6, 7], [0, 1], [7, 8]];
const X_L = [0, 1, 2];
const Z_L = [0, 3, 6];
// From qec/code913.py: syndrome bits in stabilizer order -> local qubit to flip (-1: none).
const Z_TABLE = { '0000': -1, '0010': 0, '1010': 1, '1000': 2, '0100': 3, '1100': 4, '0101': 7, '0001': 8 };
const X_TABLE = { '0000': -1, '1000': 0, '0010': 2, '1001': 3, '1100': 4, '0110': 5, '0001': 6, '0100': 7 };

export const CHECKS = [];
for (const b of [0, 1]) {
  for (const s of X_STABS) CHECKS.push({ X: s.map((i) => 9 * b + i) });
  for (const s of Z_STABS) CHECKS.push({ Z: s.map((i) => 9 * b + i) });
}

function gateList(basis) {
  const g = [];
  const add = (phase, gate, ...q) => g.push({ phase, gate, q });
  add('prepare', 'h', 0);
  for (const b of [0, 1]) {
    const P = `encode ${'AB'[b]}`, q = (i) => 9 * b + i;
    add(P, 'cx', q(0), q(1));
    add(P, 'cx', q(0), q(2));
    for (const i of [4, 5, 6, 7]) add(P, 'h', q(i));
    for (const t of [0, 1, 3]) add(P, 'cx', q(4), q(t));
    add(P, 'cx', q(5), q(2));
    add(P, 'cx', q(6), q(3));
    for (const t of [0, 1, 2, 3, 8]) add(P, 'cx', q(7), q(t));
  }
  for (let i = 0; i < 9; i++) add('transversal CNOT A→B', 'cx', i, 9 + i);
  if (basis === 'X') for (let q = 0; q < 18; q++) add('readout', 'h', q);
  return g;
}

// Greedy ASAP layering as in qec/spacetime.py: each phase starts above every layer used so far.
export function layers(basis = 'Z') {
  const out = [], last = new Map();
  let floor = 0, phase = null;
  for (const { phase: p, gate, q } of gateList(basis)) {
    if (p !== phase) {
      floor = last.size ? Math.max(...last.values()) + 1 : 0;
      phase = p;
    }
    const t = Math.max(floor, ...q.map((x) => (last.has(x) ? last.get(x) + 1 : 0)));
    q.forEach((x) => last.set(x, t));
    while (out.length <= t) out.push({ phase: p, gates: [] });
    out[t].gates.push({ gate, q });
  }
  return out;
}

// A patch's checks run in place only where they are stabilizers: from the round after its own encoder
// (its reference round for relative syndromes) through the round after the transversal CNOT.
// Rounds: per layer, 16 entries (0/1, or null for a check not running); null if none runs.
export const CHECK_START = ['encode A', 'encode B'].map((ph) => layers().findLastIndex((l) => l.phase === ph));
export const REF_LAYER = CHECK_START[1];
export const LAST_CHECK_LAYER = layers().findLastIndex((l) => l.phase.startsWith('transversal'));
const running = (t, k) => t >= CHECK_START[k >> 3] && t <= LAST_CHECK_LAYER;

const PAULI = ['x', 'y', 'z'];

function decode(bits, b, basis) {
  const [stabs, table, logical] = basis === 'Z' ? [Z_STABS, Z_TABLE, Z_L] : [X_STABS, X_TABLE, X_L];
  const local = bits.slice(9 * b, 9 * b + 9);
  const key = stabs.map((s) => s.reduce((a, i) => a ^ local[i], 0)).join('');
  if (!(key in table)) return null;
  if (table[key] >= 0) local[table[key]] ^= 1;
  return logical.reduce((a, i) => a ^ local[i], 0);
}

export function runShots({ shots, basis = 'Z', inject = null, p = 0, seed = 1 }) {
  const L = layers(basis);
  const rng = mulberry32(seed);
  const fire = L.map((_, t) => (running(t, 0) || running(t, 8)
    ? CHECKS.map((_, k) => (running(t, k) ? 0 : null)) : null));
  const out = [];
  let kept = 0, agree = 0;
  for (let n = 0; n < shots; n++) {
    const tab = new Tableau(18, rng);
    const rounds = [];
    const ref = new Array(16).fill(0);
    for (let t = 0; t < L.length; t++) {
      for (const { gate, q } of L[t].gates) {
        tab[gate](...q);
        if (p > 0) for (const x of q) if (rng() < p) tab[PAULI[Math.floor(rng() * 3)]](x);
      }
      rounds.push(fire[t] && CHECKS.map((spec, k) => {
        if (!running(t, k)) return null;
        const v = tab.measurePauli(spec);
        if (t === CHECK_START[k >> 3]) ref[k] = v;
        return v ^ ref[k];
      }));
      if (inject && inject.afterLayer === t) tab[inject.pauli.toLowerCase()](inject.qubit);
    }
    const bits = [];
    for (let q = 0; q < 18; q++) bits.push(tab.measureZ(q));
    const a = decode(bits, 0, basis), b = decode(bits, 1, basis);
    const logical = a === null || b === null ? null : [a, b];
    if (logical) { kept++; if (a === b) agree++; }
    rounds.forEach((row, t) => row && row.forEach((v, k) => { if (v !== null) fire[t][k] += v; }));
    out.push({ rounds, bits, logical });
  }
  return {
    shots: out,
    agree: kept ? agree / kept : 0,
    discard: shots ? (shots - kept) / shots : 0,
    checkRate: fire.map((row) => row && row.map((f) => (f === null ? null : shots ? f / shots : 0))),
  };
}
