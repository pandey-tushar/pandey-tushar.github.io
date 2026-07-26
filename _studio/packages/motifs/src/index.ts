/* @qubit/motifs: the parameterised generative art system.

   Public surface, in the order you need it:

     rng          seeded randomness. Nothing here calls Math.random.
     surface      the canvas box a motif draws into, plus token colour helpers.
     forms        the shared drawing vocabulary and a hand rolled camera.
     plate        the astronomical ground, cached per size.
     registry     the nine motifs.
     compose      a canto as data, rendered at a scroll progress.

   The contract every motif keeps:
     motif.draw(surface, seed, params)                 still frame, pure
     motif.frame(surface, seed, progress, overrides)   animated frame
     motif.at(progress, overrides)                     the params it would use
     motif.signature                                   its poster progress

   frame is defined as draw of at, so the still and the animation cannot drift
   apart. There is no clock anywhere in this package. */

export * from './rng.js';
export * from './surface.js';
export * from './forms.js';
export * from './plate.js';
export * from './types.js';
export * from './registry.js';
export * from './compose.js';

export type { CoinParams } from './motifs/coin.js';
export type { SphereParams } from './motifs/sphere.js';
export type { LatticeParams } from './motifs/lattice.js';
export type { WallParams } from './motifs/wall.js';
export type { ThreadParams } from './motifs/thread.js';
export type { FireParams } from './motifs/fire.js';
export type { LockParams } from './motifs/lock.js';
export type { MirrorParams } from './motifs/mirror.js';
export type { DialParams } from './motifs/dial.js';
