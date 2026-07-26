/* The drawing surface every motif receives.

   Canvas 2D, deliberately, for all nine motifs. The reasons are worth writing
   down because the choice is load bearing:

   1. Determinism. The seed gate compares pixel hashes of the same frame
      rendered twice. GPU rasterisation and shader float precision differ by
      driver, so a WebGL motif would make that gate report drift that is not a
      loose random. Canvas 2D paths rasterise the same way for a given browser
      build and size.
   2. Context budget. Browsers cap live WebGL contexts near sixteen and drop
      the oldest without asking. Twenty two cantos with a live context each is
      not a thing that can exist. 2D contexts have no such cap, and a disposed
      2D canvas frees its backing store the moment width is set to zero.
   3. The art direction is engraved line, not lit volume. Nothing in the motif
      table asks for a light model. The sphere is a wireframe plate, projected
      by hand in eleven lines of maths, not a mesh.

   The one thing 2D costs is fill rate on large plates. That is paid for by
   caching every progress invariant layer (see plate.ts) and by redrawing only
   when scroll progress actually moved. */

import { palette as tokenPalette, type Palette } from '@qubit/tokens';

export type { Palette };

/** A box in normalised 0..1 coordinates of the parent surface. */
export interface Region { x: number; y: number; w: number; h: number }

export interface Surface {
  readonly ctx: CanvasRenderingContext2D;
  /** drawing box in CSS pixels */
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
  readonly palette: Palette;
  /** the ratio the backing store was sized at. Part of the determinism key:
      the same seed at a different dpr is a different picture, correctly. */
  readonly dpr: number;
}

export interface Metrics {
  cx: number;
  cy: number;
  /** the short side of the box. Motifs size themselves in these units so a
      composition reads the same at any viewport. */
  unit: number;
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export const metrics = (s: Surface): Metrics => ({
  cx: s.x + s.w / 2,
  cy: s.y + s.h / 2,
  unit: Math.min(s.w, s.h),
  left: s.x,
  top: s.y,
  right: s.x + s.w,
  bottom: s.y + s.h,
});

/** A sub box of a surface, given in normalised coordinates. */
export function sub(s: Surface, r: Region): Surface {
  return {
    ctx: s.ctx,
    x: s.x + r.x * s.w,
    y: s.y + r.y * s.h,
    w: r.w * s.w,
    h: r.h * s.h,
    palette: s.palette,
    dpr: s.dpr,
  };
}

export interface MountOptions {
  width: number;
  height: number;
  dpr?: number;
  /** defaults to the dark palette. The illustrated edition is a night plate in
      every theme, the same rule the reader scenes already follow. */
  palette?: Palette;
}

/** Sizes a canvas and returns a surface drawing in CSS pixels. */
export function mountSurface(canvas: HTMLCanvasElement, opts: MountOptions): Surface {
  const dpr = opts.dpr ?? Math.min(globalThis.devicePixelRatio || 1, 2);
  const w = Math.max(1, Math.round(opts.width));
  const h = Math.max(1, Math.round(opts.height));
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  canvas.style.width = w + 'px';
  canvas.style.height = h + 'px';
  const ctx = canvas.getContext('2d', { alpha: false });
  if (!ctx) throw new Error('motifs: 2d context unavailable');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, x: 0, y: 0, w, h, palette: opts.palette ?? tokenPalette.dark, dpr };
}

/** Frees the backing store. A canvas left in the heap at 1440x900 costs about
    five megabytes; twenty two of those is the leak this design dies of. */
export function releaseCanvas(canvas: HTMLCanvasElement): void {
  const ctx = canvas.getContext('2d');
  if (ctx) ctx.setTransform(1, 0, 0, 1, 0, 0);
  canvas.width = 0;
  canvas.height = 0;
  canvas.removeAttribute('style');
}

export function clear(s: Surface): void {
  s.ctx.save();
  s.ctx.fillStyle = s.palette.void;
  s.ctx.fillRect(s.x, s.y, s.w, s.h);
  s.ctx.restore();
}

/* ---------- colour ---------- */

const rgbCache = new Map<string, [number, number, number, number]>();

function parse(color: string): [number, number, number, number] {
  const hit = rgbCache.get(color);
  if (hit) return hit;
  let out: [number, number, number, number] = [255, 255, 255, 1];
  if (color.charCodeAt(0) === 35) {
    const hex = color.slice(1);
    const full = hex.length === 3 ? hex[0]! + hex[0]! + hex[1]! + hex[1]! + hex[2]! + hex[2]! : hex;
    out = [
      parseInt(full.slice(0, 2), 16),
      parseInt(full.slice(2, 4), 16),
      parseInt(full.slice(4, 6), 16),
      full.length >= 8 ? parseInt(full.slice(6, 8), 16) / 255 : 1,
    ];
  } else {
    const nums = color.match(/[\d.]+/g);
    if (nums && nums.length >= 3) {
      out = [Number(nums[0]), Number(nums[1]), Number(nums[2]), nums[3] === undefined ? 1 : Number(nums[3])];
    }
  }
  rgbCache.set(color, out);
  return out;
}

/** Multiplies a token colour by an alpha. Motifs never write a literal hue. */
export function alpha(color: string, a: number): string {
  const [r, g, b, base] = parse(color);
  const out = Math.max(0, Math.min(1, a * base));
  return 'rgba(' + r + ',' + g + ',' + b + ',' + out.toFixed(4) + ')';
}

/** Blends two token colours. Used for gradients between palette entries. */
export function mix(a: string, b: string, t: number, at = 1): string {
  const A = parse(a);
  const B = parse(b);
  const k = Math.max(0, Math.min(1, t));
  return (
    'rgba(' +
    Math.round(A[0] + (B[0] - A[0]) * k) + ',' +
    Math.round(A[1] + (B[1] - A[1]) * k) + ',' +
    Math.round(A[2] + (B[2] - A[2]) * k) + ',' +
    Math.max(0, Math.min(1, (A[3] + (B[3] - A[3]) * k) * at)).toFixed(4) +
    ')'
  );
}
