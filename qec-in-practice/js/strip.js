// Gate-block strip: phase names above one block per gate layer, labelled with gate symbols.
import { GATE } from './patch.js';

export const BW = 38; // px per gate layer, shared with the live heatmap

export function phasesOf(ops, T) {
  const out = [];
  for (let t = 0; t <= T; t++) {
    const name = (ops.find((o) => o.t === t) || {}).phase || '';
    const last = out[out.length - 1];
    if (last && last.name === name) last.t1 = t;
    else out.push({ name, t0: t, t1: t });
  }
  return out;
}

export function blockLabel(gates) {
  const n = {};
  for (const g of gates) { const s = GATE[g.gate] || g.gate.toUpperCase(); n[s] = (n[s] || 0) + 1; }
  return Object.entries(n).map(([s, c]) => (c > 1 ? `${s}×${c}` : s));
}

// An encoder shown as one step (lessons after the first) is labelled 'enc' instead of its twelve CNOTs.
export const cellLabel = (L) => (L.summary ? ['enc'] : blockLabel(L.gates));

// The name a phase goes by on the page: the readout rotation is called by its gate, H on the patch, in the
// strip, the step label and the written-out steps alike (_studio/tools/lesson_text.py phase_label mirrors this).
export const phaseLabel = (name) => name.replace(/^readout rotation (\S+) \(\w\)$/, 'H on $1');

// Short phase names for the strip; the page name stays in the tooltip and in the layer label.
export function shortPhase(name) {
  return phaseLabel(name).replace(/^prepare /, 'prep ').replace(/^transversal CNOT /, 'CNOT ')
    .replace(/^measure$/, 'meas').replace(/^inject .*/, 'error');
}

// The player's position label. Position 0 shows the state before the first step, so it gets its own name.
export function whereText(pos, T, phase) {
  if (pos >= T + 1) return `All ${T + 1} steps done`;
  if (pos <= 0) return `Start: before step 1 of ${T + 1}`;
  return `Step ${Math.min(Math.floor(pos), T) + 1} of ${T + 1}: ${phaseLabel(phase)}`;
}

// Hide a phase name that does not fit its span instead of cutting it.
export function fitPhaseLabels(root) {
  for (const d of root.querySelectorAll('.phase')) {
    d.classList.remove('tight');
    if (d.scrollWidth > d.clientWidth + 1) d.classList.add('tight');
  }
}

// Phase row and block row for a list of layers [{phase, gates:[{gate,q,role}]}].
// fluid: blocks share the root's width (lesson strip); otherwise BW px each (live heatmap).
export function drawStrip(root, layers, phases, onPick, fluid = false) {
  const n = layers.length;
  const at = (t) => (fluid ? `${(100 * t) / n}%` : `${t * BW}px`);
  root.classList.toggle('fluid', fluid);
  root.style.width = fluid ? '' : `${n * BW}px`;
  // fluid: wide enough that every short phase name fits over its blocks (12px mono, about 7.5px a character),
  // so on a phone the strip scrolls with readable names instead of squeezing them out
  const need = Math.max(34, ...phases.map((p) => Math.ceil((shortPhase(p.name).length * 7.5 + 14) / (p.t1 - p.t0 + 1))));
  root.style.minWidth = fluid ? `${n * need}px` : '';
  const prow = document.createElement('div');
  prow.className = 'phase-row';
  for (const p of phases) {
    const d = document.createElement('div');
    d.className = 'phase';
    d.style.left = at(p.t0);
    d.style.width = at(p.t1 - p.t0 + 1);
    d.textContent = shortPhase(p.name);
    d.title = phaseLabel(p.name);
    prow.appendChild(d);
  }
  const brow = document.createElement('div');
  brow.className = 'block-row';
  const cells = layers.map((L, t) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'gblock' + (L.gates.some((g) => g.role === 'inject') ? ' inject' : '');
    b.innerHTML = cellLabel(L).map((s) => `<span>${s}</span>`).join('');
    b.title = `Step ${t + 1}: ${phaseLabel(L.phase)}`;
    b.setAttribute('aria-label', `Step ${t + 1}, ${phaseLabel(L.phase)}, ${cellLabel(L).join(' ')}`);
    if (onPick) b.addEventListener('click', () => onPick(t));
    else b.tabIndex = -1;
    brow.appendChild(b);
    return b;
  });
  root.append(prow, brow);
  requestAnimationFrame(() => fitPhaseLabels(root));
  return cells;
}
