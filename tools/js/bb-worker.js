// Runs the distance search of bb-distance.js off the main thread. The page sends one message
// { l, m, A, B, seed, target, capMs } and terminates the worker to stop it. Posts { kind: 'progress' | 'done' }.
import { buildCode } from './bb-math.js';
import { createSearch } from './bb-distance.js';

let S, t0, target, capMs, sent = 0;

function post(kind, reason) {
  const fresh = S.history.slice(sent).map(h => ({ weight: h.weight, type: h.type, iteration: h.iteration, ms: h.ms }));
  sent = S.history.length;
  const b = S.best && { weight: S.best.weight, type: S.best.type, iteration: S.best.iteration, support: S.best.support };
  postMessage({ kind, reason, k: S.k, iterations: S.iterations, ms: performance.now() - t0, best: b, fresh });
}

function loop() {
  const until = performance.now() + 150;
  let reason = null;
  while (!reason && performance.now() < until) {
    const before = S.history.length;
    S.step(1);
    for (let i = before; i < S.history.length; i++) S.history[i].ms = performance.now() - t0;
    if (S.best && S.best.weight <= target) reason = 'target';
    else if (performance.now() - t0 >= capMs) reason = 'time';
  }
  if (reason) post('done', reason);
  else { post('progress'); setTimeout(loop, 0); }
}

onmessage = e => {
  const { l, m, A, B, seed } = e.data;
  target = e.data.target; capMs = e.data.capMs;
  t0 = performance.now();
  S = createSearch(buildCode(l, m, A, B), seed);
  if (S.k === 0) post('done', 'k0'); else loop();
};
