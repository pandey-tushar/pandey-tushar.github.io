/* Scene registry and lazy mounting.

   Each entry is a dynamic import, so Three.js and the scene code are their own
   chunks and never load for a reader who does not open a canto that has one.
   Scenes mount on EXPAND, not on intersection: a scene inside a collapsed
   canto has zero height and would never initialise.

   This module is the opt-in half of the reader. `mountReader` takes a
   SceneMounter rather than importing this file, so a text-only edition
   (`scenes: false`) never puts three.js in its module graph and Rollup emits
   no scene chunks at all. An edition that wants scenes does:

     import { scenes } from '@qubit/reader/scenes';
     mountReader({ cantos, front, scenes });

   TO REGISTER A NEW SCENE: add `kind: () => import('./kind.js')` below and give
   its module a default export of `(el: HTMLElement) => void`. The content block
   is `{ t: 'scene', kind: 'kind', hint, controls, strings }`. */

import type { SceneFn, SceneMounter } from './types.js';

export type { SceneFn, SceneMounter } from './types.js';

const REGISTRY: Record<string, () => Promise<{ default: SceneFn }>> = {
  bloch: () => import('./bloch.js'),
  entangle: () => import('./entangle.js'),
  decohere: () => import('./decohere.js'),
  toric: () => import('./toric.js'),
  biascat: () => import('./biascat.js'),
  modular: () => import('./modular.js'),
  globe: () => import('./globe.js'),
  lock: () => import('./lock.js'),
  cosmos: () => import('./cosmos.js'),
};

export const sceneKinds = Object.keys(REGISTRY);

const mounted = new WeakSet<HTMLElement>();

/** Mounts every unmounted `.scene[data-scene]` inside `root`. */
export function mountScenes(root: ParentNode): void {
  for (const el of root.querySelectorAll<HTMLElement>('.scene[data-scene]')) {
    if (mounted.has(el)) continue;
    mounted.add(el);
    const kind = el.dataset.scene ?? '';
    const load = REGISTRY[kind];
    if (!load) { console.warn('reader: no scene registered for kind ' + JSON.stringify(kind)); continue; }
    load()
      .then((m) => m.default(el))
      .catch((e) => console.warn('reader: scene ' + kind + ' failed', e));
  }
}

/** Starfield and cover lattice, after first paint. */
export function mountBackground(canvas: HTMLCanvasElement | null, coverMount: HTMLElement | null): void {
  if (!canvas && !coverMount) return;
  import('./background.js')
    .then((m) => {
      if (canvas) m.starfield(canvas);
      if (coverMount) m.cover(coverMount);
    })
    .catch((e) => console.warn('reader: background scenes failed', e));
}

/** The bundled mounter, to hand to `mountReader({ scenes })`. */
export const scenes: SceneMounter = { mountScenes, mountBackground };
