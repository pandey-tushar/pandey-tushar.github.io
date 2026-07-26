/* The shared drawing vocabulary.

   Coherence across twenty two cantos comes from here, not from discipline.
   When the coin and the mirror both engrave a face, they call the same
   function with different degradation, so the mirror is visibly failing to
   copy the same object the coin is.

   No canvas text anywhere in this library. Text rasterises against whatever
   font the machine resolved, which would break the cross machine half of the
   determinism promise. Marks are paths. */

import { alpha, type Palette } from './surface.js';
import { clamp, TAU, type Rng } from './rng.js';

export type Pt = readonly [number, number];

export function poly(ctx: CanvasRenderingContext2D, pts: readonly Pt[], close = false): void {
  if (pts.length === 0) return;
  ctx.beginPath();
  ctx.moveTo(pts[0]![0], pts[0]![1]);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i]![0], pts[i]![1]);
  if (close) ctx.closePath();
}

export function segment(ctx: CanvasRenderingContext2D, a: Pt, b: Pt): void {
  ctx.beginPath();
  ctx.moveTo(a[0], a[1]);
  ctx.lineTo(b[0], b[1]);
}

/** A soft radial bloom. Cheaper and calmer than a shadowBlur, and unlike
    shadowBlur it rasterises identically across builds. */
export function haze(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, r: number, color: string, strength = 0.5,
): void {
  if (r <= 0 || strength <= 0) return;
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, alpha(color, strength));
  g.addColorStop(0.45, alpha(color, strength * 0.28));
  g.addColorStop(1, alpha(color, 0));
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
}

/** A graduation ring: the astronomical plate's signature mark. Every fifth
    tick runs long, so the eye reads it as an instrument and not a doily. */
export function tickRing(
  ctx: CanvasRenderingContext2D,
  cx: number, cy: number, r: number,
  count: number, len: number,
  opts: { phase?: number; color: string; alpha?: number; width?: number; major?: number } = { color: '#fff' },
): void {
  const phase = opts.phase ?? 0;
  const major = opts.major ?? 5;
  ctx.save();
  ctx.lineWidth = opts.width ?? 1;
  ctx.lineCap = 'butt';
  for (let i = 0; i < count; i++) {
    const a = phase + (i / count) * TAU;
    const big = i % major === 0;
    const l = big ? len : len * 0.55;
    ctx.strokeStyle = alpha(opts.color, (opts.alpha ?? 1) * (big ? 1 : 0.55));
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
    ctx.lineTo(cx + Math.cos(a) * (r + l), cy + Math.sin(a) * (r + l));
    ctx.stroke();
  }
  ctx.restore();
}

/** A node in a lattice or a star in the ground: a filled core, a thin ring,
    and a bloom sized by magnitude. */
export function starDot(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, r: number, color: string,
  opts: { ring?: boolean; glow?: number; alpha?: number } = {},
): void {
  const a = opts.alpha ?? 1;
  if (opts.glow) haze(ctx, x, y, r * (4 + opts.glow * 8), color, 0.3 * opts.glow * a);
  ctx.fillStyle = alpha(color, a);
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
  if (opts.ring !== false) {
    ctx.strokeStyle = alpha(color, a * 0.45);
    ctx.lineWidth = Math.max(0.6, r * 0.35);
    ctx.beginPath();
    ctx.arc(x, y, r * 2.4, 0, TAU);
    ctx.stroke();
  }
}

/** Points along a hanging line, offset perpendicular to the span. sag 0 is
    taut, 1 hangs half a span. `braid` is a separate perpendicular wave with
    its own amplitude and phase, so two threads can twist around each other
    without the sag changing. */
export function catenary(
  a: Pt, b: Pt, sag: number, n = 24, braid = 0, phase = 0,
): Pt[] {
  const out: Pt[] = [];
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const len = Math.hypot(dx, dy) || 1;
  const nx = -dy / len;
  const ny = dx / len;
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const drop = Math.sin(t * Math.PI) * sag * len * 0.5;
    const tw = braid ? Math.sin(t * Math.PI * 2 + phase) * braid * len * Math.sin(t * Math.PI) : 0;
    out.push([a[0] + dx * t + nx * (drop + tw), a[1] + dy * t + ny * (drop + tw)]);
  }
  return out;
}

/** Sample a circle in the plane, useful anywhere a projected disc is not. */
export function ring(cx: number, cy: number, r: number, n = 96, from = 0, to = TAU): Pt[] {
  const out: Pt[] = [];
  for (let i = 0; i <= n; i++) out.push([cx + Math.cos(from + ((to - from) * i) / n) * r, cy + Math.sin(from + ((to - from) * i) / n) * r]);
  return out;
}

export interface EngraveOptions {
  alpha?: number;
  /** 0 is a perfect strike, 1 is a failed copy: arcs missing, strokes
      displaced, the sigil unreadable. The mirror motif drives this. */
  degrade?: number;
  /** stroke displacement in units of r */
  jitter?: number;
  scale?: number;
}

/** The face of the coin. Concentric rules, a ward ring, and a seeded central
    sigil. The mirror reflects this same face and fails at it. */
export function engraveFace(
  ctx: CanvasRenderingContext2D,
  cx: number, cy: number, r: number,
  rnd: Rng, palette: Palette,
  opts: EngraveOptions = {},
): void {
  const a = opts.alpha ?? 1;
  const bad = clamp(opts.degrade ?? 0);
  const jit = (opts.jitter ?? 0) * r;
  if (a <= 0.004 || r <= 1) return;

  const off = (): number => (jit ? (rnd() * 2 - 1) * jit : 0);
  const keep = (p: number): boolean => rnd() > bad * p;

  ctx.save();
  ctx.lineCap = 'round';

  /* two concentric rules */
  for (const [k, w] of [[0.92, 1.4], [0.84, 0.8]] as const) {
    if (!keep(0.7)) continue;
    ctx.strokeStyle = alpha(palette.gold, a * 0.75);
    ctx.lineWidth = w;
    ctx.beginPath();
    ctx.arc(cx + off(), cy + off(), r * k, 0, TAU);
    ctx.stroke();
  }

  /* ward ring: radial teeth, a seeded pattern of long and short */
  const wards = 24;
  ctx.lineWidth = 1.1;
  for (let i = 0; i < wards; i++) {
    if (!keep(0.9)) continue;
    const ang = (i / wards) * TAU;
    const long = i % 3 === 0;
    const r0 = r * 0.62;
    const r1 = r * (long ? 0.8 : 0.73);
    ctx.strokeStyle = alpha(palette.gold, a * (long ? 0.8 : 0.42));
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(ang) * r0 + off(), cy + Math.sin(ang) * r0 + off());
    ctx.lineTo(cx + Math.cos(ang) * r1 + off(), cy + Math.sin(ang) * r1 + off());
    ctx.stroke();
  }

  /* the sigil: three arcs at seeded angles and a struck centre */
  const arcs = 3;
  ctx.lineWidth = Math.max(1.2, r * 0.035);
  for (let i = 0; i < arcs; i++) {
    if (!keep(1)) continue;
    const start = rnd.range(0, TAU);
    const sweep = rnd.range(0.8, 2.2);
    const rr = r * (0.24 + i * 0.13);
    ctx.strokeStyle = alpha(i === 1 ? palette.rose : palette.gold, a * 0.85);
    ctx.beginPath();
    ctx.arc(cx + off(), cy + off(), rr, start, start + sweep * (1 - bad * 0.6));
    ctx.stroke();
  }
  if (keep(0.5)) {
    ctx.fillStyle = alpha(palette.gold, a);
    ctx.beginPath();
    ctx.arc(cx + off(), cy + off(), Math.max(1, r * 0.045), 0, TAU);
    ctx.fill();
  }
  ctx.restore();
}

/** Parallel engraving hatch inside the current clip. Used for mirror glass and
    for the cold floor under the wall. */
export function hatch(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number,
  angle: number, spacing: number, color: string, a = 0.2,
): void {
  if (spacing <= 0.5) return;
  ctx.save();
  ctx.beginPath();
  ctx.rect(x, y, w, h);
  ctx.clip();
  ctx.strokeStyle = alpha(color, a);
  ctx.lineWidth = 1;
  const diag = Math.hypot(w, h);
  const dx = Math.cos(angle);
  const dy = Math.sin(angle);
  const cx = x + w / 2;
  const cy = y + h / 2;
  const n = Math.ceil(diag / spacing);
  for (let i = -n; i <= n; i++) {
    const ox = cx + -dy * i * spacing;
    const oy = cy + dx * i * spacing;
    ctx.beginPath();
    ctx.moveTo(ox - dx * diag, oy - dy * diag);
    ctx.lineTo(ox + dx * diag, oy + dy * diag);
    ctx.stroke();
  }
  ctx.restore();
}

/* ---------- minimal 3D, projected by hand ---------- */

export type Vec3 = readonly [number, number, number];

export const v3 = {
  add: (a: Vec3, b: Vec3): Vec3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]],
  scale: (a: Vec3, k: number): Vec3 => [a[0] * k, a[1] * k, a[2] * k],
  dot: (a: Vec3, b: Vec3): number => a[0] * b[0] + a[1] * b[1] + a[2] * b[2],
  cross: (a: Vec3, b: Vec3): Vec3 => [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ],
  norm: (a: Vec3): Vec3 => {
    const l = Math.hypot(a[0], a[1], a[2]) || 1;
    return [a[0] / l, a[1] / l, a[2] / l];
  },
};

/** Orthographic camera with a pitch, y up in world space, y down on canvas.
    Eleven lines instead of a renderer, and pixel identical everywhere. */
export interface Cam {
  project(p: Vec3): Pt;
  /** larger is nearer the viewer */
  depth(p: Vec3): number;
  readonly view: Vec3;
}

export function camera(cx: number, cy: number, scale: number, pitch: number): Cam {
  const cp = Math.cos(pitch);
  const sp = Math.sin(pitch);
  const right: Vec3 = [1, 0, 0];
  const up: Vec3 = [0, cp, -sp];
  const view: Vec3 = [0, sp, cp];
  return {
    view,
    project: (p) => [cx + v3.dot(p, right) * scale, cy - v3.dot(p, up) * scale],
    depth: (p) => v3.dot(p, view),
  };
}
