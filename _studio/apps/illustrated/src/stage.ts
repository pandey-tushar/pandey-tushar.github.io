/* Scene virtualisation and the scroll driver.

   Rules this file exists to enforce:

   - At most three canvases are mounted at once. Twenty two live canvases is
     not a thing that can exist, and the failure is not gradual: it is a phone
     dropping the page.
   - Unmount is a full dispose. The canvas leaves the DOM and its backing store
     is freed by zeroing width and height. A 1440 by 900 canvas at dpr 2 is
     about twenty megabytes of GPU-backed memory; three of those is the whole
     budget, so a scene that lingers is a leak with a visible cost.
   - Poster first. Every stage shows its seeded still frame before any script
     mounts anything, and the live layer fades in over the top of it. There is
     never a blank rectangle where the art will be.
   - Nothing is driven by elapsed time. The renderer runs inside a scroll
     coalesced animation frame and paints only when progress actually moved, so
     a still page costs nothing and a stopped scroll leaves a composed frame. */

import {
  disposePlates, mountSurface, releaseCanvas, renderComposition, renderSignature,
  type Surface,
} from '@qubit/motifs';
import type { CantoArt } from './cantos/index.js';

export interface SceneHost {
  canto: number;
  art: CantoArt;
  /** the tall region whose position in the viewport is the canto's progress */
  track: HTMLElement;
  /** the pinned box the canvas fills */
  stage: HTMLElement;
}

/** Below this the frame has not moved enough to be worth a repaint. At a
    four screen canto it is about half a pixel of scroll. */
const EPS = 0.0006;

const dprFor = (): number => Math.min(globalThis.devicePixelRatio || 1, 2);

class Scene {
  private canvas: HTMLCanvasElement | null = null;
  private surface: Surface | null = null;
  private last = -1;

  constructor(readonly host: SceneHost) {}

  get mounted(): boolean {
    return this.canvas !== null;
  }

  /** Allocating the backing store and drawing the first frame in the same
      frame as a scroll update is the one thing that produced a long task in
      the budget run. They are split, and the director mounts at most one scene
      per frame. The poster is underneath the whole time, so the reader never
      sees the gap. */
  mount(progress: number): void {
    if (this.canvas) return;
    const canvas = document.createElement('canvas');
    canvas.className = 'live';
    canvas.setAttribute('aria-hidden', 'true');
    this.host.stage.append(canvas);
    this.canvas = canvas;
    this.size();
    requestAnimationFrame(() => {
      if (this.canvas !== canvas) return;
      this.paint(progress, true);
      canvas.classList.add('is-up');
    });
  }

  size(): void {
    if (!this.canvas) return;
    const w = this.host.stage.clientWidth;
    const h = this.host.stage.clientHeight;
    if (w < 2 || h < 2) return;
    this.surface = mountSurface(this.canvas, { width: w, height: h, dpr: dprFor() });
    this.last = -1;
  }

  paint(progress: number, force = false): void {
    if (!this.surface) return;
    if (!force && Math.abs(progress - this.last) < EPS) return;
    this.last = progress;
    renderComposition(this.surface, this.host.art.composition, progress);
  }

  /** Off screen: keep the canvas but forget what is on it, so the next frame
      that matters is a full repaint rather than a skipped one. */
  hold(): void {
    this.last = -1;
  }

  dispose(): void {
    const canvas = this.canvas;
    this.canvas = null;
    this.surface = null;
    this.last = -1;
    if (!canvas) return;
    canvas.classList.remove('is-up');
    canvas.remove();
    releaseCanvas(canvas);
  }
}

export function progressOf(track: HTMLElement): number {
  const rect = track.getBoundingClientRect();
  const total = rect.height - innerHeight;
  if (total <= 1) return 0.5;
  const p = -rect.top / total;
  return p < 0 ? 0 : p > 1 ? 1 : p;
}

export class SceneDirector {
  private scenes: Scene[];
  private near = new Set<Scene>();
  private io: IntersectionObserver;
  private frame = 0;
  private onScroll = (): void => this.schedule();
  private onResize = (): void => {
    for (const s of this.scenes) if (s.mounted) s.size();
    this.schedule();
  };

  constructor(hosts: SceneHost[], private budget = 3) {
    this.scenes = hosts.map((h) => new Scene(h));
    const byEl = new Map<Element, Scene>(this.scenes.map((s) => [s.host.track, s]));
    this.io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          const scene = byEl.get(e.target);
          if (!scene) continue;
          if (e.isIntersecting) this.near.add(scene);
          else this.near.delete(scene);
        }
        this.schedule();
      },
      /* a screen of lead in either direction, so the next canto is mounted and
         painted before it can be looked at */
      { rootMargin: '100% 0px 100% 0px', threshold: 0 },
    );
    for (const s of this.scenes) this.io.observe(s.host.track);

    addEventListener('scroll', this.onScroll, { passive: true });
    addEventListener('resize', this.onResize);
    this.schedule();
  }

  private schedule(): void {
    if (this.frame) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      this.tick();
    });
  }

  private tick(): void {
    const mid = innerHeight / 2;
    const ranked = [...this.near]
      .map((scene) => {
        const rect = scene.host.track.getBoundingClientRect();
        const centre = rect.top + rect.height / 2;
        return { scene, d: Math.abs(centre - mid), rect };
      })
      .sort((a, b) => a.d - b.d);

    const keep = new Set(ranked.slice(0, this.budget).map((r) => r.scene));
    for (const scene of this.scenes) {
      if (!keep.has(scene) && scene.mounted) scene.dispose();
    }
    let mountedThisFrame = false;
    for (const { scene, rect } of ranked.slice(0, this.budget)) {
      const total = rect.height - innerHeight;
      const p = total <= 1 ? 0.5 : Math.max(0, Math.min(1, -rect.top / total));
      /* mounted is not the same as on screen. The neighbour scenes are held
         ready so they never appear blank, but repainting a canvas nobody can
         see doubles the per frame cost wherever two composed cantos are
         adjacent, which is exactly cantos one and two. */
      const onScreen = rect.bottom > 0 && rect.top < innerHeight;
      if (scene.mounted) {
        if (onScreen) scene.paint(p);
        else scene.hold();
      } else if (!mountedThisFrame) {
        scene.mount(p);
        mountedThisFrame = true;
      } else {
        /* one allocation per frame; the rest come round on the next one */
        this.schedule();
      }
    }
  }

  destroy(): void {
    removeEventListener('scroll', this.onScroll);
    removeEventListener('resize', this.onResize);
    this.io.disconnect();
    if (this.frame) cancelAnimationFrame(this.frame);
    this.frame = 0;
    for (const s of this.scenes) s.dispose();
    this.near.clear();
    disposePlates();
  }

  /** Test hook: how many canvases are alive right now. */
  get liveCount(): number {
    return this.scenes.filter((s) => s.mounted).length;
  }
}

/* ---------- posters ---------- */

/** Renders a canto's signature frame and hands back a data URL, reusing one
    scratch canvas and releasing it immediately. Used only when a built poster
    PNG is missing, so the page never has a stage without artwork. */
export function posterDataUrl(art: CantoArt, width = 800): string {
  const canvas = document.createElement('canvas');
  try {
    const surface = mountSurface(canvas, { width, height: Math.round(width * 0.625), dpr: 1 });
    renderSignature(surface, art.composition);
    const webp = canvas.toDataURL('image/webp', 0.86);
    return webp.startsWith('data:image/webp') ? webp : canvas.toDataURL('image/png');
  } finally {
    releaseCanvas(canvas);
  }
}
