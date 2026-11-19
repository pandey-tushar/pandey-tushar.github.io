// Pure figure logic for papers/adaptive-graph-of-thoughts.html: papers/js/agot-logic.js.
// Reads the real papers/data/adaptive-graph-of-thoughts.json.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { datasets, options, resolve, pick, axisMax, describe } from '../../../../papers/js/agot-logic.js';

const DATA = JSON.parse(readFileSync(new URL('../../../../papers/data/adaptive-graph-of-thoughts.json', import.meta.url), 'utf8'));

test('datasets come in the order of Table 2, with its categories', () => {
  assert.deepEqual(datasets(DATA).map(d => d.id),
    ['GPQA_D', 'GPQA_S', 'HotpotQA', 'MoreHopQA', 'HybridQA', 'Crossword Letters', 'Crossword Words', 'Game of 24']);
  assert.deepEqual([...new Set(datasets(DATA).map(d => d.category))], ['Reasoning', 'Retrieval', 'Explorative']);
});

test('options list the models and metrics the paper reports for a dataset', () => {
  assert.deepEqual(options(DATA, 'GPQA_S'), { models: ['gpt-4o-mini', 'gpt-4o'], metrics: ['accuracy'] });
  assert.deepEqual(options(DATA, 'GPQA_D'), { models: ['gpt-4o-mini'], metrics: ['accuracy'] });
  assert.deepEqual(options(DATA, 'HotpotQA'), { models: ['gpt-4o-mini'], metrics: ['LAAS', 'EM', 'F1'] });
  assert.deepEqual(options(DATA, 'Crossword Words'), { models: ['gpt-4o-mini'], metrics: ['word accuracy'] });
});

test('resolve falls back to what exists and says what changed', () => {
  const a = resolve(DATA, { dataset: 'HotpotQA', model: 'gpt-4o', metric: 'EM' });
  assert.deepEqual(a.sel, { dataset: 'HotpotQA', model: 'gpt-4o-mini', metric: 'EM' });
  assert.deepEqual(a.changed, ['model']);
  const b = resolve(DATA, { dataset: 'Game of 24', model: 'gpt-4o-mini', metric: 'F1' });
  assert.deepEqual(b.sel, { dataset: 'Game of 24', model: 'gpt-4o-mini', metric: 'accuracy' });
  assert.deepEqual(b.changed, ['metric']);
  assert.deepEqual(resolve(DATA, { dataset: 'GPQA_S', model: 'gpt-4o', metric: 'accuracy' }).changed, []);
});

test('pick takes the fullest row and ranks it from highest', () => {
  const v = pick(DATA, { dataset: 'GPQA_S', model: 'gpt-4o-mini', metric: 'accuracy' });
  assert.equal(v.table.number, 2);
  assert.deepEqual(v.ranked.map(e => [e.method, e.score]), [['AGoT', 49.5], ['AIoT', 39.4], ['CoT', 38.6], ['IO', 37.4]]);
  assert.equal(v.ranked.find(e => e.method === 'AIoT').delta, 5.4);
  const o = pick(DATA, { dataset: 'GPQA_S', model: 'gpt-4o', metric: 'accuracy' });
  assert.equal(o.table.number, 1);
  assert.deepEqual(o.ranked.map(e => [e.method, e.score, e.delta, e.text]), [['AGoT', 57.6, 46.2, '57.6'], ['IO', 39.4, null, '39.4']]);
  const laas = pick(DATA, { dataset: 'HybridQA', model: 'gpt-4o-mini', metric: 'LAAS' });
  assert.equal(laas.table.number, 2, 'Table 2 has CoT as well');
  const em = pick(DATA, { dataset: 'HotpotQA', model: 'gpt-4o-mini', metric: 'EM' });
  assert.equal(em.table.number, 3);
  assert.deepEqual(em.ranked.map(e => e.method), ['IO', 'AGoT', 'AIoT']);
  assert.equal(pick(DATA, { dataset: 'HotpotQA', model: 'gpt-4o', metric: 'EM' }), null);
});

test('axisMax rounds up to a plain scale end, at most 100', () => {
  assert.equal(axisMax(11.1), 20);
  assert.equal(axisMax(50), 60);
  assert.equal(axisMax(57.6), 80);
  assert.equal(axisMax(84), 100);
  assert.equal(axisMax(99), 100);
});

test('describe states the reported gain exactly, and says it is relative', () => {
  const s = describe(DATA, pick(DATA, { dataset: 'GPQA_S', model: 'gpt-4o', metric: 'accuracy' }));
  assert.match(s, /AGoT 57\.6, IO 39\.4/);
  assert.match(s, /\+46\.2% relative to direct IO/);
  assert.match(s, /18\.2 percentage points/);
  assert.match(s, /Table 1/);
  const n = describe(DATA, pick(DATA, { dataset: 'HybridQA', model: 'gpt-4o-mini', metric: 'LAAS' }));
  assert.match(n, /CoT −5\.9%/);
  const em = describe(DATA, pick(DATA, { dataset: 'HotpotQA', model: 'gpt-4o-mini', metric: 'EM' }));
  assert.match(em, /reports no relative change/);
  assert.match(em, /AGoT is 3 percentage points below IO/);
});
