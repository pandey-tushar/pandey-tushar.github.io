/* Chapter accordion: exactly one canto open, opened by scroll settle.

   Two traps are load-bearing here and both cost real debugging time:

   1. Do NOT drive expansion from an IntersectionObserver watching a thin band.
      IO compares state between frames, so a 250-800px wheel flick hops the band
      without firing, and reflow during expand/collapse sweeps other headers
      through it and opens the wrong canto. Geometry-on-settle instead: pick the
      last header above the viewport centre line once scrolling stops.
   2. Never gate the scroll handler behind requestAnimationFrame with an
      "already queued" flag. rAF freezes in background tabs, the flag never
      clears, and the handler dies for the rest of the session. The settle timer
      is armed directly on the scroll event; rAF only rate-limits. */

export interface AccordionApi {
  expand(sec: HTMLElement, opts?: { scroll?: boolean }): void;
  current(): HTMLElement | null;
}

const SETTLE_MS = 150;
/* How long an explicit open outranks the settle heuristic. Long enough to
   cover a smooth scrollIntoView, short enough to feel like nothing happened. */
const SUPPRESS_MS = 1200;

export function initAccordion(
  sections: HTMLElement[],
  onExpand: (sec: HTMLElement) => void,
): AccordionApi {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let current: HTMLElement | null = null;
  let suppressUntil = 0;

  function apply(sec: HTMLElement, opts: { scroll?: boolean } = {}): void {
    if (sec === current) { if (opts.scroll) sec.scrollIntoView(); return; }
    const prev = current;
    current = sec;

    /* anchor on the target head so its viewport position is preserved */
    const head = sec.querySelector('.canto-head') as HTMLElement;
    const before = head.getBoundingClientRect().top;

    if (prev) {
      /* collapsing a card ABOVE the anchor yanks the visible text upward, so
         drop the animation and let the height change land in this same frame
         where it can be measured and compensated. */
      const above = prev.getBoundingClientRect().top < before;
      const wrap = prev.querySelector('.canto-wrap') as HTMLElement;
      if (above && !reduce) wrap.style.transition = 'none';
      prev.classList.remove('expanded');
      (prev.querySelector('.canto-head') as HTMLElement).setAttribute('aria-expanded', 'false');
      if (above && !reduce) { wrap.getBoundingClientRect(); wrap.style.transition = ''; }
    }

    sec.classList.add('expanded');
    head.setAttribute('aria-expanded', 'true');

    /* same-frame compensation; 'instant' bypasses css smooth scrolling */
    const after = head.getBoundingClientRect().top;
    if (after !== before) scrollTo({ top: scrollY + (after - before), behavior: 'instant' });

    onExpand(sec);
    if (opts.scroll) sec.scrollIntoView();
  }

  /* An explicit open (header click, bead) beats the heuristic. Without this
     the compensation scroll settles and re-picks by geometry, so clicking a
     header sitting just below the centre line silently opens the one above
     it and the reader lands in the wrong chapter. */
  function expand(sec: HTMLElement, opts: { scroll?: boolean } = {}): void {
    suppressUntil = performance.now() + SUPPRESS_MS;
    apply(sec, opts);
  }

  for (const sec of sections) {
    const head = sec.querySelector('.canto-head') as HTMLElement;
    head.addEventListener('click', () => expand(sec));
  }

  /* Pick the canto the reader is inside: the last header above the centre
     line. The compensation scroll re-triggers this, but it converges because
     the re-pick lands on the same section. */
  function pickCanto(): void {
    if (performance.now() < suppressUntil) { suppressUntil = 0; return; }
    const line = scrollY + innerHeight / 2;
    let best: HTMLElement | null = null;
    for (const s of sections) {
      const head = s.querySelector('.canto-head') as HTMLElement;
      if (head.getBoundingClientRect().top + scrollY <= line) best = s;
      else break;
    }
    if (best && best !== current) apply(best);
  }

  let raf = 0;
  let settle: ReturnType<typeof setTimeout> | undefined;
  addEventListener('scroll', () => {
    clearTimeout(settle);
    settle = setTimeout(pickCanto, SETTLE_MS);
    if (raf) return;
    raf = requestAnimationFrame(() => { raf = 0; });
  }, { passive: true });

  /* the first canto starts open, but not as an explicit act: the reader's
     first scroll must still be free to move the opening elsewhere */
  if (sections[0]) apply(sections[0]);

  return { expand, current: () => current };
}
