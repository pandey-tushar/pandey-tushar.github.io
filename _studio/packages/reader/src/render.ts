/* Content to markup. Authored `html`, `counter`, `controls` and prediction
   `text` are trusted markup and go through unescaped, exactly as the shipped
   edition renders them. Everything else is escaped. */
import type { Block, Canto, FrontMatter, Labels } from '@qubit/content/schema';

/** Every string the reader prints for itself, in English. An edition overrides
    what it needs through `front.labels`; anything it leaves out stays as it is
    here, so apps that carry no labels render exactly as before. */
export type ReaderLabels = Required<Omit<Labels, 'digits'>> & { digits?: string };

export const DEFAULT_LABELS: ReaderLabels = {
  canto: 'Canto {n} of {total}',
  appendixCanto: 'CANTO {n} · {title}',
  bead: 'Canto {n}: {title}',
  beadTip: '{n}. {title}',
  rail: 'Cantos',
  assume: 'The Assumption Challenged',
  prediction: 'A Prediction',
  confidence: 'confidence',
  reflect: 'A Question For You',
  science: 'The Science',
  seeker: 'THE SEEKER',
  oracle: 'THE ORACLE',
  themeTitle: 'Switch theme',
  themeAria: 'Toggle light or dark theme',
};

export function resolveLabels(front?: { labels?: Labels }): ReaderLabels {
  return { ...DEFAULT_LABELS, ...(front?.labels ?? {}) };
}

/** Substitutes {name} spans. An unknown placeholder is left alone so a typo in
    content shows up in the page rather than turning into an empty string. */
export function fill(tpl: string, vars: Record<string, string>): string {
  return tpl.replace(/\{(\w+)\}/g, (m, k: string) => (k in vars ? vars[k] : m));
}

/** Canto numbers in the edition's numeral system. Percentages never go through
    this: spec 03 allows Devanagari digits for canto numbers and nothing else. */
export function numeral(n: number, digits?: string): string {
  if (!digits) return String(n);
  const d = [...digits];
  return String(n).replace(/\d/g, (c) => d[Number(c)] ?? c);
}

export function esc(s: unknown): string {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* Scene controls are authored markup and some carry a bare <input>. The
   readout span next to it already names the control in prose, so borrow that
   text as the accessible name rather than editing content. */
function labelControls(controls: string): string {
  if (!/<input\b/i.test(controls)) return controls;
  const m = controls.match(/<span class=["']rl["']>([^<]*)<\/span>/i);
  const label = (m?.[1] ?? 'scene control').trim();
  return controls.replace(/<input\b(?![^>]*\baria-label=)/gi, '<input aria-label="' + esc(label) + '"');
}

export function blockHtml(b: Block, labels: ReaderLabels = DEFAULT_LABELS): string {
  switch (b.t) {
    case 'dlg': {
      const cls = b.who === 'oracle' ? 'oracle' : 'seeker';
      const name = b.name ?? (b.who === 'oracle' ? labels.oracle : labels.seeker);
      const paras = b.text.map((p) => '<p>' + esc(p) + '</p>').join('');
      return '<div class="dlg ' + cls + '"><span class="speaker">' + esc(name) + '</span>' + paras + '</div>';
    }
    case 'p':
      return '<div class="dlg"><p>' + esc(b.text) + '</p></div>';
    case 'science':
      return '<div class="science"><h4>' + esc(b.head ?? labels.science) + '</h4>' + b.html + '</div>';
    case 'assume':
      return '<div class="assume"><div class="a-head">' + esc(labels.assume) + '</div>' +
        '<div class="a-body"><p class="claim">“' + esc(b.claim) + '”</p>' +
        '<p class="counter">' + b.counter + '</p></div></div>';
    case 'pred': {
      const pct = Math.max(4, Math.min(100, b.conf || 50));
      return '<div class="pred"><div class="p-title">' + esc(labels.prediction) + ' · ' +
        '<span class="tag ' + esc(b.tagc) + '">' + esc(b.tag) + '</span></div>' +
        '<div class="p-text">' + b.text + '</div>' +
        '<div class="conf"><span class="label">' + esc(labels.confidence) + '</span>' +
        '<span class="label">' + pct + '%</span></div></div>';
    }
    case 'scene': {
      /* the readouts the scene writes on interaction, handed to the module on
         the element so a translated edition needs no DOM rewriting */
      const strings = b.strings ? ' data-strings="' + esc(JSON.stringify(b.strings)) + '"' : '';
      return '<div class="scene" data-scene="' + esc(b.kind) + '"' + strings + '>' + labelControls(b.controls ?? '') +
        '<div class="hint">' + esc(b.hint ?? '') + '</div></div>';
    }
    case 'reflect':
      return '<div class="reflect"><span class="r-label">' + esc(labels.reflect) + '</span>' + esc(b.text) + '</div>';
    case 'note':
      return '<div class="foot-note">' + b.html + '</div>';
  }
}

export function cantoHtml(c: Canto, total: number, labels: ReaderLabels = DEFAULT_LABELS): string {
  const bodyId = 'canto-' + c.n + '-body';
  let pre = '';
  if (c.movement) {
    pre = '<div class="movement"><div class="mlabel">' + esc(c.movement.label) + '</div>' +
      '<div class="mtitle">' + esc(c.movement.title) + '</div><div class="mline"></div></div>';
  }
  const num = fill(labels.canto, {
    n: numeral(c.n, labels.digits), total: numeral(total, labels.digits),
  });
  const head = '<div class="canto-num">' + esc(num) + '</div>' +
    '<h2 class="canto-title">' + esc(c.title) + '</h2><span class="caret">▸</span>';
  let body = '';
  if (c.epigraph) {
    body += '<div class="epigraph">' + esc(c.epigraph.text) +
      '<span class="attr">' + esc(c.epigraph.attr) + '</span></div>';
  }
  body += c.blocks.map((b) => blockHtml(b, labels)).join('');
  return pre +
    '<button type="button" class="canto-head" aria-expanded="false" aria-controls="' + bodyId + '">' + head + '</button>' +
    '<div class="canto-wrap"><div class="canto-body" id="' + bodyId + '">' + body + '</div></div>';
}

/** The references appendix: every canto note gathered in one place. */
export function appendixHtml(cantos: Canto[], front: FrontMatter): string {
  const labels = resolveLabels(front);
  let html = '<div class="canto-num">' + esc(front.appendix.label) + '</div>' +
    '<h2 class="canto-title">' + esc(front.appendix.title) + '</h2>' +
    '<div class="dlg"><p>' + esc(front.appendix.intro) + '</p></div>';
  for (const c of cantos) {
    const note = c.blocks.find((b) => b.t === 'note');
    if (!note) continue;
    const head = fill(labels.appendixCanto, {
      n: numeral(c.n, labels.digits), title: c.title.toUpperCase(),
    });
    html += '<div class="foot-note"><strong style="color:var(--gold);letter-spacing:.08em">' +
      esc(head) + '</strong><br>' + note.html + '</div>';
  }
  return html;
}

export function coverHtml(front: FrontMatter): string {
  const c = front.cover;
  return '<div id="cover3d"></div>' +
    '<div class="om">' + esc(c.glyph) + '</div>' +
    '<h1>' + esc(c.title) + '</h1>' +
    '<div class="sub">' + esc(c.sub) + '</div>' +
    '<div class="scrollcue">' + esc(c.scrollcue) + '</div>' +
    '<div class="cover-copy">' + esc(c.copy) + '</div>';
}

export function invocationHtml(front: FrontMatter): string {
  const i = front.invocation;
  return '<div class="canto-num">' + esc(i.label) + '</div>' +
    '<h2 class="canto-title">' + esc(i.title) + '</h2>' +
    '<div class="epigraph">' + esc(i.epigraph.text) +
    '<span class="attr">' + esc(i.epigraph.attr) + '</span></div>' +
    '<div class="dlg">' + i.paras.map((p) => '<p>' + esc(p) + '</p>').join('') + '</div>' +
    '<div class="reflect"><span class="r-label">' + esc(i.reflect.label) + '</span>' +
    esc(i.reflect.text) + '</div>';
}

export function footerHtml(front: FrontMatter, home: string): string {
  const f = front.footer;
  return '<div class="closeq">' + esc(f.mark) + '</div>' +
    f.lines.map(esc).join('<br>') + '<br>' +
    '<span class="cite">' + f.cite.map(esc).join('<br>') +
    ' · <a href="' + esc(home) + '">' + esc(home.replace(/^https?:\/\//, '')) + '</a></span>';
}
