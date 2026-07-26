import * as THREE from 'three';
import { sceneColors } from '@qubit/tokens';

/** Scenes keep their night palette in both themes. */
export const C = sceneColors;

export type Sized = THREE.WebGLRenderer & { __cam?: THREE.PerspectiveCamera };

/** Renderer sized to its container and kept in sync on resize. A scene stores
    its camera on `__cam` so the observer can fix the aspect ratio too. */
export function makeRenderer(el: HTMLElement): Sized {
  const r: Sized = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  r.setPixelRatio(Math.min(devicePixelRatio, 2));
  r.setSize(el.clientWidth, el.clientHeight);
  el.insertBefore(r.domElement, el.firstChild);
  const fit = () => {
    const w = el.clientWidth, h = el.clientHeight;
    if (!w || !h) return;
    r.setSize(w, h);
    if (r.__cam) { r.__cam.aspect = w / h; r.__cam.updateProjectionMatrix(); }
  };
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(fit).observe(el);
  addEventListener('resize', fit);
  return r;
}

/** Readouts a scene writes on interaction, taken from the content block that
    mounted it (`SceneBlock.strings`), with the English wording as the default.
    `{name}` spans in the string are filled from `vars`. */
export function readouts(el: HTMLElement): (key: string, fallback: string, vars?: Record<string, string>) => string {
  let map: Record<string, string> = {};
  const raw = el.dataset.strings;
  if (raw) {
    try { map = JSON.parse(raw) as Record<string, string>; }
    catch { console.warn('reader: scene strings are not valid JSON', raw); }
  }
  return (key, fallback, vars) => {
    const tpl = map[key] ?? fallback;
    return vars ? tpl.replace(/\{(\w+)\}/g, (m, k: string) => (k in vars ? vars[k] : m)) : tpl;
  };
}

export const prefersReducedMotion = (): boolean =>
  typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Animation loop that honours prefers-reduced-motion by drawing one frame and
    stopping. The returned redraw() lets interactive scenes repaint on input
    when the loop is not running. */
export function loop(fn: (t: number) => void): () => void {
  if (prefersReducedMotion()) {
    fn(0);
    return () => fn(performance.now());
  }
  const tick = (t: number) => { requestAnimationFrame(tick); fn(t); };
  requestAnimationFrame(tick);
  return () => { /* the loop is already painting */ };
}
