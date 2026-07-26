/* Book data schema. Every edition (en, hi, life) validates against this.
   The validator is deliberately loud: an unknown block type is a bug in the
   content, not something to skip quietly at render time. */

export type Speaker = 'seeker' | 'oracle';

/** Plain narration. */
export interface PBlock { t: 'p'; text: string }
/** A turn of dialogue; each string is one paragraph. */
export interface DlgBlock { t: 'dlg'; who: Speaker; text: string[]; name?: string }
/** The grounded aside. `html` is trusted authored markup, KaTeX included. */
export interface ScienceBlock { t: 'science'; head?: string; html: string }
/** A belief stated plainly, then answered. `counter` is trusted markup. */
export interface AssumeBlock { t: 'assume'; claim: string; counter: string }
/** A dated forecast with a confidence bar. `text` is trusted markup. */
export interface PredBlock {
  t: 'pred';
  tag: string;
  tagc: string;
  conf: number;
  text: string;
  /** Carried by six cantos in the shipped data and unused by the renderer. */
  html?: string;
}
/** Sources for the canto. Trusted markup. */
export interface NoteBlock { t: 'note'; html: string }
/** Mount point for an interactive scene. `controls` is trusted markup.
    `strings` carries the readouts the scene module writes on interaction, so a
    non-English edition does not have to rewrite the DOM afterwards. Keys are
    named by the scene; `{placeholder}` spans are filled by the scene. */
export interface SceneBlock {
  t: 'scene'; kind: string; hint?: string; controls?: string;
  strings?: Record<string, string>;
}
/** The question turned back on the reader. */
export interface ReflectBlock { t: 'reflect'; text: string }

export type Block =
  | PBlock | DlgBlock | ScienceBlock | AssumeBlock
  | PredBlock | NoteBlock | SceneBlock | ReflectBlock;

export type BlockType = Block['t'];

export const BLOCK_TYPES = [
  'p', 'dlg', 'science', 'assume', 'pred', 'note', 'scene', 'reflect',
] as const satisfies readonly BlockType[];

export interface Movement { label: string; title: string }
export interface Epigraph { text: string; attr: string }

export interface Canto {
  n: number;
  title: string;
  /** Present only on the canto that opens a movement. */
  movement?: Movement;
  epigraph?: Epigraph;
  blocks: Block[];
}

export type Book = Canto[];

/* ---------- runtime validation ---------- */

export class SchemaError extends Error {
  constructor(public path: string, message: string) {
    super(path + ': ' + message);
    this.name = 'SchemaError';
  }
}

const isObj = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v);

function str(v: unknown, path: string): string {
  if (typeof v !== 'string') throw new SchemaError(path, 'expected string, got ' + kind(v));
  return v;
}

function kind(v: unknown): string {
  if (v === null) return 'null';
  if (Array.isArray(v)) return 'array';
  return typeof v;
}

function validateBlock(raw: unknown, path: string): Block {
  if (!isObj(raw)) throw new SchemaError(path, 'expected an object, got ' + kind(raw));
  const t = raw.t;
  if (typeof t !== 'string') throw new SchemaError(path, 'block has no string "t"');
  switch (t) {
    case 'p':
    case 'reflect':
      str(raw.text, path + '.text');
      break;
    case 'dlg': {
      const who = str(raw.who, path + '.who');
      if (who !== 'seeker' && who !== 'oracle') {
        throw new SchemaError(path + '.who', 'expected "seeker" or "oracle", got ' + JSON.stringify(who));
      }
      if (!Array.isArray(raw.text)) throw new SchemaError(path + '.text', 'expected an array of paragraphs');
      raw.text.forEach((p, i) => str(p, path + '.text[' + i + ']'));
      break;
    }
    case 'science':
      str(raw.html, path + '.html');
      if (raw.head !== undefined) str(raw.head, path + '.head');
      break;
    case 'assume':
      str(raw.claim, path + '.claim');
      str(raw.counter, path + '.counter');
      break;
    case 'pred':
      str(raw.tag, path + '.tag');
      str(raw.tagc, path + '.tagc');
      str(raw.text, path + '.text');
      if (typeof raw.conf !== 'number' || !Number.isFinite(raw.conf)) {
        throw new SchemaError(path + '.conf', 'expected a finite number, got ' + kind(raw.conf));
      }
      if (raw.conf < 0 || raw.conf > 100) {
        throw new SchemaError(path + '.conf', 'expected 0..100, got ' + String(raw.conf));
      }
      break;
    case 'note':
      str(raw.html, path + '.html');
      break;
    case 'scene':
      str(raw.kind, path + '.kind');
      if (raw.hint !== undefined) str(raw.hint, path + '.hint');
      if (raw.controls !== undefined) str(raw.controls, path + '.controls');
      if (raw.strings !== undefined) {
        if (!isObj(raw.strings)) throw new SchemaError(path + '.strings', 'expected an object of strings');
        for (const [k, v] of Object.entries(raw.strings)) str(v, path + '.strings.' + k);
      }
      break;
    default:
      throw new SchemaError(
        path + '.t',
        'unknown block type ' + JSON.stringify(t) +
        '. Known types: ' + BLOCK_TYPES.join(', ') +
        '. Add it to schema.ts and to the reader before using it in content.',
      );
  }
  return raw as unknown as Block;
}

function validateCanto(raw: unknown, path: string): Canto {
  if (!isObj(raw)) throw new SchemaError(path, 'expected an object, got ' + kind(raw));
  if (typeof raw.n !== 'number' || !Number.isInteger(raw.n)) {
    throw new SchemaError(path + '.n', 'expected an integer canto number');
  }
  str(raw.title, path + '.title');
  if (raw.movement !== undefined) {
    if (!isObj(raw.movement)) throw new SchemaError(path + '.movement', 'expected an object');
    str(raw.movement.label, path + '.movement.label');
    str(raw.movement.title, path + '.movement.title');
  }
  if (raw.epigraph !== undefined) {
    if (!isObj(raw.epigraph)) throw new SchemaError(path + '.epigraph', 'expected an object');
    str(raw.epigraph.text, path + '.epigraph.text');
    str(raw.epigraph.attr, path + '.epigraph.attr');
  }
  if (!Array.isArray(raw.blocks)) throw new SchemaError(path + '.blocks', 'expected an array');
  raw.blocks.forEach((b, i) => validateBlock(b, path + '.blocks[' + i + ']'));
  return raw as unknown as Canto;
}

/* ---------- front matter ---------- */

/** Chrome the reader prints for itself, rather than taking from a block.
    Every field is optional; packages/reader fills the gaps with its English
    defaults, so an edition declares only what it changes. Templates take
    `{n}`, `{total}` and `{title}` placeholders. */
export interface Labels {
  /** Canto head. Default "Canto {n} of {total}". */
  canto?: string;
  /** Appendix entry head, title already upper-cased. Default "CANTO {n} · {title}". */
  appendixCanto?: string;
  /** Rail bead accessible name. Default "Canto {n}: {title}". */
  bead?: string;
  /** Rail bead tooltip. Default "{n}. {title}". */
  beadTip?: string;
  /** Rail landmark name. Default "Cantos". */
  rail?: string;
  /** Default "The Assumption Challenged". */
  assume?: string;
  /** Default "A Prediction". The middle dot and the tag chip follow it. */
  prediction?: string;
  /** Default "confidence". */
  confidence?: string;
  /** Default "A Question For You". */
  reflect?: string;
  /** Default "The Science". A science block's own `head` still wins. */
  science?: string;
  /** Default "THE SEEKER". A dialogue block's own `name` still wins. */
  seeker?: string;
  /** Default "THE ORACLE". */
  oracle?: string;
  /** Theme chip tooltip. Default "Switch theme". */
  themeTitle?: string;
  /** Theme chip accessible name. Default "Toggle light or dark theme". */
  themeAria?: string;
  /** Ten characters, 0 to 9, for an edition that numbers its cantos in another
      numeral system. Applied to {n} and {total} only, never to percentages. */
  digits?: string;
}

export interface FrontMatter {
  loader: { glyph: string; label: string };
  cover: { glyph: string; title: string; sub: string; scrollcue: string; copy: string };
  invocation: {
    label: string;
    title: string;
    epigraph: Epigraph;
    paras: string[];
    reflect: { label: string; text: string };
  };
  appendix: { label: string; title: string; intro: string };
  footer: { mark: string; lines: string[]; cite: string[] };
  theme: { toLight: string; toDark: string };
  labels?: Labels;
}

export function validateFront(raw: unknown, label = 'front'): FrontMatter {
  if (!isObj(raw)) throw new SchemaError(label, 'expected an object, got ' + kind(raw));
  for (const key of ['loader', 'cover', 'invocation', 'appendix', 'footer', 'theme']) {
    if (!isObj(raw[key])) throw new SchemaError(label + '.' + key, 'expected an object');
  }
  const inv = raw.invocation as Record<string, unknown>;
  if (!Array.isArray(inv.paras) || inv.paras.length === 0) {
    throw new SchemaError(label + '.invocation.paras', 'expected a non-empty array');
  }
  if (raw.labels !== undefined) {
    if (!isObj(raw.labels)) throw new SchemaError(label + '.labels', 'expected an object');
    for (const [k, v] of Object.entries(raw.labels)) str(v, label + '.labels.' + k);
    const digits = raw.labels.digits;
    if (typeof digits === 'string' && [...digits].length !== 10) {
      throw new SchemaError(label + '.labels.digits', 'expected exactly ten characters, 0 to 9');
    }
  }
  return raw as unknown as FrontMatter;
}

/** Validates a whole edition. Throws SchemaError on the first problem. */
export function validateBook(raw: unknown, label = 'book'): Book {
  if (!Array.isArray(raw)) throw new SchemaError(label, 'expected an array of cantos, got ' + kind(raw));
  if (raw.length === 0) throw new SchemaError(label, 'edition has no cantos');
  const seen = new Set<number>();
  const book = raw.map((c, i) => {
    const canto = validateCanto(c, label + '[' + i + ']');
    if (seen.has(canto.n)) throw new SchemaError(label + '[' + i + '].n', 'duplicate canto number ' + canto.n);
    seen.add(canto.n);
    return canto;
  });
  return book;
}
