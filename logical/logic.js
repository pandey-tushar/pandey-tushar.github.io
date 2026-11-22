// Rounds of "Beat the decoder": bit flips on a distance 5 surface code, drawn, decoded and judged by the engine.
import { mulberry32 } from '../qec-in-practice/js/stabsim.js';
import { surfaceCode } from '../qec-in-practice/js/qec/codes.js';
import { sampleErrors, syndrome } from '../qec-in-practice/js/qec/noise.js';
import { buildGraph, decode, logicalFailure } from '../qec-in-practice/js/qec/decoder.js';

export const LEVELS = [{ label: '3%', p: 0.03 }, { label: '7%', p: 0.07 }, { label: '12%', p: 0.12 }];
export const code = surfaceCode(5);
const graph = buildGraph(code, 'X'), none = () => new Uint8Array(code.n);
const fires = x => syndrome(code, { x, z: none() }).Z;

// the same seed and level give the same round; drawn again until at least one check fires
export function round(seed, level) {
  const rng = mulberry32(seed);
  let e;
  do e = sampleErrors(code, LEVELS[level].p, rng); while (!fires(e.x).some(Boolean));
  const fired = fires(e.x);
  return { err: e.x, fired, decoder: decode(graph, fired) };
}

// the checks still lit after flipping the marked qubits back
export function unexplained(fired, marks) {
  const s = fires(marks);
  return s.map((b, k) => b ^ fired[k]);
}

// restored: every check quiet and the stored bit as it was
export function restores(err, corr) {
  const rest = err.map((b, i) => b ^ corr[i]);
  return !fires(rest).some(Boolean) && !logicalFailure(code, { x: err, z: none() }, { x: corr }).x;
}
