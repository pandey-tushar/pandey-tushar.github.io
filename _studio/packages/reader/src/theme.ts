/* Theme toggle. The attribute is written before first paint (see
   preThemeScript / the inline script in the app shell), so this module only
   syncs the chip label and persists the choice. */

export const THEME_KEY = 'qd-theme';
export type Theme = 'light' | 'dark';

/** Default when nothing is stored. The book reads as a night sky. */
export const DEFAULT_THEME: Theme = 'dark';

/** Inline this in <head>, before any stylesheet, to avoid a theme flash. */
export const preThemeScript =
  "try{var t=localStorage.getItem('qd-theme');" +
  "document.documentElement.setAttribute('data-theme',t==='light'?'light':'dark');}catch(e){}";

export function currentTheme(): Theme {
  return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
}

export function setTheme(t: Theme): void {
  document.documentElement.setAttribute('data-theme', t);
  try { localStorage.setItem(THEME_KEY, t); } catch { /* private mode */ }
}

/** Wires the fixed chip. `phrases` invite the reader to the OTHER theme. */
export function initTheme(btn: HTMLElement, phrases: { toLight: string; toDark: string }): void {
  const label = () => (currentTheme() === 'light' ? phrases.toDark : phrases.toLight);
  btn.textContent = label();
  btn.addEventListener('click', () => {
    setTheme(currentTheme() === 'light' ? 'dark' : 'light');
    btn.textContent = label();
  });
}
