/* Canto 3, The Measured Life. Motifs: sphere, lattice.

   The canto's hinge is Minev at Yale: a quantum jump is not instantaneous, it
   has a beginning you can see, and warned by that beginning they sent a pulse
   and turned the atom back. So the sphere's arm does not go to the pole. It
   drifts most of the way, the rose arcs start closing behind it, and then it
   comes back. The collapse curve rises and falls, which is a thing no other
   plate in this book does, because no other canto reverses one.

   Nothing here is spent. The graticule stays lit and the equator holds all the
   way through, because the whole argument is that the surface survives being
   looked at. What rises instead is the trace: the weak continuous measurement
   learning the state's path without ending it.

   The lattice arrives last and only at the end, because the last turn of the
   canto is measurement-based computing, where the collapse is not the cost of
   the calculation but the calculation itself. Its edges are cut one after
   another: each qubit measured is a bond spent doing the work. */

import type { CantoArt } from './types.js';

export const canto03: CantoArt = {
  legend: 'Plate III. The jump, seen beginning, and turned back.',
  /* fear the question | there is a measurement that takes only one fact | the
     jump caught mid flight | degrees of looking | the collapse is the gate */
  beats: [0, 2, 4, 9, 12],
  composition: {
    id: 'canto-03',
    canto: 3,
    seed: 'qd/03/the-measured-life',
    signature: 0.58,
    plate: { wash: 'rose', stars: 210, washStrength: 0.85 },
    layers: [
      {
        motif: 'sphere',
        region: { x: 0.06, y: 0.04, w: 0.62, h: 0.92 },
        params: { radius: 0.44, pitch: 15, yaw: 0.42, meridians: 11, parallels: 5, vector: 1 },
        keys: [
          /* the drift toward the leap, and the pulse that undid it */
          { at: 0, params: { theta: 1.98, collapse: 0 } },
          { at: 0.3, params: { theta: 1.72, collapse: 0.14 } },
          { at: 0.58, params: { theta: 1.16, collapse: 0.6 } },
          { at: 0.76, params: { theta: 1.74, collapse: 0.16 } },
          { at: 1, params: { theta: 1.62, collapse: 0.28 } },
          /* the surface is never spent: that is the canto */
          { at: 0, params: { graticule: 1, equator: 1, trace: 0.4 } },
          { at: 1, params: { graticule: 1, equator: 0.95, trace: 0.92 } },
        ],
      },
      {
        /* the detail: a cluster state consumed one measurement at a time */
        motif: 'lattice',
        region: { x: 0.66, y: 0.32, w: 0.32, h: 0.46 },
        span: [0.34, 1],
        params: {
          nodes: 40, order: 0.86, reach: 1.2, spread: 0.9, nodeScale: 0.62,
          envelope: 0, highlight: 0, glow: 0.4, coupling: 1,
        },
        keys: [
          { at: 0, params: { opacity: 0, breaks: 0 } },
          { at: 0.3, params: { opacity: 0.8 } },
          { at: 1, params: { opacity: 0.9, breaks: 0.5 } },
        ],
      },
    ],
  },
};
