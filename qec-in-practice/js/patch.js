// SVG drawing of the 3x3 rotated surface code patches: checks, data qubits, gates of one layer, error marker.
export const NS = 'http://www.w3.org/2000/svg';
export const X_STABS = [[0, 1, 3, 4], [4, 5, 7, 8], [2, 5], [3, 6]];
export const Z_STABS = [[1, 2, 4, 5], [3, 4, 6, 7], [0, 1], [7, 8]];
const SHAPE = { '2,5': 'right', '3,6': 'left', '0,1': 'top', '7,8': 'bottom' };
export const GATE = { h: 'H', t: 'T', s: 'S', x: 'X', y: 'Y', z: 'Z', measure: 'M', cx: 'CX' };
const S = 60, R = 30, M = 48;

export function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

function subLabel(t, letter) {
  t.textContent = letter;
  el('tspan', { 'baseline-shift': 'sub', 'font-size': '0.75em' }, t).textContent = 'L';
}

export const checkName = (type, q) => `${type}(${q.join(',')})`;

// Per patch: how many of its eight checks hold (+1), fire (-1) or are undetermined (0).
export function checkCounts(names, checks) {
  return names.map((name, b) => {
    const v = [...checks[b].X, ...checks[b].Z];
    return { name, hold: v.filter((x) => x === 1).length, fire: v.filter((x) => x === -1).length, und: v.filter((x) => x === 0).length };
  });
}

function outline(q, x0, y0) {
  const p = (i) => [x0 + S * (i % 3), y0 + S * Math.floor(i / 3)];
  const [x, y] = p(q[0]);
  if (q.length === 4) return `M${x},${y} h${S} v${S} h${-S} Z`;
  const [bx, by] = p(q[1]);
  const side = SHAPE[q.join(',')];
  const sweep = side === 'top' || side === 'right' ? 1 : 0;
  return `M${x},${y} A${R},${R} 0 0 ${sweep} ${bx},${by} Z`;
}

// Builds the static picture once; update() redraws only what changes along the slider.
export function makePatches(svg, blocks) {
  const maxX = Math.max(...blocks.map((b) => b.x0)), maxY = Math.max(...blocks.map((b) => b.y0));
  const W = (maxX + 2) * S + 2 * M, H = (maxY + 2) * S + 2 * M + 10;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('role', 'img');
  const defs = el('defs', {}, svg);
  const mk = el('marker', { id: 'ah', viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 5, markerHeight: 5, orient: 'auto-start-reverse' }, defs);
  el('path', { d: 'M0,0 L10,5 L0,10 Z', fill: 'var(--focus)' }, mk);

  const pos = {};
  const faces = [];
  const logs = [];
  const base = el('g', {}, svg);
  blocks.forEach((b, bi) => {
    const x0 = M + b.x0 * S, y0 = M + b.y0 * S;
    b.data.forEach((qid, i) => { pos[qid] = [x0 + S * (i % 3), y0 + S * Math.floor(i / 3)]; });
    for (const [type, stabs] of [['Z', Z_STABS], ['X', X_STABS]]) {
      stabs.forEach((q, k) => {
        const d = outline(q, x0, y0);
        const col = type === 'X' ? 'var(--x)' : 'var(--z)';
        const g = el('g', { class: 'face' }, base);
        const sat = el('path', { d, fill: col, 'fill-opacity': 0.32 }, g);
        const und = el('path', { d, class: 'und' }, g);
        const bad = el('path', { d, fill: 'var(--bad)', 'fill-opacity': 0.9 }, g);
        el('path', { d, fill: 'none', stroke: col, 'stroke-width': 2 }, g);
        const title = el('title', {}, g);
        faces.push({ bi, type, k, q, sat, und, bad, title, block: b.name });
      });
    }
    // logical operators: X_L along the top row, Z_L down the left column; lit at +1, red at -1, dashed when undetermined
    for (const [type, x1, y1, x2, y2] of [['X', x0, y0 - 6, x0 + 2 * S, y0 - 6], ['Z', x0 - 6, y0, x0 - 6, y0 + 2 * S]]) {
      const g = el('g', {}, base);
      const xy = { x1, y1, x2, y2 };
      const off = el('line', { ...xy, class: 'logline' }, g);
      const on = el('line', { ...xy, class: `logline-on ${type.toLowerCase()}` }, g);
      const bad = el('line', { ...xy, class: 'logline-bad' }, g);
      logs.push({ bi, type, off, on, bad, title: el('title', {}, g), block: b.name });
    }
    subLabel(el('text', { x: x0 + 2 * S + 17, y: y0 - 14, class: 'loglab' }, base), 'X');
    subLabel(el('text', { x: x0 - 10, y: y0 + 2 * S + 24, class: 'loglab', 'text-anchor': 'middle' }, base), 'Z');
    el('text', { x: x0 + S, y: y0 + 2 * S + R + 26, class: 'pname', 'text-anchor': 'middle' }, base).textContent = `Patch ${b.name}`;
  });
  const qubits = el('g', {}, svg);
  const dots = {};
  for (const [qid, [x, y]] of Object.entries(pos)) {
    dots[qid] = el('circle', { cx: x, cy: y, r: 12, class: 'qdot' }, qubits);
    el('text', { x, y: y + 4, class: 'qnum', 'text-anchor': 'middle' }, qubits).textContent = qid;
  }
  const dyn = el('g', { 'pointer-events': 'none' }, svg);

  function gateShape(op, alpha, labelled) {
    const g = el('g', { opacity: alpha.toFixed(3) }, dyn);
    if (op.gate === 'cx') {
      const [a, b] = op.q.map((q) => pos[q]);
      const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy);
      const ux = dx / L, uy = dy / L;
      const sx = a[0] + ux * 16, sy = a[1] + uy * 16, ex = b[0] - ux * 15, ey = b[1] - uy * 15;
      const bend = Math.min(0.18 * L, 40);
      const cx = (sx + ex) / 2 + uy * bend, cy = (sy + ey) / 2 - ux * bend;
      el('path', { d: `M${sx},${sy} Q${cx},${cy} ${ex},${ey}`, class: 'cxarrow', 'marker-end': 'url(#ah)' }, g);
      el('circle', { cx: a[0], cy: a[1], r: 15, fill: 'none', stroke: 'var(--focus)', 'stroke-width': 3 }, g);
      return;
    }
    const [x, y] = pos[op.q[0]];
    const bad = op.role === 'inject';
    el('circle', { cx: x, cy: y, r: 16, fill: 'none', stroke: bad ? 'var(--bad)' : 'var(--focus)', 'stroke-width': 2.5 }, g);
    if (labelled) el('text', { x: x + 13, y: y - 13, class: bad ? 'glab err' : 'glab' }, g).textContent = GATE[op.gate] || op.gate.toUpperCase();
  }

  // st: {a, b, la, lb, m, gates: [op], gateAlpha, error: {q, pauli, alpha} | null}
  function update(st) {
    for (const l of logs) {
      const va = st.la[l.bi][l.type], vb = st.lb[l.bi][l.type];
      const w = (v) => (1 - st.m) * (va === v) + st.m * (vb === v);
      l.on.setAttribute('opacity', w(1).toFixed(3));
      l.off.setAttribute('opacity', w(0).toFixed(3));
      l.bad.setAttribute('opacity', w(-1).toFixed(3));
      const v = st.m < 0.5 ? va : vb;
      l.title.textContent = `Patch ${l.block}, ${l.type}_L: ${v === 1 ? '+1' : v === -1 ? '-1' : 'no definite value'}`;
    }
    for (const f of faces) {
      const va = st.a[f.bi][f.type][f.k], vb = st.b[f.bi][f.type][f.k];
      const w = (v) => (1 - st.m) * (va === v) + st.m * (vb === v);
      f.sat.setAttribute('opacity', w(1).toFixed(3));
      f.und.setAttribute('opacity', w(0).toFixed(3));
      f.bad.setAttribute('opacity', w(-1).toFixed(3));
      const v = st.m < 0.5 ? va : vb;
      f.title.textContent = `Patch ${f.block}, ${f.type} check on q${f.q.join(', q')}: ${v === 1 ? '+1, satisfied' : v === -1 ? '-1, fired' : 'undetermined'}`;
    }
    dyn.replaceChildren();
    for (const id in dots) dots[id].classList.remove('hit');
    if (st.error && st.error.alpha > 0) {
      const [x, y] = pos[st.error.q];
      const g = el('g', { opacity: st.error.alpha.toFixed(3) }, dyn);
      el('circle', { cx: x, cy: y, r: 19, fill: 'var(--bad)', 'fill-opacity': 0.25, stroke: 'var(--bad)', 'stroke-width': 3 }, g);
      el('text', { x: x + 16, y: y + 30, class: 'glab err' }, g).textContent = `${st.error.pauli} error`;
      if (st.error.alpha >= 1) dots[st.error.q].classList.add('hit');
    }
    // a layer with many one-qubit gates (readout rotation, measurement) keeps the rings and drops the letters
    const labelled = st.gates.filter((op) => op.gate !== 'cx').length <= 4;
    if (st.gateAlpha > 0) for (const op of st.gates) gateShape(op, st.gateAlpha, labelled);
  }
  return { update };
}

// Text with kets and _L subscripts as safe HTML: "|+>_L" -> "|+&#10217;<sub>L</sub>".
export function stateHTML(s) {
  const esc = s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return esc
    .replace(/\|([^|&\s]*?)&gt;/g, '|$1&#10217;')
    .replace(/_L\b/g, '&#8203;<sub>L</sub>')
    .replace(/sqrt2/g, '&radic;2');
}
