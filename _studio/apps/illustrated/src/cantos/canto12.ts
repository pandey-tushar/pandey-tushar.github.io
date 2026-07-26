/* Canto 12, The Skeptic's Gift. Motif: lattice.

   One motif, because the canto ends on one live doubt and the doubt has an
   exact shape. Scattered independent faults are what the surface code was
   built for, and the plate spends its first two thirds acquiring them: the
   breaks climb, the field absorbs them, nothing is in trouble. Then the swath
   arrives. About once an hour a correlated burst, most likely a cosmic ray,
   flips qubits across the whole chip at once, and the code's assumption of
   independent errors has no answer ready for a blow that lands everywhere.

   The two kinds of failure had to look different or the plate would be saying
   nothing. A scattered break is a bond cut at its middle. A struck node is
   marked with a cross, and every bond it had goes with it, and one line runs
   the length of the plate through all of them. That is the difference between
   a fault the pattern can find and a fault that arrives as a single event.

   This is the motif's one new parameter and this canto is why it exists. */

import type { CantoArt } from './types.js';

export const canto12: CantoArt = {
  legend: 'Plate XII. The scatter it was built for, and the one line it was not.',
  /* two serious people say it is impossible | state their case at full
     strength | the good skeptic gambles | two doubts remain alive | he tells
     the work where to point its lamp */
  beats: [0, 2, 6, 11, 13],
  composition: {
    id: 'canto-12',
    canto: 12,
    seed: 'qd/12/the-skeptics-gift',
    signature: 0.92,
    plate: { wash: 'rose', stars: 215, washStrength: 0.9 },
    layers: [
      {
        motif: 'lattice',
        params: {
          nodes: 84, order: 0.96, reach: 1.3, spread: 0.94, nodeScale: 0.74,
          envelope: 0, highlight: 0, glow: 0.5, coupling: 1,
          burstAt: 0.46, burstWidth: 0.85,
        },
        keys: [
          { at: 0, params: { opacity: 0.9, breaks: 0, burst: 0 } },
          /* the faults the pattern is designed to absorb */
          { at: 0.62, params: { breaks: 0.2, burst: 0 } },
          /* the one it is not */
          { at: 0.78, params: { burst: 0.42 } },
          { at: 1, params: { opacity: 0.95, breaks: 0.24, burst: 0.95 } },
        ],
      },
    ],
  },
};
