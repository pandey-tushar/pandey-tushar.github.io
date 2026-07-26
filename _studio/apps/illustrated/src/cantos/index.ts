/* THE REGISTRATION POINT.

   Every canto in the book is registered here, and as of this pass every canto
   in the book carries a composition. Nothing renders as text on a bare plate
   any more and nothing is marked unstyled.

   Adding a canto is two steps and no engineering:
     1. write cantos/cantoNN.ts, a CantoArt naming one or two motifs, their
        parameters, and three to five beat boundaries;
     2. add one line to ART below.

   That held for all seventeen. The library grew by one form and three
   parameters over the whole pass, all of them because a canto asked for
   something the vocabulary could not say rather than because a canto was
   inconvenient:

     dial          canto 18. The book is full of measurement and had no
                   instrument in it. Also used by cantos 19 and 20.
     thread.angle  canto 5. One rank of threads is a span; two ranks a quarter
                   turn apart are cloth, and only cloth says that canto.
     thread.bow    canto 13. A link hung from orbit arcs over the horizon; sag
                   could only lay it along the ground.
     lattice.burst canto 12. The canto turns on the difference between
                   scattered faults and one correlated strike, and the motif
                   could only draw the scatter.

   If adding a canto ever stops being a composition, the motif system has
   failed and the fix belongs in packages/motifs, not here. */

import { en } from '@qubit/content';
import { canto01 } from './canto01.js';
import { canto02 } from './canto02.js';
import { canto03 } from './canto03.js';
import { canto04 } from './canto04.js';
import { canto05 } from './canto05.js';
import { canto06 } from './canto06.js';
import { canto07 } from './canto07.js';
import { canto08 } from './canto08.js';
import { canto09 } from './canto09.js';
import { canto10 } from './canto10.js';
import { canto11 } from './canto11.js';
import { canto12 } from './canto12.js';
import { canto13 } from './canto13.js';
import { canto14 } from './canto14.js';
import { canto15 } from './canto15.js';
import { canto16 } from './canto16.js';
import { canto17 } from './canto17.js';
import { canto18 } from './canto18.js';
import { canto19 } from './canto19.js';
import { canto20 } from './canto20.js';
import { canto21 } from './canto21.js';
import { canto22 } from './canto22.js';
import { cover } from './cover.js';
import type { CantoArt } from './types.js';

export type { CantoArt } from './types.js';

/** canto number to its art. Canto 0 is the frontispiece. */
export const ART: Readonly<Record<number, CantoArt>> = {
  0: cover,
  1: canto01,
  2: canto02,
  3: canto03,
  4: canto04,
  5: canto05,
  6: canto06,
  7: canto07,
  8: canto08,
  9: canto09,
  10: canto10,
  11: canto11,
  12: canto12,
  13: canto13,
  14: canto14,
  15: canto15,
  16: canto16,
  17: canto17,
  18: canto18,
  19: canto19,
  20: canto20,
  21: canto21,
  22: canto22,
};

/** Every canto number in the edition, composed or not. */
export const ALL_CANTOS: readonly number[] = en.map((c) => c.n);

/** The cantos that have art in this pass. Used by the poster export, the
    determinism gate and the frame budget run so none of them can silently
    drift out of step with the registry. */
export const COMPOSED: readonly number[] = Object.keys(ART)
  .map(Number)
  .filter((n) => n > 0)
  .sort((a, b) => a - b);

/** Every registered plate including the frontispiece, in order. The poster
    export walks this so the exported set can never drift from the registry. */
export const ALL_ART: readonly number[] = Object.keys(ART)
  .map(Number)
  .sort((a, b) => a - b);

export const artFor = (n: number): CantoArt | undefined => ART[n];
