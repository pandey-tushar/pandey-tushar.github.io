/* The opening window of a book edition, in the homepage's pane system
   (/lib/site.css .tp-pane, /lib/site.js TP.live): a live field behind the whole
   window under the header, the book's cover lit in the room the words leave,
   then a mono tag, the title, one line and the way in. The two fields are the
   homepage's own for these books, ported as they are: polar for An Unpolarized
   Life, plate for the illustrated edition. TP.live runs them at about 30 fps,
   only on screen, never in a hidden tab, as one still frame under reduced
   motion, in the site's colours for either theme. */
import './styles/hero.css';

export interface HeroLink { href: string; label: string }
export interface Hero {
  tag: string;
  title: string;
  line: string;
  /** img/covers/<cover>.webp, with its -300 sibling */
  cover: string;
  start: HeroLink;
  more?: HeroLink[];
  /** where the words sit on a wide screen, as on the homepage panes */
  place?: '' | 'tp-pane-mid' | 'tp-pane-end' | 'tp-pane-top';
}
export type Field = 'polar' | 'plate';

interface Scene {
  still: number;
  dpr: number;
  cv?: HTMLCanvasElement;
  w?: number;
  h?: number;
  d?: number;
  setup?(w: number, h: number): void;
  step?(dt: number): void;
  draw(g: CanvasRenderingContext2D, w: number, h: number, t: number): void;
}
interface Live {
  add(cv: HTMLCanvasElement, s: Scene): Scene | null;
  C: Record<string, string>;
  rgba(hex: string, a: number): string;
  clamp(x: number): number;
  ss(a: number, b: number, x: number): number;
}
declare global {
  interface Window { TP?: { live?: Live } }
}

const esc = (s: string): string =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

export function heroElement(o: Hero): HTMLElement {
  const sec = document.createElement('section');
  sec.className = ('tp-pane rd-hero ' + (o.place ?? '')).trim();
  sec.id = 'top';
  sec.setAttribute('aria-labelledby', 'rd-title');
  const link = (l: HeroLink, cls: string): string =>
    '<a class="' + cls + '" href="' + esc(l.href) + '">' + esc(l.label) + '</a>';
  sec.innerHTML =
    '<div class="tp-pane-viz"><canvas aria-hidden="true"></canvas>' +
    '<img class="tp-pane-cover" src="/img/covers/' + o.cover + '.webp" srcset="/img/covers/' + o.cover +
    '-300.webp 300w, /img/covers/' + o.cover + '.webp 600w" sizes="(min-width:56em) 24rem, 50vw" ' +
    'width="600" height="900" decoding="async" fetchpriority="high" alt=""></div>' +
    '<div class="tp-pane-in tp-wrap"><div class="tp-pane-text">' +
    '<p class="tp-pane-tag">' + esc(o.tag) + '</p>' +
    '<h1 class="tp-pane-name" id="rd-title">' + esc(o.title) + '</h1>' +
    '<p class="tp-pane-line">' + esc(o.line) + '</p>' +
    '<div class="rd-actions">' + link(o.start, 'tp-btn pri rd-start') +
    (o.more ?? []).map((l) => link(l, 'tp-btn')).join('') + '</div>' +
    '</div></div>';
  return sec;
}

/** Starts the field once the hero is in the document. site.js is deferred
    ahead of the bundle, so TP.live is normally there already. */
export function liveHero(hero: HTMLElement, field: Field): void {
  const cv = hero.querySelector('canvas');
  const go = (): void => {
    const L = window.TP?.live;
    if (L && cv) L.add(cv, (field === 'polar' ? polar : plate)(L));
  };
  if (window.TP?.live || document.readyState !== 'loading') go();
  else addEventListener('DOMContentLoaded', go, { once: true });
}

/* ---------- the homepage's pane helpers ---------- */

interface Box { l: number; r: number; t: number; b: number }
type Weight = (x: number, y: number) => number;

const rnd = (n: number): number => (Math.random() * n) | 0;

/* the words, as a box in the canvas */
function words(cv: HTMLCanvasElement): Box | null {
  const t = cv.closest('.tp-pane')?.querySelector('.tp-pane-text');
  if (!t) return null;
  const c = cv.getBoundingClientRect(), r = t.getBoundingClientRect();
  return { l: r.left - c.left, r: r.right - c.left, t: r.top - c.top, b: r.bottom - c.top };
}
/* a weight that quiets the field near the words */
function calm(L: Live, b: Box | null, pad: number): Weight {
  return (x, y) => {
    if (!b) return 1;
    const dx = Math.max(b.l - x, 0, x - b.r), dy = Math.max(b.t - y, 0, y - b.b);
    return 0.1 + 0.9 * L.ss(0, pad, Math.hypot(dx, dy));
  };
}
/* the largest band beside, above or below the words for a figure of aspect a,
   clear of the edges and the rail; beside them is preferred on a wide screen */
function room(cv: HTMLCanvasElement, w: number, h: number, a: number): number[] {
  const b = words(cv), gx = Math.max(24, w * 0.05), gy = Math.max(24, h * 0.07);
  if (!b) return [w / 2, h / 2, w * 0.9, h * 0.9];
  let best: number[] | null = null, sc = -1;
  [[b.r + gx, gy, w - gx - 40, h - gy], [gx, gy, b.l - gx, h - gy], [gx, gy, w - gx, b.t - gy], [gx, b.b + gy, w - gx, h - gy]]
    .forEach((r, i) => {
      const rw = r[2] - r[0], rh = r[3] - r[1], f = Math.min(rw, rh * a) * (i > 1 && w >= 896 ? 0.75 : 1);
      if (rw > 0 && rh > 0 && f > sc) { sc = f; best = [(r[0] + r[2]) / 2, (r[1] + r[3]) / 2, rw, rh]; }
    });
  return best ?? [w / 2, h / 2, w * 0.9, h * 0.9];
}
/* the cover, stood in that room: its centre, its height and the room's smaller side */
function cover(cv: HTMLCanvasElement, w: number, h: number): number[] | null {
  const im = cv.parentElement?.querySelector<HTMLElement>('.tp-pane-cover');
  if (!im) return null;
  const R = room(cv, w, h, 2 / 3), ch = Math.min(R[3] * 0.8, R[2] * 0.8 * 1.5, 620);
  im.style.cssText = '--x:' + R[0].toFixed(1) + 'px;--y:' + R[1].toFixed(1) + 'px;--h:' + ch.toFixed(1) + 'px';
  return [R[0], R[1], ch, Math.min(R[2], R[3])];
}
/* an offscreen canvas the size of the scene's, for the parts that do not move */
function layer(s: Scene, L: HTMLCanvasElement): CanvasRenderingContext2D {
  L.width = s.cv!.width; L.height = s.cv!.height;
  const g = L.getContext('2d')!;
  g.setTransform(s.d!, 0, 0, s.d!, 0, 0);
  return g;
}
/* a small mask, alpha 1 - W(x, y), erased through so the field fades near the words on any ground */
function mask(W: Weight, w: number, h: number): HTMLCanvasElement {
  const n = 8, cw = Math.ceil(w / n), ch = Math.ceil(h / n), m = document.createElement('canvas');
  m.width = cw; m.height = ch;
  const x = m.getContext('2d')!, im = x.createImageData(cw, ch);
  for (let j = 0; j < ch; j++) for (let i = 0; i < cw; i++) im.data[(j * cw + i) * 4 + 3] = 255 * (1 - W((i + 0.5) * n, (j + 0.5) * n));
  x.putImageData(im, 0, 0);
  return m;
}
function hush(g: CanvasRenderingContext2D, m: HTMLCanvasElement, w: number, h: number): void {
  g.globalCompositeOperation = 'destination-out'; g.drawImage(m, 0, 0, w, h); g.globalCompositeOperation = 'source-over';
}

/* ---------- An Unpolarized Life: a field of circles; three at a time find their common region ---------- */
function polar(L: Live): Scene {
  const { C, rgba, ss } = L;
  interface Ev { P: number[][]; x: number; y: number; age: number }
  const lay = document.createElement('canvas');
  let at: number[] | null = null, sp = 0, r = 0, cols = 0, rows = 0, ox = 0, oy = 0, dy = 0, next = 0.6;
  let W: Weight = () => 1, ev: Ev[] = [];
  const c = (i: number, j: number): number[] => [ox + (i + (j & 1 ? 0.5 : 0)) * sp, oy + j * dy];
  const spawn = (age: number): void => {
    for (let tries = 0; tries < 40; tries++) {
      const i = 1 + rnd(cols - 3), j = 1 + rnd(rows - 3), k = j & 1;
      const P = [c(i, j), c(i + 1, j), c(i + k, j + 1)], cx = (P[0][0] + P[1][0] + P[2][0]) / 3, cy = (P[0][1] + P[1][1] + P[2][1]) / 3;
      if (cx < r || cx > S.w! - r || cy < r || cy > S.h! - r) continue;
      if (P.some((p) => W(p[0], p[1]) < 0.8) || W(cx, cy) < 0.95) continue;
      if (at && Math.abs(cx - at[0]) < at[2] / 3 + r && Math.abs(cy - at[1]) < at[2] / 2 + r) continue;
      if (ev.some((e) => Math.hypot(e.x - cx, e.y - cy) < sp * 2.5)) continue;
      ev.push({ P, x: cx, y: cy, age });
      return;
    }
  };
  const S: Scene = {
    still: 2, dpr: 1.5,
    setup(w, h) {
      at = cover(S.cv!, w, h);
      sp = Math.max(80, Math.min(128, Math.min(h, w * 1.4) / 5.6)); dy = sp * Math.sqrt(3) / 2;
      r = sp * 0.64; cols = Math.ceil(w / sp) + 3; rows = Math.ceil(h / dy) + 3;
      ox = (w - (cols - 1) * sp) / 2; oy = (h - (rows - 1) * dy) / 2;
      W = calm(L, words(S.cv!), 1.2 * sp);
      const g = layer(S, lay);
      g.strokeStyle = rgba(C.dim, 0.26); g.lineWidth = 1; g.beginPath();
      for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) { const p = c(i, j); g.moveTo(p[0] + r, p[1]); g.arc(p[0], p[1], r, 0, 7); }
      g.stroke();
      hush(g, mask(W, w, h), w, h);
      ev = []; spawn(2); spawn(0.6); spawn(3.4);
    },
    step(dt) {
      ev.forEach((e) => { e.age += dt; });
      ev = ev.filter((e) => e.age < 5.4);
      if ((next -= dt) <= 0 && ev.length < 3) { spawn(0); next = 1.2 + Math.random() * 1.4; }
    },
    /* three circles (ink), the region they share (accent) and its centre (warm) */
    draw(g, w, h) {
      g.drawImage(lay, 0, 0, w, h);
      ev.forEach((e) => {
        const f = ss(0, 1, e.age) * (1 - ss(4.2, 5.4, e.age));
        g.save();
        for (let k = 0; k < 2; k++) { g.beginPath(); g.arc(e.P[k][0], e.P[k][1], r, 0, 7); g.clip(); }
        g.beginPath(); g.arc(e.P[2][0], e.P[2][1], r, 0, 7); g.fillStyle = rgba(C.acc, 0.2 * f); g.fill();
        g.restore();
        g.strokeStyle = rgba(C.ink, 0.6 * f); g.lineWidth = 1.25;
        for (let k = 0; k < 3; k++) { g.beginPath(); g.arc(e.P[k][0], e.P[k][1], r, 0, 7); g.stroke(); }
        g.beginPath(); g.arc(e.x, e.y, 3.6, 0, 7); g.fillStyle = rgba(C.warm, f); g.fill();
      });
    },
  };
  return S;
}

/* ---------- the illustrated edition: a field of engraved spheres under a moving light ----------
   On the night ground the strokes are the light; on paper they are the shade. */
function plate(L: Live): Scene {
  const { C, rgba } = L;
  let R = 0, sp = 0, st = 0, m: HTMLCanvasElement | null = null;
  const S: Scene = {
    still: 2.2, dpr: 1.5,
    setup(w, h) {
      cover(S.cv!, w, h);
      R = Math.max(40, Math.min(84, Math.min(h, w * 1.4) / 8)); sp = R * 2.6; st = Math.max(5, Math.min(7, R / 10));
      m = mask(calm(L, words(S.cv!), 2 * R), w, h);
    },
    draw(g, w, h, t) {
      const seg = 12, la = t * 0.3, ink = document.documentElement.dataset.theme !== 'light';
      const Lt = [Math.cos(la) * 0.75, -0.5, Math.sin(la) * 0.5 + 0.55], ln = Math.hypot(Lt[0], Lt[1], Lt[2]);
      const P: number[][] = [[], [], [], [], [], [], [], []];
      for (let y = st / 2; y < h; y += st) {
        const j = Math.round(y / sp - 0.5), cy = (j + 0.5) * sp;
        for (let x0 = 0; x0 < w; x0 += seg) {
          const xm = x0 + seg / 2, i = Math.round((xm - (j & 1 ? sp / 2 : 0)) / sp - 0.5), cx = (i + 0.5) * sp + (j & 1 ? sp / 2 : 0);
          const dx = (xm - cx) / R, dy = (y - cy) / R, q = dx * dx + dy * dy;
          let a = 0.06;
          if (q < 1) {
            const b = Math.max(0, (dx * Lt[0] + dy * Lt[1] + Math.sqrt(1 - q) * Lt[2]) / ln);
            a = 0.05 + 0.5 * (ink ? b * b : (1 - b) * (1 - b));
          }
          P[Math.min(7, Math.floor(a * 14))].push(x0, y);
        }
      }
      g.lineWidth = st * 0.42; g.lineCap = 'butt';
      for (let b = 0; b < 8; b++) {
        if (!P[b].length) continue;
        g.strokeStyle = rgba(C.ink, (b + 0.5) / 14); g.beginPath();
        for (let k = 0; k < P[b].length; k += 2) { g.moveTo(P[b][k], P[b][k + 1]); g.lineTo(P[b][k] + seg, P[b][k + 1]); }
        g.stroke();
      }
      if (m) hush(g, m, w, h);
    },
  };
  return S;
}
