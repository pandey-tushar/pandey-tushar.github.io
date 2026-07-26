/* Canto 19, The Living Qubit. Motifs: dial, lattice.

   The canto's first story dissolves and its second one stands, so the plate
   draws the one that stands. A compass, and the pair of spins that turns it.

   The needle moves almost nothing across the whole canto, a tenth of a turn,
   because that is the honest magnitude: Earth's field is fifty microtesla and
   all it does is bias a chemical reaction one way rather than the other. A
   compass that swung hard would be drawing the legend rather than the physics.
   The tremble never settles either. It falls by half and stops there, since
   this is a warm wet noisy place and the coherence that matters is measured in
   microseconds, not in seconds held quiet.

   Beside it, the radical pair: four atoms of a cryptochrome, one bond going
   gold as the canto goes on, drawn with the same figure canto 7 uses for the
   nitrogen and the vacancy sitting next to it. A pair of sites in a molecule
   means the same thing in both places, which is the motif system working as
   intended rather than a coincidence.

   Nothing is cut on this plate and nothing needs to be. The whole point of the
   closing argument is that biology never asked for the fragile kind of
   coherence, so there is no severance anywhere in the picture. */

import type { CantoArt } from './types.js';

export const canto19: CantoArt = {
  legend: 'Plate XIX. A tenth of a turn, which is all the field was ever asked to give.',
  /* did life beat us to it | the leaf, and the story that dissolved | a crack
     left in the word | the bird, held lightly | not the same coherence */
  beats: [0, 2, 4, 7, 9],
  composition: {
    id: 'canto-19',
    canto: 19,
    seed: 'qd/19/the-living-qubit',
    signature: 0.78,
    plate: { wash: 'violet', stars: 250, washStrength: 0.85 },
    layers: [
      {
        motif: 'dial',
        region: { x: 0.3, y: 0.03, w: 0.56, h: 0.94 },
        params: { radius: 0.44, ticks: 32, major: 8, rings: 2, noise: 0.13, glow: 0.8, face: 1, squeeze: 0 },
        keys: [
          { at: 0, params: { needle: 0.015, tremble: 0.95, trace: 0, reading: 0.3 } },
          { at: 0.6, params: { tremble: 0.62 } },
          { at: 1, params: { needle: 0.105, tremble: 0.46, trace: 0.28, reading: 0.9 } },
        ],
      },
      {
        /* the radical pair in the protein: two sites of a small molecule, one
           bond, and the same figure canto 7 uses for the nitrogen and its
           vacancy. Four atoms, because a cryptochrome radical pair is a
           compound and not a web. */
        motif: 'lattice',
        region: { x: 0.03, y: 0.6, w: 0.24, h: 0.34 },
        span: [0.38, 1],
        params: {
          nodes: 4, order: 0.45, reach: 1.6, spread: 0.6, nodeScale: 2.4,
          envelope: 1, glow: 1, coupling: 1, breaks: 0,
        },
        keys: [
          { at: 0, params: { opacity: 0, highlight: 0.1 } },
          { at: 0.3, params: { opacity: 1 } },
          { at: 1, params: { opacity: 1, highlight: 0.95 } },
        ],
      },
    ],
  },
};
