// Pure figure logic for papers/lifted-surgery.html: group names, gains as fractions, filters, the spread of codes
// that share a point, keyboard steps. Tests: _studio/tools/tests/papers/lifted-surgery-logic.test.mjs.

// Group keys of the liftsurg result files: 'S3xZ6', 'Z9x|8Z12' (Z9 semidirect Z12, y x y^-1 = x^8), 'SL23xZ5'.
const BASES = { S3: ['S', '3'], D4: ['D', '4'], D5: ['D', '5'], A4: ['A', '4'], S4: ['S', '4'] };
const ORDER = ['S3', 'D4', 'D5', 'Z9⋊Z12', 'A4', 'S4', 'SL(2,3)'];

export function parseGroup(s) {
  let m = /^Z9x\|(\d+)Z12$/.exec(s);
  if (m) return { family: 'Z9⋊Z12', label: `Z9 ⋊ Z12 (r = ${m[1]})`, html: `Z<sub>9</sub>&nbsp;&#8906;<sub>${m[1]}</sub>&nbsp;Z<sub>12</sub>` };
  m = /^(S3|D4|D5|A4|S4|SL23)xZ(\d+)$/.exec(s);
  if (!m) throw new Error(`unknown group ${s}`);
  const z = `&nbsp;&times;&nbsp;Z<sub>${m[2]}</sub>`;
  if (m[1] === 'SL23') return { family: 'SL(2,3)', label: `SL(2,3) × Z${m[2]}`, html: 'SL(2,3)' + z };
  const [l, i] = BASES[m[1]];
  return { family: m[1], label: `${m[1]} × Z${m[2]}`, html: `${l}<sub>${i}</sub>` + z };
}

export const families = codes => ORDER.filter(f => codes.some(c => parseGroup(c.group).family === f));

const gcd = (a, b) => (b ? gcd(b, a % b) : a);
export function ratio(mu, base) {
  const g = gcd(mu, base), p = mu / g, q = base / g;
  return q === 1 ? String(p) : `${p}/${q}`;
}

// The paper's code-level gain: max over orbits of mu_E over max over orbits of the Abelian baseline.
export function codeGain(orbits) {
  const mu = Math.max(...orbits.map(o => o.mu)), base = Math.max(...orbits.map(o => o.base));
  return { mu, base, text: ratio(mu, base) };
}

// How many examined orbits reach the best gain.
export function bestOrbits(orbits) {
  const g = Math.max(...orbits.map(o => o.gamma));
  return { best: orbits.filter(o => o.gamma === g).length, examined: orbits.length };
}

// gain: 'all', '2' (Table 1) or '3' (Table 2); family: 'all' or a family of parseGroup.
export const visible = (codes, { gain, family }) => codes.filter(c =>
  (gain === 'all' || (gain === '2' ? c.table === 1 : c.table === 2)) && (family === 'all' || parseGroup(c.group).family === family));

export const sortCodes = codes => [...codes].sort((a, b) => a.n - b.n || a.d - b.d || a.table - b.table || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));

// Codes with equal n and d sit side by side: slot offsets -(k-1)/2 .. (k-1)/2 in input order.
export function slots(codes) {
  const at = new Map();
  for (const c of codes) { const k = `${c.n},${c.d}`; if (!at.has(k)) at.set(k, []); at.get(k).push(c.id); }
  const out = new Map();
  for (const ids of at.values()) ids.forEach((id, i) => out.set(id, i - (ids.length - 1) / 2));
  return out;
}

export function move(i, key, len) {
  switch (key) {
    case 'ArrowRight': case 'ArrowDown': return Math.min(len - 1, i + 1);
    case 'ArrowLeft': case 'ArrowUp': return Math.max(0, i - 1);
    case 'Home': return 0;
    case 'End': return len - 1;
    default: return null;
  }
}
