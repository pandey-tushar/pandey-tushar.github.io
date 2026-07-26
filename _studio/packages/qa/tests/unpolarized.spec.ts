import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const cantos = JSON.parse(
  readFileSync(fileURLToPath(new URL('../../../content/unpolarized.json', import.meta.url)), 'utf8'),
) as { n: number; title: string }[];

function watchConsole(page: import('@playwright/test').Page): string[] {
  const errors: string[] = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('requestfailed', (r) => errors.push('requestfailed: ' + r.url() + ' ' + (r.failure()?.errorText ?? '')));
  return errors;
}

test.describe('An Unpolarized Life', () => {
  test('renders every chapter with no console errors', async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto('/');
    await expect(page.locator('section.canto.acc')).toHaveCount(cantos.length);
    const titles = await page.locator('section.canto.acc .canto-title').allTextContents();
    expect(titles).toEqual(cantos.map((c) => c.title));
    await expect(page.locator('#mala .bead')).toHaveCount(cantos.length);
    await page.waitForTimeout(1200);
    expect(errors).toEqual([]);
  });

  test('calls its parts chapters, not cantos', async ({ page }) => {
    await page.goto('/');
    const nums = await page.locator('section.canto.acc .canto-num').allTextContents();
    expect(nums[0]).toBe('Chapter 1 of ' + cantos.length);
    expect(nums.join(' ')).not.toContain('Canto');

    await expect(page.locator('#mala')).toHaveAttribute('aria-label', 'Chapters');
    await expect(page.locator('#mala .bead').first()).toHaveAttribute(
      'aria-label', 'Chapter 1: ' + cantos[0].title,
    );
  });

  test('is a text-only build: no scene canvas, no three.js request', async ({ page }) => {
    const scripts: string[] = [];
    page.on('request', (r) => { if (r.resourceType() === 'script') scripts.push(r.url()); });
    await page.goto('/');
    await page.locator('#canto-1 .canto-head').click();
    await page.waitForTimeout(1200);
    /* the starfield element exists but nothing ever paints into it; what must
       not exist is a scene canvas, and what must not be fetched is three.js */
    await expect(page.locator('.scene canvas')).toHaveCount(0);
    await expect(page.locator('#cover3d canvas')).toHaveCount(0);
    expect(scripts.filter((u) => /three|common-/.test(u))).toEqual([]);
  });

  test('does not scroll sideways', async ({ page }) => {
    await page.goto('/');
    const over = await page.evaluate(() => {
      const h = document.documentElement;
      return h.scrollWidth - h.clientWidth;
    });
    expect(over).toBeLessThanOrEqual(0);
  });
});
