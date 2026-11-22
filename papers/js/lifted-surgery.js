// Fig. 1 of papers/lifted-surgery.html. Every value shown comes from ../data/lifted-surgery.json, written by
// _studio/tools/papers/extract_lifted-surgery.py. Nothing moves until the reader does.
import { el, linScale, niceTicks, markerPath } from './plot.js';
import { parseGroup, familyHTML, families, ratio, codeGain, bestOrbits, visible, sortCodes, slots, move } from './lifted-surgery-logic.js';

const $ = id => document.getElementById(id);
const nf = n => n.toLocaleString('en-US');
const nkd = c => `[[${c.n},${c.k},${c.d}]]`;
let D = null;
const state = { gain: 'all', family: 'all', cand: true, sel: null };
let shown = [];          // visible certified codes, in keyboard order

const plus = (x, y, r) => `M${x - r} ${y}h${2 * r}M${x} ${y - r}v${2 * r}`;
const filled = c => c.table === 1 || (() => { const g = codeGain(c.orbits.list); return g.mu >= 3 * g.base; })();
const kind = c => c.table === 1 ? 'Table 1: gain exactly two' : 'Table 2: gain at least three for a best logical';
function distWords(c) {
  if (c.d_exact === null) return `${c.d}, exact (the paper's Table 1)`;
  return 'dX' in c && c.dX !== c.dZ ? `${c.d}, exact (d<sub>X</sub> = ${c.dX}, d<sub>Z</sub> = ${c.dZ})` : `${c.d}, exact`;
}

// ---------- the plot ----------
function draw() {
  const box = $('ls-plot'), W = Math.max(280, Math.round(box.clientWidth || 600));
  const narrow = W < 460, H = Math.round(Math.min(480, Math.max(320, W * (narrow ? 1 : 0.72))));
  const m = { l: narrow ? 40 : 50, r: 14, t: 14, b: 48 };
  const f = { X0: m.l, X1: W - m.r, Y0: H - m.b, Y1: m.t };
  const xs = linScale([30, 350], [f.X0, f.X1]), ys = linScale([4, 21], [f.Y0, f.Y1]);
  const cands = state.cand && state.gain !== '3' ? D.candidates.filter(c => state.family === 'all' || parseGroup(c.group).family === state.family) : [];
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'group',
    'aria-label': `Distance against block length n: ${shown.length} certified codes${cands.length ? ` and ${cands.length} search candidates` : ''}. The numbers are in the table below the figure.` });
  for (const v of niceTicks(4, 21, 6).filter(v => v >= 4)) {
    el('line', { x1: f.X0, x2: f.X1, y1: ys(v), y2: ys(v), class: 'pc-grid' }, svg);
    el('text', { x: f.X0 - 6, y: ys(v) + 4, 'text-anchor': 'end', class: 'pc-tick' }, svg, String(v));
  }
  for (const v of niceTicks(30, 350, narrow ? 4 : 7).filter(v => v > 30)) {
    el('line', { x1: xs(v), x2: xs(v), y1: f.Y0, y2: f.Y1, class: 'pc-grid' }, svg);
    el('text', { x: xs(v), y: f.Y0 + 18, 'text-anchor': 'middle', class: 'pc-tick' }, svg, String(v));
  }
  el('path', { d: `M${f.X0} ${f.Y1}V${f.Y0}H${f.X1}`, class: 'pc-axis' }, svg);
  el('text', { x: (f.X0 + f.X1) / 2, y: H - 8, 'text-anchor': 'middle', class: 'pc-lab' }, svg, 'Block length n');
  el('text', { transform: `translate(13 ${(f.Y0 + f.Y1) / 2}) rotate(-90)`, 'text-anchor': 'middle', class: 'pc-lab' }, svg, 'Distance d');

  const cg = el('g', { 'aria-hidden': 'true' }, svg);
  for (const c of cands) el('path', { d: plus(xs(c.n), ys(c.d_est), 3.6), class: 'ls-cand' }, cg);

  const step = narrow ? 9 : 12, off = slots(shown), r = narrow ? 4.6 : 5.4;
  const list = el('g', { role: 'listbox', 'aria-label': 'Certified codes; arrow keys move between them' }, svg), at = [];
  for (const c of shown) {
    const x = xs(c.n) + off.get(c.id) * step, y = ys(c.d), sel = c.id === state.sel;
    at.push({ id: c.id, x, y });
    const g = el('g', { class: `ls-pt ${c.table === 1 ? 'ls-t1' : 'ls-t2'}${filled(c) ? '' : ' ls-open'}`, role: 'option',
      tabindex: sel ? 0 : -1, 'aria-selected': String(sel), 'data-id': c.id,
      'aria-label': `${nkd(c)} over ${parseGroup(c.group).label}, ${c.table === 1 ? 'gain two' : `gain ${ratio(c.mu, c.base)} for a best logical`}` }, list);
    if (sel) el('circle', { cx: x, cy: y, r: r + 4.5, class: 'ls-sel-ring' }, g);
    el('circle', { cx: x, cy: y, r: r + 8, class: 'ls-focus' }, g);
    el('path', { d: markerPath(c.table === 1 ? 'circle' : 'square', x, y, r), class: 'pc-mark' }, g);
  }
  box.replaceChildren(svg);
  // a click or tap selects the nearest certified code within 22 px, so every code has a target of about 44 px
  svg.addEventListener('click', e => {
    const b = svg.getBoundingClientRect(), k = W / b.width, px = (e.clientX - b.left) * k, py = (e.clientY - b.top) * k;
    let best = null, bd = 22 * k;
    for (const q of at) { const dd = Math.hypot(q.x - px, q.y - py); if (dd < bd) { bd = dd; best = q.id; } }
    if (best) choose(best, true);
  });
  list.addEventListener('keydown', e => {
    const i = shown.findIndex(c => c.id === state.sel), j = move(i, e.key, shown.length);
    if (j === null || i < 0) return;
    e.preventDefault();
    choose(shown[j].id, true);
  });
}

// ---------- the selected code ----------
function card(c) {
  const g = parseGroup(c.group), rows = [
    ['Group G', g.html],
    ['Check weight', String(c.w)],
    ['Distance d', distWords(c)],
    ['Block-affine group E', `order ${nf(c.E_order)}; ${c.rigid ? 'rigid (translations only)' : 'not rigid'}`],
  ];
  if ('orbit' in c) rows.push(['Orbit of the logical', `${c.orbit} translates`]);
  rows.push(['Co-measurable number &mu;<sub>E</sub>', `${c.mu} operators in one merged code`]);
  rows.push(['Best Abelian subgroup', `${c.base} operators (|H| = ${c.base_order})`]);
  rows.push(['Gain &gamma;', `${c.mu}/${c.base} = <b>${ratio(c.mu, c.base)}</b>${c.table === 2 ? ' for a best logical' : ''}`]);
  if (c.table === 2) {
    rows.push(['Gain of the whole code', codeGain(c.orbits.list).text]);
    rows.push(['Bounds', `cover bound ${c.cover}; index of a largest Abelian subgroup ${c.index_Amax}`]);
  }
  if (c.orbits) {
    const b = bestOrbits(c.orbits.list), all = c.orbits.total > b.examined ? ` (${c.orbits.total} exist)` : '';
    rows.push(['Orbits with this gain', `${b.best} of ${b.examined} ${c.table === 2 ? 'found' : 'examined'}${all}`]);
  } else rows.push(['Orbits with this gain', 'one logical examined']);
  if (c.mu === c.k) rows.push(['Reads out every logical', `yes, &mu;<sub>E</sub> = k = ${c.k}`]);
  return `<h3>${nkd(c)} over ${g.html}</h3><p class="ls-kind">${kind(c)}</p><dl>${rows.map(([t, d]) => `<dt>${t}</dt><dd>${d}</dd>`).join('')}</dl>`;
}

function words(c) {
  const i = shown.findIndex(s => s.id === c.id) + 1;
  const d = `distance ${c.d}, exact`;
  return `${nkd(c)} over ${parseGroup(c.group).html}, ${kind(c).replace(/^Table (\d):/, 'Table $1,')}. ${c.mu} operators in one merged code against ${c.base} for the best Abelian subgroup, gain ${ratio(c.mu, c.base)}; ${d}. Code ${i} of ${shown.length} shown.`;
}

let sayTimer = 0;
function say(text, now) {
  clearTimeout(sayTimer);
  if (now) $('ls-status').innerHTML = text;
  else sayTimer = setTimeout(() => { $('ls-status').innerHTML = text; }, 400);
}

function choose(id, focus) {
  state.sel = id;
  const c = shown.find(c => c.id === id);
  draw();
  $('ls-card').innerHTML = card(c);
  $('ls-prev').disabled = shown[0].id === id;
  $('ls-next').disabled = shown[shown.length - 1].id === id;
  if (focus) $('ls-plot').querySelector(`[data-id="${CSS.escape(id)}"]`)?.focus();
  say(words(c), true);
}

function refilter() {
  shown = sortCodes(visible(D.certified, state));
  if (!shown.length) {
    state.sel = null; draw();
    $('ls-card').innerHTML = '<p>No certified code in this selection.</p>';
    $('ls-prev').disabled = $('ls-next').disabled = true;
    say('No certified code has this gain over this group.', true);
    return;
  }
  if (!shown.some(c => c.id === state.sel)) state.sel = shown[0].id;
  choose(state.sel, false);
  const fam = state.family === 'all' ? 'all groups' : `groups ${familyHTML(state.family)}`;
  const cand = state.cand && state.gain !== '3' ? ' Search candidates shown.' : state.cand ? ' Search candidates hidden: they have gain two.' : '';
  say(`Showing ${shown.length} certified codes over ${fam}.${cand} Selected: ${words(shown.find(c => c.id === state.sel))}`, true);
}

function legend() {
  const item = (draw, label) => {
    const e = document.createElement('span'), s = el('svg', { width: 22, height: 16, viewBox: '0 0 22 16', 'aria-hidden': 'true' });
    draw(s); e.append(s, label); return e;
  };
  $('ls-legend').replaceChildren(
    item(s => el('path', { d: markerPath('circle', 11, 8, 5), class: 'pc-mark' }, el('g', { class: 'ls-t1' }, s)), 'Table 1: gain two, exact distance'),
    item(s => el('path', { d: markerPath('square', 11, 8, 5), class: 'pc-mark' }, el('g', { class: 'ls-t2' }, s)), 'Table 2: gain three or more, also for the whole code'),
    item(s => el('path', { d: markerPath('square', 11, 8, 5), class: 'pc-mark' }, el('g', { class: 'ls-t2 ls-open' }, s)), 'Table 2: gain three for a best logical only'),
    item(s => el('path', { d: plus(11, 8, 4), class: 'ls-cand' }, s), 'Search candidate: rigid, gain two, estimated distance'),
    item(s => el('circle', { cx: 11, cy: 8, r: 6.5, class: 'ls-sel-ring' }, s), 'Selected'));
}

// ---------- the data tables ----------
function table() {
  const g = c => parseGroup(c.group).html;
  const cert = sortCodes(D.certified).map(c => `<tr><td>${c.table}</td><th scope="row">${g(c)}</th><td>${nkd(c)}</td><td>${c.w}</td><td>${c.E_order}</td><td>${c.rigid ? 'yes' : 'no'}</td><td>${c.mu}</td><td>${c.base} (${c.base_order})</td><td>${ratio(c.mu, c.base)}</td><td>${c.table === 2 ? codeGain(c.orbits.list).text : ''}</td></tr>`).join('');
  const cand = D.candidates.map(c => `<tr><th scope="row">${g(c)}</th><td>[[${c.n},${c.k}]]</td><td>${c.d_est}</td><td>${c.w}</td><td>${c.mu}</td><td>${c.base} (${c.base_order})</td></tr>`).join('');
  $('ls-table').innerHTML =
    `<div class="pc-scroll"><table><caption>The 27 certified codes. &mu;: co-measurable number of a best logical over E; base: the best over Abelian subgroups H of E, with |H|; &gamma; = &mu;/base; last column: gain of the whole code (Table 2). Distances are exact.</caption>
    <thead><tr><th scope="col">Table</th><th scope="col">G</th><th scope="col">[[n,k,d]]</th><th scope="col">w</th><th scope="col">|E|</th><th scope="col">Rigid</th><th scope="col">&mu;</th><th scope="col">Base (|H|)</th><th scope="col">&gamma;</th><th scope="col">Code &gamma;</th></tr></thead><tbody>${cert}</tbody></table></div>
    <div class="pc-scroll"><table><caption>The ${D.candidates.length} rigid gain-two candidates of the code search (${D.search.file.split('/').pop()}): d is an information-set estimate, an upper bound.</caption>
    <thead><tr><th scope="col">G</th><th scope="col">[[n,k]]</th><th scope="col">d (est.)</th><th scope="col">w</th><th scope="col">&mu;</th><th scope="col">Base (|H|)</th></tr></thead><tbody>${cand}</tbody></table></div>`;
}

function init(data) {
  D = data;
  for (const id of ['ls-ctl', 'ls-detail', 'ls-legend', 'ls-data']) $(id).hidden = false;
  $('ls-fallback').hidden = true;
  $('ls-src').textContent = ` at commit ${D.source.commit.slice(0, 7)}, extracted ${D.source.extracted}`;
  const sel = $('ls-fam');
  sel.append(new Option('All groups', 'all'), ...families(D.certified).map(f => new Option(f === 'Z9⋊Z12' ? 'Z9 ⋊ Z12' : `${f} × Zm`, f)));
  sel.addEventListener('change', () => { state.family = sel.value; refilter(); });
  document.querySelectorAll('input[name=ls-gain]').forEach(i => {
    i.checked = i.value === state.gain;
    i.addEventListener('change', () => { state.gain = i.value; refilter(); });
  });
  $('ls-cand').addEventListener('change', e => { state.cand = e.target.checked; refilter(); });
  const step = k => { const i = shown.findIndex(c => c.id === state.sel), j = move(i, k, shown.length); if (j !== null && j !== i) choose(shown[j].id, false); };
  $('ls-prev').addEventListener('click', () => step('ArrowLeft'));
  $('ls-next').addEventListener('click', () => step('ArrowRight'));
  legend(); table();
  shown = sortCodes(visible(D.certified, state));
  // start on the largest gain-three code
  state.sel = shown.filter(c => c.table === 2).sort((a, b) => b.n - a.n || b.d - a.d || b.k - a.k)[0].id;
  choose(state.sel, false);
  say(`${shown.length} certified codes and ${D.candidates.length} search candidates. Selected: ${words(shown.find(c => c.id === state.sel))} Use the arrow keys or the Previous and Next buttons to move between codes.`, true);
  document.addEventListener('tp-theme', draw);
  let lastW = 0;
  new ResizeObserver(() => { const w = $('ls-plot').clientWidth; if (Math.abs(w - lastW) > 1) { lastW = w; draw(); } }).observe($('ls-plot'));
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
fetch(new URL('../data/lifted-surgery.json', import.meta.url))
  .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
  .then(init)
  .catch(() => say('The figure data could not be loaded. The text around the figure states the main result.', true));
