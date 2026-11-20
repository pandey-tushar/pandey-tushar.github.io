import { estimate } from '../../../qec-in-practice/js/qec/montecarlo.js';
import { crossing } from '../../../qec-in-practice/js/threshold-math.js';
import { writeFileSync } from 'node:fs';
// Seeds are tied to the position in this list, so 0.06 and 0.065 are appended and the points are sorted afterwards.
const ps = [0.07, 0.075, 0.08, 0.085, 0.09, 0.095, 0.10, 0.105, 0.11, 0.06, 0.065];
const ds = [3, 5, 7, 9, 11, 13, 17, 21];
const shots = 100000;
const curves = {};
for (const d of ds) {
  const t = performance.now();
  curves[d] = ps.map((p, i) => { const r = estimate({ kind: 'surface', d, p, model: 'bitflip', shots, seed: 7000 + 100 * d + i }); return { p, shots: r.shots, failures: r.failures, rate: r.rate }; }).sort((u, v) => u.p - v.p);
  console.log('d', d, curves[d].map(r => r.rate.toFixed(4)).join(' '), ((performance.now() - t) / 1000 | 0) + 's');
}
const out = { ps: [...ps].sort((u, v) => u - v), shots, curves, crossings: [] };
for (let i = 0; i + 1 < ds.length; i++) {
  const c = crossing(curves[ds[i]], curves[ds[i + 1]]);
  out.crossings.push({ a: ds[i], b: ds[i + 1], ...c });
  console.log(ds[i], ds[i + 1], c.status, c.p?.toFixed(4), c.lo?.toFixed(4), c.hi?.toFixed(4), c.multiple ? 'multi' : '');
}
writeFileSync(new URL('../../content/notes/crossing-is-not-the-threshold.json', import.meta.url), JSON.stringify(out, null, 1));
