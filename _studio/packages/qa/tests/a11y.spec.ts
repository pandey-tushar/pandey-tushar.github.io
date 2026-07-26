import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/* Every theme, the same bar: no critical or serious violations. */
for (const theme of ['dark', 'light'] as const) {
  test('axe-core, ' + theme + ' theme', async ({ page }) => {
    await page.addInitScript((t) => { localStorage.setItem('qd-theme', t); }, theme);
    await page.goto('/');
    await expect(page.locator('#loader')).toHaveCount(0, { timeout: 10_000 });

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    const blocking = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious',
    );
    if (blocking.length) {
      console.log(JSON.stringify(
        blocking.map((v) => ({
          id: v.id, impact: v.impact, help: v.help,
          nodes: v.nodes.slice(0, 3).map((n) => n.target.join(' ')),
        })),
        null, 2,
      ));
    }
    expect(blocking.map((v) => v.id)).toEqual([]);
  });
}
