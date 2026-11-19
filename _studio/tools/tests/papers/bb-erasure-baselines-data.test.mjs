// papers/data/bb-erasure-baselines.json, written by _studio/tools/papers/extract_bb-erasure-baselines.py, holds
// exactly the values of the source repository's result files. The comparison against the source needs a clone of
// https://github.com/pandey-tushar/QLDPC: set QLDPC_CLONE to its path. Without a clone those tests skip.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

const DATA = JSON.parse(readFileSync(new URL('../../../../papers/data/bb-erasure-baselines.json', import.meta.url), 'utf8'));
const CLONE = process.env.QLDPC_CLONE
  || 'C:\\Users\\thetu\\AppData\\Local\\Temp\\claude\\04561455ac0ac633\\f7dc18bb-cd48-4a03-89d4-ec2f824b181f\\scratchpad\\src\\QLDPC';
const HAVE = existsSync(path.join(CLONE, 'results'));
const SKIP = HAVE ? false : `no QLDPC clone at ${CLONE}; set QLDPC_CLONE to compare against the source files`;
const src = f => path.join(CLONE, ...f.split('/'));

function csv(file) {
  const [head, ...rows] = readFileSync(src(file), 'utf8').trim().split(/\r?\n/);
  const k = head.split(',');
  return rows.map(r => Object.fromEntries(r.split(',').map((v, i) => [k[i], v])));
}

test('required fields exist', () => {
  for (const k of ['paper', 'source', 'paper_fit', 'fss_fit', 'bb', 'toric']) assert.ok(k in DATA, k);
  for (const k of ['repository', 'commit', 'extracted', 'files']) assert.ok(k in DATA.source, `source.${k}`);
  assert.match(DATA.source.commit, /^[0-9a-f]{40}$/);
  assert.match(DATA.source.extracted, /^\d{4}-\d\d-\d\d$/);
  assert.equal(DATA.paper.arxiv, '2603.19062');
  for (const k of ['p_star_inf', 'nu', 'file', 'line_p_star_inf', 'line_nu']) assert.ok(k in DATA.paper_fit, `paper_fit.${k}`);
  for (const k of ['p_star_inf', 'nu', 'residual_ss', 'poly_degree', 'p_window', 'file', 'csv_files']) assert.ok(k in DATA.fss_fit, `fss_fit.${k}`);
  assert.deepEqual(DATA.bb.map(s => s.N), [144, 324, 576, 900, 1296]);
  for (const s of DATA.bb) {
    for (const k of ['L', 'M', 'N', 'K', 'center', 'p_star', 'p_star_ci95', 'files', 'points']) assert.ok(k in s, `bb ${s.N}.${k}`);
    assert.ok(s.points.length >= 5);
    assert.ok(s.points.every((q, i) => !i || q.p > s.points[i - 1].p), `bb ${s.N} sorted by p, no repeats`);
    assert.ok(s.points.every(q => q.fit_count >= 1));
  }
  assert.deepEqual(DATA.toric.map(t => t.id), ['erasure_aware', 'uninformed']);
  for (const t of DATA.toric) for (const k of ['label', 'file', 'shots_per_point', 'sizes']) assert.ok(k in t, `toric ${t.id}.${k}`);
});

test('no value is NaN or infinite, every rate is fails / shots in [0, 1]', () => {
  const walk = (v, at) => {
    if (typeof v === 'number') assert.ok(Number.isFinite(v), at);
    else if (v && typeof v === 'object') for (const [k, x] of Object.entries(v)) walk(x, `${at}.${k}`);
  };
  walk(DATA, 'data');
  const pts = [...DATA.bb.flatMap(s => s.points), ...DATA.toric.flatMap(t => t.sizes.flatMap(s => s.points))];
  for (const q of pts) assert.ok(Number.isInteger(q.fails) && Number.isInteger(q.shots) && q.shots > 0 && q.fails <= q.shots && q.p > 0 && q.p < 1);
});

test('the commit is the clone HEAD', { skip: SKIP }, () => {
  assert.equal(DATA.source.commit, execFileSync('git', ['-C', CLONE, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim());
});

test('BB points equal the rows of the CSV files the FSS fit read', { skip: SKIP }, () => {
  const fss = JSON.parse(readFileSync(src(DATA.fss_fit.file), 'utf8'));
  assert.deepEqual(DATA.fss_fit.csv_files, fss.csv_files.map(f => f.replace(/\\/g, '/')));
  const rows = DATA.fss_fit.csv_files.flatMap(f => csv(f)).filter(r => r.family === 'bivariate_bicycle');
  for (const s of DATA.bb) {
    const mine = rows.filter(r => Number(r.L) === s.L && Number(r.M) === s.M);
    assert.equal(s.points.reduce((t, q) => t + q.fit_count, 0), mine.length, `rows for N=${s.N}`);
    for (const r of mine) {
      const q = s.points.find(q => q.p === Number(r.p));
      assert.ok(q, `N=${s.N} p=${r.p}`);
      assert.equal(q.fails, Number(r.fails)); assert.equal(q.shots, Number(r.shots));
      assert.equal(s.N, Number(r.N)); assert.equal(s.K, Number(r.K));
    }
  }
});

test('fit, pseudo-thresholds and the paper fit equal their sources', { skip: SKIP }, () => {
  const fss = JSON.parse(readFileSync(src(DATA.fss_fit.file), 'utf8')).fss_fit;
  assert.equal(DATA.fss_fit.p_star_inf, fss.p_star_fit); assert.equal(DATA.fss_fit.nu, fss.nu_fit);
  assert.equal(DATA.fss_fit.residual_ss, fss.residual_ss); assert.equal(DATA.fss_fit.p_window, fss.p_window);
  assert.deepEqual(DATA.fss_fit.p_star_inf_ci95, fss.p_star_ci_95); assert.deepEqual(DATA.fss_fit.nu_ci95, fss.nu_ci_95);
  const ci = JSON.parse(readFileSync(src(DATA.bb[0].ci_file), 'utf8')).threshold_ci;
  for (const s of DATA.bb) {
    assert.equal(s.center, fss.per_size[`L${s.L}M${s.M}`].p_star_interp);
    const c = ci.find(c => c.N === s.N);
    assert.equal(s.p_star, c.p_star); assert.deepEqual(s.p_star_ci95, [c.ci_lo_95, c.ci_hi_95]);
  }
  const tex = readFileSync(src(DATA.paper_fit.file), 'utf8').split(/\r?\n/);
  assert.match(tex[DATA.paper_fit.line_p_star_inf - 1], new RegExp(`p\\^\\*_\\\\infty &= ${DATA.paper_fit.p_star_inf} \\\\pm ${DATA.paper_fit.p_star_inf_pm}`));
  assert.match(tex[DATA.paper_fit.line_nu - 1], new RegExp(`\\\\nu +&= ${DATA.paper_fit.nu} +\\\\pm ${DATA.paper_fit.nu_pm}`));
});

test('toric points equal their CSV rows', { skip: SKIP }, () => {
  for (const t of DATA.toric) {
    const rows = csv(t.file);
    assert.equal(t.sizes.reduce((n, s) => n + s.points.length, 0), rows.length, t.id);
    for (const r of rows) {
      const s = t.sizes.find(s => s.N === Number(r.N));
      const q = s && s.points.find(q => q.p === Number(r.p));
      assert.ok(q, `${t.id} N=${r.N} p=${r.p}`);
      assert.equal(q.fails, Number(r.fails)); assert.equal(q.shots, Number(r.shots)); assert.equal(s.K, Number(r.K));
      assert.equal(q.shots, t.shots_per_point);
    }
  }
});
