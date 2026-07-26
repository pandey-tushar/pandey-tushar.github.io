import '@qubit/tokens/tokens.css';
import './styles/reader.css';
import './styles/print.css';

import type { Canto, FrontMatter } from '@qubit/content/schema';
import { appendixHtml, cantoHtml, coverHtml, footerHtml, invocationHtml, resolveLabels } from './render.js';
import { initAccordion } from './accordion.js';
import { initProgress, initRail } from './rail.js';
import { initTheme } from './theme.js';
import type { SceneMounter } from './scenes/types.js';

export * from './render.js';
export * from './theme.js';
export { initAccordion } from './accordion.js';
export type { SceneFn, SceneMounter } from './scenes/types.js';

export interface ReaderOptions {
  cantos: Canto[];
  front: FrontMatter;
  /** Chrome and #book are appended here. Must be <body> so the fixed theme
      chip is not captured by a transformed ancestor. */
  mount?: HTMLElement;
  /** Link shown in the footer. */
  home?: string;
  /** Interactive scenes and background WebGL. Pass the bundled mounter,
      `import { scenes } from '@qubit/reader/scenes'`, to switch them on.
      Left out, the build is text-only and three.js never enters the graph. */
  scenes?: SceneMounter | false;
}

const el = <K extends keyof HTMLElementTagNameMap>(
  tag: K, attrs: Record<string, string> = {}, html = '',
): HTMLElementTagNameMap[K] => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (html) n.innerHTML = html;
  return n;
};

export function mountReader(opts: ReaderOptions): void {
  const { cantos, front, mount = document.body, home = 'https://pandey-tushar.com', scenes = false } = opts;
  const labels = resolveLabels(front);

  /* 100vw counts the classic scrollbar gutter, so the full-bleed cover built
     on it overflows the document sideways on desktop. Publish the real client
     width for reader.css to use instead. */
  const setPageWidth = (): void => {
    document.documentElement.style.setProperty('--page', document.documentElement.clientWidth + 'px');
  };
  setPageWidth();
  addEventListener('resize', setPageWidth, { passive: true });

  const loader = el('div', { id: 'loader' },
    '<div class="om">' + front.loader.glyph + '</div><div class="lt">' + front.loader.label + '</div>');
  const prog = el('div', { id: 'prog' });
  const starfield = el('canvas', { id: 'starfield', 'aria-hidden': 'true' });
  const vignette = el('div', { class: 'vignette', 'aria-hidden': 'true' });
  const toggle = el('button', {
    type: 'button', id: 'theme-toggle', class: 'theme-toggle',
    title: labels.themeTitle, 'aria-label': labels.themeAria,
  });
  const mala = el('nav', { id: 'mala', 'aria-label': labels.rail });

  const book = el('div', { id: 'book' });
  const cover = el('header', { id: 'cover' }, coverHtml(front));
  const invocation = el('section', { class: 'canto', id: 'invocation' }, invocationHtml(front));
  const content = el('main', { id: 'content' });
  const footer = el('footer', {}, footerHtml(front, home));
  book.append(cover, invocation, content, footer);

  mount.append(loader, prog, starfield, vignette, toggle, mala, book);

  /* chapters */
  const total = cantos.length;
  for (const c of cantos) {
    const sec = el('section', { class: 'canto acc', id: 'canto-' + c.n }, cantoHtml(c, total, labels));
    sec.dataset.canto = String(c.n);
    content.append(sec);
  }
  content.append(el('section', { class: 'canto', id: 'references' }, appendixHtml(cantos, front)));

  /* reveal on scroll */
  const io = new IntersectionObserver((es) => {
    for (const e of es) if (e.isIntersecting) e.target.classList.add('visible');
  }, { threshold: 0, rootMargin: '0px 0px -8% 0px' });
  for (const s of document.querySelectorAll('section.canto')) io.observe(s);

  const accs = [...content.querySelectorAll<HTMLElement>('section.canto.acc')];
  const rail = initRail(mala, cantos, (n) => {
    const sec = accs.find((s) => s.dataset.canto === String(n));
    if (sec) acc.expand(sec, { scroll: true });
  }, labels);
  const acc = initAccordion(accs, (sec) => {
    rail.setActive(Number(sec.dataset.canto));
    if (scenes) scenes.mountScenes(sec);
  });

  initProgress(prog);
  initTheme(toggle, front.theme);
  if (scenes) scenes.mountBackground(starfield, book.querySelector<HTMLElement>('#cover3d'));

  /* dismiss the loader once the page is up, and never leave it stuck */
  const dismiss = () => {
    loader.style.opacity = '0';
    setTimeout(() => loader.remove(), 800);
  };
  if (document.readyState === 'complete') setTimeout(dismiss, 600);
  else addEventListener('load', () => setTimeout(dismiss, 600), { once: true });
}
