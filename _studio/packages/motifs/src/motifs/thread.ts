/* Thread. Connection and correlation.

   "It was arranged once, when the two were together, and it endures in the
   correlation of what they are, not in any traffic between them."

   Tension is what a bond costs to hold. Pairing is threads that have found
   each other and braid. Severance is the recoil: a cut thread does not just
   stop, it curls back, and both ends move although nothing travelled between
   them. */

import { alpha, metrics, type Surface } from '../surface.js';
import { catenary, haze, poly, type Pt } from '../forms.js';
import { clamp, ease, rng, span, TAU, type Seed } from '../rng.js';
import { defineMotif } from '../types.js';

export type ThreadParams = {
  count: number;
  /** 0 hangs slack, 1 pulls straight */
  tension: number;
  /** 0..1 fraction of threads cut */
  sever: number;
  /** 0..1 how strongly neighbouring threads braid */
  pairing: number;
  spread: number;
  height: number;
  anchors: number;
  glow: number;
  /** fraction of threads carrying the gold reading rather than cyan */
  gold: number;
  width: number;
  /** the whole span turned about the middle of its box, in turns. Two layers
      at a quarter turn apart make cloth out of a set of parallel threads,
      which is what canto 5 needs and what a single direction cannot say. */
  angle: number;
  /** a constant added to the sag. Negative arcs the span the other way, over
      the horizon rather than under it, which is how canto 13 hangs a link from
      orbit instead of laying one along the ground. */
  bow: number;
}

function curl(from: Pt, dir: Pt, size: number, turns = 1.6): Pt[] {
  const out: Pt[] = [];
  const a0 = Math.atan2(dir[1], dir[0]);
  let x = from[0];
  let y = from[1];
  const steps = 18;
  for (let i = 1; i <= steps; i++) {
    const t = i / steps;
    const a = a0 + t * turns * TAU * 0.5;
    const step = (size / steps) * (1 - t * 0.75);
    x += Math.cos(a) * step;
    y += Math.sin(a) * step;
    out.push([x, y]);
  }
  return out;
}

export const thread = defineMotif<ThreadParams>({
  id: 'thread',
  signature: 0.55,
  defaults: {
    count: 15,
    tension: 0.5,
    sever: 0,
    pairing: 0,
    spread: 0.86,
    height: 0.72,
    anchors: 1,
    glow: 1,
    gold: 0.2,
    width: 1,
    angle: 0,
    bow: 0,
  },
  curve: (p) => ({
    tension: ease(span(p, 0.04, 0.56)),
    pairing: ease(span(p, 0.28, 0.72)),
    sever: ease(span(p, 0.74, 1)) * 0.55,
  }),

  draw(s: Surface, seed: Seed, p: ThreadParams) {
    const { cx, cy, unit } = metrics(s);
    const ctx = s.ctx;
    const pal = s.palette;
    const r = rng(String(seed) + '/thread');
    const halfW = (s.w * p.spread) / 2;
    const halfH = (s.h * p.height) / 2;
    const ten = clamp(p.tension);
    const sev = clamp(p.sever);
    const pair = clamp(p.pairing);

    ctx.save();
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    /* turned about the middle of its own box, before anything is drawn, so a
       warp and a weft are the same code at two angles */
    if (p.angle !== 0) {
      ctx.translate(cx, cy);
      ctx.rotate(p.angle * TAU);
      ctx.translate(-cx, -cy);
    }

    /* posts, not brackets. Two things the threads are tied to, so the picture
       reads as a span under tension and not as a ruled table. */
    if (p.anchors > 0) {
      const postW = Math.max(4, unit * 0.018);
      for (const sx of [-1, 1]) {
        const x = cx + sx * halfW;
        const top = cy - halfH * 1.16;
        const bot = cy + halfH * 1.16;
        const g = ctx.createLinearGradient(x - postW, 0, x + postW, 0);
        g.addColorStop(0, alpha(pal.gold, 0.1 * p.anchors));
        g.addColorStop(0.45, alpha(pal.gold, 0.4 * p.anchors));
        g.addColorStop(1, alpha(pal.gold, 0.08 * p.anchors));
        ctx.fillStyle = g;
        ctx.fillRect(x - postW / 2, top, postW, bot - top);
        ctx.strokeStyle = alpha(pal.gold, 0.7 * p.anchors);
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(x, top);
        ctx.lineTo(x, bot);
        ctx.stroke();
        for (const y of [top, bot]) {
          ctx.beginPath();
          ctx.moveTo(x - postW * 1.5, y);
          ctx.lineTo(x + postW * 1.5, y);
          ctx.stroke();
        }
      }
    }

    for (let i = 0; i < p.count; i++) {
      const t = p.count === 1 ? 0.5 : i / (p.count - 1);
      const ya = cy + (t - 0.5) * 2 * halfH + r.gauss() * unit * 0.012;
      const yb = cy + (t - 0.5) * 2 * halfH + r.gauss() * unit * 0.05;
      const a: Pt = [cx - halfW, ya];
      const b: Pt = [cx + halfW, yb];
      const slack = (1 - ten) * r.range(0.14, 0.26) + p.bow;
      /* neighbours twist in opposite senses, so a pair reads as one braid
         rather than two parallel waves */
      const braid = pair * 0.022 * (i % 2 === 0 ? 1 : -1);
      const pts = catenary(a, b, slack, 48, braid, r.range(0, TAU));
      const isGold = r() < p.gold;
      const hue = isGold ? pal.gold : pal.cyan;
      const base = 0.2 + 0.55 * ten;
      const cut = r() < sev;

      ctx.lineWidth = (isGold ? 1.7 : 1.1) * p.width;

      if (!cut) {
        /* a cord, not a rule: a dim sheath under a bright core */
        poly(ctx, pts);
        ctx.strokeStyle = alpha(hue, base * 0.3);
        ctx.lineWidth = (isGold ? 4.4 : 3) * p.width;
        ctx.stroke();
        poly(ctx, pts);
        ctx.strokeStyle = alpha(hue, base);
        ctx.lineWidth = (isGold ? 1.7 : 1.1) * p.width;
        ctx.stroke();
        if (isGold && p.glow > 0) {
          const mid = pts[Math.floor(pts.length / 2)]!;
          haze(ctx, mid[0], mid[1], unit * 0.12 * p.glow, hue, 0.16 * ten * p.glow);
        }
        continue;
      }

      const at = Math.floor(pts.length * r.range(0.34, 0.66));
      const left = pts.slice(0, at);
      const right = pts.slice(at + 1);
      const size = unit * 0.17;
      if (left.length > 2) {
        const tail = left[left.length - 1]!;
        const prev = left[left.length - 2]!;
        poly(ctx, left.concat(curl(tail, [prev[0] - tail[0], prev[1] - tail[1]], size)));
        ctx.strokeStyle = alpha(pal.dim, base * 0.8);
        ctx.stroke();
      }
      if (right.length > 2) {
        const head = right[0]!;
        const nxt = right[1]!;
        poly(ctx, curl(head, [nxt[0] - head[0], nxt[1] - head[1]], size).reverse().concat(right));
        ctx.strokeStyle = alpha(pal.dim, base * 0.8);
        ctx.stroke();
      }
      const mid = pts[at]!;
      ctx.fillStyle = alpha(pal.rose, 0.85);
      ctx.beginPath();
      ctx.arc(mid[0], mid[1], Math.max(2, unit * 0.008), 0, TAU);
      ctx.fill();
      haze(ctx, mid[0], mid[1], unit * 0.09, pal.rose, 0.5);
    }

    ctx.restore();
  },
});
