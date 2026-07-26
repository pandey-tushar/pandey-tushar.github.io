/* Builds the hero posters: the knot as the 3D would draw it at rest.
   Same curve, same camera, same palette, evaluated in node so the browser gets
   a finished image on the first byte instead of a 500KB renderer.

   Two files, matching the two layouts the scene itself switches between: wide
   pushes the knot right of the copy, narrow centres it.

   Run by `npm run build` before vite. Output is deterministic.
   Usage: tsx scripts/poster.mjs */

import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { site } from '@qubit/tokens';
import { fig8, place, project, ramp, rest, restNarrow, widthAt } from '../src/hero/curves.ts';

const SAMPLES = 576;    /* curve resolution before chunking */
const CHUNKS = 72;      /* one <polyline> each: enough for depth order, small enough to ship */

const hex = (h) => [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255];
const toHex = (c) => '#' + c.map((v) => Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).padStart(2, '0')).join('');
const stops = [hex(site.cyan), hex(site.violet), hex(site.magenta)];
const r2 = (n) => Math.round(n * 10) / 10;
const r0 = (n) => Math.round(n);

function poster(W, H, view) {
  /* sample the curve once, keep view depth for sorting and width */
  const pts = [];
  for (let i = 0; i <= SAMPLES; i++) {
    const u = i / SAMPLES;
    const s = project(place(fig8(u * Math.PI * 2), view), W, H, view);
    if (s) pts.push({ u, ...s });
  }

  /* chunk into runs that share an endpoint, so neighbours join without a seam */
  const per = Math.ceil(pts.length / CHUNKS);
  const chunks = [];
  for (let i = 0; i < pts.length - 1; i += per) {
    const run = pts.slice(i, Math.min(i + per + 1, pts.length));
    if (run.length < 2) continue;
    const depth = run.reduce((t, p) => t + p.d, 0) / run.length;
    chunks.push({
      depth,
      u: run[Math.floor(run.length / 2)].u,
      w: widthAt(depth, H, view),
      d: run.map((p) => r0(p.x) + ',' + r0(p.y)).join(' '),
    });
  }
  /* painter's algorithm: far chunks first, so near tube passes occlude */
  chunks.sort((a, b) => b.depth - a.depth);

  /* The tube shader is fresnel driven: base*0.30 through the middle at low
     alpha, base*2.1 at the silhouette. Two concentric strokes reproduce that
     read. Each layer is opaque inside its own group and transparent as a
     whole, so chunks that share an endpoint do not double-darken into beads. */
  const tint = (u, k, add) => toHex(ramp(u, stops).map((v) => v * k + (add || 0)));
  const line = (c, mul, col) =>
    '<polyline points="' + c.d + '" stroke="' + col + '" stroke-width="' + r2(c.w * mul) + '"/>';
  const layer = (mul, k, add) => chunks.map((c) => line(c, mul, tint(c.u, k, add))).join('');

  /* the fbm nebula reads as three broad lobes plus a vignette; a poster does
     not need the noise, it needs the same colour weight in the same places */
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="presentation">
<defs>
<radialGradient id="a" cx="22%" cy="30%" r="68%"><stop offset="0" stop-color="${site.violet}" stop-opacity=".34"/><stop offset="1" stop-color="${site.violet}" stop-opacity="0"/></radialGradient>
<radialGradient id="b" cx="74%" cy="64%" r="60%"><stop offset="0" stop-color="${site.cyan}" stop-opacity=".22"/><stop offset="1" stop-color="${site.cyan}" stop-opacity="0"/></radialGradient>
<radialGradient id="c" cx="58%" cy="12%" r="52%"><stop offset="0" stop-color="${site.magenta}" stop-opacity=".18"/><stop offset="1" stop-color="${site.magenta}" stop-opacity="0"/></radialGradient>
<radialGradient id="v" cx="50%" cy="50%" r="72%"><stop offset=".45" stop-color="${site.ink}" stop-opacity="0"/><stop offset="1" stop-color="${site.ink}" stop-opacity=".82"/></radialGradient>
<filter id="glow" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="9"/></filter>
</defs>
<rect width="${W}" height="${H}" fill="${site.ink}"/>
<rect width="${W}" height="${H}" fill="url(#a)"/><rect width="${W}" height="${H}" fill="url(#b)"/><rect width="${W}" height="${H}" fill="url(#c)"/>
<rect width="${W}" height="${H}" fill="url(#v)"/>
<g fill="none" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)" opacity=".3">${layer(1.7, 1.2)}</g>
<g fill="none" stroke-linecap="round" stroke-linejoin="round" opacity=".78">${layer(1, 1.4, 0.16)}</g>
<g fill="none" stroke-linecap="round" stroke-linejoin="round" opacity=".46">${layer(0.68, 0.32)}</g>
</svg>
`;
  return { svg, chunks: chunks.length };
}

const dir = fileURLToPath(new URL('../public', import.meta.url));
mkdirSync(dir, { recursive: true });

for (const [name, W, H, view] of [
  ['hero-poster.svg', 1600, 900, rest],
  ['hero-poster-narrow.svg', 800, 1400, restNarrow],
]) {
  const { svg, chunks } = poster(W, H, view);
  writeFileSync(dir + '/' + name, svg);
  console.log('poster: ' + name + ' ' + W + 'x' + H + ', ' + chunks + ' chunks, ' + (svg.length / 1024).toFixed(1) + ' KB');
}
