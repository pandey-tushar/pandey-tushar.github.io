// Results table under each lesson: P(logical = 1) per readout with its standard error, and what the numbers can and cannot say.
import { stateHTML } from './patch.js';

const pct = (x) => `${(100 * x).toFixed(1)}%`;

// One binomial standard error from the column's own count; a zero count is shown as such.
export function fmtP(p, n) {
  if (p === null || p === undefined) return 'n/a';
  if (p === 0) return `0.0% (0 of ${n})`;
  if (p === 1) return `100.0% (${n} of ${n})`;
  return `${(100 * p).toFixed(1)} ± ${(100 * Math.sqrt((p * (1 - p)) / n)).toFixed(1)}%`;
}

// A patch read in Y has no readable checks (its "checks" list is empty).
export const hasChecks = (row) => row.blocks.some((b) => b.checks.length > 0);

// What each row's probability counts, per lesson and readout.
const ROWS = {
  1: { Z: 'reading 1 from |0>_L in Z' },
  2: { X: 'reading 1 from |+>_L in X, one patch', ZZ: 'A and B differ, both read in Z', XX: 'A and B differ, both read in X' },
  3: { X: 'reading 1 from |T>_L in X', Y: 'reading 1 from |T>_L in Y' },
  4: { X: 'reading 1 from C in X, after the Pauli fix', Y: 'reading 1 from C in Y, after the Pauli fix' },
};
export const rowLabel = (lesson, label) => ROWS[lesson][label];

export function resultsHTML(lesson, rows, source) {
  const labels = [...new Set(rows.map((r) => r.label))];
  const tr = labels.map((lab) => {
    const e = rows.find((r) => r.kind === 'enc' && r.label === lab);
    const b = rows.find((r) => r.kind === 'bare' && r.label === lab);
    const checked = hasChecks(e);
    return `<tr><th scope="row">${stateHTML(rowLabel(lesson, lab))}</th><td>${pct(e.ideal_p1)}</td>`
      + `<td><b>${fmtP(e.p1_corrected, e.n_kept)}</b></td><td>${checked ? fmtP(e.p1_clean, e.n_clean) : 'n/a'}</td><td>${fmtP(e.p1_all, e.n_total)}</td>`
      + `<td>${b ? fmtP(b.p1_all, b.n_total) : 'n/a'}</td>`
      + `<td>${checked ? pct(e.correct_fraction) : 'n/a'}</td><td>${checked ? pct(e.discard_fraction) : 'n/a'}</td></tr>`;
  }).join('');
  const src = source.simulated
    ? `Simulated with Qiskit Aer · ${source.noise} · ${source.shots} shots per readout`
    : `Source: ${source.backend}, ${source.date}, ${source.shots} shots per readout.`;
  return `<div class="table-wrap"><table>
    <thead><tr><th scope="col">Probability of</th><th scope="col">Ideal</th><th scope="col">After correction</th><th scope="col">Clean shots only</th><th scope="col">No correction</th><th scope="col">Bare qubits</th><th scope="col">Corrected by the code</th><th scope="col">Discarded by the checks</th></tr></thead>
    <tbody>${tr}</tbody></table></div>
    <p class="source">${src}</p>`;
}
