/* Sphere. Canto 1, the Bloch sphere.

   "Every point. North and south are only two directions you happened to name
   first." So the sphere is drawn as an instrument, a graticule you could read
   a bearing off, and the state vector is a gold index arm on it. The phase is
   the violet trace running the parallel: private, invisible to any single
   measurement, and the thing that decides everything.

   Collapse is the whole canto's argument in one parameter. As it rises the
   graticule dims, the trace is spent, the arm swings to a pole, and what is
   left is one bright point where a whole surface used to be. */

import { alpha, metrics, type Surface } from '../surface.js';
import { camera, haze, poly, type Cam, type Pt, type Vec3 } from '../forms.js';
import { clamp, ease, lerp, rng, span, TAU, type Seed } from '../rng.js';
import { defineMotif } from '../types.js';

export type SphereParams = {
  /** polar angle of the state, 0 is north */
  theta: number;
  /** azimuth of the state: the phase */
  phi: number;
  /** 0..1 length of the phase trace behind the arm */
  trace: number;
  traceTurns: number;
  /** 0..1 the question being forced */
  collapse: number;
  meridians: number;
  parallels: number;
  radius: number;
  graticule: number;
  equator: number;
  vector: number;
  pitch: number;
  yaw: number;
}

const rot = (p: Vec3, yaw: number): Vec3 => {
  const c = Math.cos(yaw);
  const s = Math.sin(yaw);
  return [p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c];
};

const onSphere = (theta: number, phi: number): Vec3 => [
  Math.sin(theta) * Math.cos(phi),
  Math.cos(theta),
  Math.sin(theta) * Math.sin(phi),
];

/** Strokes a sampled great circle, splitting it at the limb so the far side
    can be drawn faint. That split is what makes a wireframe read as a solid. */
function curve3(
  ctx: CanvasRenderingContext2D, cam: Cam, pts: readonly Vec3[],
  front: string, back: string, wf: number, wb: number,
): void {
  let run: Pt[] = [];
  let side = cam.depth(pts[0]!) >= 0;
  const flush = (): void => {
    if (run.length > 1) {
      poly(ctx, run);
      ctx.strokeStyle = side ? front : back;
      ctx.lineWidth = side ? wf : wb;
      ctx.stroke();
    }
    run = [];
  };
  for (const q of pts) {
    const s = cam.depth(q) >= 0;
    if (s !== side) { flush(); side = s; }
    run.push(cam.project(q));
  }
  flush();
}

export const sphere = defineMotif<SphereParams>({
  id: 'sphere',
  signature: 0.34,
  defaults: {
    theta: 1.95,
    phi: 0,
    trace: 0.8,
    traceTurns: 1.6,
    collapse: 0,
    meridians: 10,
    parallels: 5,
    radius: 0.4,
    graticule: 1,
    equator: 1,
    vector: 1,
    pitch: 16,
    yaw: 0.35,
  },
  curve: (p) => ({
    phi: p * TAU * 2.2,
    theta: lerp(1.95, 0.055, ease(span(p, 0.55, 0.98))),
    trace: ease(span(p, 0.05, 0.45)) * (1 - ease(span(p, 0.62, 0.96))),
    collapse: ease(span(p, 0.55, 1)),
    graticule: 1 - 0.6 * ease(span(p, 0.6, 1)),
    equator: 1 - ease(span(p, 0.58, 0.92)),
  }),

  draw(s: Surface, seed: Seed, p: SphereParams) {
    const { cx, cy, unit } = metrics(s);
    const pal = s.palette;
    const ctx = s.ctx;
    const r = rng(String(seed) + '/sphere');
    const R = unit * p.radius;
    const cam = camera(cx, cy, R, (p.pitch * Math.PI) / 180);
    const yaw = p.yaw + r.range(-0.15, 0.15);
    const grat = clamp(p.graticule);
    const col = clamp(p.collapse);
    const N = 120;

    ctx.save();
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    /* interior: just enough to say the far side is behind something */
    const body = ctx.createRadialGradient(cx - R * 0.3, cy - R * 0.35, 0, cx, cy, R * 1.05);
    body.addColorStop(0, alpha(pal.violet, 0.07));
    body.addColorStop(0.7, alpha(pal.void2, 0.4));
    body.addColorStop(1, alpha(pal.void, 0.65));
    ctx.fillStyle = body;
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, TAU);
    ctx.fill();

    /* meridians */
    if (grat > 0.01) {
      for (let m = 0; m < p.meridians; m++) {
        const a = (m / p.meridians) * Math.PI;
        const pts: Vec3[] = [];
        for (let i = 0; i <= N; i++) {
          const t = (i / N) * TAU;
          pts.push(rot([Math.sin(t) * Math.cos(a), Math.cos(t), Math.sin(t) * Math.sin(a)], yaw));
        }
        curve3(ctx, cam, pts,
          alpha(pal.cyan, 0.3 * grat), alpha(pal.cyan, 0.09 * grat), 1, 0.8);
      }
      /* parallels */
      for (let k = 1; k <= p.parallels; k++) {
        const th = (k / (p.parallels + 1)) * Math.PI;
        const pts: Vec3[] = [];
        for (let i = 0; i <= N; i++) pts.push(rot(onSphere(th, (i / N) * TAU), yaw));
        curve3(ctx, cam, pts,
          alpha(pal.cyan, 0.2 * grat), alpha(pal.cyan, 0.06 * grat), 1, 0.8);
      }
    }

    /* the equator, graduated. The instrument's one emphatic circle. */
    const eq = clamp(p.equator);
    if (eq > 0.01) {
      const pts: Vec3[] = [];
      for (let i = 0; i <= N * 2; i++) pts.push(rot(onSphere(Math.PI / 2, (i / (N * 2)) * TAU), yaw));
      curve3(ctx, cam, pts,
        alpha(pal.gold, 0.55 * eq), alpha(pal.gold, 0.16 * eq), 1.4, 1);
      for (let i = 0; i < 72; i++) {
        const a = (i / 72) * TAU;
        const q = rot(onSphere(Math.PI / 2, a), yaw);
        if (cam.depth(q) < 0) continue;
        const long = i % 6 === 0;
        const inner = cam.project(q);
        const outer = cam.project([q[0] * (1 + (long ? 0.07 : 0.04)), q[1], q[2] * (1 + (long ? 0.07 : 0.04))]);
        ctx.beginPath();
        ctx.moveTo(inner[0], inner[1]);
        ctx.lineTo(outer[0], outer[1]);
        ctx.strokeStyle = alpha(pal.gold, (long ? 0.6 : 0.3) * eq);
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    /* the limb */
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, TAU);
    ctx.strokeStyle = alpha(pal.cyan, 0.4 + 0.25 * col);
    ctx.lineWidth = 1.2;
    ctx.stroke();

    /* the axis you happened to name first */
    const np = cam.project([0, 1, 0]);
    const sp = cam.project([0, -1, 0]);
    ctx.beginPath();
    ctx.moveTo(np[0], np[1]);
    ctx.lineTo(sp[0], sp[1]);
    ctx.strokeStyle = alpha(pal.dim, 0.4);
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillStyle = alpha(pal.ink, 0.85);
    ctx.beginPath();
    ctx.arc(np[0], np[1], 3.2, 0, TAU);
    ctx.fill();
    ctx.strokeStyle = alpha(pal.ink, 0.7);
    ctx.lineWidth = 1.3;
    ctx.beginPath();
    ctx.arc(sp[0], sp[1], 3.2, 0, TAU);
    ctx.stroke();

    /* the phase trace: the part that never shows itself alone */
    const tr = clamp(p.trace);
    if (tr > 0.01) {
      const arc = p.traceTurns * TAU * tr;
      const steps = Math.max(24, Math.round(arc * 26));
      for (let i = 0; i < steps; i++) {
        const t0 = p.phi - arc + (arc * i) / steps;
        const t1 = p.phi - arc + (arc * (i + 1)) / steps;
        const q0 = rot(onSphere(p.theta, t0), yaw);
        const q1 = rot(onSphere(p.theta, t1), yaw);
        const near = (cam.depth(q0) + cam.depth(q1)) / 2 >= 0;
        const fade = (i / steps) * (i / steps);
        const a0 = cam.project(q0);
        const a1 = cam.project(q1);
        ctx.beginPath();
        ctx.moveTo(a0[0], a0[1]);
        ctx.lineTo(a1[0], a1[1]);
        ctx.strokeStyle = alpha(pal.violet, (near ? 0.75 : 0.2) * fade * tr);
        ctx.lineWidth = near ? 2 : 1.2;
        ctx.stroke();
      }
    }

    /* the arm */
    const v = clamp(p.vector);
    if (v > 0.01) {
      const tipV = rot(onSphere(p.theta, p.phi), yaw);
      const c0 = cam.project([0, 0, 0]);
      const tip = cam.project(tipV);
      ctx.beginPath();
      ctx.moveTo(c0[0], c0[1]);
      ctx.lineTo(tip[0], tip[1]);
      ctx.strokeStyle = alpha(pal.gold, 0.95 * v);
      ctx.lineWidth = Math.max(1.6, unit * 0.004);
      ctx.stroke();

      const dx = tip[0] - c0[0];
      const dy = tip[1] - c0[1];
      const l = Math.hypot(dx, dy) || 1;
      const hx = dx / l;
      const hy = dy / l;
      const head = Math.max(7, unit * 0.022);
      poly(ctx, [
        [tip[0], tip[1]],
        [tip[0] - hx * head - hy * head * 0.36, tip[1] - hy * head + hx * head * 0.36],
        [tip[0] - hx * head + hy * head * 0.36, tip[1] - hy * head - hx * head * 0.36],
      ], true);
      ctx.fillStyle = alpha(pal.gold, 0.95 * v);
      ctx.fill();
      haze(ctx, tip[0], tip[1], unit * (0.06 + 0.1 * col), pal.gold, 0.45 * v);
    }

    /* the surface being spent: arcs closing on the pole that is kept */
    if (col > 0.02) {
      const target = p.theta < Math.PI / 2 ? 0 : Math.PI;
      for (let k = 0; k < 6; k++) {
        const th = lerp(Math.PI / 2, target, ease(col) * (0.35 + k * 0.11));
        const pts: Vec3[] = [];
        for (let i = 0; i <= 64; i++) pts.push(rot(onSphere(th, (i / 64) * TAU), yaw));
        curve3(ctx, cam, pts,
          alpha(pal.rose, 0.3 * col * (1 - k / 7)), alpha(pal.rose, 0.08 * col), 1, 0.8);
      }
      const keep = cam.project([0, target === 0 ? 1 : -1, 0]);
      haze(ctx, keep[0], keep[1], unit * 0.1 * col, pal.rose, 0.5 * col);
    }

    ctx.restore();
  },
});
