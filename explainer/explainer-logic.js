// Logic for why-error-correction.html, on top of the course engine in /qec-in-practice/js/. No DOM.
// A row of n qubits holds one bit as the repetition code; the checks are the engine's syndrome; Correct is the
// engine's decoder (on a line it equals a majority vote); the loss table is the exact majority-vote formula.
import { repetitionCode } from '../qec-in-practice/js/qec/codes.js';
import { syndrome } from '../qec-in-practice/js/qec/noise.js';
import { graphsFor, decodeError, repetitionCurve, emptyError } from '../qec-in-practice/js/explore-logic.js';

export const SIZES = [1, 3, 5, 7];

export function makeRow(n = 5) {
  const code = repetitionCode(n);
  return { code, graphs: graphsFor(code), err: emptyError(code) };
}

// one entry per pair of neighbours: 1 when they disagree
export const checksLit = row => syndrome(row.code, row.err).Z;

export function correct(row) {
  const r = decodeError(row.code, row.err, row.graphs);
  return { correction: r.correction.x, after: r.residual, survived: !r.failure.x };
}

export const lossTable = p => SIZES.map(n => ({ n, lost: repetitionCurve(n, p) }));

export const trend = p => (p < 0.5 ? 'help' : p > 0.5 ? 'hurt' : 'same');

const sig2 = v => { const e = 10 ** (Math.floor(Math.log10(v)) - 1); return Math.round(v / e) * e; };

export function formatChance(x) {
  if (x <= 0) return 'never';
  if (x >= 1) return 'always';
  if (x < 0.01) return `1 in ${sig2(1 / x).toLocaleString('en')}`;
  if (x < 0.1) return `${+(x * 100).toFixed(1)}%`;
  if (x <= 0.99) return `${Math.round(x * 100)}%`;
  if (x < 0.999) return `${(x * 100).toFixed(1)}%`;
  return 'over 99.9%';
}
