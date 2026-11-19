// The threshold lesson: three Monte Carlo figures on the engine in ./qec/, run in a small pool of module workers.
// Nothing runs until the reader presses Run. Pure helpers (crossing, Lambda fit, scales, queue) live in
// threshold-math.js.
import { binomialError, crossing, fitLambda, logScale, linScale, logTicks, logSpace, planQueue } from './threshold-math.js';

const $ = id => document.getElementById(id);
const SVGNS = 'http://www.w3.org/2000/svg';
const reduced = matchMedia('(prefers-reduced-motion: reduce)');

// Defaults per measurement setting and noise model, chosen from runs of this decoder so the crossing sits inside
// the range with room on both sides, and the Lambda p sits well left of it.
const DEFAULTS = {
  cc: { bitflip: [0.03, 0.15, 0.03], depolarizing: [0.04, 0.2, 0.04], shots: 20000, lamShots: 50000, chunk: 2000 },
  phen: { bitflip: [0.006, 0.04, 0.008], depolarizing: [0.008, 0.05, 0.01], shots: 10000, lamShots: 20000, chunk: 500 },
};
const SHOTS = [2000, 5000, 10000, 20000, 50000, 100000];
const LAM_SHOTS = [10000, 20000, 50000, 100000, 200000];
const REF_SHOTS = [5000, 10000, 20000, 50000];
const MARK = { 3: 'circle', 5: 'square', 7: 'triangle', 9: 'diamond', 11: 'down' };
const DASH = { 3: '1.5 3', 5: '6 3', 7: '', 9: '10 3 2 3', 11: '' };
const MODEL_WORDS = { bitflip: 'bit-flip noise', depolarizing: 'depolarizing noise' };
const MODE_WORDS = { cc: 'perfect measurement', phen: 'noisy measurement, d rounds' };

const nf = n => n.toLocaleString('en-US');
const fp = p => String(Number(p.toPrecision(3)));
function fr(r, digits = 3) {
  if (r == null) return '';
  if (r === 0) return '0';
  if (r >= 0.001) return r.toPrecision(digits);
  const [m, e] = r.toExponential(digits - 1).split('e');
  return `${m} &times; 10<sup>&minus;${-Number(e)}</sup>`;
}
const secs = ms => `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)} s`;

// ---------- worker pool ----------
class Runner {
  constructor() { this.pool = []; this.active = null; }
  size() { return Math.min(4, Math.max(1, (navigator.hardwareConcurrency || 2) - 1)); }
  start(jobs, onChunk, onEnd) {
    this.stop(true);
    this.active = { jobs, next: 0, inflight: 0, last: new Map(), onChunk, onEnd, t0: performance.now() };
    if (!jobs.length) return this.finish({});
    while (this.pool.length < Math.min(this.size(), jobs.length)) this.pool.push(this.make());
    for (const w of this.pool) this.feed(w);
  }
  make() {
    const w = new Worker(new URL('./qec/worker.js', import.meta.url), { type: 'module' });
    w.onmessage = e => this.msg(w, e.data);
    w.onerror = e => { e.preventDefault(); this.kill(); this.finish({ error: true }); };
    return w;
  }
  feed(w) {
    const r = this.active;
    if (!r) return;
    if (r.next >= r.jobs.length) { w.job = null; if (!r.inflight) this.finish({}); return; }
    const id = r.next++, j = r.jobs[id];
    w.job = id; r.inflight++;
    w.postMessage({ id, kind: 'surface', d: j.d, p: j.p, model: j.model, shots: j.shots, seed: j.seed, rounds: j.rounds, chunk: j.chunk });
  }
  msg(w, m) {
    const r = this.active;
    if (!r || w.job !== m.id) return;
    const prev = r.last.get(m.id) || { shots: 0, failures: 0 };
    r.last.set(m.id, m);
    r.onChunk(r.jobs[m.id], m.shots - prev.shots, m.failures - prev.failures);
    if (m.done) { r.inflight--; this.feed(w); }
  }
  kill() { for (const w of this.pool) w.terminate(); this.pool = []; }
  finish(info) {
    const r = this.active;
    if (!r) return;
    this.active = null;
    r.onEnd({ ...info, ms: performance.now() - r.t0 });
  }
  stop(silent) {
    if (!this.active) return;
    this.kill();
    if (silent) this.active = null; else this.finish({ stopped: true });
  }
}
const runner = new Runner();
let runCount = 0, totalShots = 0, busy = null;

// ---------- SVG plotting ----------
function el(tag, attrs, parent, text) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (text != null) e.textContent = text;
  if (parent) parent.appendChild(e);
  return e;
}
function markerPath(shape, x, y, r) {
  switch (shape) {
    case 'square': { const s = r * 0.88; return `M${x - s} ${y - s}h${2 * s}v${2 * s}h${-2 * s}Z`; }
    case 'triangle': return `M${x} ${y - r * 1.2}L${x + r * 1.1} ${y + r * 0.75}L${x - r * 1.1} ${y + r * 0.75}Z`;
    case 'down': return `M${x} ${y + r * 1.2}L${x + r * 1.1} ${y - r * 0.75}L${x - r * 1.1} ${y - r * 0.75}Z`;
    case 'diamond': return `M${x} ${y - r * 1.3}L${x + r * 1.05} ${y}L${x} ${y + r * 1.3}L${x - r * 1.05} ${y}Z`;
    default: return `M${x - r} ${y}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`;
  }
}
// A tick label: plain decimals down to 0.001, powers of ten below.
function tickLabel(parent, x, y, v, anchor) {
  const t = el('text', { x, y, 'text-anchor': anchor, class: 'thr-tick' }, parent);
  if (v >= 0.001) { t.textContent = fp(v); return; }
  const k = Math.round(Math.log10(v));
  if (Math.abs(10 ** k - v) / v > 1e-9) { t.textContent = fp(v); return; }
  t.textContent = '10';
  el('tspan', { dy: -6 }, t, `−${-k}`);
}
// p ticks on a log axis: add mantissas in order of plainness while labels keep at least minPx apart.
function pTicks(scale, a, b, minPx) {
  const levels = [[1], [2, 5], [3], [4, 6, 8], [1.5, 7]];
  let best = [], set = [];
  for (const lv of levels) {
    set = set.concat(lv);
    const ticks = [];
    for (let k = Math.floor(Math.log10(a)); k <= Math.ceil(Math.log10(b)); k++)
      for (const m of set) { const v = Number((m * 10 ** k).toPrecision(6)); if (v >= a && v <= b) ticks.push(v); }
    ticks.sort((u, v) => u - v);
    const ok = ticks.every((v, i) => !i || scale(v) - scale(ticks[i - 1]) >= minPx);
    if (!ok) break;
    best = ticks;
  }
  return best;
}
function yDomain(vals, fallback) {
  const pos = vals.filter(v => v > 0);
  if (!pos.length) return fallback;
  let lo = Math.min(...pos) / 1.5, hi = Math.min(1, Math.max(...pos) * 1.5);
  if (hi / lo < 10) { const g = Math.sqrt(hi * lo); lo = g / Math.sqrt(10); hi = Math.min(1, g * Math.sqrt(10)); lo = Math.min(lo, hi / 10); }
  return [lo, hi];
}

// spec: { x: {kind, domain, ticks:[{v,label?}], label}, yVals, yFallback, yLabel, series:[{d, pts:[{x,f,n}], line}],
//         refs:[{d,x,y}], crosses:[{a,b,lo,hi,p,loOpen,hiOpen}], fit:{lambda,slope,intercept,x0,x1}, empty, aria }
function drawPlot(box, spec, small) {
  const W = Math.max(280, Math.round(box.clientWidth || 600));
  const H = small ? Math.round(Math.min(360, Math.max(250, W * 0.5))) : Math.round(Math.min(520, Math.max(320, W * 0.6)));
  const narrow = W < 480;
  const m = { l: narrow ? 54 : 64, r: small ? 16 : (narrow ? 44 : 56), t: 14, b: 50 };
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'img', 'aria-label': spec.aria });
  const X0 = m.l, X1 = W - m.r, Y0 = H - m.b, Y1 = m.t;
  const xs = spec.x.kind === 'log' ? logScale(spec.x.domain, [X0, X1]) : linScale(spec.x.domain, [X0, X1]);
  const yd = yDomain(spec.yVals, spec.yFallback), ys = logScale(yd, [Y0, Y1]);
  const clipY = v => Math.max(Y1, Math.min(Y0, v));

  // y grid and ticks
  const yt = logTicks(yd[0], yd[1]);
  const perDecade = (Y0 - Y1) / Math.log10(yd[1] / yd[0]);
  for (const v of yt.minor) {
    el('line', { x1: X0, x2: X1, y1: ys(v), y2: ys(v), class: 'thr-grid-minor' }, svg);
    if (perDecade >= 110 && v >= 0.001) tickLabel(svg, X0 - 6, ys(v) + 4, v, 'end');
  }
  for (const v of yt.major) {
    el('line', { x1: X0, x2: X1, y1: ys(v), y2: ys(v), class: 'thr-grid' }, svg);
    tickLabel(svg, X0 - 6, ys(v) + 4, v, 'end');
  }
  // x grid and ticks
  const xt = spec.x.ticks || pTicks(xs, spec.x.domain[0], spec.x.domain[1], narrow ? 34 : 42).map(v => ({ v }));
  for (const t of xt) {
    el('line', { x1: xs(t.v), x2: xs(t.v), y1: Y0, y2: Y1, class: 'thr-grid' }, svg);
    el('line', { x1: xs(t.v), x2: xs(t.v), y1: Y0, y2: Y0 + 5, class: 'thr-axis' }, svg);
    el('text', { x: xs(t.v), y: Y0 + 19, 'text-anchor': 'middle', class: 'thr-tick' }, svg, t.label ?? fp(t.v));
  }
  el('path', { d: `M${X0} ${Y1}V${Y0}H${X1}`, class: 'thr-axis' }, svg);
  el('text', { x: (X0 + X1) / 2, y: H - 8, 'text-anchor': 'middle', class: 'thr-lab' }, svg, spec.x.label);
  el('text', { x: 0, y: 0, transform: `translate(14 ${(Y0 + Y1) / 2}) rotate(-90)`, 'text-anchor': 'middle', class: 'thr-lab' }, svg, spec.yLabel);

  const plot = el('g', {}, svg);
  if (spec.fit) {
    const { slope, intercept, x0, x1 } = spec.fit;
    const yA = Math.exp(intercept + slope * x0), yB = Math.exp(intercept + slope * x1);
    el('line', { x1: xs(x0), x2: xs(x1), y1: clipY(ys(yA)), y2: clipY(ys(yB)), class: 'thr-fit' }, plot);
  }
  const ends = [];
  for (const s of spec.series) {
    const g = el('g', { class: `s${s.d}` }, plot);
    const pts = s.pts.filter(q => q.n).map(q => ({ ...q, e: binomialError(q.f, q.n) })).sort((u, v) => u.x - v.x);
    const lit = pts.filter(q => q.f > 0);
    if (s.line && lit.length > 1)
      el('path', { d: lit.map((q, i) => `${i ? 'L' : 'M'}${xs(q.x).toFixed(1)} ${ys(q.e.rate).toFixed(1)}`).join(''), class: 'thr-line', 'stroke-dasharray': DASH[s.d] }, g);
    for (const q of pts) {
      const x = xs(q.x);
      if (q.f === 0) {
        const y = clipY(ys(q.e.upper95));
        el('path', { d: `M${x} ${y - 6}V${y + 5}M${x - 4} ${y + 1}L${x} ${y + 5}L${x + 4} ${y + 1}`, class: 'thr-refmark' }, g);
        continue;
      }
      el('line', { x1: x, x2: x, y1: clipY(q.e.lo > 0 ? ys(q.e.lo) : Y0), y2: clipY(ys(q.e.hi)), class: 'thr-bar' }, g);
      el('path', { d: markerPath(MARK[s.d], x, ys(q.e.rate), small ? 5.5 : 4.4), class: 'thr-mark' }, g);
    }
    if (s.line && lit.length) { const q = lit[lit.length - 1]; ends.push({ d: s.d, x: xs(q.x), y: ys(q.e.rate) }); }
  }
  for (const r of spec.refs || []) {
    const x = xs(r.x), y = ys(r.y), k = 5;
    el('path', { d: `M${x - k} ${y - k}L${x + k} ${y + k}M${x + k} ${y - k}L${x - k} ${y + k}`, class: `thr-refmark s${r.d}` }, plot);
  }
  // direct labels at the right end of each curve, pushed apart vertically
  ends.sort((u, v) => u.y - v.y);
  for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 15) ends[i].y = ends[i - 1].y + 15;
  for (const e of ends) el('text', { x: Math.min(e.x + 9, W - 2), y: Math.min(Y0, e.y) + 4, class: `thr-dlab s${e.d}`, 'text-anchor': e.x + 9 + 34 > W ? 'end' : 'start' }, plot, `d=${e.d}`);
  // crossing ranges along the bottom of the plot
  (spec.crosses || []).forEach((c, k) => {
    const y = Y0 - 12 - 16 * k, a = xs(Math.max(c.lo, spec.x.domain[0])), b = xs(Math.min(c.hi, spec.x.domain[1])), x = xs(c.p);
    el('line', { x1: a, x2: b, y1: y, y2: y, class: 'thr-cross' }, plot);
    el('line', { x1: x, x2: x, y1: y - 6, y2: y + 6, class: 'thr-cross-tick' }, plot);
    const left = a - 6 > X0 + 40;
    el('text', { x: left ? a - 6 : b + 6, y: y + 4, 'text-anchor': left ? 'end' : 'start', class: 'thr-cross-lab' }, plot, `${c.a} and ${c.b}`);
  });
  if (spec.fitLabel) el('text', { x: X1 - 6, y: Y1 + 16, 'text-anchor': 'end', class: 'thr-lab' }, svg, spec.fitLabel);
  if (spec.empty) el('text', { x: (X0 + X1) / 2, y: (Y0 + Y1) / 2, 'text-anchor': 'middle', class: 'thr-empty' }, svg, spec.empty);
  box.replaceChildren(svg);
}

function legendSwatch(d) {
  const s = el('svg', { width: 30, height: 14, viewBox: '0 0 30 14', 'aria-hidden': 'true', class: `s${d}` });
  el('line', { x1: 1, x2: 29, y1: 7, y2: 7, class: 'thr-line', 'stroke-dasharray': DASH[d] }, s);
  el('path', { d: markerPath(MARK[d], 15, 7, 4.4), class: 'thr-mark' }, s);
  return s;
}

function schedule(fig) {
  if (fig.pending) return;
  fig.pending = true;
  const go = () => { fig.pending = false; fig.render(); };
  if (reduced.matches) setTimeout(go, 300); else requestAnimationFrame(go);
}

// ---------- controls ----------
const ctl = {
  mode: () => document.querySelector('input[name=thr-mode]:checked').value,
  model: () => $('thr-model').value,
  ds: () => [...document.querySelectorAll('input[name=thr-d]:checked')].map(i => Number(i.value)),
};
function fillSelect(sel, values, chosen) {
  sel.replaceChildren(...values.map(v => { const o = new Option(nf(v), v); o.selected = v === chosen; return o; }));
}
function applyDefaults() {
  const mode = ctl.mode(), D = DEFAULTS[mode], [a, b, lam] = D[ctl.model()];
  $('thr-pmin').value = a; $('thr-pmax').value = b; $('lam-p').value = lam;
  fillSelect($('thr-shots'), SHOTS, D.shots);
  fillSelect($('lam-shots'), LAM_SHOTS, D.lamShots);
  lambda.note();
}
const configKey = (mode, model) => `${mode}|${model}`;
const configWords = (mode, model) => `${MODE_WORDS[mode][0].toUpperCase()}${MODE_WORDS[mode].slice(1)}, ${MODEL_WORDS[model]}`;

// A Run or Stop button that disables itself while focused hands focus to its partner, so the keyboard stays in the figure.
function setBusy(name) {
  const had = document.activeElement;
  busy = name;
  for (const f of ['thr', 'lam', 'ref']) {
    $(`${f}-run`).disabled = !!name || (f === 'ref' && !REF);
    $(`${f}-stop`).disabled = name !== f;
  }
  const m = had && had.disabled && /^(thr|lam|ref)-(run|stop)$/.exec(had.id);
  if (m) $(`${m[1]}-${m[2] === 'run' ? 'stop' : 'run'}`).focus();
}
function showTotal() { $('thr-total').textContent = `Shots simulated on this page: ${nf(totalShots)}`; }

// ---------- reference data ----------
let REF = null;
const refRows = () => (REF ? REF.rows.filter(r => r.kind === 'surface') : []);

// ---------- Fig. 1: the threshold plot ----------
const latestCross = new Map();
const history = [];
const main = {
  run: null,
  render() {
    const r = this.run, box = $('thr-plot');
    if (!r) {
      drawPlot(box, {
        x: { kind: 'log', domain: [0.025, 0.18], label: 'Physical error rate p' }, yVals: [], yFallback: [1e-3, 1],
        yLabel: 'Logical error rate', series: [], empty: 'Press Run to simulate', aria: 'Empty plot: press Run to simulate.',
      });
      return;
    }
    const series = r.ds.map(d => ({ d, line: true, pts: r.ps.map(p => { const c = r.res.get(`${d}|${p}`); return { x: p, f: c.failures, n: c.shots }; }) }));
    const yVals = [];
    for (const s of series) for (const q of s.pts) if (q.n) { const e = binomialError(q.f, q.n); yVals.push(e.rate, e.hi, e.lo, e.upper95 ?? 0); }
    const showRef = $('thr-ref').checked && r.model === 'bitflip';
    const refs = showRef ? refRows().filter(x => (r.mode === 'cc' ? x.rounds === 1 : x.rounds === x.d) && r.ds.includes(x.d) && x.p >= r.ps[0] && x.p <= r.ps[r.ps.length - 1]).map(x => ({ d: x.d, x: x.p, y: x.rate })) : [];
    yVals.push(...refs.map(x => x.y));
    drawPlot(box, {
      x: { kind: 'log', domain: [r.ps[0] / 1.12, r.ps[r.ps.length - 1] * 1.12], label: 'Physical error rate p' },
      yVals, yFallback: [1e-3, 1], yLabel: 'Logical error rate', series, refs, crosses: r.done ? r.crosses : [],
      aria: `Logical error rate against physical error rate p from ${fp(r.ps[0])} to ${fp(r.ps[r.ps.length - 1])} for distances ${r.ds.join(', ')}; ${configWords(r.mode, r.model).toLowerCase()}. The numbers are in the table below the figure.`,
    });
    this.legend(r, refs.length > 0);
    this.table(r);
    const done = [...r.res.values()].reduce((t, c) => t + c.shots, 0);
    $('thr-progress').value = r.total ? done / r.total : 0;
  },
  legend(r, ref) {
    const L = $('thr-legend');
    const items = [document.createTextNode(`${configWords(r.mode, r.model)}:`)];
    for (const d of r.ds) { const s = document.createElement('span'); s.append(legendSwatch(d), `d = ${d} (${d * d} data qubits)`); items.push(s); }
    if (ref) { const s = document.createElement('span'); s.innerHTML = '&times; matching reference'; items.push(s); }
    L.replaceChildren(...items);
    L.hidden = false;
  },
  table(r) {
    const head = `<tr><th scope="col">p</th>${r.ds.map(d => `<th scope="col">d = ${d}</th>`).join('')}</tr>`;
    const rows = r.ps.map(p => `<tr><th scope="row">${fp(p)}</th>${r.ds.map(d => {
      const c = r.res.get(`${d}|${p}`);
      if (!c.shots) return '<td>not run</td>';
      const e = binomialError(c.failures, c.shots);
      return `<td>${fr(e.rate)} &plusmn; ${fr(e.stderr, 2)} (${nf(c.failures)} / ${nf(c.shots)})</td>`;
    }).join('')}</tr>`).join('');
    $('thr-table').innerHTML = `<p class="thr-tcap">${configWords(r.mode, r.model)}, union-find decoder, this run. Each cell: logical error rate &plusmn; one standard error (failures / shots).</p><div class="thr-scroll"><table><thead>${head}</thead><tbody>${rows}</tbody></table></div>`;
    $('thr-data').hidden = false;
  },
  start() {
    const mode = ctl.mode(), model = ctl.model(), ds = ctl.ds();
    const a = Number($('thr-pmin').value), b = Number($('thr-pmax').value), n = Number($('thr-npts').value);
    const shots = Number($('thr-shots').value);
    if (ds.length < 1) return say('thr-status', 'Pick at least one distance.');
    if (!(a > 0 && b > a && b <= 0.5)) return say('thr-status', 'Set p from and p to with 0 < from < to <= 0.5.');
    const ps = logSpace(a, b, n), D = DEFAULTS[mode];
    const jobs = planQueue({ ps, ds, shots, passes: [0.25, 0.75], seed: 1 + 100000 * runCount++ })
      .map(j => ({ ...j, model, rounds: mode === 'phen' ? j.d : 1, chunk: D.chunk }));
    const res = new Map();
    for (const d of ds) for (const p of ps) res.set(`${d}|${p}`, { shots: 0, failures: 0 });
    this.run = { mode, model, ds, ps, res, total: jobs.reduce((t, j) => t + j.shots, 0), done: false, crosses: [] };
    $('thr-cross').hidden = true;
    setBusy('thr');
    $('fig-main').dataset.state = 'running';
    say('thr-status', `Running ${nf(ps.length * ds.length)} points, ${nf(shots)} shots each, ${configWords(mode, model).toLowerCase()}. A quick first pass places every point, then the error bars shrink.`);
    this.render();
    runner.start(jobs, (j, dn, df) => {
      const c = res.get(`${j.d}|${j.p}`);
      c.shots += dn; c.failures += df; totalShots += dn;
      showTotal();
      schedule(this);
    }, info => this.end(info));
  },
  end(info) {
    const r = this.run;
    setBusy(null);
    r.done = true;
    $('fig-main').dataset.state = info.error ? 'error' : info.stopped ? 'stopped' : 'done';
    if (info.error) { say('thr-status', 'The simulation could not run in this browser.'); return; }
    const shots = [...r.res.values()].reduce((t, c) => t + c.shots, 0);
    const curve = d => r.ps.map(p => ({ p, ...r.res.get(`${d}|${p}`) }));
    const pairs = [];
    for (let i = 0; i + 1 < r.ds.length; i++) pairs.push([r.ds[i], r.ds[i + 1], crossing(curve(r.ds[i]), curve(r.ds[i + 1]))]);
    r.crosses = pairs.filter(([, , c]) => c.status === 'found').map(([a, b, c]) => ({ a, b, ...c }));
    latestCross.set(configKey(r.mode, r.model), r.crosses);
    const lines = pairs.map(([a, b, c]) => crossWords(a, b, c, r));
    const zeros = [...r.res.values()].filter(c => c.shots && !c.failures).length;
    const head = info.stopped ? `Stopped after ${nf(shots)} of ${nf(r.total)} shots, ${secs(info.ms)}.` : `Finished ${nf(shots)} shots in ${secs(info.ms)}.`;
    const st = $('thr-status');
    st.textContent = `${head}${zeros ? ` ${zeros} point${zeros > 1 ? 's' : ''} had no failures; each is drawn as a down arrow at its 95% upper bound, 3 / shots.` : ''}`;
    if (lines.length) { const sr = document.createElement('span'); sr.className = 'sr-only'; sr.textContent = ` ${lines.map(l => l.text).join(' ')}`; st.append(sr); }
    $('fig-main').dataset.ms = Math.round(info.ms);
    if (pairs.length) {
      history.unshift(`${configWords(r.mode, r.model)}, ${nf(shots)} shots: ${lines.map(l => l.short).join('; ')}.`);
      history.length = Math.min(history.length, 6);
    }
    const box = $('thr-cross');
    box.innerHTML = pairs.length ? `<span class="tp-lbl">This run's estimate for this decoder</span><ul>${lines.map(l => `<li>${l.text}</li>`).join('')}</ul>
      <p class="muted">The range is where the gap between the two curves is within one standard error of zero. It is statistical only, and does not include the drift of the crossing as d grows.</p>
      ${history.length > 1 ? `<span class="tp-lbl">Runs on this page, newest first</span><ul>${history.map(h => `<li>${h}</li>`).join('')}</ul>` : ''}` : '';
    box.hidden = !pairs.length;
    this.render();
    lambda.note();
  },
};
function crossWords(a, b, c, r) {
  const lo = fp(r.ps[0]), hi = fp(r.ps[r.ps.length - 1]);
  if (c.status === 'found') {
    const from = c.loOpen ? `below ${fp(c.lo)}` : fp(c.lo), to = c.hiOpen ? `above ${fp(c.hi)}` : fp(c.hi);
    return { text: `d = ${a} and d = ${b} cross near p = ${fp(c.p)}, likely between ${from} and ${to}${c.multiple ? ' (the curves cross more than once here, so the points are noisy: add shots)' : ''}.`, short: `${a} and ${b} near ${fp(c.p)} (${from} to ${to})` };
  }
  if (c.status === 'above') return { text: `d = ${a} and d = ${b} do not cross between ${lo} and ${hi}: the larger code is better everywhere shown, so the crossing is above ${hi}.`, short: `${a} and ${b} above ${hi}` };
  if (c.status === 'below') return { text: `d = ${a} and d = ${b} do not cross between ${lo} and ${hi}: the larger code is worse everywhere shown, so the crossing is below ${lo}.`, short: `${a} and ${b} below ${lo}` };
  return { text: `d = ${a} and d = ${b}: too few points with failures to locate a crossing.`, short: `${a} and ${b} not located` };
}
function say(id, text) { $(id).textContent = text; }

// ---------- Fig. 2: Lambda ----------
const lambda = {
  run: null,
  ds: () => [3, 5, 7, 9, ...($('lam-d11').checked ? [11] : [])],
  note() {
    const mode = ctl.mode(), model = ctl.model(), cr = latestCross.get(configKey(mode, model));
    const p = Number($('lam-p').value);
    let s = `Uses the setting chosen in Fig. 1: ${MODE_WORDS[mode]}, ${MODEL_WORDS[model]}. Distances ${this.ds().join(', ')}.`;
    if (cr && cr.length && p >= Math.min(...cr.map(c => c.lo))) s += ` This p is at or above the lowest crossing range from your last Fig. 1 run in this setting, so Lambda may be near or below 1.`;
    $('lam-note').textContent = s;
  },
  render() {
    const r = this.run, box = $('lam-plot');
    const dsAll = r ? r.ds : this.ds();
    const xT = dsAll.map(d => ({ v: d, label: String(d) }));
    const x = { kind: 'lin', domain: [2, dsAll[dsAll.length - 1] + 1], ticks: xT, label: 'Code distance d' };
    if (!r) { drawPlot(box, { x, yVals: [], yFallback: [1e-4, 0.1], yLabel: 'Logical error rate', series: [], empty: 'Press Run to simulate', aria: 'Empty plot: press Run to simulate.' }, true); return; }
    const series = r.ds.map(d => { const c = r.res.get(d); return { d, line: false, pts: [{ x: d, f: c.failures, n: c.shots }] }; });
    const yVals = [];
    for (const d of r.ds) { const c = r.res.get(d); if (c.shots) { const e = binomialError(c.failures, c.shots); yVals.push(e.rate, e.hi, e.lo, e.upper95 ?? 0); } }
    const f = r.fit;
    drawPlot(box, {
      x, yVals, yFallback: [1e-4, 0.1], yLabel: 'Logical error rate', series,
      fit: f ? { ...f, x0: f.used[0], x1: f.used[f.used.length - 1] } : null,
      fitLabel: f ? `Lambda = ${f.lambda.toPrecision(3)}` : '',
      aria: `Logical error rate against code distance at p = ${fp(r.p)}${f ? `, with a fitted line; Lambda = ${f.lambda.toPrecision(3)}` : ''}. The numbers are in the table below the figure.`,
    }, true);
    const rows = r.ds.map(d => {
      const c = r.res.get(d), e = binomialError(c.failures, c.shots);
      return `<tr><th scope="row">${d}</th><td>${nf(c.shots)}</td><td>${nf(c.failures)}</td><td>${c.shots ? fr(e.rate) : ''}</td><td>${c.shots ? fr(e.stderr, 2) : ''}</td></tr>`;
    }).join('');
    $('lam-table').innerHTML = `<p class="thr-tcap">p = ${fp(r.p)}, ${configWords(r.mode, r.model).toLowerCase()}, union-find decoder, this run</p><div class="thr-scroll"><table><thead><tr><th scope="col">d</th><th scope="col">Shots</th><th scope="col">Failures</th><th scope="col">Rate</th><th scope="col">Standard error</th></tr></thead><tbody>${rows}</tbody></table></div>`;
    $('lam-data').hidden = false;
    $('lam-progress').value = r.total ? [...r.res.values()].reduce((t, c) => t + c.shots, 0) / r.total : 0;
  },
  start() {
    const mode = ctl.mode(), model = ctl.model(), ds = this.ds(), p = Number($('lam-p').value), shots = Number($('lam-shots').value);
    if (!(p > 0 && p <= 0.5)) return say('lam-status', 'Set p between 0 and 0.5.');
    const jobs = planQueue({ ps: [p], ds, shots, passes: [0.25, 0.75], seed: 1 + 100000 * runCount++ })
      .map(j => ({ ...j, model, rounds: mode === 'phen' ? j.d : 1, chunk: DEFAULTS[mode].chunk }));
    const res = new Map(ds.map(d => [d, { shots: 0, failures: 0 }]));
    this.run = { mode, model, ds, p, res, total: jobs.reduce((t, j) => t + j.shots, 0), fit: null };
    setBusy('lam');
    $('fig-lambda').dataset.state = 'running';
    say('lam-status', `Running d = ${ds.join(', ')} at p = ${fp(p)}, ${nf(shots)} shots each.`);
    this.render();
    runner.start(jobs, (j, dn, df) => {
      const c = res.get(j.d);
      c.shots += dn; c.failures += df; totalShots += dn;
      showTotal();
      this.run.fit = fitLambda(ds.map(d => ({ d, ...res.get(d) })));
      schedule(this);
    }, info => this.end(info));
  },
  end(info) {
    const r = this.run;
    setBusy(null);
    $('fig-lambda').dataset.state = info.error ? 'error' : info.stopped ? 'stopped' : 'done';
    $('fig-lambda').dataset.ms = Math.round(info.ms);
    if (info.error) { say('lam-status', 'The simulation could not run in this browser.'); return; }
    const pts = r.ds.map(d => ({ d, ...r.res.get(d) }));
    const f = r.fit = fitLambda(pts);
    const shots = pts.reduce((t, q) => t + q.shots, 0);
    const head = info.stopped ? `Stopped after ${nf(shots)} shots, ${secs(info.ms)}.` : `Finished ${nf(shots)} shots in ${secs(info.ms)}.`;
    let text;
    if (!f) text = 'Too few distances had failures to fit a line: raise p or the number of shots.';
    else {
      const L = f.lambda.toPrecision(3);
      text = `This run's estimate: at p = ${fp(r.p)}, Lambda = ${L} (${f.lo.toPrecision(3)} to ${f.hi.toPrecision(3)}, one standard error), fitted to d = ${f.used.join(', ')}. `;
      text += f.lambda > 1 ? `Each step of 2 in distance divides the logical error rate by about ${Number(f.lambda.toPrecision(2))}.` : 'Lambda is not above 1: at this p a bigger code does not help, so this p is at or above the threshold for this decoder and noise.';
      const skipped = r.ds.filter(d => !f.used.includes(d));
      if (skipped.length) text += ` d = ${skipped.join(', ')} had no failures and was left out.`;
    }
    say('lam-status', `${head} ${text}`);
    this.render();
  },
};

// ---------- Fig. 3: union-find against the matching reference ----------
const honesty = {
  run: null,
  render() {
    const rows = refRows();
    if (!rows.length) return;
    const r = this.run;
    const shots = [...new Set(rows.map(x => x.shots))];
    const body = rows.map((x, i) => {
      const c = r && r.res[i];
      const e = c && c.shots ? binomialError(c.failures, c.shots) : null;
      const uf = e ? `${fr(e.rate)}<br><span class="muted">&plusmn; ${fr(e.stderr, 2)}</span>` : (r ? 'running' : 'not run');
      const ratio = e && e.rate > 0 ? (e.rate / x.rate).toFixed(2) : '';
      const prev = rows[i - 1], kind = x.rounds === 1 ? 'Perfect measurement' : 'Noisy measurement, d rounds';
      const group = !prev || (prev.rounds === 1) !== (x.rounds === 1) ? `<tr><th scope="colgroup" colspan="5" class="thr-rowgroup">${kind}</th></tr>` : '';
      return `${group}<tr><th scope="row">${x.d}</th><td>${fp(x.p)}</td><td>${fr(x.rate)}</td><td>${uf}</td><td>${ratio}</td></tr>`;
    }).join('');
    $('ref-table').innerHTML = `<p class="thr-tcap">Logical error rate, surface code, bit-flip noise. Matching: reference data from stim and pymatching, ${shots.map(nf).join(' or ')} shots per point. Union-find: this page${r ? `, ${nf(r.shots)} shots per point` : ''}, &plusmn; one standard error.</p><div class="thr-scroll"><table><thead><tr><th scope="col">d</th><th scope="col">p</th><th scope="col">Matching</th><th scope="col">Union-find</th><th scope="col">Ratio</th></tr></thead><tbody>${body}</tbody></table></div>`;
    if (r) $('ref-progress').value = r.total ? r.res.reduce((t, c) => t + c.shots, 0) / r.total : 0;
  },
  start() {
    const rows = refRows(), shots = Number($('ref-shots').value);
    const seed = 1 + 100000 * runCount++;
    const jobs = rows.map((x, i) => ({ d: x.d, p: x.p, shots, seed: seed + i, model: 'bitflip', rounds: x.rounds, chunk: x.rounds === 1 ? 2000 : 500, row: i }));
    this.run = { shots, res: rows.map(() => ({ shots: 0, failures: 0 })), total: shots * rows.length };
    setBusy('ref');
    $('fig-ref').dataset.state = 'running';
    say('ref-status', `Running union-find at ${rows.length} reference points, ${nf(shots)} shots each.`);
    this.render();
    runner.start(jobs, (j, dn, df) => {
      const c = this.run.res[j.row];
      c.shots += dn; c.failures += df; totalShots += dn;
      showTotal();
      schedule(this);
    }, info => this.end(info));
  },
  end(info) {
    setBusy(null);
    $('fig-ref').dataset.state = info.error ? 'error' : info.stopped ? 'stopped' : 'done';
    $('fig-ref').dataset.ms = Math.round(info.ms);
    if (info.error) { say('ref-status', 'The simulation could not run in this browser.'); return; }
    const rows = refRows(), res = this.run.res;
    const ratios = rows.map((x, i) => res[i].shots && res[i].failures ? res[i].failures / res[i].shots / x.rate : null).filter(v => v != null);
    const worse = rows.filter((x, i) => {
      const c = res[i]; if (!c.shots) return false;
      const e = binomialError(c.failures, c.shots), sref = Math.sqrt(x.rate * (1 - x.rate) / x.shots);
      return e.rate - x.rate > 2 * Math.hypot(e.stderr, sref);
    }).length;
    const done = res.filter(c => c.shots).length;
    const head = info.stopped ? `Stopped after ${secs(info.ms)}.` : `Finished in ${secs(info.ms)}.`;
    say('ref-status', `${head} At ${worse} of ${done} points union-find fails more often than matching by more than two combined standard errors.${ratios.length ? ` The ratio runs from ${Math.min(...ratios).toFixed(2)} to ${Math.max(...ratios).toFixed(2)}.` : ''}`);
    this.render();
  },
};

// ---------- wiring ----------
const figs = [main, lambda, honesty];
function renderAll() { for (const f of figs) f.render(); }

function init() {
  for (const id of ['thr-controls', 'lam-controls', 'ref-controls']) $(id).hidden = false;
  applyDefaults();
  fillSelect($('ref-shots'), REF_SHOTS, 20000);
  say('thr-status', 'Nothing has run yet. Press Run to simulate the surface code at every p and d shown.');
  say('lam-status', 'Nothing has run yet. Press Run to simulate one p at several distances.');
  say('ref-status', 'Loading the reference data.');
  showTotal();
  document.querySelectorAll('input[name=thr-mode]').forEach(i => i.addEventListener('change', applyDefaults));
  $('thr-model').addEventListener('change', applyDefaults);
  $('lam-d11').addEventListener('change', () => { lambda.note(); if (!lambda.run) lambda.render(); });
  $('lam-p').addEventListener('input', () => lambda.note());
  $('thr-ref').addEventListener('change', () => main.render());
  $('thr-run').addEventListener('click', () => main.start());
  $('lam-run').addEventListener('click', () => lambda.start());
  $('ref-run').addEventListener('click', () => honesty.start());
  for (const f of ['thr', 'lam', 'ref']) $(`${f}-stop`).addEventListener('click', () => runner.stop());
  setBusy(null);
  document.addEventListener('tp-theme', renderAll);
  let lastW = 0;
  new ResizeObserver(() => {
    const w = $('thr-plot').clientWidth;
    if (Math.abs(w - lastW) > 1) { lastW = w; renderAll(); }
  }).observe($('thr-plot'));
  renderAll();
  fetch(new URL('../data/qec-reference.json', import.meta.url))
    .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(j => {
      REF = j;
      setBusy(busy);
      say('ref-status', `Reference loaded: ${refRows().length} points computed offline with stim ${j.stim} and pymatching ${j.pymatching}. Press Run comparison to compute the union-find column.`);
      renderAll();
    })
    .catch(() => say('ref-status', 'The reference data could not be loaded.'));
}
init();
