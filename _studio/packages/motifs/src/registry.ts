/* The motif vocabulary. Nine forms, drawn from images the text already uses
   repeatedly. A canto is a composition of one or two of these at specific
   parameters, never a new artist. */

import { coin } from './motifs/coin.js';
import { sphere } from './motifs/sphere.js';
import { lattice } from './motifs/lattice.js';
import { wall } from './motifs/wall.js';
import { thread } from './motifs/thread.js';
import { fire } from './motifs/fire.js';
import { lock } from './motifs/lock.js';
import { mirror } from './motifs/mirror.js';
import { dial } from './motifs/dial.js';
import type { Motif, Params } from './types.js';

export const MOTIFS = { coin, sphere, lattice, wall, thread, fire, lock, mirror, dial } as const;

export type MotifId = keyof typeof MOTIFS;

export const MOTIF_IDS = Object.keys(MOTIFS) as MotifId[];

/** Source in the text, kept next to the code so the mapping stays reviewable. */
export const MOTIF_SOURCES: Record<MotifId, string> = {
  coin: 'canto 1, spinning on edge',
  sphere: 'canto 1, the Bloch sphere',
  lattice: 'entanglement, cover art',
  wall: 'canto 9, the wall of wires',
  thread: 'connection, correlation',
  fire: 'canto 21, the fire in the house',
  lock: 'canto 16, the unsealing',
  mirror: 'copying, no-cloning',
  dial: 'canto 18, the instruments that listen',
};

export function getMotif(id: MotifId): Motif<Params> {
  return MOTIFS[id] as Motif<Params>;
}
