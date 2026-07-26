/* Canto 13, The Entangled Earth. Motifs: sphere, thread.

   The sphere is used here as what it has always been drawn as, an instrument
   with a graticule you could read a bearing off, but with the arm and the
   trace turned off entirely. Without a state vector it stops being a qubit and
   becomes the Earth, rising past the bottom edge of the plate. That is the
   cheapest possible proof that the vocabulary is a vocabulary: the same eleven
   lines of projection say a different noun when the state is removed.

   Two links cross it. The low one is fiber, laid along the face of the world,
   and it starts badly: half its strands are cut, because by a thousand
   kilometres almost none arrive. Repeaters are not drawn as a new object, they
   are drawn as the cuts healing, since a repeater is precisely the thing that
   keeps the loss from being final.

   The high one is the sky. It hangs from the two stations by a bow rather than
   a sag, which is the second thing the thread motif learned to do, and it
   arrives late and all at once, because that is how it happened. "The sky
   turned out to be the longest strand of all, and the cheapest to hang." */

import type { CantoArt } from './types.js';

export const canto13: CantoArt = {
  legend: 'Plate XIII. The strand laid along the world, and the one hung over it.',
  /* can a state cross an ocean | no cloning forbids the amplifier, not the
     repeater | teleportation moves the description | then you go up | a new
     grammar of trust */
  beats: [0, 2, 4, 6, 9],
  composition: {
    id: 'canto-13',
    canto: 13,
    seed: 'qd/13/the-entangled-earth',
    signature: 0.82,
    plate: { wash: 'cyan', stars: 265, washStrength: 0.95 },
    layers: [
      {
        /* the world, which is a sphere with the state taken out of it */
        motif: 'sphere',
        region: { x: 0.14, y: 0.3, w: 0.72, h: 1.06 },
        params: {
          radius: 0.44, meridians: 14, parallels: 6, pitch: 12, yaw: 0.4,
          collapse: 0, vector: 0, trace: 0, theta: 1.5708, phi: 0,
        },
        keys: [
          { at: 0, params: { opacity: 0.7, graticule: 0.7, equator: 0.6 } },
          { at: 1, params: { opacity: 1, graticule: 1, equator: 1 } },
        ],
      },
      {
        /* the glass, and what the vacuum charges anything that travels */
        motif: 'thread',
        region: { x: 0.23, y: 0.66, w: 0.4, h: 0.14 },
        params: {
          count: 6, spread: 0.86, height: 0.6, gold: 0.25, width: 0.9,
          anchors: 0.5, glow: 0.5, pairing: 0.2, bow: 0.05,
        },
        keys: [
          { at: 0, params: { tension: 0.35, sever: 0.62, opacity: 0.9 } },
          { at: 0.5, params: { sever: 0.36 } },
          { at: 1, params: { tension: 0.92, sever: 0.1, opacity: 1 } },
        ],
      },
      {
        /* the longest strand, and the cheapest to hang */
        motif: 'thread',
        region: { x: 0.2, y: 0.5, w: 0.6, h: 0.23 },
        span: [0.52, 1],
        params: {
          count: 1, spread: 0.86, height: 0.04, gold: 1, width: 2.2,
          anchors: 0.55, glow: 1, sever: 0, pairing: 0, tension: 1,
        },
        keys: [
          { at: 0, params: { opacity: 0, bow: -0.2 } },
          { at: 1, params: { opacity: 1, bow: -0.8 } },
        ],
      },
    ],
  },
};
