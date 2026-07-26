/* Dial. The instrument that listens.

   Canto 18: "Before the machine learned to think, it learned to listen; the
   quietest gift is the first to arrive." The book is full of measurement and
   the vocabulary had no instrument in it. The sphere is a state, the lock is a
   mechanism, the coin is a question. None of them is a thing that reads.

   The dial is a graduated face with a needle and, at the needle's tip, the
   uncertainty the reading carries. Squeeze is the canto's argument made
   geometry: "Squeezing does not break the uncertainty principle; it obeys it
   to the letter. What it does is pour the unavoidable haze into a direction
   where no one is looking." So the blob is an ellipse whose two half axes are
   divided and multiplied by the same factor. Its area never changes at any
   squeeze. The picture cannot cheat the law it illustrates.

   Tremble is the other half: "It needs only to tremble honestly." The shake is
   drawn as seeded ghost needles, exactly the way the coin draws the two faces
   it is holding to the light, and like the coin it is a parameter and not a
   clock, so a stopped scroll leaves a composed instrument. */

import { alpha, metrics, mix, type Surface } from '../surface.js';
import { haze, poly, tickRing } from '../forms.js';
import { clamp, ease, lerp, rng, span, TAU, type Seed } from '../rng.js';
import { defineMotif } from '../types.js';

export type DialParams = {
  radius: number;
  ticks: number;
  /** every major-th graduation runs long */
  major: number;
  rings: number;
  /** bearing in turns. 0 points up. */
  needle: number;
  /** 0..1 the honest tremble, drawn as ghost needles */
  tremble: number;
  /** 0..1 haze poured out of the measured direction into the one nobody reads */
  squeeze: number;
  /** the uncertainty before any squeezing, in radii */
  noise: number;
  /** 0..1 arc of the readings already taken */
  trace: number;
  /** 0..1 how brightly the instrument is reading */
  reading: number;
  glow: number;
  face: number;
}

export const dial = defineMotif<DialParams>({
  id: 'dial',
  signature: 0.62,
  defaults: {
    radius: 0.38,
    ticks: 60,
    major: 5,
    rings: 2,
    needle: 0.08,
    tremble: 0.5,
    squeeze: 0,
    noise: 0.16,
    trace: 0,
    reading: 1,
    glow: 1,
    face: 1,
  },
  curve: (p) => ({
    needle: lerp(-0.055, 0.075, ease(p)),
    tremble: 1 - 0.78 * ease(span(p, 0.12, 0.72)),
    squeeze: ease(span(p, 0.3, 0.92)),
    trace: ease(span(p, 0.14, 0.82)),
    reading: ease(span(p, 0.04, 0.55)),
  }),

  draw(s: Surface, seed: Seed, p: DialParams) {
    const { cx, cy, unit } = metrics(s);
    const ctx = s.ctx;
    const pal = s.palette;
    const r = rng(String(seed) + '/dial');
    const R = unit * p.radius;
    const read = clamp(p.reading);
    const sq = clamp(p.squeeze);
    const trem = clamp(p.tremble);
    const ang = p.needle * TAU - Math.PI / 2;

    ctx.save();
    ctx.lineJoin = 'round';

    /* the face: a plate, not a panel. Dark at the rim so the graduations sit
       on something rather than floating on the starfield. */
    if (p.face > 0) {
      const g = ctx.createRadialGradient(cx - R * 0.28, cy - R * 0.34, 0, cx, cy, R * 1.06);
      g.addColorStop(0, alpha(mix(pal.void2, pal.violet, 0.12), 0.92 * p.face));
      g.addColorStop(0.66, alpha(pal.void2, 0.72 * p.face));
      g.addColorStop(1, alpha(pal.void, 0.86 * p.face));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, TAU);
      ctx.fill();
    }

    /* graduations, coarser as they go inward, so the eye reads an instrument */
    const rings = Math.max(1, Math.round(p.rings));
    const ticks = Math.max(8, Math.round(p.ticks));
    for (let k = 0; k < rings; k++) {
      const rr = R * (1 - k * 0.17);
      const n = Math.max(8, Math.round(ticks / (k + 1)));
      tickRing(ctx, cx, cy, rr - R * 0.075, n, R * 0.075, {
        color: pal.gold, alpha: 0.42 - k * 0.14, major: Math.max(2, Math.round(p.major)),
      });
      ctx.strokeStyle = alpha(pal.gold, k === 0 ? 0.42 : 0.15);
      ctx.lineWidth = k === 0 ? 1.2 : 1;
      ctx.beginPath();
      ctx.arc(cx, cy, rr - R * 0.075, 0, TAU);
      ctx.stroke();
    }

    /* the readings already taken, trailing the needle around the face */
    const tr = clamp(p.trace);
    if (tr > 0.01) {
      const sweep = tr * TAU * 0.62;
      const steps = Math.max(16, Math.round(sweep * 22));
      const rad = R * 0.66;
      for (let i = 0; i < steps; i++) {
        const a0 = ang - sweep + (sweep * i) / steps;
        const a1 = ang - sweep + (sweep * (i + 1)) / steps;
        const fade = (i / steps) * (i / steps);
        ctx.beginPath();
        ctx.arc(cx, cy, rad, a0, a1);
        ctx.strokeStyle = alpha(pal.violet, 0.7 * fade * tr);
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    /* the uncertainty at the tip. rx and ry are divided and multiplied by the
       same factor, so the area is the same at every squeeze. */
    const tipR = R * 0.66;
    const tx = cx + Math.cos(ang) * tipR;
    const ty = cy + Math.sin(ang) * tipR;
    if (p.noise > 0.001) {
      /* the long axis is held inside the face. A blob that grows off the plate
         stops reading as the instrument's uncertainty and starts reading as a
         comet, which is a different picture and a wrong one. */
      const k = 1 + sq * 2.4;
      const rx = R * p.noise / k;
      const ry = R * p.noise * k;
      ctx.save();
      ctx.translate(tx, ty);
      ctx.rotate(ang);
      const g = ctx.createRadialGradient(0, 0, 0, 0, 0, Math.max(rx, ry));
      g.addColorStop(0, alpha(pal.cyan, 0.3));
      g.addColorStop(1, alpha(pal.cyan, 0));
      ctx.save();
      ctx.scale(rx / Math.max(rx, ry), ry / Math.max(rx, ry));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(0, 0, Math.max(rx, ry), 0, TAU);
      ctx.fill();
      ctx.restore();
      ctx.beginPath();
      ctx.ellipse(0, 0, rx, ry, 0, 0, TAU);
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = alpha(pal.cyan, 0.5 + 0.3 * sq);
      ctx.lineWidth = 1.1;
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();
    }

    /* the tremble: what the instrument is actually doing while it listens */
    if (trem > 0.02) {
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      for (let g = 5; g >= 1; g--) {
        const off = r.gauss() * trem * 0.055 * TAU;
        const a = ang + off;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(a) * R * 0.86, cy + Math.sin(a) * R * 0.86);
        ctx.strokeStyle = alpha(g % 2 === 0 ? pal.cyan : pal.violet, 0.2 * trem * (1 - (g - 1) / 6));
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }
      ctx.restore();
    }

    /* the needle, and its counterweight, so it reads as balanced on a pivot */
    const nx = cx + Math.cos(ang) * R * 0.86;
    const ny = cy + Math.sin(ang) * R * 0.86;
    const bx = cx - Math.cos(ang) * R * 0.26;
    const by = cy - Math.sin(ang) * R * 0.26;
    ctx.beginPath();
    ctx.moveTo(bx, by);
    ctx.lineTo(nx, ny);
    ctx.strokeStyle = alpha(pal.gold, 0.55 + 0.4 * read);
    ctx.lineWidth = Math.max(1.6, R * 0.018);
    ctx.stroke();

    const hx = Math.cos(ang);
    const hy = Math.sin(ang);
    const head = Math.max(7, R * 0.11);
    poly(ctx, [
      [nx + hx * head * 0.6, ny + hy * head * 0.6],
      [nx - hx * head * 0.4 - hy * head * 0.3, ny - hy * head * 0.4 + hx * head * 0.3],
      [nx - hx * head * 0.4 + hy * head * 0.3, ny - hy * head * 0.4 - hx * head * 0.3],
    ], true);
    ctx.fillStyle = alpha(pal.gold, 0.6 + 0.35 * read);
    ctx.fill();

    ctx.fillStyle = alpha(pal.void, 0.9);
    ctx.beginPath();
    ctx.arc(bx, by, Math.max(2, R * 0.038), 0, TAU);
    ctx.fill();
    ctx.strokeStyle = alpha(pal.gold, 0.5);
    ctx.lineWidth = 1;
    ctx.stroke();

    /* the pivot */
    ctx.fillStyle = alpha(pal.void, 0.95);
    ctx.beginPath();
    ctx.arc(cx, cy, R * 0.07, 0, TAU);
    ctx.fill();
    ctx.strokeStyle = alpha(pal.gold, 0.8);
    ctx.lineWidth = 1.3;
    ctx.stroke();
    ctx.fillStyle = alpha(pal.gold, 0.85);
    ctx.beginPath();
    ctx.arc(cx, cy, R * 0.022, 0, TAU);
    ctx.fill();

    if (p.glow > 0) haze(ctx, tx, ty, R * 0.34 * p.glow, pal.gold, 0.3 * read * p.glow);

    ctx.restore();
  },
});
