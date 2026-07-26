/* Canto 8, The Overhead Mirage. Motif: lattice, twice.

   "It is the easiest to wire, which is not at all the same as the cheapest to
   run. Let the qubits reach a little farther than their nearest neighbors and
   the arithmetic changes underneath you."

   Reach is a parameter of the lattice motif, so the canto's argument can be
   made by moving exactly one number and nothing else. The two panels are the
   same node count, the same order, the same seed family and the same size. The
   left one is held at nearest neighbour wiring for the whole canto. The right
   one is allowed to bend, and by the end it carries three times the bonds off
   the same silicon.

   Each panel keeps one gold pair, which is its logical qubit. That is what
   makes the plate an argument rather than a texture: the reader is looking at
   what one protected thing costs on each side, and the two sides are visibly
   the same field. The mirage was never the price. It was the assumption that
   the wiring had to lie flat. */

import type { CantoArt } from './types.js';

export const canto08: CantoArt = {
  legend: 'Plate VIII. The same silicon, and the toll that only one of them pays.',
  /* the number that broke my hope | it fell out of one code | let the
     connections bend | the assumptions gave way one by one | a shrinking wall
     is still a wall */
  beats: [0, 2, 4, 8, 11],
  composition: {
    id: 'canto-08',
    canto: 8,
    seed: 'qd/08/the-overhead-mirage',
    signature: 0.76,
    plate: { wash: 'cyan', stars: 160, washStrength: 0.7 },
    layers: [
      {
        /* laid flat, and paying for it */
        motif: 'lattice',
        region: { x: 0.05, y: 0.15, w: 0.4, h: 0.7 },
        params: {
          nodes: 60, order: 0.97, reach: 1.15, spread: 0.9, nodeScale: 0.72,
          envelope: 1, glow: 0.7, coupling: 1, breaks: 0,
        },
        keys: [
          { at: 0, params: { opacity: 0.85, highlight: 0 } },
          { at: 0.72, params: { highlight: 0.9 } },
          { at: 1, params: { opacity: 0.85, highlight: 0.9 } },
        ],
      },
      {
        /* the same field, allowed to reach */
        motif: 'lattice',
        region: { x: 0.55, y: 0.15, w: 0.4, h: 0.7 },
        seed: 'qd/08/the-overhead-mirage/bent',
        params: {
          nodes: 60, order: 0.97, spread: 0.9, nodeScale: 0.72,
          envelope: 1, glow: 0.9, coupling: 1, breaks: 0,
        },
        keys: [
          { at: 0, params: { opacity: 0.85, highlight: 0, reach: 1.15 } },
          { at: 0.34, params: { reach: 1.36 } },
          { at: 0.72, params: { highlight: 0.9 } },
          { at: 1, params: { opacity: 0.95, highlight: 0.9, reach: 1.92 } },
        ],
      },
    ],
  },
};
