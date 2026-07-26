/* Canto 7, The Heresy of Warmth. Motifs: wall, lattice.

   Two things on one plate, because the canto is one law with two answers. On
   the left the chandelier: the wall of coax and the cold under it, drawn with
   its heat high, because the transmon really does need that. On the right the
   diamond, and this is the exact figure the text gives: "a single nitrogen
   sitting where a carbon should be, with an empty seat beside it."

   The lattice motif already draws precisely that pair. Its chosen bond is an
   ordinary length edge near the middle of the field, and as the highlight
   rises the two nodes it joins go gold and an envelope closes around them
   while every other edge either node had is starved. In canto 2 that figure is
   monogamy. Here it is a substituted atom and the vacancy next to it, holding
   a spin in open air, and the reading runs the other way for free.

   The wall dims but does not go out, and the crystal's other couplings break
   rather than form, because the honest ending is that the wall moved rather
   than vanished. It now stands at the handshake between two warm qubits, and
   nobody has yet solved the coupling. */

import type { CantoArt } from './types.js';

export const canto07: CantoArt = {
  legend: 'Plate VII. The chandelier, and the flaw in the gem that needs none of it.',
  /* the cold was the god | the diamond keeps its spin in open air | watch that
     word real | the wall moved rather than vanished | the heresy spoken
     exactly as far as the evidence carries */
  beats: [0, 2, 5, 8, 12],
  composition: {
    id: 'canto-07',
    canto: 7,
    seed: 'qd/07/heresy-of-warmth',
    signature: 0.7,
    plate: { wash: 'rose', stars: 175, washStrength: 0.85 },
    layers: [
      {
        /* the road that was paved first, and its bill */
        motif: 'wall',
        region: { x: 0.04, y: 0.07, w: 0.4, h: 0.86 },
        params: {
          density: 96, ranks: 4, gap: 0.45, spread: 0.94, floor: 0.84,
          breach: 0, modules: 0, light: 0, connectors: 1,
        },
        keys: [
          { at: 0, params: { heat: 1, opacity: 1 } },
          { at: 1, params: { heat: 0.55, opacity: 0.85 } },
        ],
      },
      {
        /* the gem, ruled, and the vacancy beside the substituted atom */
        motif: 'lattice',
        region: { x: 0.56, y: 0.07, w: 0.4, h: 0.86 },
        span: [0.08, 1],
        params: {
          nodes: 44, order: 0.95, reach: 1.2, spread: 0.84, nodeScale: 0.9,
          envelope: 1, glow: 1, coupling: 1,
        },
        keys: [
          { at: 0, params: { opacity: 0, highlight: 0, breaks: 0 } },
          { at: 0.28, params: { opacity: 1 } },
          { at: 0.7, params: { highlight: 0.9 } },
          /* the couplings that would let two centres speak are weak and few */
          { at: 1, params: { opacity: 1, highlight: 0.9, breaks: 0.24 } },
        ],
      },
    ],
  },
};
