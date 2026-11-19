// Code definitions. Data qubit i sits at [x, y] = [i % d, floor(i / d)].
// Rotated surface code: plaquette (r, c) covers qubits at rows r..r+1, cols c..c+1 (clipped to the grid),
// X type when r + c is even. Bulk checks come first (row-major), then X on the right then left edge,
// Z on the top then bottom edge. For d = 3 this reproduces X_STABS and Z_STABS of ../patch.js in order.

export function repetitionCode(d) {
  const r = [...Array(d).keys()];
  return {
    kind: 'repetition', d, n: d,
    checks: { Z: r.slice(1).map(i => [i - 1, i]) },
    logical: { X: r, Z: [0] },
    coords: r.map(i => [i, 0]),
    checkCoords: { Z: r.slice(1).map(i => [i - 0.5, 0]) },
  };
}

export function surfaceCode(d) {
  if (d < 3 || d % 2 === 0) throw new Error('surfaceCode needs odd d >= 3');
  const checks = { X: [], Z: [] }, checkCoords = { X: [], Z: [] };
  const add = (r, c) => {
    const s = [];
    for (const [i, j] of [[r, c], [r, c + 1], [r + 1, c], [r + 1, c + 1]])
      if (i >= 0 && i < d && j >= 0 && j < d) s.push(i * d + j);
    const t = (r + c) % 2 === 0 ? 'X' : 'Z';
    checks[t].push(s);
    checkCoords[t].push([c + 0.5, r + 0.5]);
  };
  for (let r = 0; r < d - 1; r++) for (let c = 0; c < d - 1; c++) add(r, c);
  for (let r = 0; r < d - 1; r++) if ((r + d - 1) % 2 === 0) add(r, d - 1);
  for (let r = 0; r < d - 1; r++) if ((r - 1) % 2 === 0) add(r, -1);
  for (let c = 0; c < d - 1; c++) if (c % 2 === 0) add(-1, c);
  for (let c = 0; c < d - 1; c++) if ((d - 1 + c) % 2 === 1) add(d - 1, c);
  const r = [...Array(d).keys()];
  return {
    kind: 'surface', d, n: d * d, checks,
    logical: { X: r, Z: r.map(i => i * d) },
    coords: [...Array(d * d).keys()].map(i => [i % d, Math.floor(i / d)]),
    checkCoords,
  };
}

export function makeCode(kind, d) {
  return kind === 'repetition' ? repetitionCode(d) : surfaceCode(d);
}
