/* The frontispiece. Lattice, quiet, no bond chosen yet.

   It uses exactly the same machinery as a canto, which is the cheapest
   available proof that the registration point works: the cover is a
   composition, not a special case. */

import type { CantoArt } from './types.js';

export const cover: CantoArt = {
  legend: 'Frontispiece. The web, before any bond is asked to choose.',
  beats: [0],
  composition: {
    id: 'frontispiece',
    canto: 0,
    seed: 'qd/00/frontispiece',
    signature: 0.22,
    plate: { wash: 'violet', stars: 300, frame: false, washStrength: 0.7 },
    layers: [
      {
        motif: 'lattice',
        params: {
          nodes: 74, order: 0.42, reach: 1.5, spread: 0.94,
          nodeScale: 0.8, envelope: 0, highlight: 0, breaks: 0, glow: 0.4,
        },
        keys: [{ at: 0, params: { opacity: 0.62 } }, { at: 1, params: { opacity: 0.62 } }],
      },
    ],
  },
};
