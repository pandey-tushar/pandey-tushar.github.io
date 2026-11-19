// papers/data/adaptive-graph-of-thoughts.json, written by _studio/tools/papers/extract_adaptive-graph-of-thoughts.py,
// holds exactly the numbers of Tables 1 to 3 of arXiv:2502.05078. The comparison against the source needs the
// unpacked arXiv e-print: set AGOT_ARXIV_SRC to the folder holding eprint.bin and src/main.tex. Without it those tests skip.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';

const DATA = JSON.parse(readFileSync(new URL('../../../../papers/data/adaptive-graph-of-thoughts.json', import.meta.url), 'utf8'));
const SRC = process.env.AGOT_ARXIV_SRC
  || 'C:\\Users\\thetu\\AppData\\Local\\Temp\\claude\\04561455ac0ac633\\f7dc18bb-cd48-4a03-89d4-ec2f824b181f\\scratchpad\\arxiv-agot';
const TEX = path.join(SRC, 'src', 'main.tex');
const HAVE = existsSync(TEX);
const SKIP = HAVE ? false : `no arXiv source at ${TEX}; set AGOT_ARXIV_SRC to compare against the paper's tables`;
const LABELS = ['tab:gpt-gpqa-results', 'tab:performance_comparison', 'tab: Retrieval tasks'];
const row = (t, ds, x) => DATA.tables[t - 1].rows.find(r => r.dataset === ds && Object.entries(x).every(([k, v]) => r[k] === v));

test('required fields exist', () => {
  for (const k of ['paper', 'source', 'tables']) assert.ok(k in DATA, k);
  assert.equal(DATA.paper.arxiv, '2502.05078');
  assert.equal(DATA.paper.id, 'adaptive-graph-of-thoughts-test-time-adaptive-reasoning-unif');
  assert.match(DATA.paper.version, /^v\d+$/);
  for (const k of ['eprint', 'file', 'sha256', 'fetched', 'extracted']) assert.ok(k in DATA.source, `source.${k}`);
  assert.match(DATA.source.sha256, /^[0-9a-f]{64}$/);
  for (const k of ['fetched', 'extracted']) assert.match(DATA.source[k], /^\d{4}-\d\d-\d\d$/);
  assert.deepEqual(DATA.tables.map(t => t.label), LABELS);
  assert.deepEqual(DATA.tables.map(t => t.number), [1, 2, 3]);
  assert.deepEqual(DATA.tables.map(t => t.rows.length), [3, 8, 9]);
  for (const t of DATA.tables) {
    for (const k of ['caption', 'line', 'columns', 'rows']) assert.ok(k in t, `${t.label}.${k}`);
    for (const r of t.rows) {
      for (const k of ['line', 'dataset', 'model', 'metric', 'scores', 'delta', 'cells']) assert.ok(k in r, `${t.label} ${r.dataset}.${k}`);
      assert.equal(r.cells.length, t.columns.length);
      for (const v of [...Object.values(r.scores), ...Object.values(r.delta)]) assert.ok(Number.isFinite(v));
      for (const v of Object.values(r.scores)) assert.ok(v >= 0 && v <= 100);
    }
  }
});

// Read by eye from the typeset arXiv v1 PDF, pages 7 and 8.
test('five values looked up in the paper', () => {
  const t1 = row(1, 'GPQA_S', { model: 'gpt-4o' });
  assert.equal(t1.scores.IO, 39.4); assert.equal(t1.scores.AGoT, 57.6); assert.equal(t1.delta.AGoT, 46.2);
  const d = row(1, 'GPQA_D', { model: 'gpt-4o-mini' });
  assert.equal(d.scores.AGoT, 55.1); assert.equal(d.delta.AGoT, 0.9);
  const h = row(2, 'HybridQA', {});
  assert.equal(h.scores.CoT, 64.0); assert.equal(h.delta.CoT, -5.9);
  const g = row(2, 'Game of 24', {});
  assert.equal(g.scores.AGoT, 50.0); assert.equal(g.delta.AGoT, 400.0);
  assert.equal(row(3, 'MoreHopQA', { metric: 'EM' }).scores.AIoT, 52);
  const w = row(2, 'Crossword Words', {});
  assert.equal(w.scores.AIoT, 11.0); assert.equal(w.delta.AIoT, 340.0);
});

test('every reported change is the relative change over IO, to rounding', () => {
  // Table 2's GPQA_S AIoT entry (+5.4%) is 78/74 correct answers out of 198; from the rounded 39.4/37.4 it is 5.35%.
  for (const t of DATA.tables) for (const r of t.rows) for (const [m, dv] of Object.entries(r.delta)) {
    const rel = (r.scores[m] / r.scores.IO - 1) * 100;
    assert.ok(Math.abs(rel - dv) <= 0.15, `${t.label} ${r.dataset} ${r.model} ${m}: ${dv} vs ${rel.toFixed(2)}`);
  }
});

test('the tables agree where they overlap', () => {
  for (const r of DATA.tables[0].rows.filter(r => r.model === 'gpt-4o-mini')) {
    const o = row(2, r.dataset, {});
    assert.equal(o.model, 'gpt-4o-mini');
    for (const m of Object.keys(r.scores)) assert.equal(o.scores[m], r.scores[m], `${r.dataset} ${m}`);
  }
  for (const r of DATA.tables[2].rows.filter(r => r.metric === 'LAAS')) {
    const o = row(2, r.dataset, {});
    assert.equal(o.metric, 'LAAS');
    for (const m of Object.keys(r.scores)) assert.equal(o.scores[m], r.scores[m], `${r.dataset} ${m}`);
  }
});

test('the source file is the one extracted', { skip: SKIP }, () => {
  assert.equal(createHash('sha256').update(readFileSync(TEX)).digest('hex'), DATA.source.sha256);
});

test('each row is the numbers on its line of main.tex, in order', { skip: SKIP }, () => {
  const tex = readFileSync(TEX, 'utf8').split(/\r?\n/);
  for (const t of DATA.tables) {
    assert.ok(tex[t.line - 1].includes(`\\label{${t.label}}`), `${t.label} at line ${t.line}`);
    for (const r of t.rows) {
      const line = tex[r.line - 1].replace(/\\multirow\{\d+\}\{\*\}/g, '').replace(/\$[^$]*\$/g, '').replace(/gpt-4o(-mini)?/g, '').replace(/Game of 24|\bF1\b/g, '');
      const nums = (line.match(/[+-]?\d+(?:\.\d+)?/g) || []).map(Number);
      const want = t.columns.flatMap((c, i) => {
        if (c.startsWith('delta:')) return [r.delta[c.slice(6)]];
        return c in r.scores ? [r.scores[c]] : [];
      });
      assert.deepEqual(nums, want, `${t.label} line ${r.line}`);
      for (const c of r.cells) if (/^[+-]?\d/.test(c)) assert.ok(tex[r.line - 1].includes(c.replace('%', '\\%')), `${c} on line ${r.line}`);
    }
    const body = tex.slice(t.tabular[0] - 1, t.tabular[1]).filter(l => l.includes('\\\\') && !l.trim().startsWith('%'));
    assert.equal(body.length, t.rows.length + 1, `${t.label}: header plus one line per row`);
  }
});
