// Pure logic for Fig. 1 of papers/adaptive-graph-of-thoughts.html: which rows of the paper's Tables 1 to 3 a choice of
// benchmark, model and metric shows, ranked, and the sentence that states them. Tests:
// _studio/tools/tests/papers/adaptive-graph-of-thoughts-logic.test.mjs.
export const METHODS = ['IO', 'CoT', 'AIoT', 'AGoT'];
export const NAMES = {
  GPQA_D: 'GPQA Diamond, answer options in their default order', GPQA_S: 'GPQA Diamond, answer options shuffled',
  HotpotQA: 'HotpotQA', MoreHopQA: 'MoreHopQA', HybridQA: 'HybridQA',
  'Crossword Letters': 'Mini-crosswords, letters', 'Crossword Words': 'Mini-crosswords, words', 'Game of 24': 'Game of 24',
};
export const METRICS = {
  accuracy: 'Accuracy', LAAS: 'LLM-assisted accuracy (LAAS)', EM: 'Exact match (EM)', F1: 'F1',
  'letter accuracy': 'Letter accuracy', 'word accuracy': 'Word accuracy',
};
const uniq = a => [...new Set(a)];
const rows = data => data.tables.flatMap(t => t.rows.map(r => ({ t, r })));
const minus = s => s.replace(/^-/, '−');

// The benchmarks in Table 2's order, with its category labels.
export function datasets(data) {
  return data.tables.find(t => t.number === 2).rows.map(r => ({ id: r.dataset, category: r.category }));
}

export function options(data, dataset) {
  const here = rows(data).filter(x => x.r.dataset === dataset).map(x => x.r);
  const order = ['accuracy', 'letter accuracy', 'word accuracy', 'LAAS', 'EM', 'F1'];
  return { models: uniq(here.map(r => r.model)),
    metrics: uniq(here.map(r => r.metric)).sort((a, b) => order.indexOf(a) - order.indexOf(b)) };
}

// Keep the dataset; move model or metric to the first one the paper reports for it if needed.
export function resolve(data, sel) {
  const o = options(data, sel.dataset), out = { ...sel }, changed = [];
  if (!o.models.includes(out.model)) { out.model = o.models[0]; changed.push('model'); }
  if (!o.metrics.includes(out.metric)) { out.metric = o.metrics[0]; changed.push('metric'); }
  return { sel: out, changed };
}

// The row with the most methods for this choice (Table 2 over Tables 1 and 3, which repeat some of it), ranked high to low.
export function pick(data, sel) {
  const hits = rows(data).filter(({ r }) => r.dataset === sel.dataset && r.model === sel.model && r.metric === sel.metric);
  if (!hits.length) return null;
  const { t, r } = hits.reduce((a, b) => Object.keys(b.r.scores).length > Object.keys(a.r.scores).length ? b : a);
  const text = m => r.cells[t.columns.indexOf(m)];
  const ranked = METHODS.filter(m => m in r.scores)
    .map(m => ({ method: m, score: r.scores[m], text: text(m), delta: m in r.delta ? r.delta[m] : null,
      deltaText: m in r.delta ? minus(text('delta:' + m)) : null }))
    .sort((a, b) => b.score - a.score);
  return { sel, table: t, row: r, ranked };
}

export function axisMax(v) {
  return [10, 20, 25, 40, 50, 60, 80, 100].find(s => s >= v * 1.08) ?? 100;
}

const pp = d => Number(Math.abs(d).toFixed(1)).toString();

export function describe(data, v) {
  const { sel, table, ranked } = v;
  const io = ranked.find(e => e.method === 'IO'), ag = ranked.find(e => e.method === 'AGoT');
  const head = `${NAMES[sel.dataset]}, ${sel.model}, ${sel.metric} in percent (Table ${table.number} of the paper).`;
  const order = `From highest: ${ranked.map(e => `${e.method} ${e.text}`).join(', ')}.`;
  const d = ag.score - io.score;
  const gap = d === 0 ? 'AGoT is level with IO.' : `AGoT is ${pp(d)} percentage points ${d > 0 ? 'above' : 'below'} IO (computed here).`;
  const rel = ranked.filter(e => e.delta != null);
  if (!rel.length) return `${head} ${order} Table ${table.number} reports no relative change for this metric. ${gap}`;
  const words = rel.length === 1
    ? `The paper reports AGoT ${rel[0].deltaText} relative to direct IO. ${gap}`
    : `Relative to direct IO the paper reports ${rel.map(e => `${e.method} ${e.deltaText}`).join(', ')}. ${gap}`;
  return `${head} ${order} ${words}`;
}
