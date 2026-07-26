/* Client wiring. The page is already rendered when this runs, so this only
   handles the things a static file cannot: the sticky header, the mobile menu,
   the reveal, the theme chip, the scene caption, and the hero upgrade. */

import './styles/site.css';
import { initTheme } from './theme.ts';
import { upgradeHero } from './hero/upgrade.ts';

const $ = <T extends HTMLElement>(id: string): T | null => document.getElementById(id) as T | null;

const hdr = $('hdr');
const menuBtn = $('menuBtn');
const navlinks = $('navlinks');
const themeBtn = $('themeBtn');
const act = $('act');

if (menuBtn && navlinks) {
  menuBtn.addEventListener('click', () => {
    const open = navlinks.classList.toggle('open');
    menuBtn.setAttribute('aria-expanded', String(open));
  });
  navlinks.querySelectorAll('a').forEach((a) =>
    a.addEventListener('click', () => {
      navlinks.classList.remove('open');
      menuBtn.setAttribute('aria-expanded', 'false');
    }));
}

if (themeBtn) initTheme(themeBtn, { toLight: 'paper', toDark: 'night' });

const ro = new IntersectionObserver((es) => es.forEach((e) => {
  if (e.isIntersecting) { e.target.classList.add('in'); ro.unobserve(e.target); }
}), { rootMargin: '0px 0px -10% 0px' });
document.querySelectorAll('.reveal').forEach((el) => ro.observe(el));

/* The caption under the scene. It opens on the site's own line and hands over
   to the act labels as each section takes the screen. */
const acts = [...document.querySelectorAll<HTMLElement>('[data-act]')];
const rest = act?.textContent ?? '';
const progress = (el: Element): number => {
  const top = el.getBoundingClientRect().top, vh = innerHeight;
  return Math.max(0, Math.min(1, (vh * 0.7 - top) / (vh * 0.7)));
};

function onScroll(): void {
  hdr?.classList.toggle('scrolled', scrollY > 20);
  if (!act) return;
  let label = rest;
  for (const el of acts) if (progress(el) > Number(el.dataset.actAt ?? 0.45)) label = el.dataset.act ?? label;
  if (act.textContent !== label) act.textContent = label;
}
addEventListener('scroll', onScroll, { passive: true });
onScroll();

upgradeHero();
