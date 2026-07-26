/* Book data to markup for the illustrated edition.

   Two decisions worth stating, because they are editorial and not technical:

   1. `scene` blocks are dropped. They mount the text edition's interactive
      widgets and carry instructions like "Drag to steer the qubit"; in this
      edition the art is not something the reader drags, and the motif for the
      canto already occupies that ground.
   2. The literary blocks (narration, dialogue, the stated assumption, the
      reflection) carry the scroll beats. The apparatus (science aside,
      prediction, sources) sits after the art sequence in a plain column,
      always in the DOM and always visible. Spec 02 leaves it open whether the
      illustrated cut keeps the asides; keeping them and setting them quietly
      loses nothing and keeps the reduced motion path complete.

   Nothing here invents prose. Every string comes from content/en.json. */

import type { Block, Canto, DlgBlock } from '@qubit/content/schema';

const LITERARY = new Set(['p', 'dlg', 'assume', 'reflect']);
const APPARATUS = new Set(['science', 'pred', 'note']);

export const literary = (c: Canto): Block[] => c.blocks.filter((b) => LITERARY.has(b.t));
export const apparatus = (c: Canto): Block[] => c.blocks.filter((b) => APPARATUS.has(b.t));

const esc = (s: string): string =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const speaker = (b: DlgBlock): string =>
  b.name ?? (b.who === 'seeker' ? 'The Seeker' : 'The Oracle');

/* Strip KaTeX from this cut. Two reasons, both editorial before they are
   technical: the plates carry the argument here, and the equations are the one
   thing on the page a reader cannot look at. They also broke the phone, since
   KaTeX sets display math with SVG paths thousands of pixels wide and forced a
   567px scroll inside a 375px viewport.

   Display equations go. Inline symbols become their own text, so a sentence
   like "north for 0 and south for 1" still reads instead of losing its nouns.
   The full mathematics stays one link away in the text edition. */
function demath(html: string): string {
  const t = document.createElement('template');
  t.innerHTML = html;
  t.content.querySelectorAll('.eqblock').forEach((n) => n.remove());
  t.content.querySelectorAll('.eqi').forEach((n) => {
    n.replaceWith(document.createTextNode((n.textContent ?? '').trim()));
  });
  /* a paragraph that held nothing but a display equation is now empty */
  t.content.querySelectorAll('p').forEach((p) => {
    if (!(p.textContent ?? '').trim()) p.remove();
  });
  /* A paragraph that introduced an equation now trails off: "Its state is
     written", "Prepare two qubits in the state", "falls by a constant factor
     lambda:". The introduction means nothing once the equation is gone, so cut
     back to the last complete sentence, and drop the paragraph if there is
     none. */
  t.content.querySelectorAll('p').forEach((p) => {
    const text = (p.textContent ?? '').trim();
    if (!text || /[.!?”)]$/.test(text)) return;
    const tail = p.lastChild;
    if (tail && tail.nodeType === 3) {
      const cut = (tail.textContent ?? '').search(/[.!?][^.!?]*$/);
      if (cut >= 0) {
        tail.textContent = (tail.textContent ?? '').slice(0, cut + 1);
        if (/[.!?”)]$/.test((p.textContent ?? '').trim())) return;
      }
    }
    p.remove();
  });
  return t.innerHTML;
}

export function blockHtml(b: Block): string {
  switch (b.t) {
    case 'p':
      return '<p class="narr">' + esc(b.text) + '</p>';
    case 'dlg':
      return (
        '<div class="turn ' + b.who + '">' +
        '<p class="who">' + esc(speaker(b)) + '</p>' +
        b.text.map((t) => '<p>' + esc(t) + '</p>').join('') +
        '</div>'
      );
    case 'assume':
      return (
        '<div class="assume">' +
        '<p class="claim">' + esc(b.claim) + '</p>' +
        '<div class="counter">' + b.counter + '</div>' +
        '</div>'
      );
    case 'reflect':
      return '<blockquote class="reflect">' + esc(b.text) + '</blockquote>';
    case 'science':
      return (
        '<section class="science">' +
        (b.head ? '<h3>' + esc(b.head) + '</h3>' : '') + demath(b.html) +
        '</section>'
      );
    case 'pred':
      return (
        '<section class="pred">' +
        '<p class="tag ' + esc(b.tagc) + '">' + esc(b.tag) +
        '<span class="conf">' + String(Math.round(b.conf)) + '%</span></p>' +
        '<div class="body">' + b.text + '</div>' +
        '</section>'
      );
    case 'note':
      return '<section class="note"><h3>Sources</h3>' + b.html + '</section>';
    default:
      return '';
  }
}

/** Groups the literary blocks into beats. `starts` comes from the canto's art;
    a canto with no art is split into four near equal beats so the page still
    has structure. */
export function beatsOf(c: Canto, starts?: number[]): Block[][] {
  const blocks = literary(c);
  if (blocks.length === 0) return [];
  let cuts = starts && starts.length > 0 ? starts.slice() : defaultCuts(blocks.length);
  cuts = cuts.filter((v, i, a) => v >= 0 && v < blocks.length && a.indexOf(v) === i).sort((x, y) => x - y);
  if (cuts[0] !== 0) cuts.unshift(0);
  const out: Block[][] = [];
  for (let i = 0; i < cuts.length; i++) {
    const end = i + 1 < cuts.length ? cuts[i + 1]! : blocks.length;
    out.push(blocks.slice(cuts[i]!, end));
  }
  return out.filter((g) => g.length > 0);
}

function defaultCuts(n: number): number[] {
  const beats = n >= 12 ? 4 : n >= 6 ? 3 : 2;
  const cuts: number[] = [];
  for (let i = 0; i < beats; i++) cuts.push(Math.round((n * i) / beats));
  return cuts;
}

export function romanNumeral(n: number): string {
  const table: Array<[number, string]> = [
    [10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I'],
  ];
  let v = n;
  let out = '';
  for (const [k, s] of table) {
    while (v >= k) { out += s; v -= k; }
  }
  return out;
}
