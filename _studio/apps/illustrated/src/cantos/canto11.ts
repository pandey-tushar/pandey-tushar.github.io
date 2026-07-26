/* Canto 11, The Speed of the Possible. Motif: thread, twice.

   "The quantum part sat waiting on the classical part. What held everything
   back was never the qubits. It was the clerk, counting their mistakes by
   hand."

   Nine gates and one clerk, tied to the same two posts. The gates are gold,
   thin and pulled straight from the first frame, because they were never the
   slow thing: they run three or four orders of magnitude short of the ceiling
   physics set and nothing in the canto asks them to hurry. The clerk is the
   single heavy cyan cord below them, and it is drawn with a bow rather than
   mere slack so that the sag is unmistakably a delay and not a stylistic
   droop. Across the canto the bow comes up by two thirds and never reaches the
   others, which is the honest ending: the distance closes, though not this
   year and not by wishing.

   Both ranks share one span, so the picture cannot be read as two separate
   things happening. It is one machine, and one part of it is holding the rest
   down.

   One more line, at the very top of the plate and almost too faint to see:
   the ceiling physics set. Nothing on this plate comes anywhere near it, and
   that is the canto's first claim made in a single thread. */

import type { CantoArt } from './types.js';

const SPAN = { x: 0.06, y: 0.16, w: 0.88, h: 0.78 };

export const canto11: CantoArt = {
  legend: 'Plate XI. Nine quick gates, and the clerk they all wait on.',
  /* two stories, both false | the slow thing is classical | only the
     forgetting is dear | only early | strip away both fantasies */
  beats: [0, 4, 8, 11, 15],
  composition: {
    id: 'canto-11',
    canto: 11,
    seed: 'qd/11/speed-of-the-possible',
    signature: 0.44,
    plate: { wash: 'cyan', stars: 200, washStrength: 0.8 },
    layers: [
      {
        /* the ceiling physics set, ten orders of magnitude over our heads.
           Drawn once, faint, at the top of the plate, and nothing on this
           plate comes anywhere near it. That is the canto's first claim and it
           costs one thread to make. */
        motif: 'thread',
        region: { x: 0.06, y: 0.02, w: 0.88, h: 0.1 },
        seed: 'qd/11/speed-of-the-possible/ceiling',
        params: {
          count: 1, spread: 0.94, height: 0.02, gold: 1, width: 0.8,
          anchors: 0.4, glow: 0, sever: 0, pairing: 0, tension: 1,
        },
        keys: [{ at: 0, params: { opacity: 0.2 } }, { at: 1, params: { opacity: 0.28 } }],
      },
      {
        /* the gates */
        motif: 'thread',
        region: SPAN,
        params: {
          count: 9, spread: 0.86, height: 0.5, gold: 0.95, width: 0.9,
          anchors: 1, glow: 0.8, sever: 0, pairing: 0,
        },
        keys: [
          { at: 0, params: { tension: 0.9 } },
          { at: 1, params: { tension: 1 } },
        ],
      },
      {
        /* the accounting */
        motif: 'thread',
        region: SPAN,
        seed: 'qd/11/speed-of-the-possible/clerk',
        params: {
          count: 1, spread: 0.86, height: 0.03, gold: 0, width: 2.4,
          anchors: 0, glow: 1, sever: 0, pairing: 0, tension: 1,
        },
        keys: [
          { at: 0, params: { bow: 0.4 } },
          { at: 0.55, params: { bow: 0.3 } },
          { at: 1, params: { bow: 0.13 } },
        ],
      },
    ],
  },
};
