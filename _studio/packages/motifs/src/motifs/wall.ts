/* Wall. Canto 9, the wall of wires.

   "You described the problem exactly, and then you called it a wall. Call it a
   bill instead."

   So the wall is never breached by force. It thins from the middle outward
   into an arch, because the architecture changed underneath the price, and
   through the arch two modules talk over light. Breach is the parting. Light
   is the link that replaces the rope. Heat is the bill: warm gold at the top
   flange where every coax drags the room down into the cold. */

import { alpha, metrics, mix, type Surface } from '../surface.js';
import { hatch, haze, poly, type Pt } from '../forms.js';
import { clamp, ease, rng, span, TAU, type Seed } from '../rng.js';
import { defineMotif } from '../types.js';

export type WallParams = {
  /** wires in the nearest rank */
  density: number;
  ranks: number;
  /** 0 is a ruled comb, 1 clusters and leaves holes */
  gap: number;
  /** 0..1 how wide the arch opens */
  breach: number;
  /** 0..1 warmth at the flange */
  heat: number;
  /** 0..1 brightness of the photonic link */
  light: number;
  sway: number;
  connectors: number;
  modules: number;
  spread: number;
  floor: number;
}

export const wall = defineMotif<WallParams>({
  id: 'wall',
  signature: 0.72,
  defaults: {
    density: 46,
    ranks: 3,
    gap: 0.4,
    breach: 0,
    heat: 1,
    light: 0,
    sway: 1,
    connectors: 1,
    modules: 0,
    spread: 0.96,
    floor: 0.86,
  },
  curve: (p) => ({
    heat: 1 - 0.3 * ease(span(p, 0, 0.45)),
    breach: ease(span(p, 0.36, 0.9)),
    modules: ease(span(p, 0.44, 0.78)),
    light: ease(span(p, 0.56, 1)),
  }),

  draw(s: Surface, seed: Seed, p: WallParams) {
    const { cx, unit } = metrics(s);
    const ctx = s.ctx;
    const pal = s.palette;
    const r = rng(String(seed) + '/wall');
    const left = s.x + s.w * (1 - p.spread) / 2;
    const width = s.w * p.spread;
    const topY = s.y + s.h * 0.1;
    const floorY = s.y + s.h * p.floor;
    const breach = clamp(p.breach);
    const arch = breach * width * 0.32;

    ctx.save();
    ctx.lineCap = 'round';

    /* the cold below */
    const cold = ctx.createLinearGradient(0, floorY - unit * 0.06, 0, s.y + s.h);
    cold.addColorStop(0, alpha(pal.void, 0));
    cold.addColorStop(1, alpha(pal.void2, 0.9));
    ctx.fillStyle = cold;
    ctx.fillRect(s.x, floorY - unit * 0.06, s.w, s.y + s.h - floorY + unit * 0.06);
    hatch(ctx, s.x, floorY, s.w, s.y + s.h - floorY, 0.14, Math.max(6, unit * 0.02), pal.cyan, 0.07);

    for (let rank = 0; rank < p.ranks; rank++) {
      const near = p.ranks === 1 ? 1 : rank / (p.ranks - 1);
      const shrink = 0.24 * (1 - near);
      const rTop = topY + s.h * shrink * 0.5;
      const rFloor = floorY - s.h * shrink * 0.55;
      /* Density is a look, not a count. A 375 pixel plate given 66 wires puts
         one every five pixels: it costs the same strokes as a laptop, reads as
         a grey smear, and is the one frame budget failure measured on this
         edition. Scaling by box width fixes both, and it stays deterministic
         because the surface size is already part of the seed key. */
      const fit = clamp(s.w / 1200, 0.42, 1);
      const n = Math.max(6, Math.round(p.density * (0.62 + near * 0.38) * fit));
      const dim = 0.34 + near * 0.62;
      const rr = r.fork('rank' + rank);

      for (let i = 0; i < n; i++) {
        const base = (i + 0.5) / n;
        const jitter = (rr() * 2 - 1) * (p.gap / n) * 1.5;
        const t = clamp(base + jitter, 0.005, 0.995);
        const x = left + t * width;
        const d = Math.abs(x - cx);

        /* the arch: cut height eases from fully open at the centre */
        let bottom = rFloor;
        let cutTip = false;
        if (arch > 1 && d < arch) {
          const k = ease(d / arch);
          bottom = rTop + (rFloor - rTop) * k;
          cutTip = k < 0.985;
        }
        if (bottom - rTop < unit * 0.01) continue;

        const swayAmp = p.sway * unit * 0.012 * (0.4 + rr());
        const phase = rr() * TAU;
        const pts: Pt[] = [];
        const steps = 16;
        for (let k = 0; k <= steps; k++) {
          const u = k / steps;
          const y = rTop + (bottom - rTop) * u;
          pts.push([x + Math.sin(phase + u * 2.4) * swayAmp * u, y]);
        }
        poly(ctx, pts);
        ctx.strokeStyle = alpha(pal.dim, dim * (0.4 + rr() * 0.5) * (0.4 + near * 0.6));
        ctx.lineWidth = 0.7 + near * 1.5;
        ctx.stroke();

        /* one bright side to each near wire, so it reads as a round cable */
        if (near > 0.7) {
          ctx.strokeStyle = alpha(pal.gold, 0.22 * dim);
          ctx.lineWidth = 0.7;
          ctx.beginPath();
          ctx.moveTo(pts[0]![0] - 0.9, pts[0]![1]);
          for (let k = 1; k < pts.length; k++) ctx.lineTo(pts[k]![0] - 0.9, pts[k]![1]);
          ctx.stroke();
        }

        if (p.connectors > 0 && near > 0.55) {
          const beads = 3;
          for (let b = 1; b <= beads; b++) {
            const u = b / (beads + 1);
            const q = pts[Math.round(u * steps)]!;
            ctx.fillStyle = alpha(pal.gold, 0.3 * dim * p.connectors);
            ctx.fillRect(q[0] - 2, q[1] - 1.6, 4, 3.2);
          }
        }

        if (cutTip) {
          const tip = pts[pts.length - 1]!;
          ctx.fillStyle = alpha(pal.rose, 0.5 * dim);
          ctx.beginPath();
          ctx.arc(tip[0], tip[1], 1.5, 0, TAU);
          ctx.fill();
        }
      }
    }

    /* the flange: where the room meets the cold and pays for it */
    const flangeH = Math.max(8, s.h * 0.045);
    const fg = ctx.createLinearGradient(0, topY - flangeH, 0, topY + flangeH * 0.4);
    fg.addColorStop(0, alpha(pal.gold, 0.34 * p.heat));
    fg.addColorStop(1, alpha(pal.gold, 0.05 * p.heat));
    ctx.fillStyle = fg;
    ctx.fillRect(s.x, topY - flangeH, s.w, flangeH * 1.4);
    ctx.strokeStyle = alpha(pal.gold, 0.55 * p.heat);
    ctx.lineWidth = 1.3;
    ctx.beginPath();
    ctx.moveTo(s.x, topY);
    ctx.lineTo(s.x + s.w, topY);
    ctx.stroke();
    for (let i = 0; i <= 28; i++) {
      const x = s.x + (s.w * i) / 28;
      ctx.strokeStyle = alpha(pal.gold, (i % 4 === 0 ? 0.45 : 0.2) * p.heat);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, topY - flangeH * (i % 4 === 0 ? 0.62 : 0.34));
      ctx.lineTo(x, topY);
      ctx.stroke();
    }

    /* heat falling away down the wall */
    if (p.heat > 0) {
      const hg = ctx.createLinearGradient(0, topY, 0, floorY);
      hg.addColorStop(0, alpha(pal.gold, 0.12 * p.heat));
      hg.addColorStop(0.45, alpha(pal.rose, 0.03 * p.heat));
      hg.addColorStop(1, alpha(pal.void, 0));
      ctx.fillStyle = hg;
      ctx.fillRect(s.x, topY, s.w, floorY - topY);
    }

    /* the congregation, and the light between */
    const mods = clamp(p.modules);
    if (mods > 0.02 && arch > unit * 0.08) {
      const bw = Math.min(arch * 0.5, unit * 0.19);
      const bh = bw * 0.58;
      const by = floorY - bh - unit * 0.02;
      for (const sx of [-1, 1]) {
        const bx = cx + sx * arch * 0.66 - bw / 2;
        drawModule(ctx, bx, by, bw, bh, s, mods, r.fork('mod' + sx));
      }
      const lit = clamp(p.light) * mods;
      if (lit > 0.01) {
        const y = by + bh * 0.42;
        const x0 = cx - arch * 0.66 + bw / 2;
        const x1 = cx + arch * 0.66 - bw / 2;
        const beam = ctx.createLinearGradient(x0, 0, x1, 0);
        beam.addColorStop(0, alpha(pal.cyan, 0.15 * lit));
        beam.addColorStop(0.5, alpha(pal.cyan, 0.5 * lit));
        beam.addColorStop(1, alpha(pal.cyan, 0.15 * lit));
        ctx.fillStyle = beam;
        ctx.fillRect(x0, y - unit * 0.006 * lit, x1 - x0, unit * 0.012 * lit);
        ctx.strokeStyle = alpha(pal.cyan, 0.9 * lit);
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(x0, y);
        ctx.lineTo(x1, y);
        ctx.stroke();
        /* the link is lossy: photons in flight, not a solid rope */
        const rr = r.fork('photons');
        for (let i = 0; i < 7; i++) {
          const px = x0 + (x1 - x0) * rr();
          haze(ctx, px, y, unit * 0.03, pal.cyan, 0.5 * lit);
        }
        haze(ctx, (x0 + x1) / 2, y, unit * 0.2, pal.cyan, 0.2 * lit);
      }
    }

    ctx.restore();
  },
});

function drawModule(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number,
  s: Surface, a: number, r: ReturnType<typeof rng>,
): void {
  const pal = s.palette;
  ctx.save();
  ctx.save();
  ctx.fillStyle = mix(pal.void2, pal.void, 0.25);
  ctx.globalAlpha *= a;
  ctx.fillRect(x, y, w, h);
  ctx.restore();
  ctx.strokeStyle = alpha(pal.gold, 0.55 * a);
  ctx.lineWidth = 1.2;
  ctx.strokeRect(x, y, w, h);
  ctx.strokeStyle = alpha(pal.gold, 0.2 * a);
  ctx.strokeRect(x + 3, y + 3, w - 6, h - 6);
  const cols = 6;
  const rows = 3;
  for (let i = 0; i < cols; i++) {
    for (let j = 0; j < rows; j++) {
      const px = x + w * ((i + 0.5) / cols);
      const py = y + h * ((j + 0.5) / rows);
      ctx.fillStyle = alpha(pal.cyan, (0.25 + r() * 0.5) * a);
      ctx.beginPath();
      ctx.arc(px, py, Math.max(0.8, w * 0.018), 0, TAU);
      ctx.fill();
    }
  }
  ctx.restore();
}
