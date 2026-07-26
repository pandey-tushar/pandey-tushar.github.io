/* The ground: deep field, star grain, and the engraved plate border.

   This layer never changes with scroll progress, so it is rendered once per
   (seed, size, dpr) into an offscreen canvas and blitted after that. That is
   the whole reason a 2D pipeline can hold sixty frames a second while painting
   a starfield, a border, and four thousand grain specks. The cache is capped
   at four entries because at most three scenes are ever mounted. */

import { alpha, mix, type Surface } from './surface.js';
import { rng, TAU, type Seed } from './rng.js';

export interface PlateOptions {
  /** star count at a 1000 by 700 box, scaled by area */
  stars?: number;
  frame?: boolean;
  grain?: number;
  vignette?: number;
  /** which palette hue washes the field */
  wash?: 'cyan' | 'violet' | 'gold' | 'rose' | 'none';
  washStrength?: number;
}

const DEFAULTS: Required<PlateOptions> = {
  stars: 220,
  frame: true,
  grain: 1,
  vignette: 1,
  wash: 'violet',
  washStrength: 1,
};

interface Entry { canvas: HTMLCanvasElement; key: string }

const cache: Entry[] = [];
const LIMIT = 4;

function evict(): void {
  while (cache.length > LIMIT) {
    const old = cache.shift();
    if (old) { old.canvas.width = 0; old.canvas.height = 0; }
  }
}

/** Drops every cached plate. Call on scene teardown so a long session does not
    keep four full size backing stores alive per orphaned composition. */
export function disposePlates(): void {
  for (const e of cache) { e.canvas.width = 0; e.canvas.height = 0; }
  cache.length = 0;
}

export function drawPlate(s: Surface, seed: Seed, options: PlateOptions = {}): void {
  const o = { ...DEFAULTS, ...options };
  const w = Math.round(s.w);
  const h = Math.round(s.h);
  if (w < 2 || h < 2) return;

  const key = [
    String(seed), w, h, s.dpr, s.palette.void, s.palette.gold,
    o.stars, o.frame, o.grain, o.vignette, o.wash, o.washStrength,
  ].join('|');

  const hit = cache.find((e) => e.key === key);
  if (hit) {
    cache.splice(cache.indexOf(hit), 1);
    cache.push(hit);
    s.ctx.drawImage(hit.canvas, s.x, s.y, s.w, s.h);
    return;
  }

  if (typeof document === 'undefined') {
    paint(s.ctx, s.x, s.y, w, h, s, seed, o);
    return;
  }

  const off = document.createElement('canvas');
  off.width = Math.round(w * s.dpr);
  off.height = Math.round(h * s.dpr);
  const octx = off.getContext('2d', { alpha: false });
  if (!octx) return;
  octx.setTransform(s.dpr, 0, 0, s.dpr, 0, 0);
  paint(octx, 0, 0, w, h, s, seed, o);

  cache.push({ canvas: off, key });
  evict();
  s.ctx.drawImage(off, s.x, s.y, s.w, s.h);
}

function paint(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number,
  s: Surface, seed: Seed, o: Required<PlateOptions>,
): void {
  const p = s.palette;
  const r = rng(String(seed) + '/plate');

  ctx.save();
  ctx.fillStyle = p.void;
  ctx.fillRect(x, y, w, h);

  /* the field is not flat: a low gradient from void2 at the horizon up to void */
  const g = ctx.createLinearGradient(x, y + h, x, y);
  g.addColorStop(0, mix(p.void2, p.void, 0.15));
  g.addColorStop(0.55, p.void);
  g.addColorStop(1, mix(p.void, p.void2, 0.5));
  ctx.fillStyle = g;
  ctx.fillRect(x, y, w, h);

  /* a single wash of hue, placed by seed, so each canto has its own weather */
  if (o.wash !== 'none' && o.washStrength > 0) {
    const hue = p[o.wash];
    const wx = x + w * r.range(0.25, 0.75);
    const wy = y + h * r.range(0.2, 0.6);
    const wr = Math.hypot(w, h) * r.range(0.45, 0.7);
    const wg = ctx.createRadialGradient(wx, wy, 0, wx, wy, wr);
    wg.addColorStop(0, alpha(hue, 0.1 * o.washStrength));
    wg.addColorStop(0.5, alpha(hue, 0.035 * o.washStrength));
    wg.addColorStop(1, alpha(hue, 0));
    ctx.fillStyle = wg;
    ctx.fillRect(x, y, w, h);
  }

  /* stars, scaled to area so a phone does not get a denser sky than a laptop */
  const n = Math.round(o.stars * ((w * h) / (1000 * 700)));
  for (let i = 0; i < n; i++) {
    const sx = x + r() * w;
    const sy = y + r() * h;
    const mag = r();
    const rad = 0.35 + mag * mag * 1.5;
    const hue = mag > 0.94 ? p.cyan : mag > 0.86 ? p.gold : p.ink;
    /* magnitudes quantised to eight steps, same reason as the grain */
    ctx.fillStyle = alpha(hue, 0.12 + (Math.round(mag * 8) / 8) * 0.5);
    ctx.beginPath();
    ctx.arc(sx, sy, rad, 0, TAU);
    ctx.fill();
    if (mag > 0.985) {
      /* a plate's brightest stars carry a cross flare */
      const fl = rad * 7;
      ctx.strokeStyle = alpha(hue, 0.3);
      ctx.lineWidth = 0.6;
      ctx.beginPath();
      ctx.moveTo(sx - fl, sy); ctx.lineTo(sx + fl, sy);
      ctx.moveTo(sx, sy - fl); ctx.lineTo(sx, sy + fl);
      ctx.stroke();
    }
  }

  /* Grain: sparse specks, not a per pixel pass, and banded into a handful of
     opacities. A distinct fillStyle per speck means several thousand colour
     strings built and parsed in one go, which is the whole of the one long
     task the frame budget run found at first mount. Six bands look the same
     and cost six string builds. */
  if (o.grain > 0) {
    const gn = Math.round(2000 * o.grain * ((w * h) / (1000 * 700)));
    const bands = 6;
    const per = Math.round(gn / bands);
    for (let b = 0; b < bands; b++) {
      ctx.fillStyle = alpha(p.ink, 0.006 + (b / bands) * 0.042);
      for (let i = 0; i < per; i++) ctx.fillRect(x + r() * w, y + r() * h, 1, 1);
    }
  }

  if (o.vignette > 0) {
    const vg = ctx.createRadialGradient(
      x + w / 2, y + h / 2, Math.min(w, h) * 0.25,
      x + w / 2, y + h / 2, Math.hypot(w, h) * 0.62,
    );
    vg.addColorStop(0, alpha(p.void, 0));
    vg.addColorStop(1, alpha(p.void, 0.82 * o.vignette));
    ctx.fillStyle = vg;
    ctx.fillRect(x, y, w, h);
  }

  if (o.frame) plateFrame(ctx, x, y, w, h, p.gold);
  ctx.restore();
}

/** Double rule with corner ornaments. The manuscript half of the stance. */
function plateFrame(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, gold: string,
): void {
  const m = Math.max(14, Math.min(w, h) * 0.035);
  ctx.save();
  ctx.strokeStyle = alpha(gold, 0.22);
  ctx.lineWidth = 1;
  ctx.strokeRect(x + m, y + m, w - m * 2, h - m * 2);
  ctx.strokeStyle = alpha(gold, 0.1);
  ctx.strokeRect(x + m + 5, y + m + 5, w - m * 2 - 10, h - m * 2 - 10);

  const t = Math.max(8, m * 0.5);
  const corners: Array<[number, number, number, number]> = [
    [x + m, y + m, 1, 1],
    [x + w - m, y + m, -1, 1],
    [x + m, y + h - m, 1, -1],
    [x + w - m, y + h - m, -1, -1],
  ];
  ctx.strokeStyle = alpha(gold, 0.4);
  ctx.lineWidth = 1.2;
  for (const [cx, cy, sx, sy] of corners) {
    ctx.beginPath();
    ctx.moveTo(cx + sx * t, cy);
    ctx.lineTo(cx, cy);
    ctx.lineTo(cx, cy + sy * t);
    ctx.stroke();
    ctx.fillStyle = alpha(gold, 0.5);
    ctx.beginPath();
    ctx.moveTo(cx + sx * t * 0.62, cy + sy * t * 0.62);
    ctx.lineTo(cx + sx * t * 0.82, cy + sy * t * 0.42);
    ctx.lineTo(cx + sx * t * 1.02, cy + sy * t * 0.62);
    ctx.lineTo(cx + sx * t * 0.82, cy + sy * t * 0.82);
    ctx.closePath();
    ctx.fill();
  }
  ctx.restore();
}
