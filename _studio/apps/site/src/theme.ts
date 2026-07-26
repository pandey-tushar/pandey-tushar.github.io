/* Theme chip. The attribute is written before first paint by the inline script
   in index.html, so this only relabels the chip and persists the choice.
   The key matches the reader's, so the site and the book agree. */

export const THEME_KEY = 'qd-theme';
export type Theme = 'light' | 'dark';

export const current = (): Theme =>
  document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';

export function set(t: Theme): void {
  document.documentElement.setAttribute('data-theme', t);
  try { localStorage.setItem(THEME_KEY, t); } catch { /* private mode */ }
}

/** `phrases` invite the reader to the OTHER theme. */
export function initTheme(btn: HTMLElement, phrases: { toLight: string; toDark: string }): void {
  const paint = () => {
    const to = current() === 'light' ? phrases.toDark : phrases.toLight;
    btn.textContent = to;
    btn.setAttribute('aria-label', 'Switch to the ' + to + ' theme');
  };
  paint();
  btn.addEventListener('click', () => { set(current() === 'light' ? 'dark' : 'light'); paint(); });
}
