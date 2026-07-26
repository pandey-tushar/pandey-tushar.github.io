/* Canto 6, The Machines That Are. Motif: sphere, five times.

   "There are five families, and each is strong where the others are weak." So
   the plate is a survey: five bodies on one field, at five magnitudes, each
   drawn as the instrument it is. This is the one place in the book where the
   astronomical half of the stance does the whole job, because a census is
   exactly what an astronomical plate is for.

   Each body is drawn from what the text says about that family, and the
   drawing is the only claim being made:

     the fast one       dense graticule, a long phase trace, the arm moving
     the accurate one   fewest lines, the sharpest arm, almost no trace
     the numerous one   the largest body and the most populated surface
     the cold bet       beautiful limb, faint graticule, a half strength arm
     the unconfirmed    a limb, and nothing inside it, and no arm at all

   They arrive in the order the Oracle names them, which is why each layer has
   its own span. The fifth never rises above two fifths opacity: after years
   and one retracted paper, no one has shown these states are what they are
   claimed to be, and a plate that drew it as bright as the other four would be
   telling the reader something the canto refuses to tell him. */

import type { CantoArt } from './types.js';

export const canto06: CantoArt = {
  legend: 'Plate VI. Five families, counted honestly, at their true magnitudes.',
  /* tell me what is built | the fast ones and the accurate ones | the numerous
     ones | the ratio that already fell | where the field lies to itself */
  beats: [0, 2, 4, 6, 9],
  composition: {
    id: 'canto-06',
    canto: 6,
    seed: 'qd/06/the-machines-that-are',
    signature: 0.88,
    plate: { wash: 'violet', stars: 285, washStrength: 0.75 },
    layers: [
      {
        /* superconducting circuits: fast, printed, and expensive per logical */
        motif: 'sphere',
        region: { x: 0.03, y: 0.14, w: 0.30, h: 0.46 },
        params: {
          radius: 0.44, meridians: 12, parallels: 4, pitch: 8, yaw: 0.4,
          theta: 1.2, phi: 2.1, trace: 0.92, traceTurns: 2.4, collapse: 0,
          graticule: 1, equator: 1, vector: 1,
        },
        keys: [{ at: 0, params: { opacity: 0.2 } }, { at: 0.14, params: { opacity: 1 } }],
      },
      {
        /* trapped ions: fewest lines, the exact arm, two to one */
        motif: 'sphere',
        region: { x: 0.30, y: 0.03, w: 0.24, h: 0.36 },
        span: [0.14, 1],
        params: {
          radius: 0.4, meridians: 8, parallels: 3, pitch: 34, yaw: -0.3,
          theta: 0.92, phi: 0.6, trace: 0.22, traceTurns: 0.6, collapse: 0,
          graticule: 1, equator: 1, vector: 1,
        },
        keys: [{ at: 0, params: { opacity: 0 } }, { at: 0.22, params: { opacity: 1 } }],
      },
      {
        /* neutral atoms: the largest and most populated */
        motif: 'sphere',
        region: { x: 0.58, y: 0.16, w: 0.37, h: 0.62 },
        span: [0.3, 1],
        params: {
          radius: 0.46, meridians: 16, parallels: 6, pitch: 13, yaw: 0.85,
          theta: 1.72, phi: 4.2, trace: 0.5, traceTurns: 1.5, collapse: 0,
          graticule: 1, equator: 1, vector: 1,
        },
        keys: [{ at: 0, params: { opacity: 0 } }, { at: 0.24, params: { opacity: 1 } }],
      },
      {
        /* photonics: the architecture is beautiful, the delivery is not */
        motif: 'sphere',
        region: { x: 0.16, y: 0.54, w: 0.26, h: 0.44 },
        span: [0.46, 1],
        params: {
          radius: 0.42, meridians: 7, parallels: 2, pitch: 29, yaw: -0.75,
          theta: 1.42, phi: 5.4, trace: 0.66, traceTurns: 1.1, collapse: 0,
          graticule: 0.5, equator: 0.3, vector: 0.55,
        },
        keys: [{ at: 0, params: { opacity: 0 } }, { at: 0.3, params: { opacity: 0.85 } }],
      },
      {
        /* topological: a limb, and no evidence inside it */
        motif: 'sphere',
        region: { x: 0.46, y: 0.58, w: 0.22, h: 0.38 },
        span: [0.62, 1],
        params: {
          radius: 0.36, meridians: 5, parallels: 2, pitch: 20, yaw: 0.2,
          theta: 1.5, phi: 0, trace: 0, traceTurns: 0, collapse: 0,
          graticule: 0.12, equator: 0, vector: 0,
        },
        keys: [{ at: 0, params: { opacity: 0 } }, { at: 0.5, params: { opacity: 0.42 } }],
      },
    ],
  },
};
