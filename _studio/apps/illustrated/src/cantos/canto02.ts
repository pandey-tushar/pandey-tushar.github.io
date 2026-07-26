/* Canto 2, The Web of All Things. Motifs: lattice, thread.

   The lattice is the web; the threads crossing its middle are the pair carried
   to opposite ends of the Earth. The threads pull taut and stay silent, and
   nothing travels along them: they only end up agreeing. Then monogamy
   arrives. One bond goes gold, an envelope closes around the pair, and every
   other edge either node had is starved by exactly what the bond gained. */

import type { CantoArt } from './types.js';

export const canto02: CantoArt = {
  legend: 'Plate II. One state, shared, and what it costs every other bond.',
  /* two prepared as one | the bond is silent | it endures in the correlation |
     the faithfulness that cannot be spent twice */
  beats: [0, 4, 7, 10],
  composition: {
    id: 'canto-02',
    canto: 2,
    seed: 'qd/02/web-of-all-things',
    signature: 0.66,
    plate: { wash: 'cyan', stars: 210 },
    layers: [
      {
        /* figure a: the web, and the one bond that takes everything */
        motif: 'lattice',
        region: { x: 0, y: 0, w: 1, h: 0.79 },
        params: { nodes: 58, order: 0.5, reach: 1.55, spread: 0.88, nodeScale: 1 },
        keys: [
          { at: 0, params: { opacity: 0.9 } },
          { at: 1, params: { opacity: 0.78 } },
        ],
      },
      {
        /* figure b, the detail strip: the same pair carried to opposite ends
           of the Earth. Three threads, not a curtain of them, because the
           canto is about two things and what they cost a third. */
        motif: 'thread',
        region: { x: 0.36, y: 0.6, w: 0.28, h: 0.38 },
        params: { count: 2, spread: 0.78, height: 0.34, gold: 1, anchors: 1, width: 1.5, glow: 1, tension: 0.6 },
        keys: [
          { at: 0, params: { opacity: 0, pairing: 0.1 } },
          { at: 0.16, params: { opacity: 0.95 } },
          /* the third bond is cut at exactly the moment the pair goes gold */
          { at: 0.42, params: { sever: 0 } },
          { at: 0.66, params: { sever: 0.55, pairing: 0.3 } },
          { at: 1, params: { opacity: 1, sever: 0.6, pairing: 0.34 } },
        ],
      },
    ],
  },
};
