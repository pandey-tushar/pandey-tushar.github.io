// The bivariate bicycle code explorer: inputs, results, the layout (Fig. 1) and the distance search (Fig. 2).
// The mathematics is in bb-math.js and bb-distance.js; the search runs in bb-worker.js. Nothing moves until the
// reader does.
import {
  PRESETS, LIMITS, parsePoly, checkSide, buildCode, analyze, matrixFile, toQuery, fromQuery, matchPreset,
} from './bb-math.js';

const $ = id => document.getElementById(id);
const SVGNS = 'http://www.w3.org/2000/svg';
const nf = v => v.toLocaleString('en-US');
const LE = String.fromCharCode(0x2264);   // less than or equal to
const DEFAULT = PRESETS.find(p => p.name === '[[144,12,12]]');
const CAP_MS = 120000;
const gcd = (a, b) => (b ? gcd(b, a % b) : a);
const frac = (a, b) => { if (!a) return '0'; const g = gcd(a, b); return b / g === 1 ? `${a / g}` : `${a / g}/${b / g}`; };
const its = v => `${nf(v)} iteration${v === 1 ? '' : 's'}`;
const secs = ms => `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)} s`;
const cellName = (r, m) => `(${Math.floor(r / m)}, ${r % m})`;
const list = a => a.length < 2 ? a.join('') : `${a.slice(0, -1).join(', ')} and ${a[a.length - 1]}`;
const monoHTML = ([a, b]) => (a || b) ? `${a ? (a === 1 ? 'x' : `x<sup>${a}</sup>`) : ''}${b ? (b === 1 ? 'y' : `y<sup>${b}</sup>`) : ''}` : '1';
const polyHTML = t => t.length ? t.map(monoHTML).join(' + ') : '0';
const dText = p => `${p.dExact ? '' : LE}${p.d}`;

let cur = null;               // the valid code on screen: { l, m, Atext, Btext, code, an, preset, xOn, zOn }
let sayTimer = 0;
function say(id, text, now) {
  clearTimeout(sayTimer);
  if (now) $(id).textContent = text;
  else sayTimer = setTimeout(() => { $(id).textContent = text; }, 700);
}

// ---------- inputs ----------
const F = { l: $('in-l'), m: $('in-m'), A: $('in-A'), B: $('in-B') };
function setErr(key, msg) {
  $(`err-${key}`).textContent = msg || '';
  if (msg) F[key].setAttribute('aria-invalid', 'true'); else F[key].removeAttribute('aria-invalid');
}

function read() {
  const errs = {};
  const L = checkSide(F.l.value), M = checkSide(F.m.value);
  if (L.error) errs.l = `l: ${L.error}`;
  if (M.error) errs.m = `m: ${M.error}`;
  if (!errs.l && !errs.m && L.value * M.value > LIMITS.cells)
    errs.m = `l times m is ${nf(L.value * M.value)}; the limit is ${nf(LIMITS.cells)}.`;
  const ok = !errs.l && !errs.m;
  // with l or m invalid, still check the syntax of A and B
  const l = ok ? L.value : 1e9, m = ok ? M.value : 1e9;
  const P = {};
  for (const k of ['A', 'B']) {
    const p = parsePoly(F[k].value, l, m);
    if (p.error) errs[k] = `${k}: ${p.error}`;
    else if (!p.terms.length) errs[k] = `${k}: every monomial cancels for l = ${l} and m = ${m}, so ${k} is 0. Change a term.`;
    P[k] = p.terms;
  }
  for (const k of ['l', 'm', 'A', 'B']) setErr(k, errs[k]);
  return Object.keys(errs).length ? { errs } : { l, m, A: P.A, B: P.B };
}

function compute(now) {
  const r = read();
  stopSearch(true);
  if (r.errs) {
    cur = null;
    $('bb-results').hidden = true;
    $('fig-layout').dataset.state = 'invalid';
    layoutEmpty();
    distIdle();
    syncPreset(null);
    say('bb-status', `Not computed: ${Object.values(r.errs).join(' ')}`, now);
    return;
  }
  const t = performance.now();
  const code = buildCode(r.l, r.m, r.A, r.B), an = analyze(code);
  const ms = performance.now() - t;
  const preset = matchPreset(r.l, r.m, r.A, r.B);
  const xOn = Array.from({ length: code.n }, () => []), zOn = Array.from({ length: code.n }, () => []);
  code.hx.forEach((row, i) => row.forEach(q => xOn[q].push(i)));
  code.hz.forEach((row, i) => row.forEach(q => zOn[q].push(i)));
  cur = { l: r.l, m: r.m, Atext: F.A.value.trim(), Btext: F.B.value.trim(), code, an, preset, xOn, zOn, ms, best: null };
  syncPreset(preset);
  history.replaceState(null, '', toQuery({ l: r.l, m: r.m, A: cur.Atext, B: cur.Btext }));
  params();
  $('bb-results').hidden = false;
  $('fig-layout').dataset.state = 'ok';
  $('fig-layout').dataset.ms = ms.toFixed(1);
  sel.logical = false;
  $('lay-kind').querySelector('option[value=logical]').disabled = true;
  if ($('lay-kind').value === 'logical') $('lay-kind').value = 'X';
  if (!(Number($('lay-i').value) < r.l)) $('lay-i').value = '0';
  if (!(Number($('lay-j').value) < r.m)) $('lay-j').value = '0';
  layoutChanged(true);
  distIdle();
  say('bb-status', `${summary()} Computed in ${ms < 10 ? ms.toFixed(1) : Math.round(ms)} ms.`, now);
}

function summary() {
  const { an, preset } = cur;
  const w = an.rowWeightsX.length === 1 && an.rowWeightsZ.length === 1 && an.rowWeightsX[0] === an.rowWeightsZ[0] ? `checks of weight ${an.rowWeightsX[0]}` : 'checks of mixed weight';
  const comp = an.components === 1 ? 'Tanner graph connected' : `Tanner graph in ${nf(an.components)} connected pieces`;
  const d = preset ? ` This is ${preset.name.replace('<=', LE)} from the paper's table, which gives d ${preset.dExact ? '=' : LE} ${preset.d}.` : '';
  return `n = ${nf(an.n)} physical qubits, k = ${an.k} logical qubits, ${w}, ${comp}.${d}`;
}

function params() {
  const { an, code, preset, l, m } = cur;
  const rows = [];
  const add = (dt, dd) => rows.push(`<dt>${dt}</dt><dd>${dd}</dd>`);
  if (preset) add('Code', `<span class="bb-big">[[${an.n}, ${an.k}, ${preset.dExact ? '' : '&le;'}${preset.d}]]</span><span class="bb-sub">n and k computed here; d ${preset.dExact ? '=' : '&le;'} ${preset.d} from the paper (Table 3)${preset.dExact ? '' : ', an upper bound'}</span>`);
  else add('Code', `<span class="bb-big">[[${an.n}, ${an.k}]]</span><span class="bb-sub">${an.k === 0 ? 'This code has k = 0, so it has no logical operators and no distance.' : 'The distance is not computed exactly; the search in Fig. 2 gives an upper bound.'}</span>`);
  add('A and B, reduced', `A = ${polyHTML(code.A)}<br>B = ${polyHTML(code.B)}<span class="bb-sub">exponents of x mod ${l}, of y mod ${m}</span>`);
  add('Physical qubits', `n = 2lm = <b>${nf(an.n)}</b><span class="bb-sub">${nf(code.half)} L qubits and ${nf(code.half)} R qubits</span>`);
  add('Logical qubits', `k = n &minus; rank H<sub>X</sub> &minus; rank H<sub>Z</sub> = ${nf(an.n)} &minus; ${nf(an.rankX)} &minus; ${nf(an.rankZ)} = <b>${an.k}</b><span class="bb-sub">2 dim(ker A &cap; ker B) = 2 &times; ${an.kerAB} = ${2 * an.kerAB}</span>`);
  const same = (u, v) => u.length === v.length && u.every((x, i) => x === v[i]);
  add('Check weight', same(an.rowWeightsX, an.rowWeightsZ) && an.rowWeightsX.length === 1
    ? `<b>${an.rowWeightsX[0]}</b> for every X check and every Z check`
    : `X checks: ${an.rowWeightsX.join(', ')}; Z checks: ${an.rowWeightsZ.join(', ')}`);
  add('Qubit degree', an.colWeightsX.length === 1 && an.colWeightsZ.length === 1
    ? `every qubit is in <b>${an.colWeightsX[0]}</b> X checks and <b>${an.colWeightsZ[0]}</b> Z checks`
    : `X checks per qubit: ${an.colWeightsX.join(', ')}; Z checks per qubit: ${an.colWeightsZ.join(', ')}`);
  add('H<sub>X</sub> H<sub>Z</sub><sup>T</sup> = 0', an.commute ? 'holds: every X check commutes with every Z check' : '<b>fails</b>');
  add('Tanner graph', an.components === 1 ? 'connected' : `<b>${nf(an.components)}</b> connected pieces`);
  add('Encoding rate', `k/n = ${an.k}/${nf(an.n)} = <b>${frac(an.k, an.n)}</b><span class="bb-sub">net encoding rate k/2n = ${frac(an.k, 2 * an.n)}, the paper&rsquo;s r, which counts n check qubits too${preset ? `; its table prints ${preset.rate}, rounded to an inverse integer where k/2n is not one` : ''}</span>`);
  $('bb-params').innerHTML = rows.join('');
}

// ---------- presets ----------
function fillPresets() {
  const s = $('in-preset');
  s.replaceChildren(new Option('Custom code', ''), ...PRESETS.map(p => new Option(`${p.name.replace('<=', LE)}: l = ${p.l}, m = ${p.m}`, p.name)));
}
function syncPreset(p) { $('in-preset').value = p ? p.name : ''; }
function loadPreset(p) {
  F.l.value = p.l; F.m.value = p.m; F.A.value = p.A; F.B.value = p.B;
}

// ---------- share and export ----------
async function copyLink() {
  const msg = $('act-msg'), url = location.href;
  try { await navigator.clipboard.writeText(url); msg.textContent = 'Copied the link to this code.'; }
  catch { msg.textContent = `Copying was blocked. The link is ${url}`; }
}
function download(which) {
  if (!cur) return;
  const text = matrixFile(cur.code, which, { A: cur.Atext, B: cur.Btext });
  const name = `bb-l${cur.l}-m${cur.m}-H${which}.txt`;
  const url = URL.createObjectURL(new Blob([text], { type: 'text/plain' }));
  const a = document.createElement('a');
  a.href = url; a.download = name;
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  $('act-msg').textContent = `Downloaded ${name}: H_${which}, ${nf(cur.code.half)} rows and ${nf(cur.code.n)} columns.`;
}

// ---------- Fig. 1: the layout ----------
const sel = { logical: false };
function el(tag, attrs, parent, text) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (text != null) e.textContent = text;
  if (parent) parent.appendChild(e);
  return e;
}

// what is selected: { kind, cell } or { logical }, with the nodes it lights
function selection() {
  if (!cur) return null;
  const { code, xOn, zOn, m } = cur, half = code.half;
  const kind = $('lay-kind').value;
  if (!kind) return { lit: new Map(), words: 'Nothing is selected. Choose a check or a qubit above, or click one in the drawing.' };
  if (kind === 'logical') {
    const b = cur.best, lit = new Map();
    for (const q of b.support) lit.set(`${q < half ? 'L' : 'R'}${q % half}`, 'sel');
    const Ls = b.support.filter(q => q < half).map(q => cellName(q, m)), Rs = b.support.filter(q => q >= half).map(q => cellName(q - half, m));
    return { lit, words: `The lowest-weight logical operator found so far is ${b.type} type, weight ${b.weight}: it acts on ${[Ls.length ? `the L qubits of cells ${list(Ls)}` : '', Rs.length ? `the R qubits of cells ${list(Rs)}` : ''].filter(Boolean).join(' and ')}. Its weight is an upper bound on the distance, not a proof of it.` };
  }
  const I = $('lay-i').value.trim(), J = $('lay-j').value.trim();
  const okI = /^\d+$/.test(I) && Number(I) < cur.l, okJ = /^\d+$/.test(J) && Number(J) < cur.m;
  if (!okI || !okJ) {
    const e = [!okI ? `i must be a whole number from 0 to ${cur.l - 1}` : '', !okJ ? `j must be a whole number from 0 to ${cur.m - 1}` : ''].filter(Boolean).join('; ');
    return { error: `Cell not shown: ${e}.` };
  }
  const r = Number(I) * m + Number(J), lit = new Map([[`${kind}${r}`, 'sel']]);
  const names = qs => {
    const Ls = qs.filter(q => q < half).map(q => cellName(q, m)), Rs = qs.filter(q => q >= half).map(q => cellName(q - half, m));
    qs.forEach(q => lit.set(`${q < half ? 'L' : 'R'}${q % half}`, 'on'));
    return [Ls.length ? `the L qubit${Ls.length > 1 ? 's' : ''} of cell${Ls.length > 1 ? 's' : ''} ${list(Ls)}` : '', Rs.length ? `the R qubit${Rs.length > 1 ? 's' : ''} of cell${Rs.length > 1 ? 's' : ''} ${list(Rs)}` : ''].filter(Boolean).join(' and ');
  };
  if (kind === 'X' || kind === 'Z') {
    const qs = (kind === 'X' ? code.hx : code.hz)[r];
    return { lit, from: `${kind}${r}`, words: `The ${kind} check of cell ${cellName(r, m)} acts on ${qs.length} qubits: ${names(qs)}.` };
  }
  const q = kind === 'L' ? r : half + r, xs = xOn[q], zs = zOn[q];
  xs.forEach(c => lit.set(`X${c}`, 'on')); zs.forEach(c => lit.set(`Z${c}`, 'on'));
  return { lit, from: `${kind}${r}`, words: `The ${kind} qubit of cell ${cellName(r, m)} is in ${xs.length} X check${xs.length === 1 ? '' : 's'}, of cell${xs.length === 1 ? '' : 's'} ${list(xs.map(c => cellName(c, m)))}, and ${zs.length} Z check${zs.length === 1 ? '' : 's'}, of cell${zs.length === 1 ? '' : 's'} ${list(zs.map(c => cellName(c, m)))}.` };
}

function layoutEmpty() {
  $('lay-plot').replaceChildren();
  $('lay-legend').hidden = true;
  $('lay-data').hidden = true;
  $('lay-controls').hidden = true;
  $('lay-status').textContent = 'No layout: the inputs above have an error.';
}

function drawLayout() {
  if (!cur) return;
  const box = $('lay-plot'), W = Math.max(280, Math.round(box.clientWidth || 600));
  const { l, m, code } = cur, half = code.half;
  const flip = W < 600 && l > m;                       // on a phone the longer side runs down the page
  const cols = flip ? m : l, rows = flip ? l : m;
  const left = 30, top = 22;
  const p = Math.min(44, (W - left - 4) / (2 * cols));
  const detailed = p >= 15, letters = p >= 28;
  const H = Math.round(top + rows * 2 * p + 4);
  const S0 = selection(), S = S0 && S0.lit ? S0 : { lit: new Map() };
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'img',
    'aria-label': `Layout of the code on a ${l} by ${m} torus of cells, ${detailed ? 'each with an X check, an L qubit, an R qubit and a Z check' : 'drawn as dots'}. ${S.words || ''}` });
  const pos = (kind, r) => {
    const i = Math.floor(r / m), j = r % m, c = flip ? j : i, rr = flip ? i : j;
    const dx = kind === 'X' || kind === 'R' ? 0.5 : 1.5, dy = kind === 'X' || kind === 'L' ? 0.5 : 1.5;
    return [left + (c * 2 + dx) * p, top + (rr * 2 + dy) * p];
  };
  // index labels: columns are i (or j when flipped), rows the other
  const every = Math.ceil(16 / (2 * p));
  for (let c = 0; c < cols; c += every) el('text', { x: left + (2 * c + 1) * p, y: top - 7, 'text-anchor': 'middle', class: 'bb-tick' }, svg, c);
  for (let r = 0; r < rows; r += Math.ceil(14 / (2 * p))) el('text', { x: left - 6, y: top + (2 * r + 1) * p + 4, 'text-anchor': 'end', class: 'bb-tick' }, svg, r);
  if (detailed) for (let c = 0; c < cols; c++) for (let r = 0; r < rows; r++)
    el('rect', { x: left + 2 * c * p + 1, y: top + 2 * r * p + 1, width: 2 * p - 2, height: 2 * p - 2, rx: 2, class: 'bb-cell' }, svg);
  // edges from the selected node to what it touches
  if (S.from) {
    const [x0, y0] = pos(S.from[0], Number(S.from.slice(1)));
    for (const [key, v] of S.lit) if (v === 'on') { const [x1, y1] = pos(key[0], Number(key.slice(1))); el('line', { x1: x0, y1: y0, x2: x1, y2: y1, class: 'bb-edge' }, svg); }
  }
  const g = el('g', {}, svg);
  const s = detailed ? p * 0.62 : p * 0.7;
  for (let r = 0; r < half; r++) for (const kind of ['X', 'L', 'R', 'Z']) {
    const [x, y] = pos(kind, r), st = S.lit.get(`${kind}${r}`) || '';
    const cls = `bb-node${detailed ? '' : ' bb-dot'}${st ? ` ${st}` : ''}`;
    const attrs = { class: cls, 'data-k': `${kind}${r}` };
    if (kind === 'L' || kind === 'R') el('circle', { ...attrs, cx: x, cy: y, r: s * 0.55 }, g);
    else if (kind === 'X') el('rect', { ...attrs, x: x - s / 2, y: y - s / 2, width: s, height: s }, g);
    else el('path', { ...attrs, d: `M${x} ${y - s * 0.62}L${x + s * 0.62} ${y}L${x} ${y + s * 0.62}L${x - s * 0.62} ${y}Z` }, g);
    if (letters) el('text', { x, y: y + 4.2, 'text-anchor': 'middle', class: `bb-glyph${st ? ` ${st}` : ''}` }, g, kind);
  }
  box.replaceChildren(svg);
  legend(flip, detailed);
}

function legend(flip, detailed) {
  const sw = (cls, text) => `<span><i class="bb-sw ${cls}" aria-hidden="true"></i>${text}</span>`;
  $('lay-legend').innerHTML = [
    `<span>Columns: ${flip ? 'j, the power of y' : 'i, the power of x'}; rows: ${flip ? 'i, the power of x' : 'j, the power of y'}.</span>`,
    detailed ? `<span>In each cell: X check (square) and L qubit (circle) on top, R qubit (circle) and Z check (diamond) below.</span>` : '<span>Each cell is four dots: X check and L qubit on top, R qubit and Z check below.</span>',
    ...($('lay-kind').value === 'logical' ? [sw('sel round', 'qubits of the logical operator')] : [sw('sel', 'selected'), sw('on round', 'what it touches')]),
  ].join('');
  $('lay-legend').hidden = false;
}

function layoutChanged(quiet) {
  if (!cur) return;
  $('lay-controls').hidden = false;
  const S = selection();
  $('lay-err').textContent = S && S.error ? S.error : '';
  const kind = $('lay-kind').value, needCell = kind && kind !== 'logical';
  $('lay-i').disabled = $('lay-j').disabled = !needCell;
  drawLayout();
  $('lay-data').hidden = false;
  if ($('lay-data').open) layoutTable();
  const words = S.error || S.words;
  if (quiet) $('lay-status').textContent = words; else say('lay-status', words, true);
}

function layoutTable() {
  const { code, m } = cur, half = code.half;
  const side = qs => {
    const Ls = qs.filter(q => q < half).map(q => cellName(q, m)), Rs = qs.filter(q => q >= half).map(q => cellName(q - half, m));
    return `L ${Ls.join(' ')}; R ${Rs.join(' ')}`;
  };
  const rows = code.hx.map((row, r) => `<tr><th scope="row">${cellName(r, m)}</th><td>${side(row)}</td><td>${side(code.hz[r])}</td></tr>`).join('');
  $('lay-table').innerHTML = `<table><caption>For each cell (i, j), the cells whose L and R qubits its X check and its Z check act on.</caption><thead><tr><th scope="col">Cell</th><th scope="col">X check acts on</th><th scope="col">Z check acts on</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function clickNode(e) {
  const t = e.target.closest('[data-k]');
  if (!t || !cur) return;
  const key = t.getAttribute('data-k'), kind = key[0], r = Number(key.slice(1));
  $('lay-kind').value = kind;
  $('lay-i').value = Math.floor(r / cur.m); $('lay-j').value = r % cur.m;
  layoutChanged();
}

// ---------- Fig. 2: the distance search ----------
let worker = null, run = null;
function setBusy(on) {
  const had = document.activeElement;
  $('dist-run').disabled = on || !cur;
  $('dist-stop').disabled = !on;
  if (had && had.disabled) (on ? $('dist-stop') : $('dist-run')).focus();
}
function distIdle() {
  $('dist-controls').hidden = false;
  $('dist-readout').hidden = true;
  $('dist-data').hidden = true;
  setBusy(false);
  if (!cur) { $('dist-status').textContent = 'No search: the inputs above have an error.'; return; }
  const p = cur.preset;
  $('dist-status').textContent = cur.an.k === 0
    ? 'This code has k = 0, so it has no logical operators and no distance to bound.'
    : `Nothing has run yet. Press Run search to look for low-weight logical operators of this code.${p ? ` The paper gives d ${p.dExact ? '=' : LE} ${p.d}.` : ''}`;
}
function startSearch() {
  if (!cur) return;
  const s = $('dist-seed').value.trim();
  if (!/^\d{1,9}$/.test(s)) { $('dist-err').textContent = 'The seed must be a whole number from 0 to 999999999.'; $('dist-seed').setAttribute('aria-invalid', 'true'); return; }
  $('dist-err').textContent = ''; $('dist-seed').removeAttribute('aria-invalid');
  stopSearch(true);
  const p = cur.preset, seed = Number(s);
  run = { seed, history: [], last: null, code: cur, announced: 0 };
  worker = new Worker(new URL('./bb-worker.js', import.meta.url), { type: 'module' });
  worker.onmessage = e => onSearch(e.data);
  worker.onerror = e => { e.preventDefault(); stopSearch(true); $('dist-status').textContent = 'The search could not run in this browser.'; };
  worker.postMessage({ l: cur.l, m: cur.m, A: cur.code.A, B: cur.code.B, seed, target: p && p.dExact ? p.d : 0, capMs: CAP_MS });
  setBusy(true);
  $('fig-dist').dataset.state = 'running';
  $('dist-readout').hidden = false;
  $('dist-readout').textContent = 'Starting the search.';
  say('dist-status', `Searching with seed ${seed}. Press Stop at any time.`, true);
}
function readout(m) {
  const r = run, p = r.code.preset;
  const paper = p ? ` The paper gives d ${p.dExact ? '=' : '&le;'} ${p.d}.` : '';
  const b = m.best;
  $('dist-readout').innerHTML = b
    ? `Upper bound found so far (not a proof): <b>${b.weight}</b><br>A ${b.type}-type logical operator of weight ${b.weight}, first found at iteration ${nf(b.iteration)}. ${its(m.iterations)} in ${secs(m.ms)}, seed ${r.seed}.${paper}`
    : `No logical operator found yet. ${its(m.iterations)} in ${secs(m.ms)}, seed ${r.seed}.${paper}`;
  $('fig-dist').dataset.iterations = m.iterations;
  if (b) $('fig-dist').dataset.bound = b.weight;
}
function onSearch(m) {
  if (!run) return;
  run.history.push(...m.fresh);
  run.last = m;
  if (m.best) {
    cur.best = m.best;
    const opt = $('lay-kind').querySelector('option[value=logical]');
    opt.disabled = false;
    if ($('lay-kind').value === 'logical') layoutChanged(true);
  }
  readout(m);
  distTable();
  if (m.kind === 'done') {
    const why = {
      target: `It reached ${m.best && m.best.weight}, the distance the paper gives for this code, and stopped, because the paper states that no logical operator has lower weight. The search itself proves no lower bound.`,
      time: 'It stopped after two minutes; press Run search to start again, perhaps with another seed.',
      k0: 'This code has k = 0, so it has no logical operators.',
    }[m.reason];
    finish(why);
  } else if (m.best && m.best.weight !== run.announced) {
    run.announced = m.best.weight;
    say('dist-status', `Upper bound found so far (not a proof): ${m.best.weight}.`);
  }
}
function finish(why) {
  const m = run.last;
  worker && worker.terminate();
  worker = null;
  setBusy(false);
  $('fig-dist').dataset.state = 'done';
  const b = m && m.best;
  say('dist-status', `${m ? `Search ended after ${its(m.iterations)}, ${secs(m.ms)}. ` : ''}${b ? `Upper bound found (not a proof): ${b.weight}. ` : ''}${why || ''}${b ? ' Choose "The lowest-weight logical found" in Fig. 1 to see it.' : ''}`, true);
  run = null;
}
function stopSearch(silent) {
  if (!worker) return;
  if (silent) { worker.terminate(); worker = null; run = null; setBusy(false); return; }
  finish('Stopped.');
}
function distTable() {
  const h = run.history;
  if (!h.length) return;
  $('dist-table').innerHTML = `<table><caption>Each time the search found a lower weight, seed ${run.seed}.</caption><thead><tr><th scope="col">Iteration</th><th scope="col">Time</th><th scope="col">Weight</th><th scope="col">Type</th></tr></thead><tbody>${h.map(x => `<tr><td>${nf(x.iteration)}</td><td>${secs(x.ms)}</td><td>${x.weight}</td><td>${x.type}</td></tr>`).join('')}</tbody></table>`;
  $('dist-data').hidden = false;
}

// ---------- wiring ----------
function init() {
  for (const id of ['lim-side', 'lim-side2']) $(id).textContent = LIMITS.side;
  for (const id of ['lim-cells', 'lim-cells2']) $(id).textContent = nf(LIMITS.cells);
  fillPresets();
  const q = fromQuery(location.search);
  if (q) { F.l.value = q.l; F.m.value = q.m; F.A.value = q.A; F.B.value = q.B; } else loadPreset(DEFAULT);
  $('lay-kind').value = 'X'; $('lay-i').value = '0'; $('lay-j').value = '0';
  $('bb-form').hidden = false;
  $('bb-form').addEventListener('submit', e => e.preventDefault());
  let timer = 0;
  for (const k in F) F[k].addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => compute(false), 250); });
  $('in-preset').addEventListener('change', () => {
    const p = PRESETS.find(x => x.name === $('in-preset').value);
    if (p) { loadPreset(p); compute(true); }
  });
  $('act-link').addEventListener('click', copyLink);
  $('act-hx').addEventListener('click', () => download('X'));
  $('act-hz').addEventListener('click', () => download('Z'));
  $('lay-kind').addEventListener('change', () => layoutChanged());
  for (const id of ['lay-i', 'lay-j']) $(id).addEventListener('input', () => layoutChanged());
  $('lay-plot').addEventListener('click', clickNode);
  $('lay-data').addEventListener('toggle', () => { if ($('lay-data').open && cur) layoutTable(); });
  $('dist-run').addEventListener('click', startSearch);
  $('dist-stop').addEventListener('click', () => stopSearch(false));
  let lastW = 0;
  new ResizeObserver(() => { const w = $('lay-plot').clientWidth; if (Math.abs(w - lastW) > 1) { lastW = w; drawLayout(); } }).observe($('lay-plot'));
  compute(true);
}
init();
