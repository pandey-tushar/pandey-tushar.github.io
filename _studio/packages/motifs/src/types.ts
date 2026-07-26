/* The motif contract.

   A motif is a pure function from (seed, params) to pixels. It holds no clock,
   no state, and no reference to the document. That is what makes the same code
   path serve the poster, the print export, the reduced motion edition, and the
   scroll animation: the still frame is literally a frame of the animation, not
   a second implementation that drifts from it.

   Every parameter is a number, deliberately. It makes keyframe interpolation
   total, so a composition can move any parameter of any motif without the
   library knowing what that parameter means. */

import type { Surface } from './surface.js';
import type { Seed } from './rng.js';

export type Params = Record<string, number>;

export interface Motif<P extends Params = Params> {
  readonly id: string;
  readonly defaults: Readonly<P>;
  /** the progress this motif reads best at when shown alone */
  readonly signature: number;
  /** the motif's own choreography: normalised progress to params */
  at(progress: number, overrides?: Partial<P>): P;
  /** still frame. Pure in (seed, params, surface geometry). */
  draw(surface: Surface, seed: Seed, params: P): void;
  /** animated frame, driven by scroll progress 0..1. Never by elapsed time. */
  frame(surface: Surface, seed: Seed, progress: number, overrides?: Partial<P>): void;
}

export interface MotifSpec<P extends Params> {
  id: string;
  defaults: P;
  signature: number;
  /** how this motif evolves across a canto when nothing overrides it */
  curve(progress: number): Partial<P>;
  draw(surface: Surface, seed: Seed, params: P): void;
}

export function defineMotif<P extends Params>(spec: MotifSpec<P>): Motif<P> {
  const at = (progress: number, overrides?: Partial<P>): P => ({
    ...spec.defaults,
    ...spec.curve(progress < 0 ? 0 : progress > 1 ? 1 : progress),
    ...(overrides ?? {}),
  });
  return {
    id: spec.id,
    defaults: spec.defaults,
    signature: spec.signature,
    at,
    draw: spec.draw,
    frame: (surface, seed, progress, overrides) => spec.draw(surface, seed, at(progress, overrides)),
  };
}
