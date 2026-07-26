/* Canto 17, The Uncloneable Coin. Motif: mirror.

   One motif, and the composition is an asymmetry. The original coin is drawn
   at full fidelity for the whole canto and never degrades, because nothing in
   the text is done to it. Everything happens on the far side of the glass: the
   copy loses arcs, displaces strokes, grains over, and finally comes apart
   into wedges, while the glass itself carries the rose bruise the attempt
   leaves behind. The coin is engraved by the same function the coin motif
   uses in canto 1, so the thing that cannot be copied is the same object the
   book opened with. */

import type { CantoArt } from './types.js';

export const canto17: CantoArt = {
  legend: 'Plate XVII. The world refuses to make the second.',
  /* the third kind of thing | Wiesner, and how you check it | why it is not
     in your wallet | the honest die | a limitation read from the far side */
  beats: [0, 2, 4, 7, 10],
  composition: {
    id: 'canto-17',
    canto: 17,
    seed: 'qd/17/uncloneable-coin',
    signature: 0.62,
    plate: { wash: 'gold', stars: 200, washStrength: 0.85 },
    layers: [
      {
        motif: 'mirror',
        params: { radius: 0.21, split: 0.5, glass: 1, rays: 1 },
        keys: [
          { at: 0, params: { opacity: 1 } },
          { at: 1, params: { opacity: 1 } },
        ],
      },
    ],
  },
};
