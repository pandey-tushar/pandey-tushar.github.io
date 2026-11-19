// Shared SVG plotting helpers for the paper companion pages: scales, ticks, markers and an element maker.
// Pure except el(), which needs a document. Tests: _studio/tools/tests/papers/fss.test.mjs.
const SVGNS = 'http://www.w3.org/2000/svg';

export function el(tag, attrs, parent, text) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (text != null) e.textContent = text;
  if (parent) parent.appendChild(e);
  return e;
}

export function linScale([d0, d1], [r0, r1]) {
  return v => r0 + (v - d0) / (d1 - d0) * (r1 - r0);
}

export function logScale([d0, d1], [r0, r1]) {
  const a = Math.log10(d0), b = Math.log10(d1);
  return v => r0 + (Math.log10(v) - a) / (b - a) * (r1 - r0);
}

// About `count` ticks inside [a, b], at a step of 1, 2 or 5 times a power of ten.
export function niceTicks(a, b, count = 5) {
  const raw = (b - a) / Math.max(1, count), mag = 10 ** Math.floor(Math.log10(raw));
  const m = raw / mag, step = (m < 1.5 ? 1 : m < 3 ? 2 : m < 7 ? 5 : 10) * mag;
  const out = [];
  for (let v = Math.ceil(a / step - 1e-9) * step; v <= b + step * 1e-9; v += step) out.push(Number(v.toPrecision(12)));
  return out;
}

// The powers of ten in [a, b].
export function logTicks(a, b) {
  const out = [];
  for (let k = Math.ceil(Math.log10(a) - 1e-9); k <= Math.floor(Math.log10(b) + 1e-9); k++) out.push(Number((10 ** k).toPrecision(12)));
  return out;
}

// Marker outlines, so series differ by shape as well as by colour.
export const SHAPES = ['circle', 'square', 'triangle', 'diamond', 'down'];
export function markerPath(shape, x, y, r) {
  switch (shape) {
    case 'square': { const s = r * 0.88; return `M${x - s} ${y - s}h${2 * s}v${2 * s}h${-2 * s}Z`; }
    case 'triangle': return `M${x} ${y - r * 1.2}L${x + r * 1.1} ${y + r * 0.75}L${x - r * 1.1} ${y + r * 0.75}Z`;
    case 'down': return `M${x} ${y + r * 1.2}L${x + r * 1.1} ${y - r * 0.75}L${x - r * 1.1} ${y - r * 0.75}Z`;
    case 'diamond': return `M${x} ${y - r * 1.3}L${x + r * 1.05} ${y}L${x} ${y + r * 1.3}L${x - r * 1.05} ${y}Z`;
    default: return `M${x - r} ${y}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`;
  }
}
