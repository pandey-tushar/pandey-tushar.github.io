import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import {
  PRESETS, LIMITS, parsePoly, formatPoly, checkSide, buildCode, analyze, packRows, rankGF2,
  matrixBody, matrixFile, toQuery, fromQuery, matchPreset,
} from '../../../../tools/js/bb-math.js';

const REF = JSON.parse(readFileSync(new URL('./bb-reference.json', import.meta.url), 'utf8'));
const sha = s => createHash('sha256').update(s, 'ascii').digest('hex');
const terms = (s, l, m) => { const p = parsePoly(s, l, m); assert.ok(p.terms, `${s}: ${p.error}`); return p.terms; };
const code = (l, m, A, B) => buildCode(l, m, terms(A, l, m), terms(B, l, m));

test('parser accepts monomials in the usual notations', () => {
  assert.deepEqual(terms('x^3 + y + y^2', 6, 6), [[0, 1], [0, 2], [3, 0]]);
  assert.deepEqual(terms('1 + x*y', 6, 6), [[0, 0], [1, 1]]);
  assert.deepEqual(terms('x^2y^3', 6, 6), [[2, 3]]);
  assert.deepEqual(terms('x^2 y^3', 6, 6), [[2, 3]]);
  assert.deepEqual(terms('  X^2*Y^3+1 ', 6, 6), [[0, 0], [2, 3]]);
  assert.deepEqual(terms('y x', 6, 6), [[1, 1]]);
  assert.deepEqual(terms('x*x^2', 6, 6), [[3, 0]]);
  assert.deepEqual(terms('x^0', 6, 6), [[0, 0]]);
});

test('exponents are reduced mod l and m', () => {
  assert.deepEqual(terms('x^7 + y^6', 6, 6), [[0, 0], [1, 0]]);
  assert.deepEqual(terms('x^25 + x^26 + y^3', 30, 6), [[0, 3], [25, 0], [26, 0]]);
  assert.deepEqual(terms('x^30y^13', 30, 6), [[0, 1]]);
  assert.deepEqual(terms('x + y', 1, 1), []);   // x = y = 1 when l = m = 1: they cancel
});

test('repeated monomials cancel over F2', () => {
  assert.deepEqual(terms('x + x + y', 6, 6), [[0, 1]]);
  assert.deepEqual(terms('x + x + x', 6, 6), [[1, 0]]);
  assert.deepEqual(terms('x^8 + x^2 + 1', 6, 6), [[0, 0]]);
});

test('parser rejects malformed input with a message in words', () => {
  for (const bad of ['', '   ', 'x +', '+ x', 'x ++ y', '2x', 'z', 'x^', 'x^-1', 'x^1.5', 'x^a', 'x - y', '(x+y)', 'x^^2', '3', 'xy^', 'x y z']) {
    const p = parsePoly(bad, 6, 6);
    assert.ok(!p.terms && typeof p.error === 'string' && p.error.length > 5 && !/NaN|undefined/.test(p.error), `${JSON.stringify(bad)} gave ${JSON.stringify(p)}`);
  }
  assert.ok(parsePoly('x^99999999999999999999', 6, 6).error);
});

test('l and m are checked against the limits', () => {
  assert.equal(checkSide('6').value, 6);
  assert.equal(checkSide(' 12 ').value, 12);
  assert.equal(checkSide(String(LIMITS.side)).value, LIMITS.side);
  for (const bad of ['', '0', '-1', '1.5', 'abc', String(LIMITS.side + 1), '1e3', 'NaN']) {
    const r = checkSide(bad);
    assert.ok(r.error && !/NaN|undefined/.test(r.error), `${bad}: ${JSON.stringify(r)}`);
  }
});

test('formatPoly writes the canonical form back', () => {
  assert.equal(formatPoly([[0, 1], [0, 2], [3, 0]]), 'y + y^2 + x^3');
  assert.equal(formatPoly([[0, 0], [1, 1], [2, 3]]), '1 + xy + x^2y^3');
  assert.equal(formatPoly([]), '0');
});

test('every preset from Table 3 of arXiv:2308.07915: n, k, commutation, weight 6', () => {
  assert.equal(PRESETS.length, 7);
  for (const p of PRESETS) {
    const c = code(p.l, p.m, p.A, p.B), a = analyze(c);
    assert.equal(a.n, p.n, p.name);
    assert.equal(a.k, p.k, p.name);
    assert.equal(a.commute, true, p.name);
    assert.deepEqual(a.rowWeightsX, [6], p.name);
    assert.deepEqual(a.rowWeightsZ, [6], p.name);
    assert.deepEqual(a.colWeightsX, [3], p.name);
    assert.deepEqual(a.colWeightsZ, [3], p.name);
    assert.equal(a.components, 1, `${p.name} Tanner graph connected`);
    assert.equal(a.k, 2 * a.kerAB, `${p.name}: k = 2 dim(ker A cap ker B)`);
    assert.equal(p.name, `[[${p.n},${p.k},${p.dExact ? '' : '<='}${p.d}]]`);
  }
});

test('presets, ranks and full supports agree with the numpy/ldpc reference', () => {
  assert.equal(REF.presets.length, PRESETS.length);
  for (const r of REF.presets) {
    const p = PRESETS.find(q => q.name === r.name);
    assert.ok(p, r.name);
    assert.equal(p.l, r.l); assert.equal(p.m, r.m);
    assert.deepEqual(terms(p.A, p.l, p.m), [...r.A].sort((u, v) => u[0] - v[0] || u[1] - v[1]), `${r.name} A`);
    assert.deepEqual(terms(p.B, p.l, p.m), [...r.B].sort((u, v) => u[0] - v[0] || u[1] - v[1]), `${r.name} B`);
    const c = code(p.l, p.m, p.A, p.B), a = analyze(c);
    assert.deepEqual([a.n, a.k, a.rankX, a.rankZ], [r.n, r.k, r.rankX, r.rankZ], r.name);
    assert.equal(sha(matrixBody(c.hx)), r.hashX, `${r.name} H_X supports`);
    assert.equal(sha(matrixBody(c.hz)), r.hashZ, `${r.name} H_Z supports`);
  }
});

test('random codes from the reference script (fixed seed) agree in n, k, ranks, weights and supports', () => {
  assert.ok(REF.random.length >= 10);
  for (const r of REF.random) {
    const c = code(r.l, r.m, r.A, r.B), a = analyze(c);
    const tag = `l=${r.l} m=${r.m} A=${r.A} B=${r.B}`;
    assert.deepEqual([a.n, a.k, a.rankX, a.rankZ], [r.n, r.k, r.rankX, r.rankZ], tag);
    assert.deepEqual([a.rowWeightsX, a.rowWeightsZ, a.colWeightsX, a.colWeightsZ], [r.rowWeightsX, r.rowWeightsZ, r.colWeightsX, r.colWeightsZ], tag);
    assert.equal(a.commute, true, tag);
    assert.equal(sha(matrixBody(c.hx)), r.hashX, `${tag} H_X`);
    assert.equal(sha(matrixBody(c.hz)), r.hashZ, `${tag} H_Z`);
  }
});

test('the commutation check catches a broken H_Z', () => {
  const c = code(6, 6, 'x^3 + y + y^2', 'y^3 + x + x^2');
  c.hz = c.hz.map((r, i) => (i ? r : r.slice(1)));
  assert.equal(analyze(c).commute, false);
});

test('GF(2) rank on small cases', () => {
  const R = (rows, n) => rankGF2(packRows(rows, n));
  assert.equal(R([], 4), 0);
  assert.equal(R([[0], [1], [0, 1]], 2), 2);
  assert.equal(R([[0, 40], [40, 70], [0, 70]], 71), 2);
  assert.equal(R([[31], [32], [63], [64]], 65), 4);
});

test('Tanner graph components: a code that splits into pieces', () => {
  // A = 1 + x^2, B = 1 + x^4 on l = 8, m = 2: only even shifts of x and no y, so the cells split by
  // (i mod 2, j): 4 components
  const a = analyze(code(8, 2, '1 + x^2', '1 + x^4'));
  assert.equal(a.components, 4);
});

test('the export format: header lines start with #, then one row per line', () => {
  const p = PRESETS.find(q => q.name === '[[72,12,6]]');
  const c = code(p.l, p.m, p.A, p.B);
  const f = matrixFile(c, 'X', { A: p.A, B: p.B });
  const lines = f.split('\n');
  assert.ok(lines[0].startsWith('#'));
  const body = lines.filter(s => !s.startsWith('#')).join('\n');
  assert.equal(body, matrixBody(c.hx));
  assert.equal(sha(body), REF.presets.find(r => r.name === p.name).hashX);
  assert.ok(f.endsWith('\n'));
  assert.ok(/^[\x09\x0a\x20-\x7e]*$/.test(f), 'ASCII only');
});

test('the page states the limits of bb-math.js and imports nothing from papers/ or qec-in-practice/', () => {
  const root = new URL('../../../../tools/', import.meta.url);
  const html = readFileSync(new URL('bb-codes.html', root), 'utf8');
  for (const id of ['lim-side', 'lim-side2']) assert.ok(html.includes(`<span id="${id}">${LIMITS.side}</span>`), id);
  for (const id of ['lim-cells', 'lim-cells2']) assert.ok(html.includes(`<span id="${id}">${LIMITS.cells.toLocaleString('en-US')}</span>`), id);
  for (const f of ['bb-codes.html', 'bb-codes.css', 'js/bb-page.js', 'js/bb-math.js', 'js/bb-distance.js', 'js/bb-worker.js']) {
    const s = readFileSync(new URL(f, root), 'utf8');
    assert.ok(!/papers\/|qec-in-practice\/js/.test(s.replace(/href="\/papers\/bb-erasure-baselines\.html"/, '')), `${f} imports from another section`);
    assert.ok(/^[\x09\x0a\x0d\x20-\x7e]*$/.test(s), `${f} is ASCII`);
  }
});

test('query string round trip and preset matching', () => {
  const q = toQuery({ l: 12, m: 6, A: 'x^3 + y + y^2', B: 'y^3 + x + x^2' });
  assert.equal(q, '?l=12&m=6&A=x%5E3+%2B+y+%2B+y%5E2&B=y%5E3+%2B+x+%2B+x%5E2');
  assert.deepEqual(fromQuery(q), { l: '12', m: '6', A: 'x^3 + y + y^2', B: 'y^3 + x + x^2' });
  assert.equal(fromQuery(''), null);
  assert.equal(fromQuery('?l=3'), null);
  const p = matchPreset(12, 6, terms('y^2 + x^3 + y', 12, 6), terms('x^2+x+y^3', 12, 6));
  assert.equal(p && p.name, '[[144,12,12]]');
  assert.equal(matchPreset(12, 6, terms('x^3 + y + y^2', 12, 6), terms('y^3 + x', 12, 6)), null);
});
