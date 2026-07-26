/* Canto 10, The Cloning Forbidden. Motifs: lattice, thread.

   Canto 17 draws the prohibition itself, so this plate draws what the
   prohibition permits, which is the whole turn of this canto.

   "You do not copy the state; you spread it. You smear one qubit's information
   across many, woven into their shared entanglement, so that no single one of
   them holds a copy you could point to." The lattice is that smear, and it is
   drawn fine and dense rather than as a constellation for exactly that reason:
   the reader must not be able to point at a node and say the state is there.

   Over it, two cords, and the sending is the difference between them. "You
   spend a shared entangled pair and two ordinary bits of message, and the
   state vanishes from your hand and reappears in another's." The upper cord is
   the pair: gold, pulled straight, spent but intact. The lower one is the
   state, and it is cut through the middle with both ends curling back.

   The curl is the reason the theorem is obeyed. The original is destroyed in
   the very act of sending, which is precisely why no copy was ever made, and
   both ends move although nothing travelled between them. */

import type { CantoArt } from './types.js';

export const canto10: CantoArt = {
  legend: 'Plate X. Not copied. Spread, and then sent by being given up.',
  /* one accident away from gone | say precisely what is forbidden | you do not
     copy it, you spread it | a gift wearing the mask of a prohibition | the
     law handed you the blueprint */
  beats: [0, 3, 6, 10, 15],
  composition: {
    id: 'canto-10',
    canto: 10,
    seed: 'qd/10/the-cloning-forbidden',
    signature: 0.86,
    plate: { wash: 'violet', stars: 240, washStrength: 0.95 },
    layers: [
      {
        /* everywhere and nowhere */
        motif: 'lattice',
        params: {
          nodes: 112, order: 0.56, reach: 1.28, spread: 0.96, nodeScale: 0.42,
          envelope: 0, highlight: 0, glow: 0.4, breaks: 0,
        },
        keys: [
          { at: 0, params: { opacity: 0.42, coupling: 0.22 } },
          { at: 1, params: { opacity: 0.86, coupling: 1 } },
        ],
      },
      {
        /* the pair that is spent, and never breaks */
        motif: 'thread',
        region: { x: 0.08, y: 0.02, w: 0.84, h: 0.66 },
        params: {
          count: 1, spread: 0.88, height: 0.02, gold: 1, width: 2.4,
          anchors: 1, glow: 1, pairing: 0, sever: 0,
        },
        keys: [
          { at: 0, params: { tension: 0.2, opacity: 0.5 } },
          { at: 1, params: { tension: 0.98, opacity: 1 } },
        ],
      },
      {
        /* the state, and the sending that destroys it */
        motif: 'thread',
        region: { x: 0.08, y: 0.3, w: 0.84, h: 0.66 },
        seed: 'qd/10/the-cloning-forbidden/sent',
        params: {
          count: 1, spread: 0.88, height: 0.02, gold: 1, width: 3,
          anchors: 1, glow: 1, pairing: 0,
        },
        keys: [
          { at: 0, params: { tension: 0.2, sever: 0 } },
          { at: 0.62, params: { tension: 0.9, sever: 0 } },
          { at: 0.7, params: { sever: 1 } },
          { at: 1, params: { tension: 0.98, sever: 1 } },
        ],
      },
    ],
  },
};
