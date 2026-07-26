/* Canto 16, The Unsealing. Motifs: lock, lattice.

   Shor does not cut the rings. He finds the rhythm, so the period comb lights
   first and only then do the ward gaps rotate into line and the corridor open.
   The lattice enters last and quietly: FIPS 203 and 204 are built on lattices,
   so the wards do not simply fall away, they reassemble as the mathematics the
   next lock is made of. It arrives dim, because the honest answer in the text
   is that the new locks are only unbroken so far. */

import type { CantoArt } from './types.js';

export const canto16: CantoArt = {
  legend: 'Plate XVI. The lock was never a wall. It was a corridor.',
  /* the lock and the corridor | the number that lets you sleep is not a
     constant | Q-day and harvest now | the rebuilding that began first |
     only unbroken so far */
  beats: [0, 2, 4, 6, 9],
  composition: {
    id: 'canto-16',
    canto: 16,
    seed: 'qd/16/the-unsealing',
    signature: 0.68,
    plate: { wash: 'rose', stars: 190, washStrength: 0.9 },
    layers: [
      {
        motif: 'lock',
        params: { complexity: 5, teeth: 30, period: 7, radius: 0.36 },
        keys: [
          { at: 0, params: { opacity: 1 } },
          { at: 1, params: { opacity: 0.9 } },
        ],
      },
      {
        motif: 'lattice',
        span: [0.72, 1],
        params: { nodes: 44, order: 0.85, reach: 1.4, spread: 0.92, nodeScale: 0.7, envelope: 0, highlight: 0, breaks: 0 },
        keys: [
          { at: 0, params: { opacity: 0, coupling: 0 } },
          { at: 1, params: { opacity: 0.5, coupling: 0.8 } },
        ],
      },
    ],
  },
};
