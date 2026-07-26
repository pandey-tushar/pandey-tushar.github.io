/* Mirror. Copying, and the law that forbids it.

   Canto 17: "An unknown quantum state cannot be copied. Copying it is not
   merely hard, and no decree forbids it. The mathematics of the world holds no
   operation that does the deed."

   The subject is the coin, engraved by the same function the coin motif uses,
   so the thing failing to be copied is visibly the same object. Fidelity is
   the only honest parameter here: as it falls the reflection loses arcs,
   displaces strokes, grains over and finally comes apart into wedges, while
   the original stays perfectly sharp. Nothing is done to the original. That
   asymmetry is the canto. */

import { alpha, metrics, mix, type Surface } from '../surface.js';
import { engraveFace, hatch, haze, type Pt } from '../forms.js';
import { clamp, ease, rng, span, TAU, type Rng, type Seed } from '../rng.js';
import { defineMotif } from '../types.js';

export type MirrorParams = {
  /** 1 is a perfect copy, 0 is a failed one */
  fidelity: number;
  distortion: number;
  /** where the glass stands, as a fraction of the box width */
  split: number;
  grain: number;
  /** 0..1 the reflection comes apart into wedges */
  shatter: number;
  /** 0..1 the rose mark the attempt leaves on the glass */
  bruise: number;
  radius: number;
  glass: number;
  rays: number;
}

function disc(
  ctx: CanvasRenderingContext2D, s: Surface,
  cx: number, cy: number, rad: number, r: Rng,
  opts: { alpha: number; degrade: number; jitter: number; dim: number },
): void {
  const pal = s.palette;
  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, rad, 0, TAU);
  const g = ctx.createRadialGradient(cx - rad * 0.3, cy - rad * 0.35, 0, cx, cy, rad * 1.3);
  g.addColorStop(0, mix(pal.gold, pal.void2, 0.3 + opts.dim * 0.5));
  g.addColorStop(0.65, mix(pal.gold, pal.void, 0.55 + opts.dim * 0.35));
  g.addColorStop(1, mix(pal.void2, pal.void, 0.5));
  ctx.globalAlpha *= opts.alpha;
  ctx.fillStyle = g;
  ctx.fill();

  ctx.save();
  ctx.clip();
  engraveFace(ctx, cx, cy, rad, r, pal, {
    alpha: opts.alpha,
    degrade: opts.degrade,
    jitter: opts.jitter,
  });
  ctx.restore();

  /* rim: solid on the original, broken into dashes as the copy fails */
  ctx.beginPath();
  ctx.arc(cx, cy, rad, 0, TAU);
  ctx.strokeStyle = alpha(pal.gold, 0.95 * opts.alpha * (1 - opts.dim * 0.55));
  ctx.lineWidth = Math.max(1.2, rad * 0.03);
  if (opts.degrade > 0.05) ctx.setLineDash([Math.max(2, rad * (0.5 - opts.degrade * 0.44)), rad * opts.degrade * 0.5]);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.restore();
}

export const mirror = defineMotif<MirrorParams>({
  id: 'mirror',
  signature: 0.62,
  defaults: {
    fidelity: 1,
    distortion: 0,
    split: 0.5,
    grain: 0,
    shatter: 0,
    bruise: 0,
    radius: 0.2,
    glass: 1,
    rays: 1,
  },
  curve: (p) => ({
    fidelity: 1 - ease(span(p, 0.2, 0.86)) * 0.97,
    distortion: ease(span(p, 0.28, 0.92)) * 0.055,
    shatter: ease(span(p, 0.54, 1)),
    bruise: ease(span(p, 0.32, 0.95)),
    grain: ease(span(p, 0.26, 1)),
  }),

  draw(s: Surface, seed: Seed, p: MirrorParams) {
    const { cy, unit } = metrics(s);
    const ctx = s.ctx;
    const pal = s.palette;
    const r = rng(String(seed) + '/mirror');
    const mx = s.x + s.w * p.split;
    const rad = unit * p.radius;
    const fid = clamp(p.fidelity);
    const shat = clamp(p.shatter);
    const offset = s.w * 0.21;
    const ox = mx - offset;
    const rx = mx + offset;

    ctx.save();

    /* the glass */
    if (p.glass > 0) {
      const bandW = Math.max(8, unit * 0.045);
      const g = ctx.createLinearGradient(mx - bandW, 0, mx + bandW, 0);
      g.addColorStop(0, alpha(pal.cyan, 0));
      g.addColorStop(0.5, alpha(pal.cyan, 0.14 * p.glass));
      g.addColorStop(1, alpha(pal.cyan, 0));
      ctx.fillStyle = g;
      ctx.fillRect(mx - bandW, s.y, bandW * 2, s.h);
      hatch(ctx, mx - bandW, s.y + s.h * 0.06, bandW * 2, s.h * 0.88, Math.PI / 2.6, 7, pal.cyan, 0.12 * p.glass);
      ctx.strokeStyle = alpha(pal.cyan, 0.55 * p.glass);
      ctx.lineWidth = 1.3;
      ctx.beginPath();
      ctx.moveTo(mx, s.y + s.h * 0.05);
      ctx.lineTo(mx, s.y + s.h * 0.95);
      ctx.stroke();
      for (let i = 0; i <= 18; i++) {
        const y = s.y + s.h * 0.05 + (s.h * 0.9 * i) / 18;
        ctx.strokeStyle = alpha(pal.cyan, (i % 3 === 0 ? 0.4 : 0.18) * p.glass);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(mx - (i % 3 === 0 ? 7 : 4), y);
        ctx.lineTo(mx, y);
        ctx.stroke();
      }
    }

    /* the attempt: a ray in, a ray out that is never as bright */
    if (p.rays > 0) {
      ctx.setLineDash([5, 6]);
      ctx.lineWidth = 1;
      ctx.strokeStyle = alpha(pal.gold, 0.4 * p.rays);
      ctx.beginPath();
      ctx.moveTo(ox + rad, cy - rad * 0.2);
      ctx.lineTo(mx, cy);
      ctx.stroke();
      ctx.strokeStyle = alpha(pal.gold, 0.4 * p.rays * fid);
      ctx.beginPath();
      ctx.moveTo(mx, cy);
      ctx.lineTo(rx - rad, cy + rad * 0.2);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    /* the original, untouched by any of this */
    disc(ctx, s, ox, cy, rad, r.fork('face'), { alpha: 1, degrade: 0, jitter: 0, dim: 0 });
    haze(ctx, ox, cy, rad * 2.2, pal.gold, 0.18);

    /* the copy */
    const degrade = 1 - fid;
    const wedges = shat > 0.02 ? 5 : 1;
    for (let k = 0; k < wedges; k++) {
      const wr = r.fork('wedge' + k);
      const a0 = (k / wedges) * TAU - Math.PI / 2;
      const a1 = ((k + 1) / wedges) * TAU - Math.PI / 2;
      const push = shat * rad * wr.range(0.15, 0.75);
      const am = (a0 + a1) / 2;
      ctx.save();
      if (wedges > 1) {
        ctx.beginPath();
        ctx.moveTo(rx, cy);
        ctx.arc(rx, cy, rad * 2, a0, a1);
        ctx.closePath();
        ctx.clip();
        ctx.translate(Math.cos(am) * push, Math.sin(am) * push);
        ctx.globalAlpha *= 1 - shat * wr.range(0.1, 0.6);
      }
      ctx.save();
      ctx.translate(rx, cy);
      ctx.scale(-1, 1);
      ctx.translate(-rx, -cy);
      disc(ctx, s, rx, cy, rad, r.fork('face'), {
        alpha: 0.28 + fid * 0.72,
        degrade,
        jitter: p.distortion,
        dim: degrade,
      });
      ctx.restore();
      ctx.restore();
    }

    /* grain: what is left where the copy should have been */
    if (p.grain > 0) {
      const gn = Math.round(620 * p.grain * clamp(rad / 190, 0.5, 1.6));
      const gr = r.fork('grain');
      for (let i = 0; i < gn; i++) {
        const a = gr() * TAU;
        const d = Math.sqrt(gr()) * rad * (1.15 + shat * 0.6);
        ctx.fillStyle = alpha(gr() < 0.25 ? pal.rose : pal.gold, gr() * 0.55 * p.grain);
        ctx.fillRect(rx + Math.cos(a) * d, cy + Math.sin(a) * d, 1.3, 1.3);
      }
    }

    /* the bruise the attempt leaves on the glass */
    if (p.bruise > 0.01) {
      const b = clamp(p.bruise);
      const g = ctx.createRadialGradient(mx, cy, 0, mx, cy, rad * 1.5);
      g.addColorStop(0, alpha(pal.rose, 0.4 * b));
      g.addColorStop(0.6, alpha(pal.rose, 0.1 * b));
      g.addColorStop(1, alpha(pal.rose, 0));
      ctx.fillStyle = g;
      ctx.fillRect(mx - rad * 1.5, cy - rad * 1.5, rad * 3, rad * 3);
      const br = r.fork('bruise');
      ctx.strokeStyle = alpha(pal.rose, 0.55 * b);
      ctx.lineWidth = 1;
      for (let i = 0; i < 5; i++) {
        const a = br.range(0, TAU);
        const l = rad * br.range(0.3, 1.1) * b;
        const from: Pt = [mx, cy + br.gauss() * rad * 0.3];
        ctx.beginPath();
        ctx.moveTo(from[0], from[1]);
        ctx.lineTo(from[0] + Math.cos(a) * l * 0.2, from[1] + Math.sin(a) * l);
        ctx.stroke();
      }
    }

    ctx.restore();
  },
});
