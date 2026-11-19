// Monte Carlo logical error rates. rounds = R follows buildGraph: R rounds of data noise, the first R-1 syndrome
// measurements flipped with prob q = p, the last one perfect. A shot fails if either logical is flipped.
import { mulberry32 } from '../stabsim.js';
import { makeCode } from './codes.js';
import { sampleErrors, syndrome, sampleMeasurementFlips, detectionEvents } from './noise.js';
import { buildGraph, decode, logicalFailure } from './decoder.js';

export function* estimateChunks({ code, kind, d, p, model = 'bitflip', shots, seed = 1, rounds = 1 }, chunk = 1000) {
  code ||= makeCode(kind, d);
  const rng = mulberry32(seed), gx = buildGraph(code, 'X', rounds);
  const gz = model === 'depolarizing' && code.checks.X ? buildGraph(code, 'Z', rounds) : null;
  const shot = () => {
    const acc = { x: new Uint8Array(code.n), z: new Uint8Array(code.n) }, mx = [], mz = [];
    let s;
    for (let t = 0; t < rounds; t++) {
      const e = sampleErrors(code, p, rng, model);
      for (let i = 0; i < code.n; i++) { acc.x[i] ^= e.x[i]; acc.z[i] ^= e.z[i]; }
      s = syndrome(code, acc);
      if (t < rounds - 1) {
        const f = sampleMeasurementFlips(code, p, rng);
        for (let k = 0; k < s.Z.length; k++) s.Z[k] ^= f.Z[k];
        for (let k = 0; k < s.X.length; k++) s.X[k] ^= f.X[k];
      }
      mx.push(s.X); mz.push(s.Z);
    }
    const x = decode(gx, rounds === 1 ? s.Z : detectionEvents(mz));
    const z = gz ? decode(gz, rounds === 1 ? s.X : detectionEvents(mx)) : null;
    const f = logicalFailure(code, acc, { x, z });
    return f.x || f.z;
  };
  let done = 0, failures = 0;
  while (done < shots) {
    const k = Math.min(chunk, shots - done);
    for (let i = 0; i < k; i++) if (shot()) failures++;
    done += k;
    const rate = failures / done;
    yield { shots: done, failures, rate, stderr: Math.sqrt(rate * (1 - rate) / done), done: done === shots };
  }
}

export function estimate(opts) {
  let last;
  for (last of estimateChunks(opts, opts.shots)) ;
  const { done, ...r } = last;
  return r;
}
