/* Canto 9, The Wall of Wires. Motif: wall.

   One motif, because the canto has one argument. The wall never breaks. It
   thins from the middle into an arch as the price stops being paid, two
   modules appear inside the arch, and a photonic link lights between them. The
   heat at the flange dims while that happens and then comes partly back at the
   end, because the last turn of the canto is the power bill that is still
   three orders of magnitude away from payable. */

import type { CantoArt } from './types.js';

export const canto09: CantoArt = {
  legend: 'Plate IX. Not a wall. A bill, and the arch that stopped paying it.',
  /* the wall, called a bill | controllers into the cold | do not build one
     chip | the link is lossy, so purify | where it still hurts: the power */
  beats: [0, 2, 5, 8, 11],
  composition: {
    id: 'canto-09',
    canto: 9,
    seed: 'qd/09/wall-of-wires',
    signature: 0.74,
    plate: { wash: 'gold', stars: 150, washStrength: 0.8 },
    layers: [
      {
        motif: 'wall',
        params: { density: 66, ranks: 4, gap: 0.5, spread: 1, floor: 0.84 },
        keys: [
          /* the heat is the bill: high, falling as the architecture changes,
             and climbing again for the last beat where the cost is still due */
          { at: 0, params: { heat: 1 } },
          { at: 0.62, params: { heat: 0.5 } },
          { at: 0.86, params: { heat: 0.55 } },
          { at: 1, params: { heat: 0.85 } },
        ],
      },
    ],
  },
};
