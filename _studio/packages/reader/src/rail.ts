/* Bead rail and top progress bar. Beads are real buttons so the rail works
   from the keyboard. */
import type { Canto } from '@qubit/content/schema';
import { DEFAULT_LABELS, esc, fill, numeral, type ReaderLabels } from './render.js';

export interface Rail { setActive(n: number): void }

export function initRail(
  nav: HTMLElement,
  cantos: Canto[],
  onPick: (n: number) => void,
  labels: ReaderLabels = DEFAULT_LABELS,
): Rail {
  nav.setAttribute('aria-label', labels.rail);
  nav.innerHTML = cantos.map((c) => {
    const vars = { n: numeral(c.n, labels.digits), title: c.title };
    return '<button type="button" class="bead" data-n="' + c.n +
      '" data-t="' + esc(fill(labels.beadTip, vars)) +
      '" aria-label="' + esc(fill(labels.bead, vars)) + '"></button>';
  }).join('');

  const beads = [...nav.querySelectorAll<HTMLElement>('.bead')];
  for (const b of beads) {
    b.addEventListener('click', () => onPick(Number(b.dataset.n)));
  }
  return {
    setActive(n) {
      for (const b of beads) b.classList.toggle('active', b.dataset.n === String(n));
    },
  };
}

export function initProgress(bar: HTMLElement): void {
  addEventListener('scroll', () => {
    const h = document.documentElement;
    const span = h.scrollHeight - h.clientHeight;
    bar.style.width = (span > 0 ? (h.scrollTop / span) * 100 : 0) + '%';
  }, { passive: true });
}
