/* Canto 1, The Superposition of Doubt. Motifs: coin, sphere.

   The two figures share one plate and one event. The sphere is above: the
   capacity the coin has not yet spent, arm out on the equator, phase trace
   running. The coin is below on its table, spinning and blurred, holding both
   faces to the light. Across the canto the coin slows, tilts and settles while
   the sphere's arm swings to a pole and the surface closes behind it. What is
   left at the end is a flat coin and a single bright point.

   The coin's spin is keyframed rather than left to the motif's own curve. Nine
   turns across a canto means the face angle cycles nine times, so which frame
   the poster lands on is a decision, not an accident: the signature is pinned
   where the disc is foreshortened to about two fifths and the engraved face
   still reads. */

import type { CantoArt } from './types.js';

export const canto01: CantoArt = {
  legend: 'Plate I. A coin spending its sphere.',
  /* arrival and the spinning coin | interference refutes ignorance | every
     point is real state | the private phase | the cost of collapsing early */
  beats: [0, 3, 5, 8, 11],
  composition: {
    id: 'canto-01',
    canto: 1,
    seed: 'qd/01/superposition-of-doubt',
    signature: 0.56,
    plate: { wash: 'violet', stars: 250, washStrength: 1.1 },
    layers: [
      {
        motif: 'sphere',
        region: { x: 0.05, y: 0.02, w: 0.48, h: 0.66 },
        params: { radius: 0.46, pitch: 14, yaw: 0.55, meridians: 12, parallels: 5 },
        keys: [
          { at: 0, params: { opacity: 0.25 } },
          { at: 0.16, params: { opacity: 1 } },
          { at: 0.75, params: { opacity: 1 } },
          { at: 1, params: { opacity: 0.62 } },
        ],
      },
      {
        motif: 'coin',
        region: { x: 0.44, y: 0.26, w: 0.54, h: 0.72 },
        params: { radius: 0.32, pitch: 17, table: 1, ghosts: 7, shadow: 1 },
        keys: [
          /* decelerating, never looping, and pinned at the signature */
          { at: 0, params: { spin: 0 } },
          { at: 0.2, params: { spin: 3.1 } },
          { at: 0.4, params: { spin: 5.25 } },
          { at: 0.56, params: { spin: 6.431 } },
          { at: 0.78, params: { spin: 7.9 } },
          { at: 1, params: { spin: 8.62 } },
        ],
      },
    ],
  },
};
