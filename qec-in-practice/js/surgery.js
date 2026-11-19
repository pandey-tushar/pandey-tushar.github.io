// Lattice surgery between two distance-3 rotated surface code patches, as data plus a tableau run.
// Pure logic, no DOM. Qubits: A data 0..8, B data 9..17 (both row-major as in patch.js), seam 18..20
// (rows 0..2). On the merged 7 x 3 grid A takes columns 0..2, the seam column 3, B columns 4..6.
// A's right edge and B's left edge carry the weight-2 X checks, so they face each other across the seam;
// Z_L of each patch is a column, parallel to that edge, and the merge measures Z_L(A) Z_L(B).
import { Tableau, mulberry32 } from './stabsim.js';
import { X_STABS, Z_STABS } from './patch.js';

export const N = 21;
export const A = [0, 1, 2, 3, 4, 5, 6, 7, 8];
export const B = A.map((i) => 9 + i);
export const SEAM = [18, 19, 20];
export const INPUTS = ['0', '1', '+', '-'];

// [column, row] on the merged grid
export const COORD = [
  ...A.map((i) => [i % 3, Math.floor(i / 3)]),
  ...A.map((i) => [4 + (i % 3), Math.floor(i / 3)]),
  ...SEAM.map((_, r) => [3, r]),
];

// Logical operators as in lesson 1: X_L along the top row, Z_L down the left column.
export const LOGICAL = { XA: [0, 1, 2], ZA: [0, 3, 6], XB: [9, 10, 11], ZB: [9, 12, 15] };

const label = (q) => (q >= 18 ? `s${q - 18}` : q >= 9 ? `B${q - 9}` : `A${q}`);

function check(type, q, patch) {
  const c = { id: `${patch}.${type}(${q.map(label).join(',')})`, type, q, patch };
  if (q.length === 2) {
    const [[c0, r0], [c1]] = q.map((x) => COORD[x]);
    c.side = c0 === c1 ? (c0 === 0 || c0 === 4 ? 'left' : 'right') : r0 === 0 ? 'top' : 'bottom';
  }
  return c;
}

const patchChecks = (name, off) => [
  ...X_STABS.map((s) => check('X', s.map((i) => i + off), name)),
  ...Z_STABS.map((s) => check('Z', s.map((i) => i + off), name)),
];

// Before the merge and again after the split: the 16 checks of the two separate patches.
export const PATCH_CHECKS = [...patchChecks('A', 0), ...patchChecks('B', 9)];
export const SPLIT_CHECKS = PATCH_CHECKS;

// The facing edge checks that stop being checks while the patches are merged.
const FACING = ['A.X(A2,A5)', 'B.X(B3,B6)'];

// New checks across the seam, continuing the checkerboard of the 7 x 3 grid.
export const SEAM_CHECKS = [
  check('Z', [2, 18], 'seam'),            // top edge
  check('X', [2, 18, 5, 19], 'seam'),
  check('Z', [5, 19, 8, 20], 'seam'),
  check('Z', [18, 9, 19, 12], 'seam'),
  check('X', [19, 12, 20, 15], 'seam'),
  check('Z', [20, 15], 'seam'),           // bottom edge
];
export const MERGE_CHECKS = [...PATCH_CHECKS.filter((c) => !FACING.includes(c.id)), ...SEAM_CHECKS];

// The seam Z checks: their product is Z on A's right column and B's left column, which is
// Z_L(A) Z_L(B) times the four Z checks of A (tested in _studio/tools/tests/surgery/).
export const PARITY_CHECKS = SEAM_CHECKS.filter((c) => c.type === 'Z').map((c) => c.id);
const A_Z = PATCH_CHECKS.filter((c) => c.patch === 'A' && c.type === 'Z').map((c) => c.id);
const SEAM_X = SEAM_CHECKS.filter((c) => c.type === 'X').map((c) => c.id);

export function commute(p, q) {
  if (p.type === q.type) return true;
  return q.q.filter((x) => p.q.includes(x)).length % 2 === 0;
}

const spec = (type, q) => ({ [type]: q });
const sign = (bit) => (bit ? -1 : 1);

// +1 / -1 if the Pauli has a definite value in this state, 0 if measuring it would be random.
function peek(tab, type, q) {
  const lo = tab.clone(), hi = tab.clone();
  lo.rng = () => 0;
  hi.rng = () => 0.99;
  const a = lo.measurePauli(spec(type, q)), b = hi.measurePauli(spec(type, q));
  return a === b ? sign(a) : 0;
}

// Ideal preparation: start in |0...0> or |+...+>, measure the checks of the other type and fix each
// -1 with a single-qubit Pauli that flips only that check; a logical Pauli then gives |1> or |->.
const Z_FIX = [0, 8, 2, 6];   // Z on these flips only X_STABS[k]
const X_FIX = [2, 6, 0, 8];   // X on these flips only Z_STABS[k]
function prepare(tab, off, state) {
  const zBasis = state === '0' || state === '1';
  if (!zBasis) for (let i = 0; i < 9; i++) tab.h(off + i);
  const [stabs, type, fix, gate] = zBasis ? [X_STABS, 'X', Z_FIX, 'z'] : [Z_STABS, 'Z', X_FIX, 'x'];
  stabs.forEach((s, k) => {
    if (tab.measurePauli(spec(type, s.map((i) => i + off)))) tab[gate](off + fix[k]);
  });
  if (state === '1') for (const i of LOGICAL.XA) tab.x(off + i);
  if (state === '-') for (const i of LOGICAL.ZA) tab.z(off + i);
}

function logicals(tab) {
  const v = {};
  for (const k of ['XA', 'ZA', 'XB', 'ZB']) v[k] = peek(tab, k[0], LOGICAL[k]);
  v.ZZ = peek(tab, 'Z', [...LOGICAL.ZA, ...LOGICAL.ZB]);
  v.XX = peek(tab, 'X', [...LOGICAL.XA, ...LOGICAL.XB]);
  return v;
}

const peekAll = (tab, checks) => checks.map((c) => ({ id: c.id, value: peek(tab, c.type, c.q) }));
const measureAll = (tab, checks) => checks.map((c) => ({ id: c.id, value: sign(tab.measurePauli(spec(c.type, c.q))) }));

// One shot. basis: the logical readout at the end, 'Z' or 'X' on both patches.
// frame: apply the Pauli frame after the split (false only to show it is needed).
export function runShot({ a, b, basis = 'Z', seed = 1, frame = true, snapshots = true }) {
  const tab = new Tableau(N, mulberry32(seed));
  prepare(tab, 0, a);
  prepare(tab, 9, b);
  for (const q of SEAM) tab.h(q);
  const stages = [];
  if (snapshots) stages.push({ name: 'start', checks: peekAll(tab, PATCH_CHECKS), logicals: logicals(tab) });

  // merge: one round of the merged code's checks
  const merged = measureAll(tab, MERGE_CHECKS);
  const val = Object.fromEntries(merged.map((c) => [c.id, c.value]));
  const parity = [...PARITY_CHECKS, ...A_Z].reduce((p, id) => p * val[id], 1);
  if (snapshots) stages.push({ name: 'merge', checks: merged, logicals: logicals(tab), parity });

  // split: the seam qubits are measured in X, then one round of the separate patches' checks
  const seam = SEAM.map((q) => sign(tab.measurePauli({ X: [q] })));
  const split = measureAll(tab, SPLIT_CHECKS);
  // A's right-edge X check comes back as (seam X check) x X_s0 x X_s1, B's left-edge one as
  // (seam X check) x X_s1 x X_s2; X_L(A) X_s0 X_L(B) survived the merge, so X_L(A) X_L(B) picks up X_s0.
  const aEdge = val[SEAM_X[0]] * seam[0] * seam[1];
  const bEdge = val[SEAM_X[1]] * seam[1] * seam[2];
  const qubits = [];
  if (aEdge === -1) qubits.push(5, 8);                 // Z on A5, A8 flips only A's right-edge X check
  if (bEdge === -1) qubits.push(15);                   // Z on B6 flips only B's left-edge X check
  if (seam[0] === -1) qubits.push(...LOGICAL.ZA);      // Z_L(A) restores X_L(A) X_L(B)
  const fr = { aEdge, bEdge, logical: seam[0], qubits };
  if (snapshots) stages.push({ name: 'split', checks: split, logicals: logicals(tab), parity, seam, frame: fr });

  if (frame) for (const q of qubits) tab.z(q);
  const after = snapshots ? { checks: peekAll(tab, SPLIT_CHECKS), logicals: logicals(tab) } : null;
  const keys = basis === 'Z' ? ['ZA', 'ZB'] : ['XA', 'XB'];
  const readout = { basis, A: sign(tab.measurePauli(spec(basis, LOGICAL[keys[0]]))), B: sign(tab.measurePauli(spec(basis, LOGICAL[keys[1]]))) };
  if (snapshots) stages.push({ name: 'readout', ...after, parity, seam, frame: fr, readout });
  return { seed, a, b, parity, seam, frame: fr, readout, stages };
}

// Many shots; table[parity][product of the two readouts] counts them.
export function runShots({ a, b, basis = 'Z', shots = 200, seed = 1 }) {
  const table = { '+1': { '+1': 0, '-1': 0 }, '-1': { '+1': 0, '-1': 0 } };
  const key = (v) => (v === 1 ? '+1' : '-1');
  let agree = 0;
  for (let i = 0; i < shots; i++) {
    const s = runShot({ a, b, basis, seed: (seed + Math.imul(i + 1, 0x9e3779b9)) >>> 0, snapshots: false });
    const p = s.readout.A * s.readout.B;
    table[key(s.parity)][key(p)]++;
    if (p === s.parity) agree++;
  }
  return { shots, agree, table };
}
