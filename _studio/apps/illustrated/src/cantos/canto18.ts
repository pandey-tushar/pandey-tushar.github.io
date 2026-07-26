/* Canto 18, The Deeper Instruments. Motif: dial, three times.

   This canto is why the library has a dial at all. The book is full of
   measurement and the vocabulary had a state, a mechanism and a question in
   it, and nothing that reads. The sphere is what is being measured. The dial
   is what does the measuring, and none of the other eight forms could be bent
   into that without lying about what they mean.

   Three instruments, at three sizes, each squeezed a different amount and each
   pointing somewhere else. "Squeezing does not break the uncertainty
   principle; it obeys it to the letter. What it does is pour the unavoidable
   haze into a direction where no one is looking." The blob at each needle tip
   has one axis divided and the other multiplied by the same factor, so its
   area is identical at every squeeze on the plate. Three ellipses of the same
   area, turned three ways, is the sentence "each chooses where to be ignorant,
   so that somewhere else it may be exact" with nothing left over.

   The great one squeezes hardest and steadies as it does. The clock arrives
   second, almost still, with a long arc of readings already behind it. The
   gravimeter arrives last and never stops trembling. */

import type { CantoArt } from './types.js';

export const canto18: CantoArt = {
  legend: 'Plate XVIII. Three instruments, one area of haze, three directions to spend it.',
  /* instruments, not engines | the clock and the helmet | below the limit the
     world seemed to set | it obeys the principle to the letter | the
     revolution that arrives first */
  beats: [0, 2, 4, 6, 10],
  composition: {
    id: 'canto-18',
    canto: 18,
    seed: 'qd/18/the-deeper-instruments',
    signature: 0.82,
    plate: { wash: 'cyan', stars: 230, washStrength: 0.9 },
    layers: [
      {
        /* the great detector */
        motif: 'dial',
        region: { x: 0.3, y: 0.06, w: 0.4, h: 0.88 },
        params: { radius: 0.46, ticks: 72, major: 6, rings: 3, noise: 0.15, glow: 1, face: 1 },
        keys: [
          { at: 0, params: { squeeze: 0, tremble: 0.95, trace: 0, needle: -0.06, reading: 0.25 } },
          { at: 0.5, params: { squeeze: 0.45, tremble: 0.6 } },
          { at: 1, params: { squeeze: 0.95, tremble: 0.22, trace: 0.8, needle: 0.1, reading: 1 } },
        ],
      },
      {
        /* the clock, which has been running a long time */
        motif: 'dial',
        region: { x: 0.03, y: 0.3, w: 0.24, h: 0.44 },
        span: [0.18, 1],
        params: {
          radius: 0.44, ticks: 48, major: 4, rings: 2, noise: 0.1, glow: 0.5,
          face: 0.9, needle: 0.42, tremble: 0.12, squeeze: 0.12, reading: 0.85,
        },
        keys: [
          { at: 0, params: { opacity: 0, trace: 0.2 } },
          { at: 1, params: { opacity: 0.92, trace: 0.96 } },
        ],
      },
      {
        /* the gravimeter, which never stops feeling the ground */
        motif: 'dial',
        region: { x: 0.73, y: 0.3, w: 0.24, h: 0.44 },
        span: [0.4, 1],
        params: {
          radius: 0.44, ticks: 36, major: 3, rings: 2, noise: 0.22, glow: 0.6,
          face: 0.9, needle: -0.28, tremble: 0.55, squeeze: 0.62, reading: 0.8,
        },
        keys: [
          { at: 0, params: { opacity: 0, trace: 0 } },
          { at: 1, params: { opacity: 0.92, trace: 0.4 } },
        ],
      },
    ],
  },
};
