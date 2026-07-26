/* Lattice. Entanglement, and the cover art.

   Canto 2 ends on monogamy: "The more completely two qubits belong to each
   other, the less either can belong to a third. A qubit perfectly entangled
   with one partner has nothing left over to share."

   That sentence is the highlight parameter. As it rises one bond goes gold and
   a shared envelope closes around the pair, and every other edge touching
   either node is faded by exactly the same amount. The image cannot be read
   any other way, which is the point: the mapping between text and picture runs
   in both directions. */

import { alpha, metrics, type Surface } from '../surface.js';
import { haze, starDot } from '../forms.js';
import { clamp, ease, rng, span, TAU, type Seed } from '../rng.js';
import { defineMotif } from '../types.js';

export type LatticeParams = {
  nodes: number;
  /** 0 is an organic scatter, 1 is a ruled grid */
  order: number;
  coupling: number;
  /** neighbour radius as a multiple of the grid spacing */
  reach: number;
  /** fraction of edges cut */
  breaks: number;
  /** 0..1 monogamy: one bond takes everything the pair had to give */
  highlight: number;
  envelope: number;
  glow: number;
  spread: number;
  nodeScale: number;
  /** 0..1 one correlated strike across a swath of the field, as against the
      scattered independent faults `breaks` draws. Canto 12 turns on exactly
      this distinction: the pattern absorbs the scatter and has no answer ready
      for a blow that lands everywhere at once. */
  burst: number;
  /** where the swath crosses, 0..1 of the plate */
  burstAt: number;
  /** half width of the swath, in grid spacings */
  burstWidth: number;
}

interface Strike { nx: number; ny: number; c: number; half: number }

/** The swath, taken from the seed rather than from a draw, so it is the same
    line at every progress and adding it moves no other stream in the motif. */
function strikeOf(seed: Seed, p: LatticeParams, s: Surface, spacing: number): Strike {
  const { cx, cy } = metrics(s);
  const r = rng(String(seed) + '/lattice/burst');
  const a = r.range(0, TAU);
  const nx = Math.cos(a);
  const ny = Math.sin(a);
  /* burstAt slides the line across the plate along its own normal */
  const reach = Math.hypot(s.w, s.h) * 0.42;
  const c = nx * cx + ny * cy + (clamp(p.burstAt) - 0.5) * 2 * reach;
  return { nx, ny, c, half: spacing * Math.max(0.2, p.burstWidth) };
}

interface Node { x: number; y: number; m: number }
interface Edge { a: number; b: number; d: number; roll: number }

function build(seed: Seed, p: LatticeParams, s: Surface): { nodes: Node[]; edges: Edge[]; spacing: number } {
  const { cx, cy } = metrics(s);
  const r = rng(String(seed) + '/lattice');
  const w = s.w * p.spread;
  const h = s.h * p.spread;
  const aspect = w / h;
  const rows = Math.max(2, Math.round(Math.sqrt(p.nodes / aspect)));
  const cols = Math.max(2, Math.round(p.nodes / rows));
  const sx = w / cols;
  const sy = h / rows;
  const spacing = Math.min(sx, sy);
  const wobble = (1 - clamp(p.order)) * 0.62;

  const nodes: Node[] = [];
  for (let j = 0; j < rows; j++) {
    for (let i = 0; i < cols; i++) {
      const gx = cx - w / 2 + sx * (i + 0.5);
      const gy = cy - h / 2 + sy * (j + 0.5);
      nodes.push({
        x: gx + r.gauss() * sx * wobble,
        y: gy + r.gauss() * sy * wobble,
        m: r(),
      });
    }
  }

  const max = spacing * p.reach;
  const edges: Edge[] = [];
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const d = Math.hypot(nodes[i]!.x - nodes[j]!.x, nodes[i]!.y - nodes[j]!.y);
      if (d <= max) edges.push({ a: i, b: j, d, roll: r() });
    }
  }
  return { nodes, edges, spacing };
}

/** The bond that wins: an ordinary length edge near the middle of the plate.
    Chosen from geometry, not from a random draw, so it never jumps between
    frames, and not the shortest, or the pair is too small to read. */
function chosen(nodes: Node[], edges: Edge[], s: Surface, spacing: number): number {
  const { cx, cy, unit } = metrics(s);
  let best = -1;
  let score = Infinity;
  for (let i = 0; i < edges.length; i++) {
    const e = edges[i]!;
    const mx = (nodes[e.a]!.x + nodes[e.b]!.x) / 2;
    const my = (nodes[e.a]!.y + nodes[e.b]!.y) / 2;
    const v = Math.hypot(mx - cx, my - cy) / unit + (Math.abs(e.d - spacing * 1.15) / unit) * 0.8;
    if (v < score) { score = v; best = i; }
  }
  return best;
}

export const lattice = defineMotif<LatticeParams>({
  id: 'lattice',
  signature: 0.62,
  defaults: {
    nodes: 54,
    order: 0.55,
    coupling: 1,
    reach: 1.5,
    breaks: 0,
    highlight: 0,
    envelope: 1,
    glow: 1,
    spread: 0.82,
    nodeScale: 1,
    burst: 0,
    burstAt: 0.5,
    burstWidth: 0.9,
  },
  curve: (p) => ({
    coupling: ease(span(p, 0, 0.28)),
    highlight: ease(span(p, 0.34, 0.82)),
    breaks: ease(span(p, 0.6, 1)) * 0.42,
  }),

  draw(s: Surface, seed: Seed, p: LatticeParams) {
    const { unit } = metrics(s);
    const ctx = s.ctx;
    const pal = s.palette;
    const { nodes, edges, spacing } = build(seed, p, s);
    const pick = chosen(nodes, edges, s, spacing);
    const hi = clamp(p.highlight);
    const cpl = clamp(p.coupling);
    const maxd = spacing * p.reach;
    const bst = clamp(p.burst);

    ctx.save();
    ctx.lineCap = 'round';

    const A = pick >= 0 ? edges[pick]!.a : -1;
    const B = pick >= 0 ? edges[pick]!.b : -1;

    /* everything the strike touched, decided once for the whole frame */
    const struck = new Uint8Array(nodes.length);
    let strike: Strike | null = null;
    if (bst > 0.004) {
      strike = strikeOf(seed, p, s, spacing);
      const reach = strike.half * (0.35 + bst * 1.25);
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i]!;
        if (Math.abs(strike.nx * n.x + strike.ny * n.y - strike.c) <= reach) struck[i] = 1;
      }
    }

    for (let i = 0; i < edges.length; i++) {
      if (i === pick) continue;
      const e = edges[i]!;
      const na = nodes[e.a]!;
      const nb = nodes[e.b]!;
      /* a short edge is a strong coupling, but even the long ones have to be
         legible or the web reads as loose dust */
      const near = 0.42 + 0.58 * (1 - e.d / maxd);
      /* every edge touching the bonded pair loses exactly what the bond gains */
      const touched = e.a === A || e.b === A || e.a === B || e.b === B;
      const starve = touched ? 1 - hi * 0.94 : 1 - hi * 0.34;
      /* the scatter the code was designed for, and the swath it was not */
      const hit = struck[e.a] === 1 || struck[e.b] === 1;
      const broken = e.roll < clamp(p.breaks) || hit;
      const base = cpl * near * starve * (hit ? 1 - bst * 0.72 : 1);
      if (base < 0.012) continue;

      if (broken) {
        const cut = 0.34;
        ctx.strokeStyle = alpha(pal.dim, base * 0.5);
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(na.x, na.y);
        ctx.lineTo(na.x + (nb.x - na.x) * cut, na.y + (nb.y - na.y) * cut);
        ctx.moveTo(nb.x, nb.y);
        ctx.lineTo(nb.x + (na.x - nb.x) * cut, nb.y + (na.y - nb.y) * cut);
        ctx.stroke();
        ctx.fillStyle = alpha(pal.rose, base * 0.5);
        ctx.beginPath();
        ctx.arc((na.x + nb.x) / 2, (na.y + nb.y) / 2, 1.4, 0, TAU);
        ctx.fill();
      } else {
        ctx.strokeStyle = alpha(pal.cyan, base * 0.85);
        ctx.lineWidth = 0.55 + near * 1.2 * cpl;
        ctx.beginPath();
        ctx.moveTo(na.x, na.y);
        ctx.lineTo(nb.x, nb.y);
        ctx.stroke();
      }
    }

    /* the bond */
    if (pick >= 0 && hi > 0.01) {
      const na = nodes[A]!;
      const nb = nodes[B]!;
      const mx = (na.x + nb.x) / 2;
      const my = (na.y + nb.y) / 2;

      if (p.envelope > 0) {
        /* one state, shared, belonging to the pair and to neither half alone */
        const ang = Math.atan2(nb.y - na.y, nb.x - na.x);
        const half = Math.hypot(nb.x - na.x, nb.y - na.y) / 2 + spacing * 0.6;
        const minor = spacing * (0.55 + 0.18 * hi);
        ctx.save();
        ctx.translate(mx, my);
        ctx.rotate(ang);
        ctx.beginPath();
        ctx.ellipse(0, 0, half, minor, 0, 0, TAU);
        ctx.setLineDash([6, 5]);
        ctx.strokeStyle = alpha(pal.gold, 0.5 * hi * p.envelope);
        ctx.lineWidth = 1.1;
        ctx.stroke();
        ctx.setLineDash([]);
        const g = ctx.createRadialGradient(0, 0, 0, 0, 0, half);
        g.addColorStop(0, alpha(pal.gold, 0.1 * hi * p.envelope));
        g.addColorStop(1, alpha(pal.gold, 0));
        ctx.fillStyle = g;
        ctx.fill();
        ctx.restore();
      }

      ctx.strokeStyle = alpha(pal.gold, 0.4 + 0.55 * hi);
      ctx.lineWidth = 1 + 3.4 * hi;
      ctx.beginPath();
      ctx.moveTo(na.x, na.y);
      ctx.lineTo(nb.x, nb.y);
      ctx.stroke();
      if (p.glow > 0) haze(ctx, mx, my, spacing * 0.95 * p.glow, pal.gold, 0.22 * hi * p.glow);
    }

    /* the track of the strike, laid over the field it crossed. One event, one
       line, and every node on it taken at the same instant. */
    if (strike) {
      const { cx, cy } = metrics(s);
      const reach = Math.hypot(s.w, s.h);
      const px = strike.c * strike.nx;
      const py = strike.c * strike.ny;
      const tx = -strike.ny;
      const ty = strike.nx;
      const g = ctx.createLinearGradient(
        px - tx * reach, py - ty * reach, px + tx * reach, py + ty * reach,
      );
      g.addColorStop(0, alpha(pal.rose, 0));
      g.addColorStop(0.5, alpha(pal.rose, 0.5 * bst));
      g.addColorStop(1, alpha(pal.rose, 0));
      ctx.strokeStyle = g;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(px - tx * reach, py - ty * reach);
      ctx.lineTo(px + tx * reach, py + ty * reach);
      ctx.stroke();
      haze(ctx, cx, cy, Math.min(s.w, s.h) * 0.5, pal.rose, 0.06 * bst);
    }

    /* nodes */
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i]!;
      const bonded = i === A || i === B;
      const hit = struck[i] === 1;
      const rad = unit * 0.0042 * p.nodeScale * (bonded ? 2 + hi * 1.2 : 1 + n.m * 0.7);
      if (hit) {
        /* struck nodes are marked, not merely dimmed: a fault at a known
           address is the one thing the swath does not leave behind */
        const k = rad * (2.1 + bst);
        ctx.strokeStyle = alpha(pal.rose, 0.35 + 0.5 * bst);
        ctx.lineWidth = 1.1;
        ctx.beginPath();
        ctx.moveTo(n.x - k, n.y - k);
        ctx.lineTo(n.x + k, n.y + k);
        ctx.moveTo(n.x + k, n.y - k);
        ctx.lineTo(n.x - k, n.y + k);
        ctx.stroke();
        continue;
      }
      starDot(ctx, n.x, n.y, rad, bonded ? pal.gold : pal.cyan, {
        alpha: bonded ? 1 : 0.34 + n.m * 0.4,
        glow: bonded ? p.glow * (0.4 + hi) : 0,
        ring: bonded || n.m > 0.72,
      });
    }

    ctx.restore();
  },
});
