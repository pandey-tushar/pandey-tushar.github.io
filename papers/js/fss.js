// Finite-size scaling collapse for papers/bb-erasure-baselines.html, after the paper's ansatz
// WER(p, N) ~ f[(p - p*_inf) N^(1/nu)] with f a polynomial fitted by least squares. Pure; tests in
// _studio/tools/tests/papers/fss.test.mjs.

export const scaled = (p, N, pStar, nu) => (p - pStar) * N ** (1 / nu);

// Weighted least-squares polynomial of the given degree. x is mapped onto [-1, 1] first so the normal
// equations stay well conditioned at any scale; the fitted curve and its residual do not depend on that map.
export function fitPoly(xs, ys, degree, ws = xs.map(() => 1)) {
  const lo = Math.min(...xs), hi = Math.max(...xs), mid = (lo + hi) / 2, half = (hi - lo) / 2 || 1;
  const t = x => (x - mid) / half, n = degree + 1;
  const A = Array.from({ length: n }, () => new Array(n + 1).fill(0));
  xs.forEach((x, k) => {
    const pw = Array.from({ length: n }, (_, i) => t(x) ** i);
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) A[i][j] += ws[k] * pw[i] * pw[j];
      A[i][n] += ws[k] * pw[i] * ys[k];
    }
  });
  for (let c = 0; c < n; c++) {                                   // Gaussian elimination, partial pivoting
    let piv = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(A[r][c]) > Math.abs(A[piv][c])) piv = r;
    [A[c], A[piv]] = [A[piv], A[c]];
    for (let r = 0; r < n; r++) if (r !== c) {
      const f = A[r][c] / A[c][c];
      for (let j = c; j <= n; j++) A[r][j] -= f * A[c][j];
    }
  }
  const coef = A.map((row, i) => row[n] / row[i]);
  const evaluate = x => coef.reduce((s, c, i) => s + c * t(x) ** i, 0);
  const rss = xs.reduce((s, x, k) => s + ws[k] * (ys[k] - evaluate(x)) ** 2, 0);
  return { evaluate, rss };
}

// sizes: [{N, center, points: [{p, fails, shots, fit_count}]}]. Keeps the points with |p - center| <= window,
// rescales them and fits the polynomial. Each point is weighted by how often the paper's fit read it.
export function collapse(sizes, pStar, nu, window, degree = 3) {
  const points = sizes.flatMap(s => s.points.filter(q => Math.abs(q.p - s.center) <= window)
    .map(q => ({ N: s.N, p: q.p, x: scaled(q.p, s.N, pStar, nu), y: q.fails / q.shots, w: q.fit_count ?? 1 })));
  const fit = fitPoly(points.map(q => q.x), points.map(q => q.y), degree, points.map(q => q.w));
  return { points, fit, rss: fit.rss };
}

// 95% Wilson score interval for fails out of shots.
export function wilson(fails, shots, z = 1.96) {
  const r = fails / shots, d = 1 + z * z / shots;
  const c = (r + z * z / (2 * shots)) / d, h = z * Math.sqrt(r * (1 - r) / shots + z * z / (4 * shots * shots)) / d;
  return [Math.max(0, c - h), Math.min(1, c + h)];
}
