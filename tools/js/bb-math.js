// Bivariate bicycle codes: parse the two polynomials, build H_X and H_Z, and compute n, k, ranks, weights and the
// components of the Tanner graph. Pure; no DOM. Tests: _studio/tools/tests/tools/bb-math.test.mjs.
//
// Definitions from Bravyi, Cross, Gambetta, Maslov, Rall and Yoder, "High-threshold and low-overhead fault-tolerant
// quantum memory", Nature 627, 778 (2024), arXiv:2308.07915, Section 4: S_l is the l x l cyclic shift whose row i
// has its one in column i + 1 mod l; x = S_l (x) I_m, y = I_l (x) S_m; A and B are sums of monomials in x and y;
// H_X = [A | B], H_Z = [B^T | A^T], n = 2lm, k = n - rank H_X - rank H_Z = 2 dim(ker A cap ker B).
// Index r = i*m + j stands for the cell (i, j), the monomial x^i y^j. The monomial x^a y^b has its one in row r at
// the column of cell (i + a mod l, j + b mod m).

// Table 3 of arXiv:2308.07915 (n, k, d, l, m, A, B and the net encoding rate r = k/2n as printed there, rounded
// down to an inverse integer). dExact false: the paper gives only the upper bound d <= value.
export const PRESETS = [
  { name: '[[72,12,6]]', n: 72, k: 12, d: 6, dExact: true, rate: '1/12', l: 6, m: 6, A: 'x^3 + y + y^2', B: 'y^3 + x + x^2' },
  { name: '[[90,8,10]]', n: 90, k: 8, d: 10, dExact: true, rate: '1/23', l: 15, m: 3, A: 'x^9 + y + y^2', B: '1 + x^2 + x^7' },
  { name: '[[108,8,10]]', n: 108, k: 8, d: 10, dExact: true, rate: '1/27', l: 9, m: 6, A: 'x^3 + y + y^2', B: 'y^3 + x + x^2' },
  { name: '[[144,12,12]]', n: 144, k: 12, d: 12, dExact: true, rate: '1/24', l: 12, m: 6, A: 'x^3 + y + y^2', B: 'y^3 + x + x^2' },
  { name: '[[288,12,18]]', n: 288, k: 12, d: 18, dExact: true, rate: '1/48', l: 12, m: 12, A: 'x^3 + y^2 + y^7', B: 'y^3 + x + x^2' },
  { name: '[[360,12,<=24]]', n: 360, k: 12, d: 24, dExact: false, rate: '1/60', l: 30, m: 6, A: 'x^9 + y + y^2', B: 'y^3 + x^25 + x^26' },
  { name: '[[756,16,<=34]]', n: 756, k: 16, d: 34, dExact: false, rate: '1/95', l: 21, m: 18, A: 'x^3 + y^10 + y^17', B: 'y^5 + x^3 + x^19' },
];
export const SOURCE = 'Bravyi, Cross, Gambetta, Maslov, Rall and Yoder, Nature 627, 778 (2024), arXiv:2308.07915, Table 3';

// l and m each up to LIMITS.side, and lm up to LIMITS.cells (n = 2lm up to 2400).
export const LIMITS = { side: 60, cells: 1200 };

// ---------- parsing ----------
const HELP = 'Write a sum of monomials such as x^3 + y + y^2, 1 + x*y or x^2y^3.';

function parseTerm(s) {
  let i = 0, a = 0, b = 0, factors = 0, star = false;
  const digits = () => { const st = i; while (i < s.length && s[i] >= '0' && s[i] <= '9') i++; return s.slice(st, i); };
  const space = () => { while (i < s.length && /\s/.test(s[i])) i++; };
  for (;;) {
    space();
    if (i >= s.length) break;
    const ch = s[i];
    if (ch === '*') {
      if (!factors || star) return { error: `A "*" must stand between two factors. ${HELP}` };
      star = true; i++; continue;
    }
    if (ch >= '0' && ch <= '9') {
      const d = digits();
      if (d !== '1') return { error: `"${d}" is not a monomial: the only constant over F2 is 1. ${HELP}` };
      factors++; star = false; continue;
    }
    if (ch === 'x' || ch === 'y') {
      i++; space();
      let e = 1;
      if (s[i] === '^') {
        i++; space();
        const d = digits();
        if (!d) return { error: `"^" after ${ch} must be followed by a whole number, as in ${ch}^2.` };
        if (d.length > 9) return { error: `The exponent ${d.slice(0, 12)}${d.length > 12 ? '...' : ''} is too large.` };
        e = Number(d);
      }
      if (ch === 'x') a += e; else b += e;
      factors++; star = false; continue;
    }
    if (ch === '-') return { error: `Use + between terms: over F2, minus is the same as plus. ${HELP}` };
    return { error: `Unexpected character "${ch}". ${HELP}` };
  }
  if (star) return { error: `A "*" must stand between two factors. ${HELP}` };
  return { a, b };
}

// text -> { terms: [[a, b], ...] } with 0 <= a < l, 0 <= b < m, sorted, repeats cancelled over F2; or { error }.
// The zero polynomial gives terms: [].
export function parsePoly(text, l, m) {
  const s = String(text ?? '').toLowerCase().trim();
  if (!s) return { error: `The polynomial is empty. ${HELP}` };
  const parts = s.split('+');
  const odd = new Map();
  for (const part of parts) {
    if (!part.trim()) return { error: `A term is missing: check for a "+" at the start or end, or two in a row. ${HELP}` };
    const t = parseTerm(part);
    if (t.error) return t;
    const key = `${t.a % l},${t.b % m}`;
    if (odd.has(key)) odd.delete(key); else odd.set(key, [t.a % l, t.b % m]);
  }
  return { terms: [...odd.values()].sort((u, v) => u[0] - v[0] || u[1] - v[1]) };
}

const mono = ([a, b]) => (a || b) ? `${a ? (a === 1 ? 'x' : `x^${a}`) : ''}${b ? (b === 1 ? 'y' : `y^${b}`) : ''}` : '1';
export const formatPoly = terms => terms.length ? terms.map(mono).join(' + ') : '0';

export function checkSide(text) {
  const s = String(text ?? '').trim();
  if (!/^\d+$/.test(s)) return { error: `Enter a whole number from 1 to ${LIMITS.side}.` };
  const v = Number(s);
  if (v < 1 || v > LIMITS.side) return { error: `Enter a whole number from 1 to ${LIMITS.side}; ${v} is out of range.` };
  return { value: v };
}

// ---------- the code ----------
export function buildCode(l, m, A, B) {
  const half = l * m, n = 2 * half;
  const at = (r, a, b, sign) => {
    const i = Math.floor(r / m), j = r % m;
    return (((i + sign * a) % l + l) % l) * m + (((j + sign * b) % m + m) % m);
  };
  const hx = [], hz = [];
  for (let r = 0; r < half; r++) {
    // X check r: L qubits r + A, R qubits r + B (row r of [A | B])
    hx.push([...A.map(([a, b]) => at(r, a, b, 1)).sort((u, v) => u - v), ...B.map(([a, b]) => half + at(r, a, b, 1)).sort((u, v) => u - v)]);
    // Z check r: L qubits r - B, R qubits r - A (row r of [B^T | A^T])
    hz.push([...B.map(([a, b]) => at(r, a, b, -1)).sort((u, v) => u - v), ...A.map(([a, b]) => half + at(r, a, b, -1)).sort((u, v) => u - v)]);
  }
  const ablock = [], bblock = [];
  for (let r = 0; r < half; r++) { ablock.push(A.map(([a, b]) => at(r, a, b, 1))); bblock.push(B.map(([a, b]) => at(r, a, b, 1))); }
  return { l, m, half, n, A, B, hx, hz, ablock, bblock };
}

// ---------- GF(2) linear algebra on bit-packed rows ----------
export function packRows(rows, ncols) {
  const nw = Math.ceil(ncols / 32) || 1, data = new Uint32Array(rows.length * nw);
  rows.forEach((row, r) => { for (const c of row) data[r * nw + (c >>> 5)] ^= 1 << (c & 31); });
  return { rows: rows.length, ncols, nw, data };
}

export function popcount(v) {
  v -= (v >>> 1) & 0x55555555;
  v = (v & 0x33333333) + ((v >>> 2) & 0x33333333);
  return (((v + (v >>> 4)) & 0x0f0f0f0f) * 0x01010101) >>> 24;
}

// Reduced row echelon form in place; returns the pivot column of each of the first `rank` rows.
export function rref(P) {
  const { rows, ncols, nw, data } = P, piv = [];
  let r = 0;
  for (let c = 0; c < ncols && r < rows; c++) {
    const w = c >>> 5, bit = 1 << (c & 31);
    let p = r;
    while (p < rows && !(data[p * nw + w] & bit)) p++;
    if (p === rows) continue;
    if (p !== r) for (let t = 0; t < nw; t++) { const x = data[p * nw + t]; data[p * nw + t] = data[r * nw + t]; data[r * nw + t] = x; }
    for (let q = 0; q < rows; q++) {
      if (q !== r && (data[q * nw + w] & bit)) for (let t = w; t < nw; t++) data[q * nw + t] ^= data[r * nw + t];
    }
    piv.push(c); r++;
  }
  return piv;
}

export const rankGF2 = P => rref({ ...P, data: P.data.slice() }).length;

// A basis of { v : H v = 0 }, packed.
export function kernelBasis(P) {
  const Q = { ...P, data: P.data.slice() }, piv = rref(Q), { nw, ncols, data } = Q;
  const isPiv = new Uint8Array(ncols);
  for (const c of piv) isPiv[c] = 1;
  const out = [];
  for (let f = 0; f < ncols; f++) {
    if (isPiv[f]) continue;
    const v = [f];
    piv.forEach((c, r) => { if (data[r * nw + (f >>> 5)] & (1 << (f & 31))) v.push(c); });
    out.push(v);
  }
  return packRows(out, ncols);
}

export const supportOf = (data, off, nw) => {
  const s = [];
  for (let t = 0; t < nw; t++) { let x = data[off + t]; while (x) { const b = 31 - Math.clz32(x & -x); s.push(t * 32 + b); x &= x - 1; } }
  return s;
};

// ---------- the parameters ----------
export function analyze(code) {
  const { n, half, hx, hz } = code;
  const PX = packRows(hx, n), PZ = packRows(hz, n);
  const rankX = rankGF2(PX), rankZ = rankGF2(PZ);
  // ker A cap ker B = ker of [A; B] (2lm x lm)
  const kerAB = half - rankGF2(packRows([...code.ablock, ...code.bblock], half));
  const set = a => [...new Set(a)].sort((u, v) => u - v);
  const colw = rows => { const w = new Array(n).fill(0); for (const r of rows) for (const c of r) w[c]++; return w; };
  // H_X H_Z^T = 0: every X row meets every Z row in an even number of ones (counted through the qubits they share)
  const zOn = Array.from({ length: n }, () => []);
  hz.forEach((row, j) => row.forEach(q => zOn[q].push(j)));
  let commute = true;
  const meet = new Uint8Array(half);
  for (let i = 0; i < half && commute; i++) {
    const touched = [];
    for (const q of hx[i]) for (const j of zOn[q]) { if (!meet[j]) touched.push(j); meet[j] ^= 1; }
    for (const j of touched) { if (meet[j]) commute = false; meet[j] = 0; }
  }
  // components of the Tanner graph: nodes are the n qubits, then the X checks, then the Z checks
  const parent = Int32Array.from({ length: 2 * n }, (_, i) => i);
  const find = i => { while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i]; } return i; };
  const join = (a, b) => { a = find(a); b = find(b); if (a !== b) parent[a] = b; };
  hx.forEach((row, r) => row.forEach(q => join(n + r, q)));
  hz.forEach((row, r) => row.forEach(q => join(n + half + r, q)));
  let components = 0;
  for (let i = 0; i < 2 * n; i++) if (find(i) === i) components++;
  const k = n - rankX - rankZ;
  return {
    n, k, rankX, rankZ, kerAB, commute, components,
    rowWeightsX: set(hx.map(r => r.length)), rowWeightsZ: set(hz.map(r => r.length)),
    colWeightsX: set(colw(hx)), colWeightsZ: set(colw(hz)),
  };
}

// ---------- export ----------
// One line per row: the sorted 0-based column indices of its ones, separated by single spaces.
export const matrixBody = rows => rows.map(r => r.join(' ')).join('\n') + '\n';

export function matrixFile(code, which, text) {
  const { l, m, half, n } = code;
  const rows = which === 'X' ? code.hx : code.hz;
  const A = formatPoly(code.A), B = formatPoly(code.B);
  return [
    `# H_${which} of the bivariate bicycle code l = ${l}, m = ${m}, A = ${A}, B = ${B}`,
    `# Conventions of arXiv:2308.07915: x = S_l (x) I_m, y = I_l (x) S_m, H_X = [A | B], H_Z = [B^T | A^T].`,
    `# ${half} rows, ${n} columns. Each line after these comments is one row: the 0-based column indices of its ones.`,
    `# Columns 0 to ${half - 1} are the L qubits and ${half} to ${n - 1} the R qubits; within a block, cell (i, j)`,
    `# (the monomial x^i y^j) is index i*m + j. Row r is the ${which} check of cell r.`,
    `# https://pandey-tushar.com/tools/bb-codes.html${toQuery({ l, m, A: text ? text.A : A, B: text ? text.B : B })}`,
  ].join('\n') + '\n' + matrixBody(rows);
}

// ---------- links and presets ----------
export function toQuery({ l, m, A, B }) {
  return '?' + new URLSearchParams({ l: String(l), m: String(m), A, B }).toString();
}
export function fromQuery(search) {
  const q = new URLSearchParams(search || '');
  const out = {};
  for (const k of ['l', 'm', 'A', 'B']) { if (!q.has(k)) return null; out[k] = q.get(k); }
  return out;
}
// What a page link asks for: no code ('none'), a valid code ('ok', with its fields), or something that is not one ('bad').
export function linkState(search) {
  const s = new URLSearchParams(search || '');
  if (!['l', 'm', 'A', 'B'].some(k => s.has(k))) return { status: 'none' };
  const q = fromQuery(search);
  if (!q) return { status: 'bad' };
  const L = checkSide(q.l), M = checkSide(q.m);
  if (L.error || M.error || L.value * M.value > LIMITS.cells) return { status: 'bad' };
  for (const k of ['A', 'B']) {
    const p = parsePoly(q[k], L.value, M.value);
    if (p.error || !p.terms.length) return { status: 'bad' };
  }
  return { status: 'ok', q };
}
const same = (u, v) => u.length === v.length && u.every((t, i) => t[0] === v[i][0] && t[1] === v[i][1]);
export function matchPreset(l, m, A, B) {
  return PRESETS.find(p => p.l === l && p.m === m && same(parsePoly(p.A, l, m).terms, A) && same(parsePoly(p.B, l, m).terms, B)) || null;
}
