// decoding.html: errors and checks on a surface code patch (Fig. 1), the union-find decoder step by step
// (Fig. 2), an error the decoder gets wrong (Fig. 3), measurement errors in space-time (Fig. 4).
import { surfaceCode } from './qec/codes.js';
import { sampleErrors, syndrome } from './qec/noise.js';
import { codeFigure } from './qec-draw.js';
import { emptyError, pauliAt, cyclePauli, graphsFor, decodeError, frames, foolingPreset, measurementDemo } from './explore-logic.js';

const $ = (root, s) => root.querySelector(s);
const ones = a => [...a.keys()].filter(i => a[i]);
const list = a => (a.length === 1 ? a[0] : a.length === 2 ? `${a[0]} and ${a[1]}` : `${a.slice(0, -1).join(', ')} and ${a[a.length - 1]}`);
const plural = (n, w) => `${n} ${w}${n === 1 ? '' : 's'}`;
// the drawing, legend and controls start hidden in the HTML, so without scripts only the note and caption show
const reveal = root => root.querySelectorAll('svg.code, .legend, .ex-controls').forEach(e => e.removeAttribute('hidden'));

function patchFigure(root, { decoder = false, preset = false } = {}) {
  reveal(root);
  const svg = $(root, 'svg'), status = $(root, '.ex-status'), sel = $(root, '[data-d]');
  const btn = name => $(root, `[data-${name}]`);
  let code, graphs, fig, err, stage = 0, run = null;
  const where = q => `(${code.coords[q][1] + 1}, ${code.coords[q][0] + 1})`;

  function setD() {
    code = surfaceCode(+sel.value);
    graphs = graphsFor(code);
    err = emptyError(code);
    fig = codeFigure(svg, code, { onActivate: cycle });
    reset();
  }
  function reset() { stage = 0; run = null; draw(); buttons(); }
  function firedText() {
    const s = syndrome(code, err), z = ones(s.Z).length, x = ones(s.X).length;
    return `Fired: ${plural(z, 'Z check')} (blue), ${plural(x, 'X check')} (orange).`;
  }
  function errText() {
    const e = [...Array(code.n).keys()].filter(q => pauliAt(err, q) !== 'I');
    return e.length ? `Errors: ${list(e.map(q => `${pauliAt(err, q)} at ${where(q)}`))}.` : 'No errors.';
  }
  function cycle(q) {
    err = cyclePauli(err, q);
    reset();
    const p = pauliAt(err, q);
    status.textContent = `${where(q)} now has ${p === 'I' ? 'no error' : `${p === 'X' ? 'an' : 'a'} ${p} error`}. ${firedText()}`;
  }
  const G = () => run ? Math.max(run.fr.X.length, run.fr.Z.length) - 1 : 0;

  function draw() {
    const syn = syndrome(code, err), st = { err, syn };
    if (run && stage >= 1) {
      const g = G();
      if (stage <= g + 1) st.growth = ['X', 'Z'].map(t => ({ g: graphs[t], frame: run.fr[t][Math.min(stage, run.fr[t].length - 1)] }));
      if (stage === g + 1) st.correction = run.dec.correction;
      if (stage === g + 2) { st.residual = run.dec.residual; st.residualBad = run.dec.failure.x || run.dec.failure.z; }
    }
    fig.render(st);
  }
  function buttons() {
    if (!decoder) return;
    btn('back').disabled = stage === 0;
    btn('next').disabled = btn('end').disabled = run !== null && stage === G() + 2;
  }

  function describe() {
    const g = G(), d = run.dec;
    if (stage <= g) {
      const fx = run.fr.X[Math.min(stage, run.fr.X.length - 1)], fz = run.fr.Z[Math.min(stage, run.fr.Z.length - 1)];
      const n = fx.clusters.length + fz.clusters.length, odd = fx.odd + fz.odd;
      return `<b>Growth round ${stage} of ${g}.</b> ${plural(n, 'cluster')}; ${odd ? `${odd} still odd (filled dots) and still growing` : 'every cluster now holds an even number of fired checks or touches a boundary, so growth stops'}.`;
    }
    if (stage === g + 1) {
      const cx = ones(d.correction.x), cz = ones(d.correction.z);
      const parts = [cx.length ? `X on ${list(cx.map(where))}` : '', cz.length ? `Z on ${list(cz.map(where))}` : ''].filter(Boolean);
      return `<b>Correction.</b> ${g ? 'Inside each cluster the decoder picks a path that links its fired checks in pairs or to the boundary' : 'No check fired, so there is nothing to correct'}${parts.length ? `: ${parts.join('; ')} (dashed rings). It fires exactly the same checks as the error` : ''}.`;
    }
    const f = d.failure, bad = [];
    if (f.x) bad.push('a logical X, equivalent to a chain of X errors from the left edge to the right edge');
    if (f.z) bad.push('a logical Z, equivalent to a chain of Z errors from the top edge to the bottom edge');
    const left = [...Array(code.n).keys()].filter(q => pauliAt(d.residual, q) !== 'I').length;
    if (bad.length) return `<b>Logical error.</b> Error and correction together form ${bad.join(', and ')}. No check can see it, and it has changed the stored qubit.`;
    return `<b>The logical qubit survived.</b> ${left ? `Error and correction together (the ${plural(left, 'letter')} left on the patch) form a product of checks, a stabilizer, which does nothing to the stored state.` : 'The correction undid the error exactly.'}`;
  }
  function step(to) {
    if (!run) {
      const r = decodeError(code, err, graphs, { trace: true }), syn = syndrome(code, err);
      run = { dec: r, fr: { X: frames(graphs.X, syn.Z, r.traces.X), Z: frames(graphs.Z, syn.X, r.traces.Z) } };
    }
    stage = Math.max(0, Math.min(to, G() + 2));
    draw(); buttons();
    status.innerHTML = stage === 0 ? `Before decoding. ${errText()} ${firedText()}` : describe();
  }

  sel.addEventListener('change', () => { setD(); status.textContent = `Distance ${code.d}: ${code.n} data qubits, ${code.checks.X.length} X checks and ${code.checks.Z.length} Z checks. No errors.`; });
  btn('clear').addEventListener('click', () => { err = emptyError(code); reset(); status.textContent = 'Cleared: no errors, no fired checks.'; });
  if (decoder) {
    btn('next').addEventListener('click', () => step(stage + 1));
    btn('back').addEventListener('click', () => step(stage - 1));
    btn('end').addEventListener('click', () => step(Infinity));
  }
  if (btn('random')) {
    const p = btn('p'), pout = btn('pout'), model = btn('model');
    p.addEventListener('input', () => { pout.textContent = (+p.value).toFixed(2); });
    btn('random').addEventListener('click', () => {
      err = sampleErrors(code, +p.value, Math.random, model.value);
      reset();
      status.textContent = `Random ${model.value === 'bitflip' ? 'bit-flip' : 'depolarizing'} errors at p = ${(+p.value).toFixed(2)}. ${errText()} ${firedText()} Press Next step.`;
    });
  }
  if (preset) {
    btn('preset').addEventListener('click', () => {
      const pre = foolingPreset(code.d);
      err = emptyError(code);
      for (const q of pre.qubits) err.x[q] = 1;
      reset();
      status.textContent = `${pre.qubits.length} X errors on the left of the top row: ${list(pre.qubits.map(where))}. ${firedText()} Step through the decoder.`;
    });
  }
  setD();
  status.textContent = preset ? 'Press Load the example, then step through the decoder.'
    : decoder ? 'Click qubits to place errors, or draw random ones, then press Next step.'
      : 'No errors. Click a qubit to give it an X error; click again for Z, then Y, then none.';
}

function spaceTime(root) {
  reveal(root);
  const box = $(root, '[data-grids]'), status = $(root, '.ex-status');
  const btns = [...root.querySelectorAll('[data-case]')];
  function show(which) {
    for (const b of btns) b.setAttribute('aria-pressed', String(b.dataset.case === which));
    const r = measurementDemo(which), m = r.m;
    const grid = (title, cell) => {
      let h = `<div class="mgrid" style="--m:${m}"><span class="hd">${title}</span><span></span>`;
      for (let c = 0; c < m; c++) h += `<span class="cl">c${c + 1}</span>`;
      for (let t = 0; t < r.rounds; t++) {
        h += `<span class="rl">round ${t + 1}</span>`;
        for (let c = 0; c < m; c++) h += cell(t, c);
      }
      return h + '</div>';
    };
    box.innerHTML =
      grid('Check readings', (t, c) => `<span class="mcell${r.measured[t][c] ? ' on' : ''}${r.flips[t][c] ? ' wrong' : ''}"></span>`) +
      grid('Detection events', (t, c) => `<span class="ecell${r.events[t * m + c] ? ' on' : ''}"></span>`);
    const ev = ones(r.events).map(i => `round ${Math.floor(i / m) + 1} at c${(i % m) + 1}`);
    const fix = ones(r.correction).map(i => `qubit ${i + 1}`);
    const what = { data: 'Qubit 2 flips before round 2 and stays flipped.', measure: 'Check c4 is misread in round 2 only.', both: 'Qubit 2 flips before round 2, and check c4 is misread in round 2.' }[which];
    status.innerHTML = `${what} Detection events: ${list(ev)}. <b>The decoder flips ${fix.length ? list(fix) : 'no data qubit'}</b>${which === 'measure' ? ': it recognises a wrong reading and leaves the data alone' : ''}.`;
  }
  for (const b of btns) b.addEventListener('click', () => show(b.dataset.case));
  show('measure');
}

patchFigure(document.getElementById('fig-patch'));
patchFigure(document.getElementById('fig-uf'), { decoder: true });
patchFigure(document.getElementById('fig-fool'), { decoder: true, preset: true });
spaceTime(document.getElementById('fig-time'));
