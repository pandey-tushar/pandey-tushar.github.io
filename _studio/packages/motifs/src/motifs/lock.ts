/* Lock. Canto 16, the unsealing.

   "You were told the lock was a wall. It was always a very long corridor."

   The lock is drawn as a ward lock and an astrolabe at once: concentric rings
   of teeth, each ring carrying one gap. Closed, the gaps sit at seeded angles
   and there is no way through. Shor does not cut the rings; he finds the
   rhythm, so the comb parameter lights every period-th tooth first, and only
   then do the gaps rotate into line and the corridor appear. Dissolve is 2024:
   the wards break up and reassemble as a lattice, which is the mathematics the
   new locks are built on. */

import { alpha, metrics, type Surface } from '../surface.js';
import { haze, poly, tickRing, type Pt } from '../forms.js';
import { clamp, ease, lerp, rng, span, TAU, type Seed } from '../rng.js';
import { defineMotif } from '../types.js';

export type LockParams = {
  /** number of ward rings */
  complexity: number;
  teeth: number;
  /** 0..1 gaps rotating into line */
  open: number;
  /** the hidden rhythm; every period-th tooth belongs to it */
  period: number;
  comb: number;
  corridor: number;
  shackle: number;
  /** 0..1 wards break up into the lattice the new locks are built on */
  dissolve: number;
  radius: number;
  keyway: number;
}

const CORRIDOR = -Math.PI / 2;

export const lock = defineMotif<LockParams>({
  id: 'lock',
  signature: 0.66,
  defaults: {
    complexity: 5,
    teeth: 28,
    open: 0,
    period: 7,
    comb: 0,
    corridor: 0,
    shackle: 0,
    dissolve: 0,
    radius: 0.38,
    keyway: 1,
  },
  curve: (p) => ({
    comb: ease(span(p, 0.1, 0.44)),
    open: ease(span(p, 0.34, 0.86)),
    corridor: ease(span(p, 0.44, 0.9)),
    shackle: ease(span(p, 0.58, 0.94)),
    dissolve: ease(span(p, 0.78, 1)),
  }),

  draw(s: Surface, seed: Seed, p: LockParams) {
    const { cx, cy, unit } = metrics(s);
    const ctx = s.ctx;
    const pal = s.palette;
    const r = rng(String(seed) + '/lock');
    const R = unit * p.radius;
    const open = clamp(p.open);
    const comb = clamp(p.comb);
    const corr = clamp(p.corridor);
    const diss = clamp(p.dissolve);
    const rings = Math.max(1, Math.round(p.complexity));
    const teeth = Math.max(6, Math.round(p.teeth));
    const period = Math.max(2, Math.round(p.period));

    ctx.save();
    ctx.lineCap = 'butt';
    ctx.lineJoin = 'round';

    /* the bow, lifting */
    if (p.shackle > 0) {
      const lift = ease(clamp(p.shackle)) * R * 0.5;
      const bw = R * 0.62;
      ctx.beginPath();
      ctx.moveTo(cx - bw, cy - R * 0.55 - lift * 0.2);
      ctx.arc(cx, cy - R * 0.62 - lift, bw, Math.PI, TAU);
      ctx.strokeStyle = alpha(pal.gold, 0.5);
      ctx.lineWidth = Math.max(4, R * 0.055);
      ctx.stroke();
      ctx.strokeStyle = alpha(pal.gold, 0.9);
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }

    /* corridor: the way through, opening from the keyway outward */
    if (corr > 0.01) {
      const half = 0.1 + 0.05 * corr;
      const reach = R * (1.15 + corr * 0.35);
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, reach);
      g.addColorStop(0, alpha(pal.cyan, 0.45 * corr));
      g.addColorStop(0.6, alpha(pal.cyan, 0.14 * corr));
      g.addColorStop(1, alpha(pal.cyan, 0));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, reach, CORRIDOR - half, CORRIDOR + half);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = alpha(pal.cyan, 0.7 * corr);
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(CORRIDOR) * reach, cy + Math.sin(CORRIDOR) * reach);
      ctx.stroke();
    }

    /* ward rings */
    const combLinks: Array<{ ring: number; a: number; at: Pt }> = [];
    for (let k = 0; k < rings; k++) {
      const kt = k / Math.max(1, rings - 1);
      const rIn = R * (0.34 + kt * 0.52);
      const rOut = rIn + R * 0.085;
      const rr = r.fork('ring' + k);
      const closedGap = rr.range(0, TAU);
      const gapAngle = lerp(closedGap, CORRIDOR + Math.round((closedGap - CORRIDOR) / TAU) * TAU, ease(open));
      /* every ring shares a tooth phase, so the period marks line up radially.
         The rhythm is the point; a scatter of gold blocks is not a rhythm. */
      const spin = 0;

      ctx.strokeStyle = alpha(pal.dim, 0.3);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, (rIn + rOut) / 2, 0, TAU);
      ctx.stroke();

      const gapWidth = (2.4 * TAU) / teeth;
      for (let i = 0; i < teeth; i++) {
        const a = spin + (i / teeth) * TAU;
        let da = ((a - gapAngle + Math.PI) % TAU + TAU) % TAU - Math.PI;
        da = Math.abs(da);
        if (da < gapWidth / 2) continue;

        const onBeat = i % period === 0;
        const w = (TAU / teeth) * 0.42;
        /* dissolve pushes each tooth outward into a lattice dot */
        const push = diss * R * (0.1 + rr() * 0.5);
        const a0 = a - w;
        const a1 = a + w;
        const i0 = rIn + push * 0.4;
        const o0 = rOut + push;

        if (diss > 0.55) {
          const mid = (i0 + o0) / 2;
          const px = cx + Math.cos(a) * mid;
          const py = cy + Math.sin(a) * mid;
          ctx.fillStyle = alpha(onBeat ? pal.gold : pal.cyan, (0.25 + (onBeat ? 0.5 : 0.2)) * (diss));
          ctx.beginPath();
          ctx.arc(px, py, Math.max(1, R * 0.012), 0, TAU);
          ctx.fill();
          if (onBeat) combLinks.push({ ring: k, a, at: [px, py] });
          continue;
        }

        const quad: Pt[] = [
          [cx + Math.cos(a0) * i0, cy + Math.sin(a0) * i0],
          [cx + Math.cos(a1) * i0, cy + Math.sin(a1) * i0],
          [cx + Math.cos(a1) * o0, cy + Math.sin(a1) * o0],
          [cx + Math.cos(a0) * o0, cy + Math.sin(a0) * o0],
        ];
        poly(ctx, quad, true);
        const lit = onBeat ? 0.24 + comb * 0.7 : 0.26;
        ctx.fillStyle = alpha(onBeat ? pal.gold : pal.dim, lit * (1 - diss * 0.6));
        ctx.fill();
        ctx.strokeStyle = alpha(onBeat ? pal.gold : pal.dim, (onBeat ? 0.7 : 0.3) * (1 - diss * 0.6));
        ctx.lineWidth = 1;
        ctx.stroke();
        if (onBeat) combLinks.push({ ring: k, a, at: [(quad[0]![0] + quad[2]![0]) / 2, (quad[0]![1] + quad[2]![1]) / 2] });
      }
    }

    /* the rhythm buried in the arithmetic: links between teeth on the beat */
    if (comb > 0.02) {
      ctx.strokeStyle = alpha(pal.gold, 0.45 * comb);
      ctx.lineWidth = 1;
      /* joined by angle, not by list position. A ring whose gap swallowed a
         marked tooth must not drag the whole comb sideways: the rhythm is
         radial or it is not a rhythm. */
      for (const link of combLinks) {
        let best: Pt | null = null;
        let bestD = Infinity;
        for (const other of combLinks) {
          if (other.ring !== link.ring + 1) continue;
          const d = Math.abs(((other.a - link.a + Math.PI) % TAU + TAU) % TAU - Math.PI);
          if (d < bestD) { bestD = d; best = other.at; }
        }
        if (!best || bestD > TAU / 24) continue;
        ctx.beginPath();
        ctx.moveTo(link.at[0], link.at[1]);
        ctx.lineTo(best[0], best[1]);
        ctx.stroke();
      }
      for (const link of combLinks) haze(ctx, link.at[0], link.at[1], R * 0.05, pal.gold, 0.22 * comb);
    }

    /* the plate's outer graduation, and the keyway */
    tickRing(ctx, cx, cy, R * 1.03, 60, R * 0.055, { color: pal.gold, alpha: 0.34, major: 5 });

    if (p.keyway > 0) {
      const kr = R * 0.16;
      ctx.fillStyle = alpha(pal.void, 0.9);
      ctx.beginPath();
      ctx.arc(cx, cy, kr, 0, TAU);
      ctx.fill();
      ctx.strokeStyle = alpha(pal.gold, 0.75);
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.arc(cx, cy, kr, 0, TAU);
      ctx.stroke();
      ctx.fillStyle = alpha(pal.void, 0.95);
      ctx.beginPath();
      ctx.moveTo(cx - kr * 0.32, cy);
      ctx.lineTo(cx + kr * 0.32, cy);
      ctx.lineTo(cx + kr * 0.18, cy + kr * 1.5);
      ctx.lineTo(cx - kr * 0.18, cy + kr * 1.5);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = alpha(pal.gold, 0.55);
      ctx.lineWidth = 1;
      ctx.stroke();
      if (corr > 0.02) haze(ctx, cx, cy, R * 0.3 * corr, pal.cyan, 0.4 * corr);
    }

    ctx.restore();
  },
});
