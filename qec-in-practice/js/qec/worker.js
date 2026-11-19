// Module worker: new Worker(new URL('./qec/worker.js', import.meta.url), { type: 'module' }).
import { estimateChunks } from './montecarlo.js';

self.onmessage = ({ data: { id, kind, d, p, model, shots, seed, rounds, chunk } }) => {
  for (const s of estimateChunks({ kind, d, p, model, shots, seed, rounds }, chunk))
    self.postMessage({ id, done: s.done, shots: s.shots, failures: s.failures });
};
