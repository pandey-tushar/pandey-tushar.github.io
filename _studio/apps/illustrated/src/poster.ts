/* The poster route.

   Renders one canto's signature frame at an arbitrary size, then publishes a
   SHA-256 of the raw pixels. Three gates drive this one page:

     posters.mjs      writes the PNG for the poster test and the OG cards
     determinism.mjs  loads it twice in fresh browser contexts and compares
                      the hashes, which is how an unseeded random gets caught
     print            the same route at any width, since nothing here is
                      resolution dependent

   It calls renderSignature, the same function the reduced motion edition and
   the live stage go through, so a poster cannot be a different picture from
   the frame the reader stops on. */

import { mountSurface, renderComposition, renderSignature } from '@qubit/motifs';
import { ALL_ART, ART } from './cantos/index.js';

declare global {
  interface Window {
    __poster?: { canto: number; width: number; height: number; progress: number; hash: string };
    __cantos?: readonly number[];
    __signature?: number;
  }
}

/* the registry is the single source of truth for which cantos are composed;
   the export and the gates read it from here rather than keeping a list */
window.__cantos = ALL_ART;

const q = new URLSearchParams(location.search);
const canto = Number(q.get('canto') ?? '1');
const width = Number(q.get('w') ?? '1600');
const height = Number(q.get('h') ?? Math.round(width * 0.625));
const dpr = Number(q.get('dpr') ?? '1');
const at = q.get('at');

const art = ART[canto];
if (!art) throw new Error('poster: canto ' + String(canto) + ' has no composition registered');
window.__signature = art.composition.signature;

const canvas = document.createElement('canvas');
document.body.append(canvas);
const surface = mountSurface(canvas, { width, height, dpr });

const progress = at === null ? art.composition.signature : Number(at);
if (at === null) renderSignature(surface, art.composition);
else renderComposition(surface, art.composition, progress);

const ctx = canvas.getContext('2d');
if (!ctx) throw new Error('poster: no 2d context');
const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height).data;

const hex = (buf: ArrayBuffer): string =>
  [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');

void crypto.subtle.digest('SHA-256', pixels).then((digest) => {
  window.__poster = { canto, width, height, progress, hash: hex(digest) };
  document.documentElement.dataset.posterReady = '1';
});
