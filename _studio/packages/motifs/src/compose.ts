/* Composition: how a canto is made out of the vocabulary.

   A composition is data. It names one or two motifs, where they sit, and how
   their parameters move across the canto's normalised scroll progress. Adding
   a canto is writing one of these objects. That is the whole point of the
   motif system: the system beats the set. */

import { clear, sub, type Region, type Surface } from './surface.js';
import { drawPlate, type PlateOptions } from './plate.js';
import { getMotif, type MotifId } from './registry.js';
import { clamp, span as remap, type Seed } from './rng.js';
import type { Params } from './types.js';

export interface Keyframe {
  /** layer progress 0..1 */
  at: number;
  params: Partial<Params>;
}

/** The one parameter name the compositor reads instead of passing through.
    Layer alpha has to be keyframeable, since a motif entering and leaving is
    choreography, and every other choreography knob is a keyframe. */
export const OPACITY = 'opacity';

export interface Layer {
  motif: MotifId;
  /** defaults to composition seed plus the motif id */
  seed?: Seed;
  /** normalised box inside the stage. Omit for the whole stage. */
  region?: Region;
  alpha?: number;
  composite?: GlobalCompositeOperation;
  /** remaps canto progress into this layer's own 0..1, so a motif can enter
      late or finish early without knowing anything about the canto */
  span?: readonly [number, number];
  /** constants for this canto: size, density, camera */
  params?: Partial<Params>;
  /** choreography overriding the motif's own curve */
  keys?: readonly Keyframe[];
}

export interface Composition {
  id: string;
  canto: number;
  seed: Seed;
  /** the progress that produces the poster. The forcing function lives here:
      if this frame does not stand alone, the canto's art is not done. */
  signature: number;
  plate?: PlateOptions | false;
  layers: readonly Layer[];
}

/** Piecewise linear interpolation, per field, across the keyframes that define
    that field. A field defined in only one keyframe is held constant, so a
    composition can pin one parameter without listing every other. */
export function resolveKeys(keys: readonly Keyframe[] | undefined, t: number): Partial<Params> {
  if (!keys || keys.length === 0) return {};
  const out: Partial<Params> = {};
  const fields = new Set<string>();
  for (const k of keys) for (const f of Object.keys(k.params)) fields.add(f);

  for (const f of fields) {
    const pts: Array<[number, number]> = [];
    for (const k of keys) {
      const v = k.params[f];
      if (typeof v === 'number') pts.push([k.at, v]);
    }
    pts.sort((a, b) => a[0] - b[0]);
    if (pts.length === 0) continue;
    if (t <= pts[0]![0]) { out[f] = pts[0]![1]; continue; }
    const last = pts[pts.length - 1]!;
    if (t >= last[0]) { out[f] = last[1]; continue; }
    for (let i = 0; i + 1 < pts.length; i++) {
      const a = pts[i]!;
      const b = pts[i + 1]!;
      if (t >= a[0] && t <= b[0]) {
        const u = b[0] === a[0] ? 0 : (t - a[0]) / (b[0] - a[0]);
        out[f] = a[1] + (b[1] - a[1]) * u;
        break;
      }
    }
  }
  return out;
}

/** Draws a whole canto at a given scroll progress. This is the only entry
    point the app needs, and the poster route calls it too, at
    comp.signature, so the two can never disagree. */
export function renderComposition(surface: Surface, comp: Composition, progress: number): void {
  const p = clamp(progress);
  clear(surface);
  if (comp.plate !== false) drawPlate(surface, comp.seed, comp.plate ?? {});

  for (const layer of comp.layers) {
    const lp = layer.span ? remap(p, layer.span[0], layer.span[1]) : p;
    const motif = getMotif(layer.motif);
    const overrides: Partial<Params> = { ...(layer.params ?? {}), ...resolveKeys(layer.keys, lp) };
    const target = layer.region ? sub(surface, layer.region) : surface;

    const keyed = overrides[OPACITY];
    const op = (layer.alpha ?? 1) * (typeof keyed === 'number' ? clamp(keyed) : 1);
    if (op <= 0.004) continue;

    surface.ctx.save();
    surface.ctx.globalAlpha = op;
    if (layer.composite) surface.ctx.globalCompositeOperation = layer.composite;
    motif.frame(target, layer.seed ?? String(comp.seed) + '/' + layer.motif, lp, overrides);
    surface.ctx.restore();
  }
}

/** The still frame. Posters, OG cards, print, and the reduced motion edition
    all come through here, and all of them are a real frame of the animation. */
export function renderSignature(surface: Surface, comp: Composition): void {
  renderComposition(surface, comp, comp.signature);
}
