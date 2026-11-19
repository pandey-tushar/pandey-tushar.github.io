// Decoders. buildGraph(code, type) is the decoding graph for errors of Pauli `type` ('X' errors are seen by Z checks,
// 'Z' errors by X checks). With rounds = R the graph is space-time: R layers of detectors (layer t, check c is node
// t * m + c), data errors in every layer, a noisy measurement in layers 0..R-2 and a perfect one in layer R-1.
// R = 1 is code capacity. Each boundary edge gets its own boundary node (node index >= nDet).

const SYN = { X: 'Z', Z: 'X' };

export function majorityDecode(code, synZ) {
  const x = new Uint8Array(code.n);
  for (let i = 1; i < code.n; i++) x[i] = x[i - 1] ^ synZ[i - 1];
  let w = 0;
  for (const b of x) w += b;
  if (2 * w > code.n) for (let i = 0; i < code.n; i++) x[i] ^= 1;
  return x;
}

export function buildGraph(code, type, rounds = 1) {
  const checks = code.checks[SYN[type]];
  if (!checks) throw new Error(`${code.kind} code has no ${SYN[type]} checks`);
  const m = checks.length, nDet = rounds * m, of = Array.from({ length: code.n }, () => []);
  checks.forEach((s, c) => { for (const q of s) of[q].push(c); });
  const nodes = [], edges = [];
  for (let t = 0; t < rounds; t++) for (let c = 0; c < m; c++) nodes.push({ check: c, t, boundary: false });
  for (let t = 0; t < rounds; t++) for (let q = 0; q < code.n; q++) {
    const [a, b] = of[q];
    if (b !== undefined) edges.push([t * m + a, t * m + b, q]);
    else { nodes.push({ check: a, t, boundary: true }); edges.push([t * m + a, nodes.length - 1, q]); }
  }
  for (let t = 0; t + 1 < rounds; t++) for (let c = 0; c < m; c++) edges.push([t * m + c, (t + 1) * m + c, -1]);
  const N = nodes.length, E = edges.length;
  const eu = new Int32Array(E), ev = new Int32Array(E), eq = new Int32Array(E), start = new Int32Array(N + 1);
  edges.forEach(([u, v, q], e) => { eu[e] = u; ev[e] = v; eq[e] = q; start[u + 1]++; start[v + 1]++; });
  for (let v = 0; v < N; v++) start[v + 1] += start[v];
  const adj = new Int32Array(2 * E), fill = start.slice(0, N);
  for (let e = 0; e < E; e++) { adj[fill[eu[e]]++] = e; adj[fill[ev[e]]++] = e; }
  const isB = new Uint8Array(N);
  for (let v = nDet; v < N; v++) isB[v] = 1;
  return { type, rounds, n: code.n, m, nDet, N, nodes, edges, eu, ev, eq, start, adj, isB };
}

function scratch(g) {
  const { N } = g, parent = new Int32Array(N), size = new Int32Array(N).fill(1);
  for (let v = 0; v < N; v++) parent[v] = v;
  return {
    parent, size, odd: new Uint8Array(N), bnd: g.isB.slice(), lists: new Array(N).fill(null),
    support: new Uint8Array(g.edges.length), inT: new Uint8Array(N), stamp: new Int32Array(N),
    pe: new Int32Array(N), def: new Uint8Array(N), seen: new Uint8Array(N), clock: 0,
  };
}

// Union-find decoder (Delfosse-Nickerson): odd clusters grow by half-edges, smallest boundary first,
// clusters touching a boundary node are neutral; then each cluster's spanning forest is peeled.
export function decode(g, defects, opts = {}) {
  const S = g.scratch ||= scratch(g);
  const { parent, size, odd, bnd, lists, support, inT, stamp, pe, def, seen } = S;
  const { eu, ev, eq, start, adj, isB } = g;
  const touched = [], tEdges = [], dnodes = [], steps = opts.trace ? [] : null;
  const find = v => { while (parent[v] !== v) { parent[v] = parent[parent[v]]; v = parent[v]; } return v; };
  const touch = v => { if (!inT[v]) { inT[v] = 1; touched.push(v); lists[v] = [v]; } };
  for (let v = 0; v < g.nDet; v++) if (defects[v]) { touch(v); odd[v] = 1; def[v] = 1; dnodes.push(v); }

  for (;;) {
    const st = ++S.clock, grow = [];
    let min = Infinity;
    for (const d of dnodes) {
      const r = find(d);
      if (stamp[r] === st || !odd[r] || bnd[r]) continue;
      stamp[r] = st;
      const keep = [];
      for (const v of lists[r]) {
        for (let k = start[v]; k < start[v + 1]; k++) if (support[adj[k]] < 2) { keep.push(v); break; }
      }
      lists[r] = keep;
      grow.push(r);
      if (keep.length < min) min = keep.length;
    }
    if (!grow.length) break;
    if (min === 0) throw new Error('odd cluster cannot grow: graph component without boundary');
    const growing = grow.filter(r => lists[r].length === min), fused = [];
    for (const r of growing) {
      for (const v of lists[r]) for (let k = start[v]; k < start[v + 1]; k++) {
        const e = adj[k];
        if (support[e] === 2) continue;
        if (support[e] === 0) tEdges.push(e);
        if (++support[e] === 2) fused.push(e);
      }
    }
    for (const e of fused) {
      touch(eu[e]); touch(ev[e]);
      let a = find(eu[e]), b = find(ev[e]);
      if (a === b) continue;
      if (size[a] < size[b]) [a, b] = [b, a];
      parent[b] = a; size[a] += size[b]; odd[a] ^= odd[b]; bnd[a] |= bnd[b];
      for (const v of lists[b]) lists[a].push(v);
      lists[b] = null;
    }
    if (steps) {
      const cluster = new Int32Array(g.N).fill(-1);
      for (const v of touched) cluster[v] = find(v);
      steps.push({ grown: growing, cluster, support: support.slice() });
    }
  }

  // peel: spanning forest over fully grown edges, rooted at a boundary node when the cluster has one
  const order = [];
  const bfs = root => {
    seen[root] = 1; pe[root] = -1; order.push(root);
    for (let i = order.length - 1; i < order.length; i++) {
      const v = order[i];
      for (let k = start[v]; k < start[v + 1]; k++) {
        const e = adj[k];
        if (support[e] !== 2) continue;
        const w = eu[e] === v ? ev[e] : eu[e];
        if (!seen[w]) { seen[w] = 1; pe[w] = e; order.push(w); }
      }
    }
  };
  for (const v of touched) if (isB[v] && !seen[v]) bfs(v);
  for (const v of dnodes) if (!seen[v]) bfs(v);
  const correction = new Uint8Array(g.n);
  for (let i = order.length - 1; i >= 0; i--) {
    const v = order[i], e = pe[v];
    if (e < 0 || !def[v]) continue;
    def[v] = 0;
    def[eu[e] === v ? ev[e] : eu[e]] ^= 1;
    if (eq[e] >= 0) correction[eq[e]] ^= 1;
  }

  for (const v of touched) { parent[v] = v; size[v] = 1; odd[v] = 0; bnd[v] = isB[v]; lists[v] = null; inT[v] = 0; def[v] = 0; seen[v] = 0; }
  for (const v of order) { seen[v] = 0; def[v] = 0; }
  for (const e of tEdges) support[e] = 0;
  return steps ? { correction, steps } : correction;
}

export function logicalFailure(code, err, correction) {
  let x = 0, z = 0;
  for (const i of code.logical.Z) x ^= err.x[i] ^ (correction.x ? correction.x[i] : 0);
  for (const i of code.logical.X) z ^= err.z[i] ^ (correction.z ? correction.z[i] : 0);
  return { x: x === 1, z: z === 1 };
}
