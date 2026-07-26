/* Canto 4, The Fragile Flame. Motifs: fire, sphere.

   "No flame is promised the next hour; still, the one who cups her hands
   rightly can burn until dawn." The fire is the figure and containment is the
   cupping: it starts open and closes, and the flame it holds is smaller at the
   end than at the start. That is the honest shape of the argument. Nothing
   here defeats impermanence; the plate ends with less fire, held better.

   The sphere is the detail that names which fragility was given up. The cat
   qubit makes the bit flip rare as a comet and leaves only the phase to guard,
   so the poles stay marked for the whole canto and the equator, which is the
   phase, fades to almost nothing. The graticule dims with it. The arm never
   moves off the equator, because nothing in this canto forces an answer. */

import type { CantoArt } from './types.js';

export const canto04: CantoArt = {
  legend: 'Plate IV. The hands close. The equator goes out, and the poles keep.',
  /* the state is dying from birth | channels can be shaped | why the world
     takes the phase first | choose which fragility to accept | you cannot
     armor everything */
  beats: [0, 2, 5, 8, 11],
  composition: {
    id: 'canto-04',
    canto: 4,
    seed: 'qd/04/the-fragile-flame',
    signature: 0.68,
    plate: { wash: 'gold', stars: 165, washStrength: 0.8 },
    layers: [
      {
        motif: 'fire',
        region: { x: 0.3, y: 0.02, w: 0.68, h: 0.96 },
        params: { spread: 0.5, tongues: 9, embers: 52, vessel: 1, hearth: 1 },
        keys: [
          /* the hands closing, and the flame that is left */
          { at: 0, params: { containment: 0.2, intensity: 0.92, plume: 1.9 } },
          { at: 0.45, params: { containment: 0.52 } },
          { at: 1, params: { containment: 0.96, intensity: 0.54, plume: 1.5 } },
          { at: 0, params: { phase: 0 } },
          { at: 1, params: { phase: 5.4 } },
        ],
      },
      {
        /* which fragility is being spent, and which is kept */
        motif: 'sphere',
        region: { x: 0.01, y: 0.14, w: 0.34, h: 0.62 },
        params: {
          radius: 0.44, pitch: 18, yaw: -0.3, meridians: 9, parallels: 3,
          theta: 1.5708, collapse: 0, vector: 1, traceTurns: 1.4,
        },
        keys: [
          { at: 0, params: { opacity: 0.4, equator: 1, graticule: 1, trace: 0.9 } },
          { at: 0.2, params: { opacity: 1 } },
          { at: 1, params: { opacity: 1, equator: 0.12, graticule: 0.42, trace: 0.1 } },
        ],
      },
    ],
  },
};
