// Pure helpers for the threshold lesson: error bars, the crossing of two curves, the Lambda fit, plot scales,
// and the order in which Monte Carlo jobs are run. No DOM, no engine imports.

// Binomial standard error of a failure rate; lo/hi are rate -/+ one stderr clipped to [0, 1].
// With no failures the rate is 0 and upper95 = 3 / shots (the rule of three) bounds it.
export function binomialError(failures, shots) {
  if (!shots) return { rate: null, stderr: null, lo: null, hi: null, upper95: null };
  const rate = failures / shots, stderr = Math.sqrt(rate * (1 - rate) / shots);
  return {
    rate, stderr, lo: Math.max(0, rate - stderr), hi: Math.min(1, rate + stderr),
    upper95: failures === 0 ? 3 / shots : null,
  };
}

// Zeros of a piecewise-linear h over x (here x = ln p), by linear interpolation between neighbours.
function zeros(x, h) {
  const z = [];
  for (let i = 0; i + 1 < x.length; i++) {
    const a = h[i], b = h[i + 1];
    if (a === 0) { if (!z.length || z[z.length - 1] !== x[i]) z.push(x[i]); continue; }
    if (b === 0) { z.push(x[i + 1]); continue; }
    if ((a < 0) !== (b < 0)) z.push(x[i] + (x[i + 1] - x[i]) * a / (a - b));
  }
  return z;
}

// Crossing of the curve of the smaller code (a) and the larger code (b), each [{p, failures, shots}].
// g(p) = ln r_b - ln r_a, interpolated linearly in ln p; sigma_g from the binomial errors of both points.
// The range comes from the zeros of g + sigma and g - sigma: one standard error, statistical only.
// status: 'found'; 'above' (the larger code is better at every p, so any crossing is above the range);
// 'below' (the larger code is worse at every p); 'none' (fewer than two points with failures in both curves).
export function crossing(a, b) {
  const byP = new Map(b.map(r => [r.p, r]));
  const pts = a.map(r => [r, byP.get(r.p)])
    .filter(([u, v]) => v && u.shots && v.shots && u.failures > 0 && v.failures > 0)
    .sort((u, v) => u[0].p - v[0].p);
  if (pts.length < 2) return { status: 'none' };
  const x = [], g = [], s = [];
  for (const [u, v] of pts) {
    const ru = u.failures / u.shots, rv = v.failures / v.shots;
    x.push(Math.log(u.p));
    g.push(Math.log(rv) - Math.log(ru));
    s.push(Math.sqrt((1 - ru) / u.failures + (1 - rv) / v.failures));
  }
  const pMin = pts[0][0].p, pMax = pts[pts.length - 1][0].p;
  const z0 = zeros(x, g);
  if (!z0.length) return { status: g[0] < 0 ? 'above' : 'below', pMin, pMax };
  const zUp = zeros(x, g.map((v, i) => v + s[i])), zDn = zeros(x, g.map((v, i) => v - s[i]));
  const all = [...z0, ...zUp, ...zDn];
  const mid = z0[(z0.length - 1) >> 1];
  return {
    status: 'found', p: Math.exp(mid), multiple: z0.length > 1,
    lo: zUp.length ? Math.exp(Math.min(...all)) : pMin, loOpen: !zUp.length,
    hi: zDn.length ? Math.exp(Math.max(...all)) : pMax, hiOpen: !zDn.length,
    pMin, pMax,
  };
}

// Weighted least squares of ln r against d over points with failures; var(ln r) ~ (1 - r) / failures.
// ln r = intercept + slope d, Lambda = r_d / r_{d+2} = exp(-2 slope); lo/hi from one standard error of the slope.
export function fitLambda(points) {
  const use = points.filter(q => q.shots && q.failures > 0).sort((u, v) => u.d - v.d);
  if (use.length < 2) return null;
  const w = use.map(q => q.failures / (1 - q.failures / q.shots));
  const y = use.map(q => Math.log(q.failures / q.shots));
  const W = w.reduce((t, v) => t + v, 0);
  const xm = use.reduce((t, q, i) => t + w[i] * q.d, 0) / W, ym = y.reduce((t, v, i) => t + w[i] * v, 0) / W;
  let sxx = 0, sxy = 0;
  use.forEach((q, i) => { sxx += w[i] * (q.d - xm) ** 2; sxy += w[i] * (q.d - xm) * (y[i] - ym); });
  const slope = sxy / sxx, se = 1 / Math.sqrt(sxx);
  return {
    lambda: Math.exp(-2 * slope), lo: Math.exp(-2 * (slope + se)), hi: Math.exp(-2 * (slope - se)),
    slope, intercept: ym - slope * xm, used: use.map(q => q.d),
  };
}

export function linScale([d0, d1], [r0, r1]) {
  const f = v => r0 + (v - d0) * (r1 - r0) / (d1 - d0);
  f.invert = r => d0 + (r - r0) * (d1 - d0) / (r1 - r0);
  return f;
}

export function logScale([d0, d1], [r0, r1]) {
  const l = linScale([Math.log10(d0), Math.log10(d1)], [r0, r1]);
  const f = v => l(Math.log10(v));
  f.invert = r => 10 ** l.invert(r);
  return f;
}

const tidy = v => Number(v.toPrecision(12));

// Decades inside [a, b] as major ticks, 2 and 5 times a decade as minor ticks.
export function logTicks(a, b) {
  const major = [], minor = [];
  for (let k = Math.floor(Math.log10(a)); k <= Math.ceil(Math.log10(b)); k++) {
    const t = tidy(10 ** k);
    if (t >= a && t <= b) major.push(t);
    for (const m of [2, 5]) { const v = tidy(m * 10 ** k); if (v >= a && v <= b) minor.push(v); }
  }
  return { major, minor };
}

export function linTicks(a, b, n = 5) {
  const raw = (b - a) / n, mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw * 0.999);
  const out = [];
  for (let v = Math.ceil(a / step) * step; v <= b + step * 1e-9; v += step) out.push(tidy(v));
  return out;
}

// n points evenly spaced in ln p from a to b, each rounded to 3 significant digits.
export function logSpace(a, b, n) {
  if (n === 1) return [a];
  return [...Array(n).keys()].map(i => Number((a * (b / a) ** (i / (n - 1))).toPrecision(3)));
}

// Jobs for every (p, d), split into passes: pass k gives each point floor(frac_k * shots), the last pass the rest.
// A short first pass puts every point on the plot early; later passes shrink the error bars. Within a pass the
// order is p ascending, then d, so the plot fills left to right with all distances together. Seeds are distinct.
export function planQueue({ ps, ds, shots, passes = [1], seed = 1 }) {
  const jobs = [];
  let s = seed;
  passes.forEach((frac, k) => {
    for (const p of ps) for (const d of ds) {
      const before = passes.slice(0, k).reduce((t, f) => t + Math.floor(f * shots), 0);
      const n = k === passes.length - 1 ? shots - before : Math.floor(frac * shots);
      if (n > 0) jobs.push({ d, p, shots: n, seed: s++, pass: k });
    }
  });
  return jobs;
}
