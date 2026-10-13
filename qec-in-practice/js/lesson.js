// One lesson page: gate-block strip, smooth slider, patches, state panel, error panel, results.
import { makePatches, stateHTML, checkName, checkCounts, el, X_STABS, Z_STABS } from './patch.js';
import { phasesOf, drawStrip, fitPhaseLabels } from './strip.js';
import { resultsHTML } from './results.js';


const INFO = {
  1: { title: 'A surface code patch', intro: 'Nine physical qubits in a 3 by 3 grid hold one logical qubit. An encoder spreads |0> over all nine, and eight checks (four X, four Z) watch for errors. Pick an error next to the Play button to see which checks fire.' },
  2: { title: 'Logical CNOT between two patches', intro: 'Both patches use the encoder from lesson 1: A becomes |+>_L, B becomes |0>_L. Nine physical CNOTs, one between each pair of matching qubits, then act as one logical CNOT and leave a logical Bell pair.' },
  3: { title: 'Preparing a T state', intro: 'H and T on q0 make the T state on one physical qubit; the encoder from lesson 1 carries it over as |T>_L. It is read in X (and Y): ideally 1 comes up in 14.6% of shots.' },
  4: { title: 'Teleporting the T state', intro: 'Patch A holds |T>_L (lesson 3), B and C become a logical Bell pair (lesson 2), then a logical CNOT A to B and the readouts of A in X and B in Z teleport the T state to C, up to a Pauli fix applied to the measured bits.' },
};

// Single-error lookup table for the Z checks, copied from qec/code913.py: syndrome bits in stabilizer order -> qubit to flip.
const Z_TABLE = { '0000': -1, '0010': 0, '1010': 1, '1000': 2, '0100': 3, '1100': 4, '0101': 7, '0001': 8 };

function layersOf(ops, T, summary = []) {
  const L = Array.from({ length: T + 1 }, (_, t) => ({ phase: '', gates: [], summary: summary.includes(t) }));
  for (const o of ops) { L[o.t].gates.push(o); L[o.t].phase = o.phase; }
  return L;
}

function correctionOf(pauli, q, after) {
  const bits = (vals) => vals.map((v) => (v === -1 ? 1 : 0)).join('');
  const zs = bits(after.Z), xs = bits(after.X);
  const fixX = Z_TABLE[zs];
  const parts = [];
  let flipped = false;
  if (pauli !== 'Z') {
    const res = [q, fixX].filter((v) => v >= 0);
    const odd = res.filter((v) => [0, 3, 6].includes(v)).length % 2 === 1 && fixX !== q;
    flipped ||= fixX === undefined || odd;
    parts.push(fixX === undefined ? `Z syndrome ${zs} is not in the table` : `Z syndrome ${zs}: the decoder applies X to q${fixX}${fixX === q ? '' : `, and X${q}·X${fixX} is an X check, so nothing logical changed`}`);
  }
  if (pauli !== 'X') {
    parts.push(`The X checks would read ${xs}, but this run measures in Z: they are never read, and ${pauli === 'Y' ? 'the Z part of a Y error' : 'a Z error'} cannot change a Z readout`);
  }
  return { text: parts.join('. ') + '.', ok: !flipped };
}

function teleportCircuit(root) {
  const svg = el('svg', { viewBox: '0 0 560 190', role: 'img', 'aria-label': 'Ideal logical teleportation circuit' });
  el('title', {}, svg).textContent = 'Teleportation: psi on A, Bell pair on B and C, CNOT A to B, H and measure A, measure B, then X to the M2 and Z to the M1 on C';
  const Y = { A: 40, B: 100, C: 160 };
  const txt = (x, y, s, cls = 'clab', anchor = 'middle') => { const t = el('text', { x, y, class: cls, 'text-anchor': anchor }, svg); t.innerHTML = s; return t; };
  el('line', { x1: 70, y1: Y.A, x2: 330, y2: Y.A, class: 'wire' }, svg);
  el('line', { x1: 70, y1: Y.B, x2: 330, y2: Y.B, class: 'wire' }, svg);
  el('line', { x1: 70, y1: Y.C, x2: 520, y2: Y.C, class: 'wire' }, svg);
  txt(62, Y.A + 5, 'A  |ψ⟩', 'clab', 'end');
  txt(62, Y.B + 5, 'B  |0⟩', 'clab', 'end');
  txt(62, Y.C + 5, 'C  |0⟩', 'clab', 'end');
  const box = (x, y, s, w = 30) => { el('rect', { x: x - w / 2, y: y - 15, width: w, height: 30, rx: 3, class: 'cbox' }, svg); txt(x, y + 5, s); };
  const cnot = (x, yc, yt) => {
    el('line', { x1: x, y1: yc, x2: x, y2: yt + 10 * Math.sign(yt - yc), class: 'wire' }, svg);
    el('circle', { cx: x, cy: yc, r: 5, class: 'cdot' }, svg);
    el('circle', { cx: x, cy: yt, r: 10, class: 'ctarget' }, svg);
    el('line', { x1: x - 10, y1: yt, x2: x + 10, y2: yt, class: 'wire' }, svg);
    el('line', { x1: x, y1: yt - 10, x2: x, y2: yt + 10, class: 'wire' }, svg);
  };
  box(105, Y.B, 'H');
  cnot(145, Y.B, Y.C);
  el('line', { x1: 125, y1: 8, x2: 125, y2: 182, class: 'sep' }, svg);
  txt(105, 14, 'Bell pair', 'cnote');
  cnot(200, Y.A, Y.B);
  box(250, Y.A, 'H');
  const meter = (x, y, lab) => {
    el('rect', { x: x - 17, y: y - 15, width: 34, height: 30, rx: 3, class: 'cbox' }, svg);
    el('path', { d: `M${x - 11},${y + 7} A12,12 0 0 1 ${x + 11},${y + 7}`, class: 'wire', fill: 'none' }, svg);
    el('line', { x1: x, y1: y + 8, x2: x + 9, y2: y - 8, class: 'wire' }, svg);
    txt(x + 30, y - 18, lab, 'cnote');
  };
  meter(305, Y.A, 'M<tspan baseline-shift="sub" font-size="0.75em">1</tspan>');
  meter(305, Y.B, 'M<tspan baseline-shift="sub" font-size="0.75em">2</tspan>');
  // classical wires (double lines) down to the corrections on C
  const dbl = (x0, y0, x1, y1) => {
    el('path', { d: `M${x0},${y0 - 2} H${x1 + 2} V${y1}`, class: 'cwire' }, svg);
    el('path', { d: `M${x0},${y0 + 2} H${x1 - 2} V${y1}`, class: 'cwire' }, svg);
  };
  dbl(322, Y.A, 455, Y.C - 15);
  dbl(322, Y.B, 400, Y.C - 15);
  box(400, Y.C, 'X<tspan baseline-shift="super" font-size="0.7em">M2</tspan>', 44);
  box(455, Y.C, 'Z<tspan baseline-shift="super" font-size="0.7em">M1</tspan>', 44);
  txt(530, Y.C + 5, '|ψ⟩', 'clab', 'start');
  root.appendChild(svg);
}

async function main() {
  const n = Math.min(4, Math.max(1, parseInt(new URLSearchParams(location.search).get('n'), 10) || 1));
  const D = await (await fetch(`data/lesson${n}.json`)).json();
  const info = INFO[n];
  document.title = `Lesson ${n}: ${info.title}`;
  document.getElementById('lesson-title').innerHTML = `Lesson ${n}: ${info.title}`;
  document.getElementById('lesson-intro').innerHTML = stateHTML(info.intro);
  document.getElementById('prev').hidden = n === 1;
  document.getElementById('prev').href = `lesson.html?n=${n - 1}`;
  document.getElementById('next').hidden = n === 4;
  document.getElementById('next').href = `lesson.html?n=${n + 1}`;

  const svg = document.getElementById('patches');
  addEventListener('resize', () => fitPhaseLabels(stripEl));
  // narrow screens stack the patches vertically so each stays readable
  const narrow = matchMedia('(max-width: 600px)');
  const layout = () => (narrow.matches ? D.blocks.map((b, i) => ({ ...b, x0: 0, y0: 3.7 * i })) : D.blocks);
  let patches = makePatches(svg, layout());
  narrow.addEventListener('change', () => { svg.replaceChildren(); patches = makePatches(svg, layout()); set(pos); });
  svg.setAttribute('aria-label', `Patches ${D.blocks.map((b) => b.name).join(', ')} with their checks and data qubits`);

  const slider = document.getElementById('slider');
  const stripEl = document.getElementById('strip');
  const scroller = document.getElementById('strip-scroll');
  const caption = document.getElementById('caption');
  const checkline = document.getElementById('checkline');
  const where = document.getElementById('where');
  const stateEl = document.getElementById('state');
  const errorEl = document.getElementById('error-panel');

  let cur, cells, pos = 0;
  function load(key) {
    const v = key ? D.inject_variants[key] : D;
    const L = layersOf(v.ops, v.T, D.summary);
    const inj = v.ops.find((o) => o.role === 'inject');
    cur = {
      T: v.T, ops: v.ops, checks: v.checks, logicals: v.logicals, layers: L,
      phases: key ? phasesOf(v.ops, v.T) : D.phases,
      inject: inj ? { q: inj.q[0], pauli: inj.gate.toUpperCase(), t: inj.t } : null,
      text: (t) => {
        if (!inj) return D.layer_text[t];
        if (t < inj.t) return D.layer_text[t];
        if (t === inj.t) return `${inj.gate === 'x' ? 'An' : 'A'} ${inj.gate.toUpperCase()} error strikes q${inj.q[0]}. Nothing tells us which qubit was hit, but the ${{ x: 'Z checks', z: 'X checks', y: 'X and Z checks' }[inj.gate]} that share q${inj.q[0]} now read -1.`;
        return D.layer_text[t - 1];
      },
    };
    stripEl.replaceChildren();
    cells = drawStrip(stripEl, L, cur.phases, (t) => { stop(); set(t + 0.99); }, true);
    slider.max = cur.T + 1;
    set(Math.min(pos, cur.T + 1));
  }

  let lastK = -1;
  function set(s) {
    pos = Math.max(0, Math.min(cur.T + 1, s));
    slider.value = pos;
    const T = cur.T;
    const k = Math.min(Math.floor(pos), T);
    const f = pos - k;
    const gateAlpha = Math.min(1, f * 2);
    const m = Math.max(0, Math.min(1, (f - 0.5) * 2));
    const a = cur.checks[k], b = cur.checks[Math.min(k + 1, T + 1)];
    let error = null;
    if (cur.inject) {
      const e = cur.inject;
      error = { q: e.q, pauli: e.pauli, alpha: k > e.t ? 1 : k === e.t ? gateAlpha : 0 };
    }
    const la = cur.logicals[k], lb = cur.logicals[Math.min(k + 1, T + 1)];
    // an encoder shown as one step draws no gates: lesson 1 shows them
    const gates = cur.layers[k].summary ? [] : cur.layers[k].gates;
    patches.update({ a, b, la, lb, m, gates, gateAlpha, error });
    if (k !== lastK) {
      cells.forEach((c, t) => c.classList.toggle('current', t === k && pos < T + 1));
      const c = cells[k];
      if (c && (c.offsetLeft < scroller.scrollLeft || c.offsetLeft + c.offsetWidth > scroller.scrollLeft + scroller.clientWidth)) {
        scroller.scrollLeft = c.offsetLeft - scroller.clientWidth / 2;
      }
      lastK = k;
    }
    const done = pos >= T + 1;
    where.textContent = done ? `All ${T + 1} steps done` : `Step ${k + 1} of ${T + 1}: ${cur.layers[k].phase}`;
    caption.innerHTML = stateHTML(cur.text(k));
    // per patch: how many checks hold, fire, or are undetermined in what the figure shows
    checkline.innerHTML = checkCounts(D.blocks.map((blk) => blk.name), m < 0.5 && !done ? a : b).map((c) =>
      `<span class="pill" title="Patch ${c.name}: ${c.hold} hold, ${c.fire} fire, ${c.und} undetermined"><b>Checks ${c.name}</b><i class="sw sw-ok"></i>${c.hold} hold<i class="sw sw-fire"></i>${c.fire} fired<i class="sw sw-off"></i>${c.und} undetermined</span>`).join('');
    slider.setAttribute('aria-valuetext', where.textContent);
    // logical state per block: the latest label whose layer the figure shows as done (checks switch at m = 0.5)
    const rows = D.blocks.map((blk, bi) => {
      let st = '';
      for (const e of D.logical) if (e.block === bi && pos >= e.t + 0.75) st = e.state;
      return `<li><span class="lbl">Logical ${blk.name}</span> ${stateHTML(st)}</li>`;
    }).join('');
    stateEl.innerHTML = `<ul>${rows}</ul>`;
    if (n === 1) renderError(k, m);
  }

  function renderError(k, m) {
    const e = cur.inject;
    if (!e) { errorEl.innerHTML = ''; return; }
    const head = `<p>Injected: <b class="bad">${e.pauli} on q${e.q}</b> at step ${e.t + 1}, right after encoding.</p>`;
    if (k < e.t || (k === e.t && m < 0.5)) { errorEl.innerHTML = head; return; }
    const after = cur.checks[e.t + 1][0];
    const fired = [];
    for (const [type, stabs] of [['X', X_STABS], ['Z', Z_STABS]]) stabs.forEach((q, i) => { if (after[type][i] === -1) fired.push(checkName(type, q)); });
    const fix = correctionOf(e.pauli, e.q, after);
    errorEl.innerHTML = head + `<p>Checks that fire right after the error: <b>${fired.join(', ') || 'none'}</b>.</p><p>${fix.text}</p><p class="${fix.ok ? 'good' : 'bad'}"><b>${e.pauli === 'Z' ? 'Harmless here: the logical value read in Z is unchanged.' : fix.ok ? 'Corrected: the logical value is unchanged.' : 'Not corrected: the logical value flips.'}</b></p>`;
  }

  // smooth play
  const btn = document.getElementById('play');
  let raf = 0, t0 = 0, p0 = 0;
  const SPEED = 1.1; // layers per second
  function frame(now) {
    const s = p0 + ((now - t0) / 1000) * SPEED;
    set(s);
    if (s >= cur.T + 1) { stop(); return; }
    raf = requestAnimationFrame(frame);
  }
  function play() {
    if (pos >= cur.T + 1) set(0);
    p0 = pos; t0 = performance.now();
    raf = requestAnimationFrame(frame);
    btn.textContent = 'Pause'; btn.setAttribute('aria-pressed', 'true');
  }
  function stop() {
    cancelAnimationFrame(raf); raf = 0;
    btn.textContent = 'Play'; btn.setAttribute('aria-pressed', 'false');
  }
  btn.addEventListener('click', () => (raf ? stop() : play()));
  slider.addEventListener('input', () => { stop(); set(parseFloat(slider.value)); });
  slider.addEventListener('keydown', (ev) => {
    const step = { ArrowRight: 0.5, ArrowUp: 0.5, ArrowLeft: -0.5, ArrowDown: -0.5, PageUp: 1, PageDown: -1 }[ev.key];
    if (ev.key === 'Home' || ev.key === 'End') { ev.preventDefault(); stop(); set(ev.key === 'Home' ? 0 : cur.T + 1); return; }
    if (step === undefined) return;
    ev.preventDefault(); stop();
    set(step > 0 ? Math.floor(pos / Math.abs(step) + 1e-9) * Math.abs(step) + Math.abs(step) : Math.ceil(pos / Math.abs(step) - 1e-9) * Math.abs(step) - Math.abs(step));
  });

  if (n === 1) {
    const pick = document.getElementById('inject-pick');
    document.getElementById('inject-box').hidden = false;
    for (const key of Object.keys(D.inject_variants)) {
      const o = document.createElement('option');
      o.value = key; o.textContent = `${key[0]} on q${key.slice(1)}`;
      pick.appendChild(o);
    }
    pick.addEventListener('change', () => { stop(); load(pick.value || null); });
  } else {
    errorEl.hidden = true;
  }

  load(null);
  document.getElementById('results-head').textContent = D.source.simulated ? 'Simulated results' : 'Recorded results';
  document.getElementById('results').innerHTML = resultsHTML(n, D.results, D.source);
  if (n === 4) teleportCircuit(document.getElementById('circuit'));
  else document.getElementById('circuit-box').hidden = true;
  if (n === 2) {
    document.getElementById('live-box').hidden = false;
    const { initLive } = await import('./live.js');
    initLive(document.getElementById('live'));
  }
}

main().catch((e) => {
  console.error(e);
  document.getElementById('caption').textContent = `Could not load the lesson data: ${e.message}`;
});
