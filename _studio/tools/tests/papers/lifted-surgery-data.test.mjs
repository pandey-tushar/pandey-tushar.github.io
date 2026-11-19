// papers/data/lifted-surgery.json, written by _studio/tools/papers/extract_lifted-surgery.py, holds exactly the
// values of the source repository's result files. The comparison against the source needs a clone of
// https://github.com/pandey-tushar/liftsurg: set LIFTSURG_CLONE to its path. Without a clone those tests skip.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

const DATA = JSON.parse(readFileSync(new URL('../../../../papers/data/lifted-surgery.json', import.meta.url), 'utf8'));
const CLONE = process.env.LIFTSURG_CLONE
  || 'C:\\Users\\thetu\\AppData\\Local\\Temp\\claude\\04561455ac0ac633\\f7dc18bb-cd48-4a03-89d4-ec2f824b181f\\scratchpad\\src\\liftsurg';
const HAVE = existsSync(path.join(CLONE, 'results'));
const SKIP = HAVE ? false : `no liftsurg clone at ${CLONE}; set LIFTSURG_CLONE to compare against the source files`;
const src = f => path.join(CLONE, ...f.split('/'));
const jsonl = f => readFileSync(src(f), 'utf8').split(/\r?\n/).filter(Boolean).map(l => JSON.parse(l));
const text = f => readFileSync(src(f), 'utf8');
const T1 = DATA.certified.filter(c => c.table === 1), T2 = DATA.certified.filter(c => c.table === 2);
const pick = (o, ks) => Object.fromEntries(ks.map(k => [k, o[k]]));

test('required fields exist', () => {
  for (const k of ['paper', 'source', 'certified', 'candidates', 'search']) assert.ok(k in DATA, k);
  for (const k of ['repository', 'commit', 'extracted', 'files']) assert.ok(k in DATA.source, `source.${k}`);
  assert.match(DATA.source.commit, /^[0-9a-f]{40}$/);
  assert.match(DATA.source.extracted, /^\d{4}-\d\d-\d\d$/);
  assert.equal(DATA.paper.arxiv, '2610.05307');
  assert.equal(DATA.source.repository, 'https://github.com/pandey-tushar/liftsurg');
  for (const c of DATA.certified) {
    for (const k of ['id', 'table', 'group', 'n', 'k', 'w', 'd', 'd_exact', 'E_order', 'rigid', 'mu', 'base', 'orbits', 'src'])
      assert.ok(k in c, `${c.id}.${k}`);
    assert.ok(c.src.length >= 1 && c.src.every(f => DATA.source.files.includes(f)), `${c.id} sources listed`);
  }
  for (const c of T2) for (const k of ['index_Amax', 'cover', 'base_order']) assert.ok(k in c, `${c.id}.${k}`);
  for (const c of DATA.candidates) for (const k of ['group', 'n', 'k', 'w', 'd_est', 'mu', 'base', 'base_order']) assert.ok(k in c, k);
  assert.equal(new Set(DATA.certified.map(c => c.id)).size, DATA.certified.length, 'ids unique');
});

test('no value is NaN or infinite', () => {
  const walk = (v, at) => {
    if (typeof v === 'number') assert.ok(Number.isFinite(v), at);
    else if (v && typeof v === 'object') for (const [k, x] of Object.entries(v)) walk(x, `${at}.${k}`);
  };
  walk(DATA, 'data');
});

test('the counts the paper states: 11 gain-two codes, 16 gain-three codes, 204 rigid gain-two candidates', () => {
  assert.equal(T1.length, 11);
  assert.equal(T2.length, 16);
  assert.equal(DATA.candidates.length, 204);
  assert.deepEqual(pick(DATA.search, ['codes', 'rigid', 'gain_two', 'rigid_gain_two']),
    { codes: 25465, rigid: 22962, gain_two: 254, rigid_gain_two: 204 });
  for (const c of T1) assert.equal(c.mu, 2 * c.base, `${c.id} gain two`);
  for (const c of T2) assert.ok(c.mu >= 3 * c.base, `${c.id} gain at least three`);
  assert.equal(T1.filter(c => !c.rigid).length, 1);
  assert.ok(T2.every(c => c.rigid));
});

test('the commit is the clone HEAD', { skip: SKIP }, () => {
  assert.equal(DATA.source.commit, execFileSync('git', ['-C', CLONE, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim());
});

test('gain-three rows equal the certified records of verify_gain3.jsonl', { skip: SKIP }, () => {
  const last = new Map();
  for (const r of jsonl('results/verify_gain3.jsonl')) if (r.fully_certified) last.set(r.key, r);
  assert.deepEqual(new Set(T2.map(c => c.key)), new Set(last.keys()));
  for (const c of T2) {
    const r = last.get(c.key);
    assert.deepEqual(pick(c, ['group', 'n', 'k', 'w', 'd', 'dX', 'dZ', 'E_order', 'rigid', 'mu', 'base', 'base_order', 'index_Amax', 'cover']),
      { group: r.group, n: r.n, k: r.k, w: r.w, d: r.d_exact, dX: r.dX_exact, dZ: r.dZ_exact, E_order: r.E_order, rigid: r.rigid,
        mu: r.mu_E, base: r.baseline, base_order: r.baseline_order, index_Amax: r.index_E_Amax, cover: r.cover_min_best }, c.id);
    assert.equal(c.d_exact, true);
    assert.deepEqual(c.orbits.list, r.per_orbit_Z.map(o => ({ orbit: o.orbit, mu: o.mu_E, base: o.baseline, gamma: o.gamma })));
    assert.equal(c.orbits.total, r.n_orbits_Z);
  }
});

test('gain-two rows from verify_rigid_family.jsonl equal their prep and exhaust records', { skip: SKIP }, () => {
  const v = jsonl('results/verify_rigid_family.jsonl');
  const prep = v.filter(r => r.stage === 'prep' && r.gamma === 2);
  const mine = T1.filter(c => c.src[0] === 'results/verify_rigid_family.jsonl');
  assert.deepEqual(new Set(mine.map(c => c.key)), new Set(prep.map(r => r.key)));
  for (const c of mine) {
    const r = prep.find(r => r.key === c.key), ex = v.find(e => e.stage === 'exhaust' && e.key === c.key);
    const best = r.per_seed.find(s => s.gamma === r.gamma && s.mu_S === r.mu_S && s.baseline === r.baseline);
    assert.deepEqual(pick(c, ['group', 'n', 'k', 'w', 'E_order', 'rigid', 'mu', 'base', 'base_order', 'orbit', 'd', 'd_exact']),
      { group: r.group, n: r.n, k: r.k, w: r.w, E_order: r.full_group_order, rigid: r.rigid, mu: r.mu_S, base: r.baseline,
        base_order: r.baseline_order, orbit: best.orbit, d: ex.d_lower, d_exact: ex.exact }, c.id);
    assert.deepEqual(c.orbits.list, r.per_seed.map(s => ({ orbit: s.orbit, mu: s.mu_S, base: s.baseline, gamma: s.gamma })));
    assert.equal(c.orbits.total, r.n_seed_orbits);
  }
});

// the follow-up blocks of automorphisms_bruteforce.txt: '== <label>: ...' up to 'total [..]'
function bruteBlock(label) {
  const t = text('results/automorphisms_bruteforce.txt'), i = t.lastIndexOf(`== ${label}:`);
  assert.ok(i >= 0, label);
  return t.slice(i, t.indexOf('total [', i));
}

test('the three Z9 x| Z12 rows and the two small rows equal their sources', { skip: SKIP }, () => {
  const g = jsonl('results/gains_fullgroup.jsonl'), A = jsonl('results/verify_mitten_A.jsonl'), B = jsonl('results/verify_mitten_B.jsonl');
  const ilp = jsonl('results/ilp_small.jsonl'), summary = text('results/automorphisms_bruteforce.txt');
  const row = (group, n, k) => T1.find(c => c.group === group && c.n === n && c.k === k && c.src[0] !== 'results/verify_rigid_family.jsonl');
  // rows taken from gains_fullgroup.jsonl, with rigidity from the brute-force summary table ((c)+ = 0 extras)
  for (const [group, n, k, label] of [['S3xZ6', 72, 8, 'S3xZ6 [[72,8,6]]'], ['D5xZ3', 60, 12, 'D5xZ3 [[60,12,6]]'],
                                       ['Z9x|8Z12', 216, 16, 'Z9x|8Z12 [[216,16,9]] (Mitten)']]) {
    const c = row(group, n, k), r = g.find(r => r.group === group && r.n === n && r.k === k);
    assert.deepEqual(pick(c, ['w', 'E_order', 'orbit', 'mu', 'base', 'base_order']),
      { w: r.w, E_order: r.full_order, orbit: r.orbit_full, mu: r.new_mu, base: r.new_base, base_order: r.new_base_order }, label);
    const line = summary.split(/\r?\n/).find(l => l.startsWith(label + ' '));
    assert.ok(line, label);
    const cols = line.slice(label.length).trim().split(/\s+/).map(Number);
    assert.equal(cols[cols.length - 1], 0, `${label}: no extra automorphisms`);
    assert.equal(c.rigid, true);
    assert.equal(c.orbits, null);
  }
  const s3 = row('S3xZ6', 72, 8);
  assert.equal(s3.d, g.find(r => r.group === 'S3xZ6' && r.n === 72 && r.k === 8).d);
  assert.equal(s3.d_exact, null);
  const d5 = row('D5xZ3', 60, 12), i5 = ilp.find(r => r.group === 'D5xZ3' && r.n === 60 && r.k === 12 && r.a.join() === '0,1,3,27');
  assert.ok(i5.dX_exact && i5.dZ_exact);
  assert.deepEqual(pick(d5, ['d', 'dX', 'dZ', 'd_exact']), { d: Math.min(i5.dX_lower, i5.dZ_lower), dX: i5.dX_lower, dZ: i5.dZ_lower, d_exact: true });
  const z16 = row('Z9x|8Z12', 216, 16), a16 = A.find(r => r.k === 16);
  assert.ok(a16.dX_exact && a16.dZ_exact);
  assert.deepEqual(pick(z16, ['d', 'd_exact']), { d: a16.dZ_lower, d_exact: true });

  // the non-rigid r = 2 code: the enlarged group of the brute-force search
  const r2 = row('Z9x|2Z12', 216, 16), b2 = B.find(r => r.label === 'Z9x|Z12_r2'), blk2 = bruteBlock('Z9x|2Z12 [[216,16,9]] (r=2, Table mitten)');
  const enl = blk2.match(/\[enl\] \|group\|=(\d+)[^\n]*\n\s+orbit 1: size (\d+) mu_S=(\d+) base=(\d+) \(\|A\|=(\d+)\)/);
  assert.ok(/rigid = False/.test(blk2) && enl);
  assert.deepEqual(pick(r2, ['E_order', 'orbit', 'mu', 'base', 'base_order', 'rigid', 'w', 'd', 'd_exact']),
    { E_order: +enl[1], orbit: +enl[2], mu: +enl[3], base: +enl[4], base_order: +enl[5], rigid: false,
      w: b2.a.length + b2.b.length, d: b2.dZ_lower, d_exact: b2.dZ_exact && b2.dX_exact });

  // the first [[216,12,12]]: rigid, so the translation group is E; distance from the exhaustive audit
  const r12 = row('Z9x|8Z12', 216, 12), a12 = A.find(r => r.k === 12), blk12 = bruteBlock('Z9x|8Z12 [[216,12,12]] (v0.7)');
  const tr = blk12.match(/\[trans\] \|group\|=(\d+)/), orbs = [...blk12.matchAll(/orbit \d+: size (\d+) mu_S=(\d+) base=(\d+) \(\|A\|=(\d+)\) gamma=([\d.]+)/g)];
  assert.ok(/rigid = True/.test(blk12) && tr && orbs.length === 2);
  assert.deepEqual(r12.orbits.list, orbs.map(m => ({ orbit: +m[1], mu: +m[2], base: +m[3], gamma: +m[5] })));
  assert.deepEqual(pick(r12, ['E_order', 'orbit', 'mu', 'base', 'base_order', 'rigid', 'w']),
    { E_order: +tr[1], orbit: +orbs[0][1], mu: +orbs[0][2], base: +orbs[0][3], base_order: +orbs[0][4], rigid: true, w: a12.a.length + a12.b.length });
  const audit = text('results/audit_exhaust_distance.txt').match(/RESULT Z9x\|8Z12_216_12: d >= (\d+) certified: True; exact d = (\d+): True/);
  assert.ok(audit);
  assert.deepEqual(pick(r12, ['d', 'd_exact']), { d: +audit[2], d_exact: true });
});

test('candidates are the rigid gain-two records of search_rigid.jsonl, and the search counts are its counts', { skip: SKIP }, () => {
  const rs = jsonl('results/search_rigid.jsonl'), g2 = rs.filter(r => r.rigid && r.gamma === 2);
  assert.deepEqual(DATA.candidates, g2.map(r => ({ group: r.group, n: r.n, k: r.k, w: r.w, d_est: r.d_est,
    mu: r.mu_S, base: r.baseline, base_order: r.baseline_order })));
  const done = rs.filter(r => r.gamma !== null);
  assert.deepEqual(pick(DATA.search, ['codes', 'rigid', 'gain_two', 'rigid_gain_two', 'max_gamma']),
    { codes: done.length, rigid: done.filter(r => r.rigid).length, gain_two: done.filter(r => r.gamma === 2).length,
      rigid_gain_two: g2.length, max_gamma: Math.max(...done.map(r => r.gamma)) });
});
