/* Canto 5, The Art of Forgetting Nothing. Motif: thread, twice.

   "Weave a hundred failing threads with care and the cloth outlasts them all."
   The epigraph is the plate. One rank of threads is a span; two ranks a
   quarter turn apart are cloth, and cloth is the only figure that can say the
   canto's sentence, which is that the whole survives every one of its parts.
   That is the whole reason the thread motif learned an angle.

   The warp is gold and the weft is cyan, so the two directions read as two
   different things holding each other up. Severance climbs steadily: by the
   signature about a fifth of the threads are cut, each cut curling back on
   itself with a rose bead at the break, and the cloth is still plainly cloth.
   If the reader can count the breaks and still see a weave, the canto is
   drawn. If the breaks ever win, the plate has told the wrong story. */

import type { CantoArt } from './types.js';

const CLOTH = { x: 0.22, y: 0.02, w: 0.56, h: 0.96 };

export const canto05: CantoArt = {
  legend: 'Plate V. A hundred failing threads, and the cloth that outlasts them.',
  /* built of parts that all fail | the threshold theorem | Willow crossed the
     line | the flaw that is not yet corrected | wholeness is a pattern that
     checks itself */
  beats: [0, 2, 5, 8, 10],
  composition: {
    id: 'canto-05',
    canto: 5,
    seed: 'qd/05/forgetting-nothing',
    signature: 0.64,
    plate: { wash: 'cyan', stars: 195, washStrength: 0.9 },
    layers: [
      {
        /* the weft */
        motif: 'thread',
        region: CLOTH,
        params: {
          count: 19, spread: 0.78, height: 0.66, gold: 0.06, width: 0.9,
          anchors: 0.8, glow: 0.5, pairing: 0,
        },
        keys: [
          { at: 0, params: { tension: 0.42, sever: 0 } },
          { at: 0.4, params: { sever: 0.08 } },
          { at: 1, params: { tension: 0.94, sever: 0.26 } },
        ],
      },
      {
        /* the warp, the same code turned a quarter */
        motif: 'thread',
        region: CLOTH,
        seed: 'qd/05/forgetting-nothing/warp',
        params: {
          count: 19, spread: 0.78, height: 0.66, gold: 0.7, width: 0.9,
          anchors: 0.8, glow: 0.7, pairing: 0, angle: 0.25,
        },
        keys: [
          { at: 0, params: { tension: 0.42, sever: 0 } },
          { at: 0.4, params: { sever: 0.06 } },
          { at: 1, params: { tension: 0.94, sever: 0.26 } },
        ],
      },
    ],
  },
};
