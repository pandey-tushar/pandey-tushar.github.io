/* Canto 20, The Engines of Coherence. Motifs: fire, dial.

   "Every memory you release departs as a breath of heat, and the world grows
   warmer by exactly what you chose to lose."

   Two figures on one plate and they are wired to each other. On the left a
   hearth rather than a house: the vessel is drawn faint, because nothing here
   is at risk of burning down. This is the lawful warmth of erasure and the
   embers leaving it are the bits being let go. On the right, the instrument
   that reads the price. As the fire grows the needle climbs and the arc of
   readings behind it lengthens, and the two move together for the whole canto.

   The word the canto keeps insisting on is measured. Not free, not large,
   measured. So the needle never leaves the face, the flame never leaves the
   hearth, and the plate's argument is legible in one direction only: the more
   is released, the further the needle has gone, and the receipt is exact. */

import type { CantoArt } from './types.js';

export const canto20: CantoArt = {
  legend: 'Plate XX. The warmth of letting go, and the receipt it leaves.',
  /* what does it cost me to forget | Landauer, and the one step never free |
     cells that charge together | nothing here is free | every new page written
     small */
  beats: [0, 2, 4, 8, 14],
  composition: {
    id: 'canto-20',
    canto: 20,
    seed: 'qd/20/engines-of-coherence',
    signature: 0.8,
    plate: { wash: 'gold', stars: 175, washStrength: 0.75 },
    layers: [
      {
        motif: 'fire',
        region: { x: 0.01, y: 0.04, w: 0.54, h: 0.94 },
        params: { spread: 0.5, tongues: 7, embers: 84, vessel: 0.3, hearth: 1 },
        keys: [
          { at: 0, params: { intensity: 0.34, containment: 0.42, plume: 0.75, phase: 0 } },
          { at: 1, params: { intensity: 0.86, containment: 0.24, plume: 1.35, phase: 5 } },
        ],
      },
      {
        motif: 'dial',
        region: { x: 0.58, y: 0.22, w: 0.38, h: 0.64 },
        params: { radius: 0.44, ticks: 60, major: 5, rings: 2, noise: 0.1, squeeze: 0.18, glow: 0.7, face: 1 },
        keys: [
          { at: 0, params: { needle: -0.17, tremble: 0.35, trace: 0, reading: 0.4 } },
          { at: 1, params: { needle: 0.2, tremble: 0.12, trace: 0.88, reading: 1 } },
        ],
      },
    ],
  },
};
