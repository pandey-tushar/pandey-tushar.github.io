// Noise sampling and syndromes. An error is { x, z } bit arrays over data qubits; x = z = 1 is Y.
// Z checks detect the x part, X checks detect the z part.

export function sampleErrors(code, p, rng, model = 'bitflip') {
  const x = new Uint8Array(code.n), z = new Uint8Array(code.n);
  if (model === 'bitflip') {
    for (let i = 0; i < code.n; i++) if (rng() < p) x[i] = 1;
  } else if (model === 'depolarizing') {
    for (let i = 0; i < code.n; i++) {
      const u = rng();
      if (u < p) { const k = Math.floor(u * 3 / p); x[i] = k !== 2 ? 1 : 0; z[i] = k !== 0 ? 1 : 0; }
    }
  } else throw new Error(`unknown noise model ${model}`);
  return { x, z };
}

function parities(checks = [], bits) {
  const s = new Uint8Array(checks.length);
  for (let k = 0; k < checks.length; k++) {
    let v = 0;
    for (const i of checks[k]) v ^= bits[i];
    s[k] = v;
  }
  return s;
}

export function syndrome(code, err) {
  return { X: parities(code.checks.X, err.z), Z: parities(code.checks.Z, err.x) };
}

function flips(m, q, rng) {
  const f = new Uint8Array(m);
  for (let i = 0; i < m; i++) if (rng() < q) f[i] = 1;
  return f;
}

export function sampleMeasurementFlips(code, q, rng) {
  return { X: flips((code.checks.X || []).length, q, rng), Z: flips(code.checks.Z.length, q, rng) };
}

// measured: per-round outcomes of one check type, the last round perfect.
// Returns events[t * m + c] = measured[t][c] ^ measured[t - 1][c], with an all-zero round before t = 0.
export function detectionEvents(measured) {
  const m = measured.length ? measured[0].length : 0, ev = new Uint8Array(measured.length * m);
  for (let t = 0; t < measured.length; t++)
    for (let c = 0; c < m; c++) ev[t * m + c] = measured[t][c] ^ (t ? measured[t - 1][c] : 0);
  return ev;
}
