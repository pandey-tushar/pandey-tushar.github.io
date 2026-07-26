/* Canto 21, The Race of Nations. Motif: fire.

   "Think of it instead as a fire in the house. It cooks your meal and it can
   take the roof, and the only wisdom is to know at every moment which of the
   two it is doing."

   One motif and one question, and the question is answered differently at
   every scroll position, which is the only reason this canto can be a single
   figure. The money arrives as intensity and it only ever rises. Containment
   is what the field does with it: nearly closed while the seed is still all
   cost and no harvest, falling hard through the middle where the race rewards
   the press release over the footnote, and coming back part of the way at the
   end because the same money that speeds the science pays for the antibody
   against its own exaggerations.

   Part of the way. Not all of it. The plate must not end with the house safe,
   because the canto does not.

   The signature is pinned at the moment the tongues are exactly at the ridge.
   That frame is the canto's sentence with nothing added: at this instant you
   genuinely cannot tell whether it is cooking the meal or taking the roof, and
   the reader has to decide, which is what he is being asked to do. */

import type { CantoArt } from './types.js';

export const canto21: CantoArt = {
  legend: 'Plate XXI. Cooking the meal, or taking the roof.',
  /* do kings buy growth or noise | a seed is all cost until the season turns |
     name the thrones | does a race build truth or bend it | a fire in the
     house */
  beats: [0, 2, 4, 6, 11],
  composition: {
    id: 'canto-21',
    canto: 21,
    seed: 'qd/21/the-race-of-nations',
    signature: 0.62,
    plate: { wash: 'rose', stars: 190, washStrength: 1 },
    layers: [
      {
        motif: 'fire',
        params: { spread: 0.6, tongues: 13, embers: 92, vessel: 1, hearth: 1 },
        keys: [
          /* the gold, which only ever rises */
          { at: 0, params: { intensity: 0.32, plume: 0.6 } },
          { at: 1, params: { intensity: 1, plume: 2 } },
          /* what the field does with it */
          { at: 0, params: { containment: 0.95 } },
          { at: 0.3, params: { containment: 0.74 } },
          { at: 0.72, params: { containment: 0.24 } },
          { at: 1, params: { containment: 0.5 } },
          { at: 0, params: { phase: 0 } },
          { at: 1, params: { phase: 7 } },
        ],
      },
    ],
  },
};
