// Aaronson-Gottesman (CHP) stabilizer tableau. Rows 0..n-1 destabilizers, n..2n-1 stabilizers,
// row 2n scratch. Bits packed in 32-bit words; (x,z) = (1,1) is Y. Outcome 1 means eigenvalue -1.

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

function pop(v) {
  v -= (v >>> 1) & 0x55555555;
  v = (v & 0x33333333) + ((v >>> 2) & 0x33333333);
  return (Math.imul((v + (v >>> 4)) & 0x0f0f0f0f, 0x01010101) >>> 24);
}

export class Tableau {
  constructor(n, rng = Math.random) {
    this.n = n;
    this.rng = rng;
    this.W = (n + 31) >>> 5;
    const rows = 2 * n + 1;
    this.xs = new Uint32Array(rows * this.W);
    this.zs = new Uint32Array(rows * this.W);
    this.r = new Uint8Array(rows);
    for (let i = 0; i < n; i++) {
      this.xs[i * this.W + (i >>> 5)] = 1 << (i & 31);
      this.zs[(n + i) * this.W + (i >>> 5)] = 1 << (i & 31);
    }
  }

  clone() {
    const t = Object.create(Tableau.prototype);
    Object.assign(t, this, { xs: this.xs.slice(), zs: this.zs.slice(), r: this.r.slice() });
    return t;
  }

  // Apply f(xbit, zbit) -> [x, z, flip] to qubit a on every row.
  _each(a, f) {
    const { W, xs: x, zs: z, r } = this;
    const w = a >>> 5, m = 1 << (a & 31);
    for (let i = 0, k = w; i < 2 * this.n; i++, k += W) {
      const [xb, zb, flip] = f((x[k] & m) !== 0, (z[k] & m) !== 0);
      x[k] = xb ? x[k] | m : x[k] & ~m;
      z[k] = zb ? z[k] | m : z[k] & ~m;
      if (flip) r[i] ^= 1;
    }
  }

  h(a) { this._each(a, (x, z) => [z, x, x && z]); }
  s(a) { this._each(a, (x, z) => [x, z !== x, x && z]); }
  sdg(a) { this._each(a, (x, z) => [x, z !== x, x && !z]); }
  x(a) { this._each(a, (x, z) => [x, z, z]); }
  y(a) { this._each(a, (x, z) => [x, z, x !== z]); }
  z(a) { this._each(a, (x, z) => [x, z, x]); }

  cx(a, b) {
    const { W, xs: x, zs: z, r } = this;
    const wa = a >>> 5, ma = 1 << (a & 31), wb = b >>> 5, mb = 1 << (b & 31);
    for (let i = 0, o = 0; i < 2 * this.n; i++, o += W) {
      const xa = (x[o + wa] & ma) !== 0, za = (z[o + wa] & ma) !== 0;
      const xb = (x[o + wb] & mb) !== 0, zb = (z[o + wb] & mb) !== 0;
      if (xa && zb && xb === za) r[i] ^= 1;
      if (xa) x[o + wb] ^= mb;
      if (zb) z[o + wa] ^= ma;
    }
  }

  // Row h := row i * row h.
  _rowsum(h, i) {
    const { W, xs: x, zs: z, r } = this;
    let sum = 2 * r[h] + 2 * r[i];
    for (let w = 0, oh = h * W, oi = i * W; w < W; w++, oh++, oi++) {
      const x1 = x[oi], z1 = z[oi], x2 = x[oh], z2 = z[oh];
      const plus = (x1 & z1 & ~x2 & z2) | (x1 & ~z1 & x2 & z2) | (~x1 & z1 & x2 & ~z2);
      const minus = (x1 & z1 & x2 & ~z2) | (x1 & ~z1 & ~x2 & z2) | (~x1 & z1 & x2 & z2);
      sum += pop(plus) - pop(minus);
      x[oh] = x2 ^ x1;
      z[oh] = z2 ^ z1;
    }
    r[h] = (((sum % 4) + 4) % 4) === 2 ? 1 : 0;
  }

  _anti(i, px, pz) {
    const { W, xs: x, zs: z } = this;
    let p = 0;
    for (let w = 0, o = i * W; w < W; w++, o++) p ^= pop((x[o] & pz[w]) ^ (z[o] & px[w]));
    return p & 1;
  }

  measureZ(q) { return this.measurePauli({ Z: [q] }); }

  // spec {X:[...], Z:[...]}; a qubit in both lists is Y.
  measurePauli(spec) {
    const { n, W, xs: x, zs: z, r } = this;
    const px = new Uint32Array(W), pz = new Uint32Array(W);
    for (const q of spec.X || []) px[q >>> 5] |= 1 << (q & 31);
    for (const q of spec.Z || []) pz[q >>> 5] |= 1 << (q & 31);
    let p = -1;
    for (let i = n; i < 2 * n; i++) if (this._anti(i, px, pz)) { p = i; break; }
    if (p >= 0) {
      for (let i = 0; i < 2 * n; i++) if (i !== p && this._anti(i, px, pz)) this._rowsum(i, p);
      const d = p - n;
      x.copyWithin(d * W, p * W, (p + 1) * W);
      z.copyWithin(d * W, p * W, (p + 1) * W);
      r[d] = r[p];
      x.set(px, p * W);
      z.set(pz, p * W);
      r[p] = this.rng() < 0.5 ? 1 : 0;
      return r[p];
    }
    const s = 2 * n;
    x.fill(0, s * W, (s + 1) * W);
    z.fill(0, s * W, (s + 1) * W);
    r[s] = 0;
    for (let i = 0; i < n; i++) if (this._anti(i, px, pz)) this._rowsum(s, i + n);
    return r[s];
  }
}
