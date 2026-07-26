/* Seeded randomness for the motif library.

   Nothing in packages/motifs may call Math.random(). Every draw builds its
   streams from an explicit seed, so the same seed and the same params produce
   the same pixels on every load and every machine. The determinism gate in
   apps/illustrated hashes two renders of the same frame; an unseeded call
   shows up there as drift.

   mulberry32 is used because it is 32-bit integer arithmetic only. Anything
   touching floating point accumulation would risk differing across engines. */

export type Seed = number | string;

export interface Rng {
  /** next float in [0, 1) */
  (): number;
  range(lo: number, hi: number): number;
  int(lo: number, hi: number): number;
  pick<T>(items: readonly T[]): T;
  chance(p: number): boolean;
  /** approximately normal, mean 0, sd 1, clamped to +-3 */
  gauss(): number;
  /** -1 or 1 */
  sign(): number;
  /** an independent stream derived from this seed and a tag. Use one stream
      per feature so adding a feature does not shift every other draw. */
  fork(tag: string): Rng;
}

/** xmur3: string to a well mixed 32-bit integer. */
export function hashSeed(seed: Seed): number {
  const s = typeof seed === 'number' ? String(seed) : seed;
  let h = 1779033703 ^ s.length;
  for (let i = 0; i < s.length; i++) {
    h = Math.imul(h ^ s.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  h = Math.imul(h ^ (h >>> 16), 2246822507);
  h = Math.imul(h ^ (h >>> 13), 3266489909);
  return (h ^ (h >>> 16)) >>> 0;
}

export function rng(seed: Seed): Rng {
  let a = hashSeed(seed);
  const next = (): number => {
    a = (a + 0x6d2b79f5) | 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const r = next as Rng;
  r.range = (lo, hi) => lo + (hi - lo) * next();
  r.int = (lo, hi) => lo + Math.floor((hi - lo + 1) * next());
  r.pick = <T>(items: readonly T[]): T => items[Math.floor(next() * items.length) % items.length]!;
  r.chance = (p) => next() < p;
  r.gauss = () => {
    /* sum of four uniforms, cheap and bounded. No log, no trig, no NaN path. */
    const v = next() + next() + next() + next() - 2;
    return v * 1.732;
  };
  r.sign = () => (next() < 0.5 ? -1 : 1);
  r.fork = (tag: string) => rng(String(seed) + '/' + tag);
  return r;
}

/* ---------- seeded value noise ---------- */

const TABLE = 512;

function table(seed: Seed): Float64Array {
  const r = rng(seed);
  const t = new Float64Array(TABLE);
  for (let i = 0; i < TABLE; i++) t[i] = r() * 2 - 1;
  return t;
}

const smooth = (t: number): number => t * t * (3 - 2 * t);

/** One dimensional value noise in [-1, 1]. Deterministic in the seed. */
export function noise1(seed: Seed, octaves = 3): (x: number) => number {
  const t = table(seed);
  const one = (x: number): number => {
    const i = Math.floor(x);
    const f = x - i;
    const a = t[((i % TABLE) + TABLE) % TABLE]!;
    const b = t[(((i + 1) % TABLE) + TABLE) % TABLE]!;
    return a + (b - a) * smooth(f);
  };
  if (octaves <= 1) return one;
  return (x: number): number => {
    let sum = 0;
    let amp = 1;
    let norm = 0;
    let f = 1;
    for (let o = 0; o < octaves; o++) {
      sum += one(x * f + o * 37.13) * amp;
      norm += amp;
      amp *= 0.5;
      f *= 2.03;
    }
    return sum / norm;
  };
}

/** Two dimensional value noise in [-1, 1]. */
export function noise2(seed: Seed, octaves = 2): (x: number, y: number) => number {
  const t = table(seed);
  const at = (i: number, j: number): number =>
    t[((((i * 73856093) ^ (j * 19349663)) >>> 0) % TABLE)]!;
  const one = (x: number, y: number): number => {
    const i = Math.floor(x);
    const j = Math.floor(y);
    const fx = smooth(x - i);
    const fy = smooth(y - j);
    const a = at(i, j) + (at(i + 1, j) - at(i, j)) * fx;
    const b = at(i, j + 1) + (at(i + 1, j + 1) - at(i, j + 1)) * fx;
    return a + (b - a) * fy;
  };
  if (octaves <= 1) return one;
  return (x: number, y: number): number => {
    let sum = 0;
    let amp = 1;
    let norm = 0;
    let f = 1;
    for (let o = 0; o < octaves; o++) {
      sum += one(x * f + o * 11.7, y * f - o * 5.3) * amp;
      norm += amp;
      amp *= 0.5;
      f *= 2.07;
    }
    return sum / norm;
  };
}

/* ---------- small numeric helpers used by every motif ---------- */

export const clamp = (v: number, lo = 0, hi = 1): number => (v < lo ? lo : v > hi ? hi : v);
export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;
export const ease = (t: number): number => t * t * (3 - 2 * t);
export const easeIn = (t: number): number => t * t;
export const easeOut = (t: number): number => 1 - (1 - t) * (1 - t);
/** maps [lo, hi] of v onto 0..1, clamped. The workhorse of scroll choreography. */
export const span = (v: number, lo: number, hi: number): number =>
  hi === lo ? (v < lo ? 0 : 1) : clamp((v - lo) / (hi - lo));
export const TAU = Math.PI * 2;
