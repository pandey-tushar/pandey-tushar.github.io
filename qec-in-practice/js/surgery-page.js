// Lattice surgery page: the stepper, the figure and the shot tally. Physics lives in surgery.js.
import { el } from './patch.js';
import { COORD, PATCH_CHECKS, SEAM_CHECKS, PARITY_CHECKS, SEAM, runShot, runShots } from './surgery.js';

const S = 60, ML = 40, MT = 46, W = ML + 6 * S + 40, H = MT + 2 * S + 66, R = 30;
const X = (c) => ML + c * S, Y = (r) => MT + r * S;
const P = (q) => [X(COORD[q][0]), Y(COORD[q][1])];
const STAGES = ['Start', 'Merge', 'Split', 'Read out'];
const SHOTS = 200;

const ket = (s) => `|${s === '-' ? '&minus;' : s}&#10217;`;
const L = (t) => `${t}<sub>L</sub>`;
const pm = (v) => (v === 1 ? '+1' : '-1');
const qs = (list) => list.map((q) => `q${q}`).join(', ');

function facePath(c) {
  if (c.q.length === 4) {
    const x = Math.min(...c.q.map((q) => P(q)[0])), y = Math.min(...c.q.map((q) => P(q)[1]));
    return { d: `M${x},${y} h${S} v${S} h${-S} Z`, at: [x + S / 2, y + S / 2 + 6] };
  }
  const [a, b] = c.q.map(P).sort((u, v) => u[0] - v[0] || u[1] - v[1]);
  const sweep = c.side === 'top' || c.side === 'right' ? 1 : 0;
  const off = { top: [0, -13], bottom: [0, 20], left: [-13, 6], right: [13, 6] }[c.side];
  return { d: `M${a[0]},${a[1]} A${R},${R} 0 0 ${sweep} ${b[0]},${b[1]} Z`, at: [(a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1]] };
}

function checkText(c) {
  return `${c.type} check on ${qs(c.q)}`;
}

function build(svg) {
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const faces = {};
  const base = el('g', {}, svg);
  for (const c of [...PATCH_CHECKS, ...SEAM_CHECKS]) {
    const { d, at } = facePath(c);
    const col = c.type === 'X' ? 'var(--x)' : 'var(--z)';
    const g = el('g', { class: 'face' }, base);
    const sat = el('path', { d, fill: col, 'fill-opacity': 0.32 }, g);
    const und = el('path', { d, class: 'und' }, g);
    const bad = el('path', { d, fill: 'var(--bad)', 'fill-opacity': 0.9 }, g);
    el('path', { d, fill: 'none', stroke: col, 'stroke-width': 2 }, g);
    if (PARITY_CHECKS.includes(c.id)) el('path', { d, class: 'sg-par' }, g);
    const label = el('text', { x: at[0], y: at[1], class: 'sg-v', 'text-anchor': 'middle' }, g);
    const title = el('title', {}, g);
    faces[c.id] = { c, g, sat, und, bad, label, title };
  }
  const logs = {};
  const line = (k, x1, y1, x2, y2) => {
    const g = el('g', {}, base), xy = { x1, y1, x2, y2 };
    logs[k] = { off: el('line', { ...xy, class: 'logline' }, g), on: el('line', { ...xy, class: `logline-on ${k[0].toLowerCase()}` }, g), bad: el('line', { ...xy, class: 'logline-bad' }, g), title: el('title', {}, g) };
  };
  line('XA', X(0), Y(0) - 8, X(2), Y(0) - 8);
  line('XB', X(4), Y(0) - 8, X(6), Y(0) - 8);
  line('ZA', X(0) - 8, Y(0), X(0) - 8, Y(2));
  line('ZB', X(6) + 8, Y(0), X(6) + 8, Y(2));   // any column of B is Z_L(B) while its Z checks hold
  const sub = (x, y, letter, anchor) => {
    const t = el('text', { x, y, class: 'sg-lab', 'text-anchor': anchor }, base);
    t.textContent = letter;
    el('tspan', { 'baseline-shift': 'sub', 'font-size': '0.82em' }, t).textContent = 'L';
  };
  sub(X(0) - 12, Y(0) - 14, 'X', 'end');
  sub(X(6) + 12, Y(0) - 14, 'X', 'start');
  sub(X(0) - 8, Y(2) + 30, 'Z', 'middle');
  sub(X(6) + 8, Y(2) + 30, 'Z', 'middle');
  for (const [c, name] of [[1, 'Patch A'], [3, 'seam'], [5, 'Patch B']]) {
    el('text', { x: X(c), y: Y(2) + 58, class: c === 3 ? 'sg-seam' : 'sg-name', 'text-anchor': 'middle' }, base).textContent = name;
  }
  const dots = {};
  const qg = el('g', {}, svg);
  COORD.forEach((_, q) => {
    const [x, y] = P(q);
    const g = el('g', { class: SEAM.includes(q) ? 'sg-q seamq' : 'sg-q' }, qg);
    el('circle', { cx: x, cy: y, r: 15, class: 'qdot' }, g);
    el('text', { x, y: y + 6, class: 'sg-num', 'text-anchor': 'middle' }, g).textContent = q;
    dots[q] = g;
  });
  const dyn = el('g', { 'pointer-events': 'none' }, svg);
  return { faces, logs, dots, dyn };
}

function draw(fig, shot, k, basis) {
  const st = shot.stages[k];
  const vals = Object.fromEntries(st.checks.map((c) => [c.id, c.value]));
  for (const f of Object.values(fig.faces)) {
    const v = vals[f.c.id];
    const on = v !== undefined;
    f.g.style.display = on ? '' : 'none';
    if (!on) continue;
    f.sat.setAttribute('opacity', v === 1 ? 1 : 0);
    f.und.setAttribute('opacity', v === 0 ? 1 : 0);
    f.bad.setAttribute('opacity', v === -1 ? 1 : 0);
    const isPar = PARITY_CHECKS.includes(f.c.id);
    f.label.textContent = isPar && v ? pm(v) : '';
    f.title.textContent = `${checkText(f.c)}: ${v === 1 ? 'read +1' : v === -1 ? 'read -1' : 'no definite value'}${isPar ? ' (one of the four parity checks)' : ''}`;
  }
  const lv = { ...st.logicals };
  if (st.name === 'readout') {
    for (const key of ['XA', 'XB', 'ZA', 'ZB']) lv[key] = key[0] === basis ? st.readout[key[1]] : 0;
  }
  for (const [key, l] of Object.entries(fig.logs)) {
    const v = lv[key];
    l.on.setAttribute('opacity', v === 1 ? 1 : 0);
    l.bad.setAttribute('opacity', v === -1 ? 1 : 0);
    l.off.setAttribute('opacity', v === 0 ? 1 : 0);
    l.title.textContent = `${key[0]}_L of patch ${key[1]}: ${v === 0 ? 'no definite value' : pm(v)}`;
  }
  const gone = st.name === 'split' || st.name === 'readout';
  for (const q of SEAM) fig.dots[q].classList.toggle('gone', gone);
  fig.dyn.replaceChildren();
  if (st.name === 'split' || st.name === 'readout') {
    SEAM.forEach((q, i) => {
      const [x, y] = P(q);
      el('text', { x: x + 19, y: y - 12, class: 'sg-out' }, fig.dyn).textContent = pm(st.seam[i]);
    });
  }
  if (st.name === 'split') {
    for (const q of st.frame.qubits) {
      const [x, y] = P(q);
      el('circle', { cx: x, cy: y, r: 20, class: 'sg-ring' }, fig.dyn);
    }
  }
}

function status(shot, k, basis) {
  const st = shot.stages[k];
  const { a, b } = shot;
  const zz = `${L('Z')}(A) ${L('Z')}(B)`;
  if (st.name === 'start') {
    const fixed = st.logicals.ZZ;
    return `A is ${ket(a)}<sub>L</sub> and B is ${ket(b)}<sub>L</sub>; all 16 checks hold. The seam qubits q18, q19, q20 are in |+&#10217; and belong to no check yet. `
      + (fixed ? `${zz} is already ${pm(fixed)}, so the merge can only confirm it.` : `${zz} has no definite value yet.`);
  }
  if (st.name === 'merge') {
    const v = Object.fromEntries(st.checks.map((c) => [c.id, c.value]));
    const parts = PARITY_CHECKS.map((id) => `(${pm(v[id])})`).join('');
    return `One round of the merged checks. The facing X edge checks are gone; six seam checks are new. The four outlined Z checks read ${parts}, so ${zz} = <b>${pm(st.parity)}</b>. `
      + (st.logicals.ZA === 0 ? `Neither ${L('Z')} has a value on its own.` : `Each ${L('Z')} already had a value, so this parity was fixed in advance.`);
  }
  if (st.name === 'split') {
    const f = st.frame;
    const fix = [];
    if (f.aEdge === -1) fix.push(`A's right edge check came back -1: Z on q5, q8`);
    if (f.bEdge === -1) fix.push(`B's left edge check came back -1: Z on q15`);
    if (f.logical === -1) fix.push(`q18 read -1: ${L('Z')} on A (q0, q3, q6)`);
    return `The seam qubits are measured in X: q18 ${pm(st.seam[0])}, q19 ${pm(st.seam[1])}, q20 ${pm(st.seam[2])}. The two edge checks return. `
      + (fix.length ? `Frame: ${fix.join('; ')}.` : 'Every check holds and q18 read +1, so the frame is empty.');
  }
  const r = st.readout;
  const prod = r.A * r.B;
  if (basis === 'Z') {
    return `Frame applied; all 16 checks hold. Reading ${L('Z')} of both patches gives ${pm(r.A)} and ${pm(r.B)}: product ${pm(prod)}, the parity the merge reported (${pm(st.parity)}).`;
  }
  return `Frame applied; all 16 checks hold. Reading ${L('X')} of both patches gives ${pm(r.A)} and ${pm(r.B)}: product ${pm(prod)}. The merge reported ${zz} = ${pm(st.parity)}.`;
}

function tallyHTML(t, a, b, basis) {
  const rows = ['+1', '-1'].map((p) => `<tr><th scope="row">${p}</th><td>${t.table[p]['+1']}</td><td>${t.table[p]['-1']}</td></tr>`).join('');
  const head = basis === 'Z' ? `${L('Z')}(A) ${L('Z')}(B) read` : `${L('X')}(A) ${L('X')}(B) read`;
  const plus = t.table['+1']['+1'] + t.table['+1']['-1'];
  const sum = basis === 'Z'
    ? `The two ${L('Z')} readouts multiplied to the reported parity in ${t.agree} of ${t.shots} shots. The parity was +1 in ${plus} and -1 in ${t.shots - plus}.`
    : `${L('X')}(A) ${L('X')}(B) read +1 in ${t.table['+1']['+1'] + t.table['-1']['+1']} of ${t.shots} shots. The parity was +1 in ${plus} and -1 in ${t.shots - plus}.`;
  return `<div class="sg-twrap"><table class="sg-t"><caption>${t.shots} shots, A ${ket(a)}, B ${ket(b)}, read out in ${basis}</caption>
    <thead><tr><th scope="col">Merge reported ${L('Z')}(A) ${L('Z')}(B)</th><th scope="col">${head} +1</th><th scope="col">${head} -1</th></tr></thead>
    <tbody>${rows}</tbody></table></div><p class="sg-sum">${sum}</p>`;
}

function init() {
  const $ = (id) => document.getElementById(id);
  const svg = $('sg-svg');
  if (!svg) return;
  for (const id of ['sg-controls', 'sg-legend', 'sg-tally']) $(id).hidden = false;
  const fig = build(svg);
  const steps = [...document.querySelectorAll('#sg-steps button')];
  const st = { k: 0, seed: 1, shot: null };
  const opts = () => ({ a: $('sg-a').value, b: $('sg-b').value, basis: $('sg-basis').value });

  function render() {
    const o = opts();
    st.shot = runShot({ ...o, seed: st.seed });
    draw(fig, st.shot, st.k, o.basis);
    $('sg-status').innerHTML = `<b class="sg-stage">${st.k + 1}. ${STAGES[st.k]}.</b> ${status(st.shot, st.k, o.basis)}`;
    steps.forEach((s, i) => (i === st.k ? s.setAttribute('aria-current', 'step') : s.removeAttribute('aria-current')));
    $('sg-back').disabled = st.k === 0;
    $('sg-next').disabled = st.k === STAGES.length - 1;
    $('sg-seed').textContent = `shot seed ${st.seed}`;
  }
  const go = (k) => {
    const n = Math.max(0, Math.min(STAGES.length - 1, k));
    if (n === st.k) return;
    st.k = n;
    render();
  };
  steps.forEach((s, i) => s.addEventListener('click', () => go(i)));
  $('sg-back').addEventListener('click', () => {
    go(st.k - 1);
    if (st.k === 0) $('sg-next').focus();
  });
  $('sg-next').addEventListener('click', () => {
    go(st.k + 1);
    if (st.k === STAGES.length - 1) $('sg-back').focus();
  });
  $('sg-new').addEventListener('click', () => { st.seed++; render(); });
  for (const id of ['sg-a', 'sg-b', 'sg-basis']) $(id).addEventListener('change', () => { render(); $('sg-table').replaceChildren(); $('sg-run-note').textContent = ''; });
  $('fig').addEventListener('keydown', (e) => {
    if (e.target.tagName === 'SELECT' || e.altKey || e.ctrlKey || e.metaKey) return;
    const k = { ArrowLeft: st.k - 1, ArrowRight: st.k + 1, Home: 0, End: STAGES.length - 1 }[e.key];
    if (k === undefined) return;
    e.preventDefault();
    go(k);
  });
  $('sg-run').addEventListener('click', () => {
    const o = opts();
    const t = runShots({ ...o, shots: SHOTS, seed: st.seed });
    $('sg-table').innerHTML = tallyHTML(t, o.a, o.b, o.basis);
    $('sg-run-note').textContent = `Done: ${SHOTS} shots from seed ${st.seed}.`;
  });
  render();
}

init();
