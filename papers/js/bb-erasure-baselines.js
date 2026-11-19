// Fig. 1 of papers/bb-erasure-baselines.html. Every value plotted comes from ../data/bb-erasure-baselines.json,
// written by _studio/tools/papers/extract_bb-erasure-baselines.py. Nothing moves until the reader does.
import { el, linScale, logScale, niceTicks, logTicks, markerPath, SHAPES } from './plot.js';
import { collapse, wilson } from './fss.js';

const $ = id => document.getElementById(id);
const nf = n => n.toLocaleString('en-US');
const f3 = v => Number(v.toPrecision(3)).toString();
const wer = q => q.fails / q.shots;
let D = null;

// ---------- drawing ----------
function frame(box, ratio) {
  const W = Math.max(280, Math.round(box.clientWidth || 600));
  const H = Math.round(Math.min(440, Math.max(260, W * ratio)));
  const narrow = W < 420;
  const m = { l: narrow ? 50 : 58, r: 12, t: 12, b: 48 };
  return { W, H, narrow, X0: m.l, X1: W - m.r, Y0: H - m.b, Y1: m.t };
}
function axes(svg, f, xs, ys, xt, yt, xlab, ylab, yfmt) {
  for (const v of yt) {
    el('line', { x1: f.X0, x2: f.X1, y1: ys(v), y2: ys(v), class: 'pc-grid' }, svg);
    yfmt(svg, f.X0 - 6, ys(v) + 4, v);
  }
  for (const v of xt) {
    el('line', { x1: xs(v), x2: xs(v), y1: f.Y0, y2: f.Y1, class: 'pc-grid' }, svg);
    el('text', { x: xs(v), y: f.Y0 + 18, 'text-anchor': 'middle', class: 'pc-tick' }, svg, f3(v));
  }
  el('path', { d: `M${f.X0} ${f.Y1}V${f.Y0}H${f.X1}`, class: 'pc-axis' }, svg);
  // a label is a string or a list of [text, 'sub' | 'sup' | ''] runs
  const lab = el('text', { x: (f.X0 + f.X1) / 2, y: f.H - 8, 'text-anchor': 'middle', class: 'pc-lab' }, svg);
  for (const [t, k] of typeof xlab === 'string' ? [[xlab, '']] : xlab)
    el('tspan', k ? { 'baseline-shift': k === 'sub' ? '-25%' : '40%', 'font-size': '12px' } : {}, lab, t);
  el('text', { x: 0, y: 0, transform: `translate(13 ${(f.Y0 + f.Y1) / 2}) rotate(-90)`, 'text-anchor': 'middle', class: 'pc-lab' }, svg, ylab);
}
function powTick(svg, x, y, v) {
  const t = el('text', { x, y, 'text-anchor': 'end', class: 'pc-tick' }, svg);
  const k = Math.round(Math.log10(v));
  if (k === 0) { t.textContent = '1'; return; }
  t.textContent = '10';
  el('tspan', { dy: -6 }, t, `−${-k}`);
}
const plainTick = (svg, x, y, v) => el('text', { x, y, 'text-anchor': 'end', class: 'pc-tick' }, svg, f3(v));
function series(g, pts, xs, ys, shape, dash, r) {
  if (pts.length > 1) el('path', { d: pts.map((q, i) => `${i ? 'L' : 'M'}${xs(q.x).toFixed(1)} ${ys(q.y).toFixed(1)}`).join(''), class: 'pc-line', 'stroke-dasharray': dash }, g);
  for (const q of pts) {
    if (q.lo != null) el('line', { x1: xs(q.x), x2: xs(q.x), y1: ys(Math.max(q.lo, 1e-6)), y2: ys(q.hi), class: 'pc-bar' }, g);
    el('path', { d: markerPath(shape, xs(q.x), ys(q.y), r), class: 'pc-mark' }, g);
  }
}
const DASH = { erasure_aware: '6 4', uninformed: '1.5 3' };

// (a) WER against erasure rate, log WER; points with no failures cannot sit on a log axis and are left out
function drawA() {
  const base = D.toric.find(t => t.id === state.base);
  const f = frame($('plot-a'), 0.78);
  const xd = base && base.id === 'uninformed' ? [0.29, 0.61] : [0.29, 0.51];
  const xs = linScale(xd, [f.X0, f.X1]), ys = logScale([1e-6, 1], [f.Y0, f.Y1]);
  const svg = el('svg', { viewBox: `0 0 ${f.W} ${f.H}`, width: f.W, height: f.H, role: 'img',
    'aria-label': `Word error rate, log scale, against erasure rate p from ${xd[0]} to ${xd[1]} for the five BB codes${base ? `, with the toric code under ${base.label.replace(/^./, c => c.toLowerCase())}` : ''}. The numbers are in the table below the figure.` });
  axes(svg, f, xs, ys, niceTicks(xd[0], xd[1], f.narrow ? 4 : 6).filter(v => v > xd[0]), logTicks(1e-6, 1), 'Erasure rate p', 'Word error rate', powTick);
  el('line', { x1: f.X0, x2: f.X1, y1: ys(0.1), y2: ys(0.1), class: 'pc-ref' }, svg);
  el('text', { x: f.X0 + 6, y: ys(0.1) - 5, class: 'pc-tick' }, svg, 'WER = 0.10');
  const pt = q => { const [lo, hi] = wilson(q.fails, q.shots); return { x: q.p, y: wer(q), lo, hi }; };
  if (base) {
    const g = el('g', { class: 'pc-base' }, svg);
    for (const s of base.sizes) series(g, s.points.filter(q => q.fails).map(pt), xs, ys, 'circle', DASH[base.id], 3.4);
  }
  D.bb.forEach((s, i) => series(el('g', { class: `s${i}` }, svg), s.points.filter(q => q.fails).map(pt), xs, ys, SHAPES[i], '', 4.2));
  $('plot-a').replaceChildren(svg);
}

// (b) the points the fit uses, against (p - p*_inf) N^(1/nu), with the polynomial fitted at these values
function drawB(c) {
  const f = frame($('plot-b'), 0.78);
  const xv = c.points.map(q => q.x), lo = Math.min(...xv), hi = Math.max(...xv), pad = (hi - lo) * 0.04 || 1;
  const xd = [lo - pad, hi + pad], ymax = Math.ceil(Math.max(...c.points.map(q => q.y)) * 1.08 / 0.05) * 0.05;
  const xs = linScale(xd, [f.X0, f.X1]), ys = linScale([0, ymax], [f.Y0, f.Y1]);
  const svg = el('svg', { viewBox: `0 0 ${f.W} ${f.H}`, width: f.W, height: f.H, role: 'img',
    'aria-label': `Scaling collapse at p-star-infinity ${state.ps.toFixed(3)} and nu ${state.nu.toFixed(2)}: word error rate against the scaled variable for the five BB codes, with the fitted cubic. Residual sum of squares ${c.rss.toPrecision(3)}.` });
  axes(svg, f, xs, ys, niceTicks(xd[0], xd[1], f.narrow ? 4 : 6), niceTicks(0, ymax, 5), [['(p − p*', ''], ['∞', 'sub'], [') N', ''], ['1/ν', 'sup']], 'Word error rate', plainTick);
  const n = 80, curve = Array.from({ length: n + 1 }, (_, k) => lo + (hi - lo) * k / n);
  el('path', { d: curve.map((x, k) => `${k ? 'L' : 'M'}${xs(x).toFixed(1)} ${Math.max(f.Y1, Math.min(f.Y0, ys(c.fit.evaluate(x)))).toFixed(1)}`).join(''), class: 'pc-fit' }, svg);
  D.bb.forEach((s, i) => series(el('g', { class: `s${i}` }, svg), c.points.filter(q => q.N === s.N).map(q => ({ x: q.x, y: q.y })), xs, ys, SHAPES[i], '', 4.2));
  $('plot-b').replaceChildren(svg);
}

function swatch(cls, shape, dash, hollow) {
  const s = el('svg', { width: 30, height: 14, viewBox: '0 0 30 14', 'aria-hidden': 'true', class: cls });
  el('line', { x1: 1, x2: 29, y1: 7, y2: 7, class: 'pc-line', 'stroke-dasharray': dash }, s);
  if (shape) el('path', { d: markerPath(shape, 15, 7, hollow ? 3.4 : 4.2), class: 'pc-mark' }, s);
  return s;
}
function legend() {
  const items = D.bb.map((s, i) => { const e = document.createElement('span'); e.append(swatch(`s${i}`, SHAPES[i], ''), `BB ${s.L}×${s.M}, N = ${s.N}, K = ${s.K}`); return e; });
  const base = D.toric.find(t => t.id === state.base);
  if (base) {
    const e = document.createElement('span'), Ns = base.sizes.map(s => s.N);
    e.append(swatch('pc-base', 'circle', DASH[base.id], true), `Toric, ${base.label.replace(/^./, c => c.toLowerCase())}, N = ${Ns[0]} to ${Ns[Ns.length - 1]}, K = 2`);
    items.push(e);
  }
  const fit = document.createElement('span'), s = swatch('', null, '7 4');
  s.querySelector('line').setAttribute('class', 'pc-fit');
  fit.append(s, 'Fitted cubic, panel (b)');
  items.push(fit);
  $('fss-legend').replaceChildren(...items);
}

// ---------- the data table ----------
function table() {
  const win = D.fss_fit.p_window;
  const bb = D.bb.map(s => `<tr><th scope="colgroup" colspan="5" class="pc-group">BB ${s.L}&times;${s.M}, N = ${s.N}, K = ${s.K}; p* = ${s.p_star.toFixed(4)} [${s.p_star_ci95.map(v => v.toFixed(4)).join(', ')}]</th></tr>` +
    s.points.map(q => `<tr><td>${q.p}</td><td>${nf(q.fails)}</td><td>${nf(q.shots)}</td><td>${wer(q).toPrecision(4)}</td><td>${Math.abs(q.p - s.center) <= win ? (q.fit_count > 1 ? `yes, ${q.fit_count} times` : 'yes') : 'no'}</td></tr>`).join('')).join('');
  const head = last => `<thead><tr><th scope="col">p</th><th scope="col">Failures</th><th scope="col">Shots</th><th scope="col">WER</th>${last}</tr></thead>`;
  let html = `<div class="pc-scroll"><table><caption>BB codes, BP-OSD; p* is the paper's pseudo-threshold with its 95% bootstrap interval. The last column says whether the FSS fit uses the point.</caption>${head('<th scope="col">In fit</th>')}<tbody>${bb}</tbody></table></div>`;
  for (const t of D.toric) {
    const rows = t.sizes.map(s => `<tr><th scope="colgroup" colspan="4" class="pc-group">Toric, L = ${s.L}, N = ${s.N}, K = ${s.K}</th></tr>` +
      s.points.map(q => `<tr><td>${q.p}</td><td>${nf(q.fails)}</td><td>${nf(q.shots)}</td><td>${wer(q).toPrecision(4)}</td></tr>`).join('')).join('');
    html += `<div class="pc-scroll"><table><caption>Toric code, ${t.label.replace(/^./, c => c.toLowerCase())}, ${nf(t.shots_per_point)} shots per point (${t.file.split('/').pop()})</caption>${head('')}<tbody>${rows}</tbody></table></div>`;
  }
  $('fss-table').innerHTML = html;
}

// ---------- state and controls ----------
const state = { base: 'erasure_aware', ps: 0.47, nu: 2 };
let sayTimer = 0;
function say(text, now) {
  clearTimeout(sayTimer);
  if (now) $('fss-status').textContent = text;
  else sayTimer = setTimeout(() => { $('fss-status').textContent = text; }, 600);
}
function rssAt(ps, nu) { return collapse(D.bb, ps, nu, D.fss_fit.p_window, D.fss_fit.poly_degree).rss; }

function render() {
  const c = collapse(D.bb, state.ps, state.nu, D.fss_fit.p_window, D.fss_fit.poly_degree);
  drawA(); drawB(c); legend();
  $('out-ps').value = state.ps.toFixed(3); $('out-nu').value = state.nu.toFixed(2);
  const paper = rssAt(D.paper_fit.p_star_inf, D.paper_fit.nu);
  $('fss-readout').innerHTML = `Residual sum of squares: <b>${c.rss.toPrecision(3)}</b>. At the paper&rsquo;s fit (p*<sub>&infin;</sub> = ${D.paper_fit.p_star_inf}, &nu; = ${D.paper_fit.nu}): ${paper.toPrecision(3)}.`;
  return { c, paper };
}
function collapseWords(r) {
  const ratio = r.c.rss / r.paper;
  const how = ratio < 1.05 ? 'as low as at the paper’s fit: the five sizes lie closest to one curve here'
    : ratio < 2 ? `${ratio.toFixed(1)} times the value at the paper’s fit` : `${ratio.toFixed(1)} times the value at the paper’s fit: the sizes do not line up`;
  return `p-star-infinity ${state.ps.toFixed(3)}, nu ${state.nu.toFixed(2)}. Residual sum of squares ${r.c.rss.toPrecision(3)}, ${how}.`;
}
function baseWords() {
  const t = D.toric.find(t => t.id === state.base);
  if (!t) return 'Panel (a) shows the five BB codes only.';
  const w = t.sizes.flatMap(s => s.points.map(wer));
  return `Panel (a) adds the toric code under ${t.label.replace(/^./, c => c.toLowerCase())}, ${t.sizes.length} sizes, ${nf(t.shots_per_point)} shots per point; its word error rate runs from ${f3(Math.min(...w))} to ${f3(Math.max(...w))} over the rates shown.`;
}

function init(data) {
  D = data;
  for (const id of ['fss-base', 'fss-ctl', 'fss-legend', 'fss-data']) $(id).hidden = false;
  $('fss-fallback').hidden = true;
  $('fss-src').textContent = ` at commit ${D.source.commit.slice(0, 7)}, extracted ${D.source.extracted}`;
  const sp = $('in-ps'), sn = $('in-nu');
  sp.value = state.ps; sn.value = state.nu;
  sp.addEventListener('input', () => { state.ps = Number(sp.value); say(collapseWords(render())); });
  sn.addEventListener('input', () => { state.nu = Number(sn.value); say(collapseWords(render())); });
  $('fss-paper').addEventListener('click', () => {
    state.ps = D.paper_fit.p_star_inf; state.nu = D.paper_fit.nu;
    sp.value = state.ps; sn.value = state.nu;
    say(`Set to the paper's fit. ${collapseWords(render())}`, true);
  });
  document.querySelectorAll('input[name=fss-base]').forEach(i => {
    i.checked = i.value === state.base;
    i.addEventListener('change', () => { state.base = i.value; render(); say(baseWords(), true); });
  });
  table();
  say(`${baseWords()} Panel (b) starts away from the fit: ${collapseWords(render())} Move the sliders, or press Use the paper’s fit.`, true);
  document.addEventListener('tp-theme', render);
  let lastW = 0;
  new ResizeObserver(() => { const w = $('plot-a').clientWidth; if (Math.abs(w - lastW) > 1) { lastW = w; render(); } }).observe($('plot-a'));
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
fetch(new URL('../data/bb-erasure-baselines.json', import.meta.url))
  .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
  .then(init)
  .catch(() => say('The figure data could not be loaded. The text around the figure states the main result.', true));
