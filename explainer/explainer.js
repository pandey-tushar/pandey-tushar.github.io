// why-error-correction.html, Fig. 1: five qubits hold one bit. Flip qubits by hand or at random, see the checks
// between neighbours light up, press Correct (the course engine's decoder, reading the checks only), and read
// how often the bit is lost with 1, 3, 5 or 7 qubits at the chosen error chance.
import { sampleErrors } from '../qec-in-practice/js/qec/noise.js';
import { emptyError } from '../qec-in-practice/js/explore-logic.js';
import { makeRow, checksLit, correct, lossTable, trend, formatChance } from './explainer-logic.js';

const N = 5;
const fig = document.getElementById('fig-vote');
const $ = s => fig.querySelector(s);
const rowEl = $('[data-row]'), status = $('.vote-status'), slider = $('#vote-p'), pout = $('[data-pout]');
const table = $('[data-loss]'), trendEl = $('[data-trend]');
const row = makeRow(N);
let fixedBy = null; // qubits put back by the last Correct, until the next change

const list = a => (a.length < 2 ? `${a[0]}` : `${a.slice(0, -1).join(', ')} and ${a[a.length - 1]}`);
const ones = a => [...a.keys()].filter(i => a[i]);
const pct = p => `${Math.round(p * 100)}%`;
const s = (k, w) => `${k} ${w}${k === 1 ? '' : 's'}`;

fig.querySelectorAll('[hidden]').forEach(e => e.removeAttribute('hidden'));

const qs = [], cs = [];
for (let i = 0; i < N; i++) {
  if (i) {
    const c = document.createElement('span');
    c.className = 'chk';
    c.dataset.check = i - 1;
    c.setAttribute('role', 'img');
    rowEl.append(c);
    cs.push(c);
  }
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'q';
  b.dataset.q = i;
  b.textContent = i + 1;
  b.addEventListener('click', () => flip(i));
  rowEl.append(b);
  qs.push(b);
}

function draw() {
  const lit = checksLit(row);
  qs.forEach((b, i) => {
    const f = !!row.err.x[i];
    b.setAttribute('aria-pressed', String(f));
    b.classList.toggle('fixed', !!(fixedBy && fixedBy[i]));
    b.setAttribute('aria-label', `Qubit ${i + 1}, ${f ? 'flipped' : 'not flipped'}`);
  });
  cs.forEach((c, k) => {
    c.classList.toggle('lit', !!lit[k]);
    c.setAttribute('aria-label', `Check between qubits ${k + 1} and ${k + 2}: ${lit[k] ? 'lit' : 'quiet'}`);
  });
}

function litText() {
  const k = ones(checksLit(row)).length;
  return k ? `${s(k, 'check')} lit.` : 'Every check is quiet.';
}

function flip(i) {
  fixedBy = null;
  row.err.x[i] ^= 1;
  draw();
  status.textContent = `Qubit ${i + 1} ${row.err.x[i] ? 'flipped' : 'flipped back'}. ${litText()}`;
}

$('[data-correct]').addEventListener('click', () => {
  const k = ones(row.err.x).length;
  if (!ones(checksLit(row)).length) {
    fixedBy = null;
    draw();
    status.textContent = k
      ? 'Every check is quiet, so Correct changes nothing. Every qubit holds the same value, but it is the wrong one: the stored bit is lost.'
      : 'Every check is quiet, so Correct changes nothing. The stored bit survived.';
    return;
  }
  const r = correct(row), put = ones(r.correction).map(i => i + 1);
  row.err = { x: r.after.x, z: r.after.z };
  fixedBy = r.correction;
  draw();
  const did = `Reading only the checks, Correct flipped ${put.length === 1 ? 'qubit' : 'qubits'} ${list(put)}.`;
  status.textContent = r.survived
    ? `${did} The stored bit survived.`
    : `${did} ${k} of ${N} qubits had flipped, more than half, so the vote went the wrong way. Every check is quiet again, but the stored bit is lost.`;
});

$('[data-random]').addEventListener('click', () => {
  fixedBy = null;
  row.err = sampleErrors(row.code, +slider.value, Math.random);
  draw();
  const f = ones(row.err.x).map(i => i + 1);
  const what = f.length ? `${f.length === 1 ? 'qubit' : 'qubits'} ${list(f)} flipped` : 'no qubit flipped this time';
  status.textContent = `Random errors at a ${pct(+slider.value)} chance each: ${what}. ${litText()} Press Correct.`;
});

$('[data-clear]').addEventListener('click', () => {
  fixedBy = null;
  row.err = emptyError(row.code);
  draw();
  status.textContent = 'Cleared. Every qubit holds the stored bit and every check is quiet.';
});

const TREND = {
  help: 'At this error chance, more qubits help: the bit is lost less often.',
  hurt: 'At this error chance, more qubits make it worse: the bit is lost more often.',
  same: 'At exactly one half, adding qubits changes nothing. This is the threshold.',
};

function drawLoss() {
  const p = +slider.value;
  pout.textContent = pct(p);
  table.replaceChildren(...lossTable(p).map(({ n, lost }) => {
    const tr = document.createElement('tr');
    if (n === N) tr.className = 'this';
    const th = document.createElement('th'), bar = document.createElement('td'), v = document.createElement('td');
    th.scope = 'row';
    th.textContent = n === 1 ? '1 qubit' : `${n} qubits`;
    bar.className = 'bar';
    bar.setAttribute('aria-hidden', 'true');
    const fill = document.createElement('span');
    fill.style.width = `${(lost * 100).toFixed(2)}%`;
    bar.append(fill);
    v.textContent = formatChance(lost);
    tr.append(th, bar, v);
    return tr;
  }));
  const t = trend(p);
  if (trendEl.dataset.t !== t) { trendEl.dataset.t = t; trendEl.textContent = TREND[t]; }
}

slider.addEventListener('input', drawLoss);
draw();
drawLoss();
status.textContent = 'Five qubits hold the bit and every check is quiet. Click a qubit to flip it.';
