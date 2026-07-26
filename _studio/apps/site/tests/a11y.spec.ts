import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const THEMES = ['dark', 'light'] as const;

async function settle(page: Page): Promise<void> {
  /* reveal sections and let the hero settle before scanning */
  await page.evaluate(() => scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(1200);
  await page.evaluate(() => scrollTo(0, 0));
  await page.waitForTimeout(400);
}

for (const theme of THEMES) {
  test('axe finds nothing critical or serious in the ' + theme + ' theme', async ({ page }) => {
    await page.addInitScript((t) => localStorage.setItem('qd-theme', t), theme);
    await page.goto('/');
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
    await settle(page);

    const { violations } = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
      .analyze();

    const bad = violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
    const summary = violations.map((v) =>
      v.impact + '  ' + v.id + '  x' + v.nodes.length + '  ' + v.nodes[0]?.target.join(' '));
    console.log('axe ' + theme + ': ' + (violations.length ? '\n  ' + summary.join('\n  ') : 'no violations'));
    expect(bad, summary.join('\n')).toEqual([]);
  });
}
