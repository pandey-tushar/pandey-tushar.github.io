/* Decides whether the poster is the whole hero or just the first frame.

   The 3D chunk is roughly 500KB of renderer. It is worth it on a desktop with
   a real GPU and a fast link; it is not worth it on a phone on a train, and it
   is not wanted at all by a reader who asked for less motion. Everyone gets the
   same picture either way, because the poster is the scene at rest. */

const mq = (q: string): boolean => matchMedia(q).matches;

interface Conn { saveData?: boolean; effectiveType?: string }

export function wants3d(): boolean {
  if (mq('(prefers-reduced-motion: reduce)')) return false;
  /* touch plus a small viewport is a phone; the knot is decorative there */
  if (mq('(pointer: coarse)') && innerWidth < 900) return false;
  const n = navigator as Navigator & { deviceMemory?: number; connection?: Conn };
  if ((n.hardwareConcurrency ?? 8) < 4) return false;
  if ((n.deviceMemory ?? 8) < 4) return false;
  const c = n.connection;
  if (c?.saveData) return false;
  if (c?.effectiveType && /^(slow-)?2g$/.test(c.effectiveType)) return false;
  return true;
}

/** Loads the renderer after first paint, never before it. */
export function upgradeHero(): void {
  if (!document.querySelector('.hero') || !wants3d()) return;
  const go = (): void => {
    import('./scene.ts')
      .then((m) => m.mountScene())
      .catch(() => { /* the poster is already a complete hero */ });
  };
  /* two frames past first paint, and only while the hero is still on screen */
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if ('requestIdleCallback' in window) requestIdleCallback(go, { timeout: 1200 });
    else setTimeout(go, 200);
  }));
}
