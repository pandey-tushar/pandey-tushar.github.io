// Upper bound on the distance of a CSS code by a randomized information-set search. Pure; no DOM.
// Tests: _studio/tools/tests/tools/bb-distance.test.mjs.
//
// A Z-type logical is z with H_X z = 0 that is not in the row space of H_Z; an X-type logical is the same with
// H_X and H_Z exchanged. Each iteration takes a basis of ker H_X (or ker H_Z, alternating), puts it in reduced
// row echelon form with the columns visited in a random order, and tests every row and every sum of two rows: the
// rows are codewords that vanish on all but one or two of the pivot columns, so low-weight codewords turn up often.
// A candidate counts only if it is a nontrivial logical (odd overlap with some logical of the other type). The
// lowest weight seen is an upper bound on d, never a proof of it. The random order comes from a seeded generator, so
// a seed reproduces the run iteration by iteration.
import { packRows, kernelBasis, popcount, supportOf } from './bb-math.js';

export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Logicals of the type that lives in ker(Hk): a basis of ker(Hk) modulo the row space of Hs (packed).
function logicals(kerP, stabP) {
  const { nw, ncols } = kerP, basis = [], out = [];
  const reduce = v => {
    for (const { p, row } of basis) if (v[p >>> 5] & (1 << (p & 31))) for (let t = 0; t < nw; t++) v[t] ^= row[t];
    return v;
  };
  const add = v => {
    for (let t = 0; t < nw; t++) if (v[t]) { basis.push({ p: t * 32 + (31 - Math.clz32(v[t] & -v[t])), row: v }); return true; }
    return false;
  };
  for (let r = 0; r < stabP.rows; r++) add(reduce(stabP.data.slice(r * nw, (r + 1) * nw)));
  for (let r = 0; r < kerP.rows; r++) {
    const v = kerP.data.slice(r * nw, (r + 1) * nw);
    if (add(reduce(v.slice()))) out.push(v);
  }
  return { rows: out.length, ncols, nw, data: Uint32Array.from(out.flatMap(v => [...v])) };
}

export function createSearch(code, seed) {
  const n = code.n;
  const PX = packRows(code.hx, n), PZ = packRows(code.hz, n);
  // Z-type: in ker H_X, tested against X logicals = ker H_Z mod rowspace H_X
  const sides = [
    { type: 'Z', G: kernelBasis(PX), L: logicals(kernelBasis(PZ), PX) },
    { type: 'X', G: kernelBasis(PZ), L: logicals(kernelBasis(PX), PZ) },
  ];
  const k = sides[0].L.rows;
  const rnd = mulberry32(seed);
  const nw = sides[0].G.nw, perm = Int32Array.from({ length: n }, (_, i) => i);
  const work = new Uint32Array(Math.max(sides[0].G.data.length, sides[1].G.data.length));
  const tmp = new Uint32Array(nw);
  const S = { k, iterations: 0, best: null, history: [], step };

  const nontrivial = (L, v, off) => {
    for (let r = 0; r < L.rows; r++) {
      let p = 0;
      for (let t = 0; t < nw; t++) p ^= popcount(L.data[r * nw + t] & v[off + t]);
      if (p & 1) return true;
    }
    return false;
  };
  const record = (sd, v, off, w) => {
    const support = supportOf(v, off, nw);
    S.best = { weight: w, type: sd.type, support, iteration: S.iterations };
    S.history.push(S.best);
  };

  function once(sd) {
    const { G, L } = sd, g = G.rows;
    for (let i = n - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); const t = perm[i]; perm[i] = perm[j]; perm[j] = t; }
    work.set(G.data);
    const data = work.subarray(0, G.data.length);
    // reduced row echelon form, columns in the order perm
    let r = 0;
    for (let ci = 0; ci < n && r < g; ci++) {
      const c = perm[ci], w = c >>> 5, bit = 1 << (c & 31);
      let p = r;
      while (p < g && !(data[p * nw + w] & bit)) p++;
      if (p === g) continue;
      if (p !== r) for (let t = 0; t < nw; t++) { const x = data[p * nw + t]; data[p * nw + t] = data[r * nw + t]; data[r * nw + t] = x; }
      for (let q = 0; q < g; q++) if (q !== r && (data[q * nw + w] & bit)) for (let t = 0; t < nw; t++) data[q * nw + t] ^= data[r * nw + t];
      r++;
    }
    for (let i = 0; i < g; i++) {
      let s = 0;
      for (let t = 0; t < nw; t++) s += popcount(data[i * nw + t]);
      const bound = S.best ? S.best.weight : n + 1;
      if (s < bound && nontrivial(L, data, i * nw)) record(sd, data, i * nw, s);
    }
    // sums of two rows
    for (let i = 0; i < g; i++) for (let j = i + 1; j < g; j++) {
      const bound = S.best ? S.best.weight : n + 1;
      let s = 0;
      for (let t = 0; t < nw && s < bound; t++) s += popcount(data[i * nw + t] ^ data[j * nw + t]);
      if (s < bound) {
        for (let t = 0; t < nw; t++) tmp[t] = data[i * nw + t] ^ data[j * nw + t];
        if (nontrivial(L, tmp, 0)) record(sd, tmp, 0, s);
      }
    }
  }

  function step(iters) {
    for (let it = 0; it < iters; it++) {
      S.iterations++;
      if (k > 0) once(sides[S.iterations % 2 ? 0 : 1]);
    }
    return S.best;
  }
  return S;
}
