/* Canto 22, The Universe as a Qubit. Motifs: coin, sphere.

   Plate I run backwards, and mirrored, so the reader recognises it before he
   works out why. There the coin slowed, tilted and settled while the sphere's
   arm swung to a pole and the surface closed behind it. Here the coin comes
   off the table, the tilt goes out of it, the ghost rims come back as it picks
   up its spin, and the sphere's arm leaves the pole for the equator while the
   graticule, the equator and the trace all come back up.

   That is the canto's argument and it is not a metaphor: "The future is not
   written somewhere ahead of you, finished and sealed and waiting only to be
   read. It is a superposition of everything it could still become, and it
   stays that way until someone acts."

   The two figures swap sides, coin left and sphere right, because the book
   should end facing the other way. The signature is pinned late, where the
   coin is back on its edge and holding both faces to the light and the sphere
   is fully open, so the last plate in the edition is the first one undone. */

import type { CantoArt } from './types.js';

export const canto22: CantoArt = {
  legend: 'Plate XXII. The coin back on its edge, and nothing yet asked of it.',
  /* take me to the far edge | is gravity itself quantum | the wormhole that
     was not one | the gentler wonders | what I will do */
  beats: [0, 2, 5, 7, 9],
  composition: {
    id: 'canto-22',
    canto: 22,
    seed: 'qd/22/universe-as-a-qubit',
    signature: 0.88,
    plate: { wash: 'violet', stars: 300, washStrength: 1.05 },
    layers: [
      {
        motif: 'coin',
        region: { x: 0.02, y: 0.24, w: 0.54, h: 0.74 },
        params: { radius: 0.32, pitch: 17, table: 1, ghosts: 7, shadow: 1 },
        keys: [
          /* the settled coin, coming back up onto its edge */
          { at: 0, params: { tilt: 0.94, settle: 1, spin: 0, lift: 0 } },
          { at: 0.34, params: { tilt: 0.72, settle: 0.78, spin: 0.9 } },
          { at: 0.66, params: { tilt: 0.3, settle: 0.4, spin: 3.1 } },
          { at: 0.88, params: { tilt: 0.06, settle: 0.1, spin: 5.437, lift: 0.05 } },
          { at: 1, params: { tilt: 0.02, settle: 0, spin: 6.4, lift: 0.07 } },
        ],
      },
      {
        motif: 'sphere',
        region: { x: 0.47, y: 0.03, w: 0.5, h: 0.72 },
        params: { radius: 0.46, pitch: 14, yaw: -0.5, meridians: 12, parallels: 5, vector: 1 },
        keys: [
          /* the surface coming back */
          { at: 0, params: { theta: 0.12, collapse: 0.88, graticule: 0.42, equator: 0.15, trace: 0.06 } },
          { at: 0.4, params: { theta: 0.7, collapse: 0.5, graticule: 0.7, equator: 0.5, trace: 0.4 } },
          { at: 1, params: { theta: 1.6, collapse: 0, graticule: 1, equator: 1, trace: 0.92 } },
        ],
      },
    ],
  },
};
