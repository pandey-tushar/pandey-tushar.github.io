/* Canto 15, The Mind of the Machine. Motif: mirror.

   The same glass as canto 17, and the opposite verdict. There the copy fails,
   loses arcs, grains over and comes apart, and the failure is the law of the
   world holding. Here the copy succeeds. Ewin Tang was handed a famous quantum
   recommendation algorithm and found its classical shadow, an ordinary
   algorithm doing the same work in comparable time, and from 2018 that method
   dissolved one claimed exponential advantage after another.

   So fidelity runs the wrong way for once. It starts low, where the quantum
   side still looks like the only thing that could have made this, and it
   climbs to one, where the far side of the glass is exactly as sharp as the
   near side. The grain that was scattered around the reflection resolves into
   the reflection. Nothing shatters, and the bruise is held at zero for the
   whole canto, because no law was violated here and nothing was damaged. Only
   a claim was.

   Two identical faces, and that is the bad news. A plate that had to be told
   which side was the original would be reading the canto correctly. */

import type { CantoArt } from './types.js';

export const canto15: CantoArt = {
  legend: 'Plate XV. The copy that came out perfect, which was the disappointment.',
  /* two miracles do not always multiply | the barren plateau, and no in
     between | the classical shadow | two hopes remain, real and narrow | ask
     which one should be teaching */
  beats: [0, 2, 4, 8, 11],
  composition: {
    id: 'canto-15',
    canto: 15,
    seed: 'qd/15/two-minds-meeting',
    signature: 0.9,
    plate: { wash: 'violet', stars: 205, washStrength: 1 },
    layers: [
      {
        motif: 'mirror',
        params: { radius: 0.25, split: 0.48, glass: 1, rays: 1, shatter: 0, bruise: 0, distortion: 0 },
        keys: [
          { at: 0, params: { fidelity: 0.3, grain: 0.55 } },
          { at: 0.5, params: { fidelity: 0.72, grain: 0.3 } },
          { at: 0.84, params: { fidelity: 1, grain: 0 } },
          { at: 1, params: { fidelity: 1, grain: 0 } },
        ],
      },
    ],
  },
};
