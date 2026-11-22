// SVG drawing of an engine code object (./qec/codes.js) in the inks of the lessons (css/site.css):
// plaquettes or a line of check squares, data qubits with their errors, fired checks, decoder clusters,
// the correction. The qubits are one roving tab stop; arrow keys move between them.
import { nodePoint, pauliAt, qubitName, rcName } from './explore-logic.js';

const NS = 'http://www.w3.org/2000/svg', S = 60, M = 44, R = 15;

function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}

const P = ([x, y], my = M) => [M + x * S, my + y * S];

// outline of check k of type t: a square in the bulk, a half disc bulging outward on the edge
function plaquette(code, t, k) {
  const q = code.checks[t][k].map(i => P(code.coords[i]));
  const [cx, cy] = P(code.checkCoords[t][k]);
  if (q.length === 4) return `M${cx - S / 2},${cy - S / 2} h${S} v${S} h${-S} Z`;
  const [[ax, ay], [bx, by]] = q, cross = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
  return `M${ax},${ay} A${S / 2},${S / 2} 0 0 ${cross < 0 ? 1 : 0} ${bx},${by} Z`;
}

// state: { err, syn, correction?, values?, growth?: [{ g, frame }], residual? }
export function codeFigure(svg, code, { onActivate, interactive = true } = {}) {
  const rep = code.kind === 'repetition', my = rep ? 50 : M;
  const W = (code.d - 1) * S + 2 * M, H = rep ? 2 * my : W;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.style.maxWidth = `${Math.round(rep ? W * 1.7 : Math.max(W * 1.25, 380))}px`;
  svg.replaceChildren();
  const pt = c => P(c, my);
  const paint = el('g', { 'pointer-events': 'none' }, svg);
  const hits = el('g', {}, svg);
  const btns = [];
  let cur = 0;

  if (interactive) {
    code.coords.forEach((c, i) => {
      const [x, y] = pt(c);
      const b = el('g', { class: 'qbtn', role: 'button', tabindex: i === 0 ? 0 : -1 }, hits);
      el('circle', { cx: x, cy: y, r: S / 2, class: 'qhit' }, b);
      el('circle', { cx: x, cy: y, r: R + 6, class: 'qring' }, b);
      b.addEventListener('click', () => { move(i); onActivate(i); });
      btns.push(b);
    });
    svg.onkeydown = ev => {
      const i = btns.indexOf(document.activeElement);
      if (i < 0) return;
      const [x, y] = code.coords[i];
      const step = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[ev.key];
      if (step) {
        const nx = x + step[0], ny = y + step[1], j = code.coords.findIndex(c => c[0] === nx && c[1] === ny);
        if (j >= 0) move(j, true);
        ev.preventDefault();
      } else if (ev.key === 'Home' || ev.key === 'End') {
        move(ev.key === 'Home' ? 0 : code.n - 1, true);
        ev.preventDefault();
      } else if (ev.key === 'Enter' || ev.key === ' ') {
        onActivate(i);
        ev.preventDefault();
      }
    };
  }
  function move(j, focus) {
    btns[cur].setAttribute('tabindex', -1);
    cur = j;
    btns[j].setAttribute('tabindex', 0);
    if (focus) btns[j].focus();
  }

  function render(st) {
    paint.replaceChildren();
    const { err, syn } = st;
    // checks
    if (rep) {
      const [x0, y] = pt(code.coords[0]), [x1] = pt(code.coords[code.n - 1]);
      el('line', { x1: x0, y1: y, x2: x1, y2: y, class: 'repline' }, paint);
      code.checkCoords.Z.forEach((c, k) => {
        const [x, yy] = pt(c), h = 9;
        const d = `M${x},${yy - h * 1.4} L${x + h * 1.4},${yy} L${x},${yy + h * 1.4} L${x - h * 1.4},${yy} Z`;
        el('path', { d, class: syn.Z[k] ? 'chk z fired' : 'chk z' }, paint);
      });
    } else {
      for (const t of ['Z', 'X']) code.checks[t].forEach((_, k) => {
        const d = plaquette(code, t, k);
        el('path', { d, class: `plaq ${t.toLowerCase()}` }, paint);
        if (syn[t][k]) el('path', { d, class: 'plaq fired' }, paint);
      });
    }
    // decoder clusters: grown edges in the accent, check nodes of each cluster, odd ones filled
    for (const { g, frame } of st.growth || []) {
      const at = v => pt(nodePoint(code, g, v));
      for (const h of frame.halves) {
        const [u, v, q] = g.edges[h.edge];
        const [ax, ay] = at(h.full ? u : h.from), [bx, by] = h.full ? at(v) : pt(code.coords[q]);
        el('line', { x1: ax, y1: ay, x2: bx, y2: by, class: 'grow' }, paint);
      }
      for (const c of frame.clusters) for (const v of c.nodes) {
        if (v >= g.nDet) continue;
        const [x, y] = at(v);
        el('circle', { cx: x, cy: y, r: 7, class: c.neutral ? 'cnode' : 'cnode odd' }, paint);
      }
    }
    // data qubits
    code.coords.forEach((c, i) => {
      const [x, y] = pt(c), p = pauliAt(err, i);
      const shown = st.residual ? pauliAt(st.residual, i) : p;
      const cls = shown === 'I' ? 'qdot' : (st.residual && st.residualBad ? 'qdot err bad' : 'qdot err');
      el('circle', { cx: x, cy: y, r: R, class: cls }, paint);
      const label = rep ? String(st.values ? st.values[i] : err.x[i]) : (shown === 'I' ? '' : shown);
      if (label) el('text', { x, y: y + 6, class: 'qlab', 'text-anchor': 'middle' }, paint).textContent = label;
      const cp = st.correction ? pauliAt(st.correction, i) : 'I';
      if (cp !== 'I') {
        el('circle', { cx: x, cy: y, r: R + 6, class: 'corr' }, paint);
        if (!rep) el('text', { x: x + 16, y: y - 15, class: 'clab' }, paint).textContent = cp;
      }
      if (btns[i]) btns[i].setAttribute('aria-label', describe(i, st));
    });
  }

  function describe(i, st) {
    const where = rep ? `Qubit ${qubitName(i)}` : `Qubit at ${rcName(code, i)}`;
    const p = pauliAt(st.err, i);
    const what = rep ? (st.err.x[i] ? 'flipped' : 'not flipped') : (p === 'I' ? 'no error' : `${p} error`);
    const c = st.correction && pauliAt(st.correction, i) !== 'I' ? `, correction ${pauliAt(st.correction, i)}` : '';
    return `${where}: ${what}${c}`;
  }

  return { render, focus: () => btns[cur] && btns[cur].focus() };
}
