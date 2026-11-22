// repetition-code.html: flip qubits and see the checks (Fig. 1), decode (Fig. 2),
// logical error rate against p by Monte Carlo in a worker, over the binomial formula (Fig. 3).
import { repetitionCode } from './qec/codes.js';
import { sampleErrors, syndrome } from './qec/noise.js';
import { codeFigure } from './qec-draw.js';
import { repetitionCurve, emptyError, graphsFor, decodeError, qubitName } from './explore-logic.js';

const $ = (root, s) => root.querySelector(s);
const list = a => (a.length === 1 ? a[0] : a.length === 2 ? `${a[0]} and ${a[1]}` : `${a.slice(0, -1).join(', ')} and ${a[a.length - 1]}`);
const ones = a => [...a.keys()].filter(i => a[i]);
const checkName = k => `between ${qubitName(k)} and ${qubitName(k + 1)}`;
// the drawing, legend and controls start hidden in the HTML, so without scripts only the note and caption show
const reveal = root => root.querySelectorAll('svg.code, .legend, .ex-controls, [data-plot]').forEach(e => e.removeAttribute('hidden'));

function repFigure(root, withDecoder) {
  reveal(root);
  const svg = $(root, 'svg'), status = $(root, '.ex-status'), sel = $(root, '[data-d]');
  let code, fig, graphs, err, dec = null;

  function setD() {
    code = repetitionCode(+sel.value);
    graphs = graphsFor(code);
    err = emptyError(code);
    dec = null;
    fig = codeFigure(svg, code, { onActivate: flip });
    draw();
  }
  function draw() {
    const syn = syndrome(code, err);
    fig.render({ err, syn, correction: dec && dec.correction, values: dec ? dec.residual.x : null });
  }
  function fired() {
    const f = ones(syndrome(code, err).Z);
    return f.length ? `Checks fired: ${f.length}, ${list(f.map(checkName))}.` : 'No check fired.';
  }
  function flip(i) {
    dec = null;
    err.x[i] ^= 1;
    draw();
    status.textContent = `${qubitName(i)} ${err.x[i] ? 'flipped to 1' : 'flipped back to 0'}. ${fired()}`;
  }
  const clear = () => { err = emptyError(code); dec = null; draw(); };
  sel.addEventListener('change', () => { setD(); status.textContent = `Distance ${code.d}: ${code.d} qubits, ${code.d - 1} checks, every qubit reading 0.`; });
  $(root, '[data-clear]').addEventListener('click', () => { clear(); status.textContent = 'Cleared: every qubit reads 0 and no check fired.'; });

  if (withDecoder) {
    const p = $(root, '[data-p]'), pout = $(root, '[data-pout]');
    p.addEventListener('input', () => { pout.textContent = (+p.value).toFixed(2); });
    $(root, '[data-random]').addEventListener('click', () => {
      dec = null;
      err = sampleErrors(code, +p.value, Math.random);
      draw();
      const f = ones(err.x);
      status.textContent = `Random flips at p = ${(+p.value).toFixed(2)}: ${f.length ? list(f.map(qubitName)) : 'none this time'}. ${fired()} Press Decode.`;
    });
    $(root, '[data-decode]').addEventListener('click', () => {
      dec = decodeError(code, err, graphs);
      draw();
      const c = ones(dec.correction.x).map(qubitName), k = ones(err.x).length;
      const what = c.length ? `The decoder flips ${list(c)}.` : 'No check fired, so the decoder changes nothing.';
      const bit = dec.residual.x[0];
      const verdict = bit
        ? `Every qubit now reads 1: the logical bit flipped. ${k} flips out of ${code.d} is more than half, so the decoder chose the other explanation, with ${code.d - k} flip${code.d - k === 1 ? '' : 's'}.`
        : `Every qubit now reads 0: the logical bit survived.`;
      status.innerHTML = `${what} <b>${verdict}</b>`;
    });
  }
  setD();
  status.textContent = withDecoder
    ? 'Every qubit reads 0. Flip some qubits or draw random errors, then press Decode.'
    : 'Every qubit reads 0 and no check fired. Flip a qubit.';
}

// Fig. 3
const DS = [1, 3, 5, 7], PS = [...Array(19).keys()].map(i => +(0.05 * (i + 1)).toFixed(2));
const NS = 'http://www.w3.org/2000/svg';
function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}

function plotFigure(root) {
  reveal(root);
  const box = $(root, '[data-plot]'), status = $(root, '.ex-status'), run = $(root, '[data-run]');
  const shotsSel = $(root, '[data-shots]'), prog = $(root, '[data-progress]');
  const pts = new Map();
  let width = 0, runs = 0;

  $(root, '[data-legend]').innerHTML = DS.map(d =>
    `<span class="nw"><svg width="26" height="12" aria-hidden="true" class="plot lsw"><line class="curve d${d}" x1="1" y1="6" x2="25" y2="6"/></svg> d = ${d}${d === 1 ? ' (no code)' : ''}</span>`).join(' ');

  function draw() {
    width = box.clientWidth;
    const W = width, H = Math.round(Math.max(240, Math.min(380, W * 0.62)));
    const L = 48, Rm = 14, T = 12, B = 42, sx = p => L + p * (W - L - Rm), sy = y => T + (1 - y) * (H - T - B);
    const svg = el('svg', { class: 'plot', viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'img',
      'aria-label': 'Logical error rate against flip rate for d = 1, 3, 5, 7: formula lines' + (pts.size ? ' and simulated points' : '') });
    for (const v of [0, 0.25, 0.5, 0.75, 1]) {
      el('line', { x1: sx(0), x2: sx(1), y1: sy(v), y2: sy(v), class: 'gridl' }, svg);
      el('text', { x: L - 8, y: sy(v) + 4, 'text-anchor': 'end' }, svg).textContent = v;
      el('text', { x: sx(v), y: H - B + 18, 'text-anchor': 'middle' }, svg).textContent = v;
    }
    el('line', { x1: sx(0.5), x2: sx(0.5), y1: sy(0), y2: sy(1), class: 'half' }, svg);
    el('line', { x1: sx(0), x2: sx(1), y1: sy(0), y2: sy(0), class: 'axis' }, svg);
    el('line', { x1: sx(0), x2: sx(0), y1: sy(0), y2: sy(1), class: 'axis' }, svg);
    el('text', { x: sx(0.5), y: H - 6, 'text-anchor': 'middle' }, svg).textContent = 'flip rate p';
    const yl = el('text', { x: 14, y: sy(0.5), 'text-anchor': 'middle', transform: `rotate(-90 14 ${sy(0.5)})` }, svg);
    yl.textContent = 'logical error rate';
    for (const d of DS) {
      let path = '';
      for (let i = 0; i <= 200; i++) { const p = i / 200; path += `${i ? 'L' : 'M'}${sx(p).toFixed(1)},${sy(repetitionCurve(d, p)).toFixed(1)}`; }
      el('path', { d: path, class: `curve d${d}` }, svg);
    }
    for (const d of DS) {
      const g = el('g', { class: `d${d}` }, svg);
      for (const p of PS) {
        const r = pts.get(`${d},${p}`);
        if (!r) continue;
        const se = Math.sqrt(r.rate * (1 - r.rate) / r.shots);
        if (sy(r.rate - se) - sy(r.rate + se) > 2) el('line', { x1: sx(p), x2: sx(p), y1: sy(Math.max(0, r.rate - se)), y2: sy(Math.min(1, r.rate + se)), class: 'bar' }, g);
        el('circle', { cx: sx(p), cy: sy(r.rate), r: 3.5, class: 'pt' }, g);
      }
    }
    box.replaceChildren(svg);
  }
  new ResizeObserver(() => { if (box.clientWidth !== width) draw(); }).observe(box);

  // While running, Run stays focusable (aria-disabled) so a keyboard user does not lose their place.
  const busy = on => { run.setAttribute('aria-disabled', String(on)); shotsSel.disabled = on; };
  run.addEventListener('click', () => {
    if (run.getAttribute('aria-disabled') === 'true') return;
    const shots = +shotsSel.value, jobs = [];
    for (const p of PS) for (const d of DS) jobs.push({ d, p });
    const seed0 = 1000 * ++runs;
    pts.clear(); draw();
    busy(true);
    prog.hidden = false; prog.max = jobs.length; prog.value = 0;
    status.textContent = `Running ${jobs.length} points, ${shots.toLocaleString('en')} samples each, in a background worker.`;
    const w = new Worker(new URL('./qec/worker.js', import.meta.url), { type: 'module' });
    let j = 0;
    const next = () => {
      const { d, p } = jobs[j];
      w.postMessage({ id: j, kind: 'repetition', d, p, model: 'bitflip', shots, seed: seed0 + j, rounds: 1, chunk: shots });
    };
    w.onmessage = ({ data }) => {
      if (!data.done) return;
      const { d, p } = jobs[data.id];
      pts.set(`${d},${p}`, { shots: data.shots, rate: data.failures / data.shots });
      prog.value = ++j;
      draw();
      if (j < jobs.length) return next();
      w.terminate();
      busy(false);
      prog.hidden = true;
      const at = p => DS.map(d => {
        const r = pts.get(`${d},${p}`), se = Math.sqrt(r.rate * (1 - r.rate) / r.shots);
        return `d = ${d}: ${r.rate.toFixed(4)} &plusmn; ${se.toFixed(4)} (formula ${repetitionCurve(d, p).toFixed(4)})`;
      }).join('; ');
      status.innerHTML = `Done: ${jobs.length} points, ${shots.toLocaleString('en')} samples each, decoded by the union-find decoder. At p = 0.10, ${at(0.1)}. At p = 0.70, ${at(0.7)}.`;
    };
    w.onerror = e => {
      w.terminate();
      busy(false);
      prog.hidden = true;
      status.textContent = `The simulation stopped: ${e.message || 'the worker failed to start'}.`;
    };
    next();
  });
  status.textContent = 'Lines show the formula. Press Run to simulate 19 values of p at each distance.';
}

repFigure(document.getElementById('fig-flip'), false);
repFigure(document.getElementById('fig-decode'), true);
plotFigure(document.getElementById('fig-plot'));
