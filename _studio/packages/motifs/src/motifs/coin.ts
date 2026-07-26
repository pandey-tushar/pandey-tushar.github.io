/* Coin. Canto 1, spinning on its edge.

   "A coin spinning on its edge has not failed to choose. It holds both its
   faces to the light and waits for the table to ask. While it spins it is
   honest. Your question is what will make it lie still."

   So the parameters are the sentence: spin is the honesty, tilt is the
   question arriving, settle is the answer being kept. The ghost arcs are the
   two faces held to the light at once; they vanish exactly when settle
   reaches one, because a coin at rest is showing only one thing.

   Geometry is a disc in three dimensions projected orthographically. No
   special casing of the ellipse: the rim is sampled as a circle in the disc's
   own plane and every point is projected, so the edge on case and the flat
   case are the same three lines of code. */

import { alpha, metrics, mix, type Surface } from '../surface.js';
import { camera, engraveFace, haze, poly, v3, type Pt, type Vec3 } from '../forms.js';
import { clamp, ease, rng, span, TAU, type Seed } from '../rng.js';
import { defineMotif } from '../types.js';

export type CoinParams = {
  /** turns completed. Fractional part is the phase, so 3.25 and 0.25 look alike. */
  spin: number;
  /** 0 stands on the edge, 1 lies flat on the table */
  tilt: number;
  /** -1 or 1, which face the table is given */
  faceBias: number;
  /** 0 is a wild spin trailing its own rim, 1 is still */
  settle: number;
  /** coin radius as a fraction of the box half height */
  radius: number;
  /** slab thickness as a fraction of the radius */
  thickness: number;
  ghosts: number;
  shadow: number;
  bloom: number;
  /** camera pitch in degrees; higher looks further down at the table */
  pitch: number;
  /** how far the coin floats above the table, in radii */
  lift: number;
  table: number;
}

const RIM = 88;

function discPoints(
  c: Vec3, n: Vec3, r: number, count: number,
): Vec3[] {
  const up: Vec3 = Math.abs(n[1]) > 0.985 ? [0, 0, 1] : [0, 1, 0];
  const u = v3.norm(v3.cross(up, n));
  const w = v3.cross(n, u);
  const out: Vec3[] = [];
  for (let i = 0; i <= count; i++) {
    const a = (i / count) * TAU;
    const ca = Math.cos(a) * r;
    const sa = Math.sin(a) * r;
    out.push([
      c[0] + u[0] * ca + w[0] * sa,
      c[1] + u[1] * ca + w[1] * sa,
      c[2] + u[2] * ca + w[2] * sa,
    ]);
  }
  return out;
}

function normalOf(p: CoinParams): Vec3 {
  const lean = clamp(p.tilt) * (Math.PI / 2);
  const az = p.spin * TAU;
  const s = p.faceBias >= 0 ? 1 : -1;
  return [Math.cos(lean) * Math.cos(az), Math.sin(lean) * s, Math.cos(lean) * Math.sin(az)];
}

export const coin = defineMotif<CoinParams>({
  id: 'coin',
  signature: 0.58,
  defaults: {
    spin: 0,
    tilt: 0,
    faceBias: 1,
    settle: 0,
    radius: 0.34,
    thickness: 0.09,
    ghosts: 7,
    shadow: 1,
    bloom: 1,
    pitch: 21,
    lift: 0,
    table: 1,
  },
  curve: (p) => ({
    /* fast at the top of the canto, asymptotically slowing. Nine turns spent
       over the whole canto, never a loop. */
    spin: 9 * (1 - Math.pow(1 - p, 3)),
    tilt: Math.pow(span(p, 0.5, 0.96), 1.5),
    settle: ease(span(p, 0.42, 1)),
    lift: (1 - ease(span(p, 0, 0.35))) * 0.12,
  }),

  draw(s: Surface, seed: Seed, p: CoinParams) {
    const { cx, cy, unit } = metrics(s);
    const pal = s.palette;
    const ctx = s.ctx;
    const r = rng(String(seed) + '/coin');

    const R = 1;
    const t = R * p.thickness;
    const lean = clamp(p.tilt) * (Math.PI / 2);
    const scale = (unit * p.radius) / R;
    const cam = camera(cx, cy + unit * 0.1, scale, (p.pitch * Math.PI) / 180);

    /* centre height: on edge the centre sits a radius up, flat it sits half a
       thickness up. Exactly the physical relation, so the coin never floats. */
    const yc = R * Math.cos(lean) + (t / 2) * Math.sin(lean) + p.lift * R;
    const jx = (r() * 2 - 1) * 0.06;
    const jz = (r() * 2 - 1) * 0.06;
    const c: Vec3 = [jx, yc, jz];

    ctx.save();
    ctx.lineJoin = 'round';

    if (p.table > 0) drawTable(s, cam, p.table);

    /* shadow: the rim dropped straight onto the plane, spread about its own
       centroid rather than the plate's, so it stays under the coin */
    if (p.shadow > 0) {
      const n0 = normalOf(p);
      const rim = discPoints(c, n0, R, 48);
      const flat: Pt[] = rim.map((q) => cam.project([q[0], 0, q[2]]));
      const anchor = cam.project([c[0], 0, c[2]]);
      const soft = 1 - clamp(p.settle) * 0.6;
      for (let k = 3; k >= 0; k--) {
        const g = 1 + k * 0.1 * soft;
        ctx.save();
        ctx.translate(anchor[0], anchor[1]);
        ctx.scale(g, g);
        ctx.translate(-anchor[0], -anchor[1]);
        poly(ctx, flat, true);
        ctx.fillStyle = alpha(pal.void, (k === 0 ? 0.6 : 0.22) * p.shadow);
        ctx.fill();
        ctx.restore();
      }
    }

    /* the coin itself */
    const n = normalOf(p);
    const facing = v3.dot(n, cam.view);
    const front = v3.add(c, v3.scale(n, facing >= 0 ? t / 2 : -t / 2));
    const back = v3.add(c, v3.scale(n, facing >= 0 ? -t / 2 : t / 2));
    const frontRim = discPoints(front, n, R, RIM);
    const backRim = discPoints(back, n, R, RIM);
    const fp = frontRim.map(cam.project);
    const bp = backRim.map(cam.project);

    /* edge slab. Front loop plus reversed back loop leaves the overlap hollow
       under the nonzero rule, which is precisely the visible band. */
    ctx.beginPath();
    ctx.moveTo(fp[0]![0], fp[0]![1]);
    for (let i = 1; i < fp.length; i++) ctx.lineTo(fp[i]![0], fp[i]![1]);
    ctx.moveTo(bp[bp.length - 1]![0], bp[bp.length - 1]![1]);
    for (let i = bp.length - 2; i >= 0; i--) ctx.lineTo(bp[i]![0], bp[i]![1]);
    ctx.closePath();
    const rimBox = bounds(fp.concat(bp));
    const eg = ctx.createLinearGradient(rimBox[0], 0, rimBox[2], 0);
    eg.addColorStop(0, mix(pal.gold, pal.void, 0.62));
    eg.addColorStop(0.42, pal.gold);
    eg.addColorStop(1, mix(pal.gold, pal.void, 0.7));
    ctx.fillStyle = eg;
    ctx.fill();

    /* the visible face. The gradient is centred on the coin's own projection,
       not the plate's, or the highlight slides off whenever a composition
       places the coin away from the middle. */
    const vis = Math.abs(facing);
    const centre = cam.project(front);
    poly(ctx, fp, true);
    const fg = ctx.createRadialGradient(
      centre[0] - unit * p.radius * 0.3, centre[1] - unit * p.radius * 0.35, 0,
      centre[0], centre[1], unit * p.radius * 1.35,
    );
    fg.addColorStop(0, mix(pal.gold, pal.void2, 0.35));
    fg.addColorStop(0.6, mix(pal.gold, pal.void, 0.55));
    fg.addColorStop(1, mix(pal.void2, pal.void, 0.5));
    ctx.fillStyle = fg;
    ctx.fill();

    if (vis > 0.03) {
      ctx.save();
      poly(ctx, fp, true);
      ctx.clip();
      const box = bounds(fp);
      engraveFace(
        ctx, (box[0] + box[2]) / 2, (box[1] + box[3]) / 2,
        Math.min(box[2] - box[0], box[3] - box[1]) / 2,
        r.fork('face'), pal, { alpha: vis },
      );
      ctx.restore();
    }

    /* rim highlight: the one bright line that makes it read as struck metal */
    poly(ctx, fp, true);
    ctx.strokeStyle = alpha(pal.gold, 0.95);
    ctx.lineWidth = Math.max(1.2, unit * 0.0035);
    ctx.stroke();
    poly(ctx, bp, true);
    ctx.strokeStyle = alpha(pal.gold, 0.35);
    ctx.lineWidth = 1;
    ctx.stroke();

    /* ghost rims: both faces held to the light at once. Drawn over the coin
       and added rather than painted, because this is the light the spin is
       throwing, not an object behind it. It disappears exactly when settle
       reaches one, which is the sentence the canto turns on. */
    const wild = 1 - clamp(p.settle);
    if (p.ghosts > 0 && wild > 0.02) {
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      const step = 0.05 * wild;
      const ghosts = Math.round(p.ghosts);
      for (let g = ghosts; g >= 1; g--) {
        const gspin = p.spin - g * step * (1 + r() * 0.3);
        const gn = normalOf({ ...p, spin: gspin });
        const rim = discPoints(c, gn, R * (1 + g * 0.004), 44).map(cam.project);
        const a = wild * 0.3 * (1 - (g - 1) / (ghosts + 1.2));
        poly(ctx, rim, true);
        ctx.strokeStyle = alpha(g % 2 === 0 ? pal.cyan : pal.violet, a * 0.42);
        ctx.lineWidth = 1.4;
        ctx.stroke();
      }
      ctx.restore();
    }

    if (p.bloom > 0) {
      const contact = lowest(frontRim.concat(backRim));
      const cp = cam.project([contact[0], 0, contact[2]]);
      haze(ctx, cp[0], cp[1], unit * 0.16 * p.bloom, pal.gold, 0.35 * p.bloom * (0.4 + clamp(p.settle) * 0.6));
    }

    /* the question the table asks: a rule that sharpens as the coin lies down */
    const settled = clamp(p.settle);
    if (settled > 0.02) {
      const a0 = cam.project([-2.6, 0, jz]);
      const a1 = cam.project([2.6, 0, jz]);
      const grad = ctx.createLinearGradient(a0[0], a0[1], a1[0], a1[1]);
      grad.addColorStop(0, alpha(pal.rose, 0));
      grad.addColorStop(0.5, alpha(pal.rose, 0.5 * settled));
      grad.addColorStop(1, alpha(pal.rose, 0));
      ctx.beginPath();
      ctx.moveTo(a0[0], a0[1]);
      ctx.lineTo(a1[0], a1[1]);
      ctx.strokeStyle = grad;
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    ctx.restore();
  },
});

function bounds(pts: readonly Pt[]): [number, number, number, number] {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const q of pts) {
    if (q[0] < x0) x0 = q[0];
    if (q[1] < y0) y0 = q[1];
    if (q[0] > x1) x1 = q[0];
    if (q[1] > y1) y1 = q[1];
  }
  return [x0, y0, x1, y1];
}

function lowest(pts: readonly Vec3[]): Vec3 {
  let best = pts[0]!;
  for (const q of pts) if (q[1] < best[1]) best = q;
  return best;
}

/* A pool of light on the plane rather than a lit rectangle. A rectangle gives
   the plate a hard horizontal band that fights every other line in the
   composition; a pool says table and then gets out of the way. */
function drawTable(s: Surface, cam: ReturnType<typeof camera>, strength: number): void {
  const ctx = s.ctx;
  const pal = s.palette;
  const near = cam.project([0, 0, 0]);
  const edgeX = cam.project([2.2, 0, 0]);
  const edgeZ = cam.project([0, 0, 2.2]);
  const rx = Math.abs(edgeX[0] - near[0]);
  const ry = Math.abs(edgeZ[1] - near[1]) || rx * 0.3;

  ctx.save();
  ctx.translate(near[0], near[1]);
  ctx.scale(1, Math.max(0.12, ry / rx));
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, rx);
  g.addColorStop(0, alpha(pal.void2, 1 * strength));
  g.addColorStop(0.55, alpha(pal.void2, 0.4 * strength));
  g.addColorStop(1, alpha(pal.void2, 0));
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(0, 0, rx, 0, TAU);
  ctx.fill();

  /* the near rim of the pool, an arc rather than a ruled horizon. A straight
     rule across the plate fights every other line in the composition. */
  ctx.strokeStyle = alpha(pal.line, 0.5 * strength);
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(0, 0, rx * 0.92, Math.PI * 1.12, Math.PI * 1.88);
  ctx.stroke();
  ctx.restore();
}
