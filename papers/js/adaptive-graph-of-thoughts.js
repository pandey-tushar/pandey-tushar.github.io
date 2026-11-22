// Fig. 1 of papers/adaptive-graph-of-thoughts.html. Every value shown comes from ../data/adaptive-graph-of-thoughts.json,
// written by _studio/tools/papers/extract_adaptive-graph-of-thoughts.py from the paper's own tables. Nothing moves until the reader does.
import { el, linScale, niceTicks, markerPath } from './plot.js';
import { NAMES, METRICS, datasets, options, resolve, pick, axisMax, describe } from './agot-logic.js';

const $ = id => document.getElementById(id);
const SHAPE = { IO: 'circle', CoT: 'square', AIoT: 'triangle', AGoT: 'diamond' };
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const sub = s => esc(s).replace(/_([A-Z0-9])\b/g, '<sub>$1</sub>');
let D = null;
const state = { dataset: 'GPQA_S', model: 'gpt-4o-mini', metric: 'accuracy' };

// ---------- drawing ----------
function draw(v) {
  const box = $('agot-plot');
  const W = Math.max(280, Math.round(box.clientWidth || 600)), narrow = W < 420;
  const hasDelta = v.ranked.some(e => e.delta != null);
  const rowH = 46, n = v.ranked.length;
  const m = { l: 56, r: 40 + (hasDelta ? (narrow ? 62 : 76) : 0), t: 30, b: 50 };
  const H = m.t + n * rowH + m.b, X0 = m.l, X1 = W - m.r, Y0 = H - m.b, Y1 = m.t;
  const top = axisMax(Math.max(...v.ranked.map(e => e.score)));
  const xs = linScale([0, top], [X0, X1]);
  const io = v.ranked.find(e => e.method === 'IO');
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'img',
    'aria-label': `Dot plot of ${METRICS[v.sel.metric]} in percent, from 0 to ${top}, for ${v.ranked.map(e => `${e.method} ${e.text}`).join(', ')}. The numbers are in the table below the figure.` });
  for (const t of niceTicks(0, top, narrow ? 4 : 5)) {
    el('line', { x1: xs(t), x2: xs(t), y1: Y1 - 6, y2: Y0, class: 'pc-grid' }, svg);
    el('text', { x: xs(t), y: Y0 + 18, 'text-anchor': 'middle', class: 'pc-tick' }, svg, String(t));
  }
  el('path', { d: `M${X0} ${Y1 - 6}V${Y0}H${X1}`, class: 'pc-axis' }, svg);
  el('text', { x: (X0 + X1) / 2, y: H - 8, 'text-anchor': 'middle', class: 'pc-lab' }, svg, `${METRICS[v.sel.metric]}, %`);
  el('line', { x1: xs(io.score), x2: xs(io.score), y1: Y1 - 6, y2: Y0, class: 'pc-ref' }, svg);
  if (hasDelta) el('text', { x: W - 4, y: Y1 - 12, 'text-anchor': 'end', class: 'pc-tick' }, svg, 'vs IO');
  v.ranked.forEach((e, i) => {
    const y = Y1 + rowH * (i + 0.5), x = xs(e.score), b = e.method === 'AGoT' ? ' agot-b' : '';
    const g = el('g', { class: `m-${e.method.toLowerCase()}` }, svg);
    el('text', { x: X0 - 10, y: y + 4.5, 'text-anchor': 'end', class: 'pc-lab' + b }, g, e.method);
    el('line', { x1: X0, x2: x, y1: y, y2: y, class: 'pc-line' }, g);
    el('path', { d: markerPath(SHAPE[e.method], x, y, 6), class: 'pc-mark' }, g);
    el('text', { x: x + 11, y: y + 4.5, class: 'agot-val' + b }, g, e.text);
    if (hasDelta) el('text', { x: W - 4, y: y + 4.5, 'text-anchor': 'end', class: 'agot-delta' + b }, g, e.deltaText ?? (e.method === 'IO' ? 'baseline' : ''));
  });
  box.replaceChildren(svg);
}

// ---------- controls ----------
// built once, so keyboard focus stays put; set() only checks, disables and hides
function radios(fs, key, values, label) {
  for (const v of values) {
    const l = document.createElement('label'), i = document.createElement('input'), s = document.createElement('span');
    i.type = 'radio'; i.name = fs.id; i.value = v;
    i.addEventListener('change', () => set({ [key]: v }));
    s.textContent = label(v);
    l.append(i, s); fs.append(l);
  }
}
function controls() {
  const o = options(D, state.dataset);
  for (const i of $('agot-model').querySelectorAll('input')) { i.disabled = !o.models.includes(i.value); i.checked = i.value === state.model; }
  // only the metrics this benchmark has, so the set stays short
  for (const i of $('agot-metric').querySelectorAll('input')) { i.parentNode.hidden = !o.metrics.includes(i.value); i.checked = i.value === state.metric; }
}

let view = null;
function render() { if (view) draw(view); }
function set(change) {
  const r = resolve(D, { ...state, ...change });
  Object.assign(state, r.sel);
  view = pick(D, state);
  controls();
  render();
  const note = r.changed.includes('model') ? `The paper reports gpt-4o only on shuffled GPQA Diamond, so this shows ${state.model}. ` : '';
  $('agot-status').textContent = note + describe(D, view);
}

// ---------- the data table ----------
const head = c => c.startsWith('delta:') ? `&Delta; ${c.slice(6)} vs IO` : esc(c);
const CAP = {
  1: 'Table 1 of the paper: GPQA Diamond accuracy (%) with answer options in the default order (D) and shuffled (S), for two models.',
  2: 'Table 2 of the paper: gpt-4o-mini. Retrieval rows are LAAS, crossword rows letter and word accuracy; &Delta; is the paper&rsquo;s percent change against IO.',
  3: 'Table 3 of the paper: gpt-4o-mini on the retrieval sets, by metric. It has no CoT column and no percent changes.',
};
function table() {
  $('agot-table').innerHTML = D.tables.map(t => {
    const rows = t.rows.map(r => `<tr>${r.cells.map((c, i) => {
      const txt = sub(c.replace(/^-/, '−')), bold = r.bold.includes(c) && /^\d/.test(c);
      return i < 2 && !/^[+-]?\d/.test(c) ? `<th scope="row">${txt}</th>` : `<td>${bold ? `<b>${txt}</b>` : txt}</td>`;
    }).join('')}</tr>`).join('');
    return `<div class="pc-scroll"><table><caption>${CAP[t.number]} Bold as in the paper.</caption><thead><tr>${t.columns.map(c => `<th scope="col">${head(c)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`;
  }).join('');
}

function init(data) {
  D = data;
  for (const id of ['agot-ctl', 'agot-data']) $(id).hidden = false;
  $('agot-fallback').hidden = true;
  $('agot-src').textContent = `, fetched ${D.source.fetched}`;
  const sel = $('agot-ds'), groups = {};
  for (const d of datasets(D)) {
    if (!groups[d.category]) { groups[d.category] = document.createElement('optgroup'); groups[d.category].label = d.category; sel.append(groups[d.category]); }
    const o = document.createElement('option'); o.value = d.id; o.textContent = NAMES[d.id]; groups[d.category].append(o);
  }
  sel.value = state.dataset;
  sel.addEventListener('change', () => set({ dataset: sel.value }));
  radios($('agot-model'), 'model', [...new Set(D.tables.flatMap(t => t.rows.map(r => r.model)))], v => v);
  radios($('agot-metric'), 'metric', ['accuracy', 'letter accuracy', 'word accuracy', 'LAAS', 'EM', 'F1'], v => METRICS[v]);
  table();
  set({});
  document.addEventListener('tp-theme', render);
  let lastW = 0;
  new ResizeObserver(() => { const w = $('agot-plot').clientWidth; if (Math.abs(w - lastW) > 1) { lastW = w; render(); } }).observe($('agot-plot'));
}

// ---------- citation copy ----------
function initCopy() {
  const btn = $('bib-copy'), msg = $('bib-msg');
  btn.hidden = false;
  btn.addEventListener('click', async () => {
    const text = $('bib').textContent;
    try { await navigator.clipboard.writeText(text); msg.textContent = 'Copied the BibTeX entry.'; }
    catch {
      const r = document.createRange(); r.selectNodeContents($('bib'));
      const s = getSelection(); s.removeAllRanges(); s.addRange(r);
      msg.textContent = 'Copying was blocked; the entry is selected, press Ctrl+C or Cmd+C.';
    }
  });
}

initCopy();
fetch(new URL('../data/adaptive-graph-of-thoughts.json', import.meta.url))
  .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
  .then(init)
  .catch(() => { $('agot-status').textContent = 'The figure data could not be loaded. The text around the figure states the main results.'; });
