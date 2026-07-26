/* Fire. The flame that is cupped, the toll that is paid, and the fire in the
   house.

   Three cantos ask for this form and they ask for different things, so every
   knob here had to become continuous. The first draft branched: the tip height
   jumped at containment 0.7, the lean flipped sign at 0.35, and the embers
   above the roof were dropped by an if. Three visible steps in the middle of a
   scroll, in a motif whose whole job is to change while the reader moves. All
   three are now lerps, and the poster test is what found them.

   Intensity is how much is burning. Containment is whether the house holds it:
   at one the tongues bend back toward the middle and die below the ridge and
   nothing leaves; at zero they clear the roof, the ridge takes the rose mark
   of what passed through it, and the embers leave the plate. Phase is the
   flame's shape, and it is a parameter rather than a clock so that a stopped
   scroll leaves a composed flame instead of a frozen accident.

   Canto 4 cups it. Canto 20 keeps it small and reads the receipt. Canto 21
   asks the one question the motif exists for: at this exact moment, is it
   cooking the meal or taking the roof. */

import { alpha, metrics, mix, type Surface } from '../surface.js';
import { haze, poly, type Pt } from '../forms.js';
import { clamp, ease, lerp, noise1, rng, span, TAU, type Seed } from '../rng.js';
import { defineMotif } from '../types.js';

export type FireParams = {
  intensity: number;
  /** 0 the house is open, 1 it holds */
  containment: number;
  tongues: number;
  embers: number;
  plume: number;
  /** shape phase, advanced by scroll progress */
  phase: number;
  vessel: number;
  spread: number;
  /** the pool of light the fire throws on its own floor */
  hearth: number;
}

export const fire = defineMotif<FireParams>({
  id: 'fire',
  signature: 0.5,
  defaults: {
    intensity: 0.8,
    containment: 0.6,
    tongues: 11,
    embers: 60,
    plume: 0.62,
    phase: 0,
    vessel: 1,
    spread: 0.5,
    hearth: 1,
  },
  curve: (p) => ({
    intensity: 0.3 + 0.7 * ease(span(p, 0, 0.6)),
    containment: 1 - ease(span(p, 0.25, 0.7)) * 0.85 + ease(span(p, 0.82, 1)) * 0.7,
    plume: 0.35 + 0.5 * ease(span(p, 0.1, 0.8)),
    phase: p * 7,
  }),

  draw(s: Surface, seed: Seed, p: FireParams) {
    const { cx, unit } = metrics(s);
    const ctx = s.ctx;
    const pal = s.palette;
    const r = rng(String(seed) + '/fire');
    const n = noise1(String(seed) + '/flame', 2);
    const inten = clamp(p.intensity);
    const cont = clamp(p.containment);
    const baseY = s.y + s.h * 0.8;
    const halfW = s.w * p.spread * 0.5;
    const eaveY = baseY - s.h * 0.3;
    const roofY = baseY - s.h * 0.44;

    ctx.save();
    ctx.lineJoin = 'round';

    /* the hearth: a pool on the floor rather than a lit rectangle, the same
       decision the coin's table makes and for the same reason */
    if (p.hearth > 0) {
      ctx.save();
      ctx.translate(cx, baseY);
      ctx.scale(1, 0.18);
      const g = ctx.createRadialGradient(0, 0, 0, 0, 0, halfW * 1.5);
      g.addColorStop(0, alpha(pal.gold, 0.3 * inten * p.hearth));
      g.addColorStop(0.5, alpha(pal.gold, 0.1 * inten * p.hearth));
      g.addColorStop(1, alpha(pal.gold, 0));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(0, 0, halfW * 1.5, 0, TAU);
      ctx.fill();
      ctx.restore();
    }

    /* the house, drawn before the flame so the flame stands in front of it.
       Its line brightens with the fire rather than with the containment,
       because a house with a big fire in it is a lit house whether or not the
       fire is behaving. */
    if (p.vessel > 0) {
      const a = p.vessel * (0.34 + inten * 0.42);
      /* the room behind the fire, so the outline is a house and not a glyph */
      const room = ctx.createLinearGradient(0, roofY, 0, baseY);
      room.addColorStop(0, alpha(pal.void2, 0.5 * p.vessel));
      room.addColorStop(1, alpha(pal.void2, 0.1 * p.vessel));
      poly(ctx, [
        [cx - halfW, baseY], [cx - halfW, eaveY], [cx, roofY],
        [cx + halfW, eaveY], [cx + halfW, baseY],
      ], true);
      ctx.fillStyle = room;
      ctx.fill();

      poly(ctx, [
        [cx - halfW, baseY], [cx - halfW, eaveY], [cx, roofY],
        [cx + halfW, eaveY], [cx + halfW, baseY],
      ]);
      ctx.strokeStyle = alpha(pal.gold, a);
      ctx.lineWidth = 1.6;
      ctx.stroke();
      /* the floor runs past the walls, so the house sits on ground */
      ctx.beginPath();
      ctx.moveTo(cx - halfW * 1.35, baseY);
      ctx.lineTo(cx + halfW * 1.35, baseY);
      ctx.strokeStyle = alpha(pal.gold, a * 0.65);
      ctx.lineWidth = 1.2;
      ctx.stroke();
      /* the tie beam: one more line and the pentagon reads as a roof */
      ctx.beginPath();
      ctx.moveTo(cx - halfW, eaveY);
      ctx.lineTo(cx + halfW, eaveY);
      ctx.strokeStyle = alpha(pal.gold, a * 0.4);
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    /* Tongues. Each is a sheath and a core, and the whole set is drawn added
       rather than painted. That one line is the difference between a fire and
       a stand of wheat: painted tongues overlap into flat mauve blades, added
       ones pile into a body of light with individual tips at the top, which is
       what fire actually looks like and what the first draft did not.

       Plume is measured against the height of the roof, not against the plate,
       so it means the one thing the three cantos need it to mean: at one the
       tallest tongues reach the ridge. */
    const roofH = baseY - roofY;
    const count = Math.max(1, Math.round(p.tongues));
    let highest = baseY;
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < count; i++) {
      const t = count === 1 ? 0.5 : i / (count - 1);
      const x0 = cx + (t - 0.5) * halfW * 1.44;
      const rr = r.fork('t' + i);
      const seedPhase = rr() * 40;
      const h = roofH * p.plume * rr.range(0.62, 1) * (0.5 + inten * 0.5);
      const bend = n(p.phase * 1.4 + seedPhase) * unit * 0.15;
      /* held: leans back toward the middle of the room. Open: leans with the
         draught. One lerp, no step. */
      const lean = lerp(bend, (cx - x0) * 0.62, cont);
      const tipY = baseY - h * lerp(1, 0.42, cont);
      if (tipY < highest) highest = tipY;
      const w = unit * 0.04 * rr.range(0.62, 1.3) * (0.45 + inten * 0.75);

      const left: Pt[] = [];
      const right: Pt[] = [];
      const cl: Pt[] = [];
      const cr: Pt[] = [];
      const steps = 15;
      for (let k = 0; k <= steps; k++) {
        const u = k / steps;
        const y = baseY + (tipY - baseY) * u;
        const wob = n(p.phase * 1.8 + seedPhase + u * 2.4) * unit * 0.028 * u;
        const xx = x0 + lean * u * u + wob;
        /* fuller through the lower half, so it is a tongue and not a spike */
        const ww = w * Math.pow(1 - u, 0.72) * (1 - u * 0.22);
        left.push([xx - ww, y]);
        right.push([xx + ww, y]);
        const cw = ww * 0.44;
        cl.push([xx - cw, y + (baseY - y) * 0.08]);
        cr.push([xx + cw, y + (baseY - y) * 0.08]);
      }

      poly(ctx, left.concat(right.reverse()), true);
      const g = ctx.createLinearGradient(0, baseY, 0, tipY);
      g.addColorStop(0, alpha(pal.gold, 0.3 * inten));
      g.addColorStop(0.45, alpha(mix(pal.gold, pal.rose, 0.5), 0.17 * inten));
      g.addColorStop(1, alpha(pal.rose, 0));
      ctx.fillStyle = g;
      ctx.fill();

      /* the core: the one bright thing in the plate */
      poly(ctx, cl.concat(cr.reverse()), true);
      const cg = ctx.createLinearGradient(0, baseY, 0, tipY);
      cg.addColorStop(0, alpha(mix(pal.gold, pal.ink, 0.4), 0.5 * inten));
      cg.addColorStop(0.4, alpha(pal.gold, 0.26 * inten));
      cg.addColorStop(1, alpha(pal.gold, 0));
      ctx.fillStyle = cg;
      ctx.fill();
    }
    haze(ctx, cx, baseY - unit * 0.06, unit * 0.4 * (0.4 + inten * 0.6), pal.gold, 0.18 * inten);
    ctx.restore();

    /* what the flame did to the ridge it passed. A house that is being taken
       has a mark on it; a house that is holding does not. */
    if (p.vessel > 0) {
      const over = clamp((roofY - highest) / (s.h * 0.16));
      if (over > 0.01) {
        const mark = over * (1 - cont * 0.7);
        const gw = halfW * (0.3 + over * 0.5);
        const g = ctx.createLinearGradient(cx - gw, 0, cx + gw, 0);
        g.addColorStop(0, alpha(pal.rose, 0));
        g.addColorStop(0.5, alpha(pal.rose, 0.85 * mark));
        g.addColorStop(1, alpha(pal.rose, 0));
        ctx.strokeStyle = g;
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.moveTo(cx - gw, roofY + (gw / halfW) * (eaveY - roofY));
        ctx.lineTo(cx, roofY);
        ctx.lineTo(cx + gw, roofY + (gw / halfW) * (eaveY - roofY));
        ctx.stroke();
        haze(ctx, cx, roofY, unit * 0.22 * mark, pal.rose, 0.4 * mark);
      }
    }

    /* embers: what escapes when the house does not hold. Above the ridge they
       are faded by containment rather than dropped by an if, so the roof stops
       being a cliff edge in the middle of the scroll. */
    const en = Math.round(p.embers * inten);
    const er = r.fork('embers');
    ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < en; i++) {
      const life = (er() + p.phase * 0.12) % 1;
      const rise = life * s.h * (0.35 + (1 - cont) * 0.55);
      const x = cx + er.gauss() * halfW * 0.7 + n(p.phase + i) * unit * 0.06 * (1 - cont);
      const y = baseY - rise;
      let a = (1 - life) * 0.8 * inten;
      if (y < roofY) a *= (1 - cont) * (1 - cont);
      if (a < 0.004) continue;
      ctx.fillStyle = alpha(er() < 0.3 ? pal.rose : pal.gold, a);
      ctx.beginPath();
      ctx.arc(x, y, Math.max(0.6, unit * 0.0035 * (1 - life * 0.6)), 0, TAU);
      ctx.fill();
    }

    ctx.restore();
  },
});
