/* Canto 14, The Alchemist's Return. Motif: lattice, twice, at molecular scale.

   "The dream did not die. It changed address."

   Two clusters, and the gold moves from one to the other while the reader
   scrolls. On the left the FeMo-cofactor: few atoms, loosely arranged, the
   long reach of a molecule rather than a chip, and one bright bond that is the
   whole prize. On the right the model systems that are still hard, ruled the
   way a Hubbard lattice is ruled, arriving dim and coupled to almost nothing.

   Across the canto the left cluster's highlight falls to nearly zero and the
   right one's rises, and the right one's coupling comes up with it. Nothing is
   destroyed on the left. The molecule is still there, drawn at the same size,
   with the same atoms. It simply stops being the thing the plate is lit
   around, which is exactly what happened to it: a problem solved is a problem
   solved, whoever holds the pen.

   The lattice motif is used here at a scale it has not been used at before,
   ten nodes instead of seventy, which is the difference between a web and a
   compound. Same code, same seed discipline, a different noun again. */

import type { CantoArt } from './types.js';

export const canto14: CantoArt = {
  legend: 'Plate XIV. The prize, and the address the dream moved to.',
  /* the jewel of chemistry | answered by an ordinary computer | one kilocalorie
     per mole | what survives, smaller and stranger | a hope wearing an honest
     label */
  beats: [0, 2, 4, 6, 11],
  composition: {
    id: 'canto-14',
    canto: 14,
    seed: 'qd/14/the-alchemists-return',
    signature: 0.8,
    plate: { wash: 'gold', stars: 185, washStrength: 0.8 },
    layers: [
      {
        /* the cofactor */
        motif: 'lattice',
        region: { x: 0.03, y: 0.1, w: 0.44, h: 0.8 },
        params: {
          nodes: 10, order: 0.34, reach: 1.75, spread: 0.62, nodeScale: 2.6,
          envelope: 1, glow: 1, coupling: 1, breaks: 0,
        },
        keys: [
          { at: 0, params: { opacity: 1, highlight: 0.9 } },
          { at: 0.55, params: { highlight: 0.5 } },
          { at: 1, params: { opacity: 0.5, highlight: 0.06 } },
        ],
      },
      {
        /* the model systems built to be hard */
        motif: 'lattice',
        region: { x: 0.53, y: 0.1, w: 0.44, h: 0.8 },
        seed: 'qd/14/the-alchemists-return/hubbard',
        params: {
          nodes: 12, order: 0.8, reach: 1.5, spread: 0.7, nodeScale: 1.9,
          envelope: 1, glow: 1, breaks: 0,
        },
        keys: [
          { at: 0, params: { opacity: 0.4, highlight: 0.04, coupling: 0.3 } },
          { at: 0.55, params: { highlight: 0.42 } },
          { at: 1, params: { opacity: 1, highlight: 0.92, coupling: 1 } },
        ],
      },
    ],
  },
};
