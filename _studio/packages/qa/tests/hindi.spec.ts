import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const cantos = JSON.parse(
  readFileSync(fileURLToPath(new URL('../../../content/hi.json', import.meta.url)), 'utf8'),
) as { n: number; title: string }[];

function watchConsole(page: import('@playwright/test').Page): string[] {
  const errors: string[] = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('requestfailed', (r) => errors.push('requestfailed: ' + r.url() + ' ' + (r.failure()?.errorText ?? '')));
  return errors;
}

test.describe('the Hindi edition', () => {
  test('renders every canto with no console errors', async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto('/');
    await expect(page.locator('html')).toHaveAttribute('lang', 'hi');
    await expect(page.locator('section.canto.acc')).toHaveCount(cantos.length);
    const titles = await page.locator('section.canto.acc .canto-title').allTextContents();
    expect(titles).toEqual(cantos.map((c) => c.title));
    await page.waitForTimeout(1500);
    expect(errors).toEqual([]);
  });

  test('prints its chrome in Hindi, with Devanagari canto numbers', async ({ page }) => {
    await page.goto('/');
    const nums = await page.locator('section.canto.acc .canto-num').allTextContents();
    expect(nums[0]).toBe('सर्ग १ / ४');
    expect(nums.join(' ')).not.toContain('Canto');

    await expect(page.locator('#mala')).toHaveAttribute('aria-label', 'सर्ग');
    await expect(page.locator('#theme-toggle')).toHaveAttribute('aria-label', 'उजाला या अँधेरा रंगरूप बदलें');
    /* scoped to #content: the invocation's own reflect label is front matter */
    await expect(page.locator('#content .reflect .r-label').first()).toHaveText('आपके लिए एक प्रश्न');
    await expect(page.locator('#references .foot-note strong').first()).toContainText('सर्ग १');

    /* nothing the reader prints for itself is left in English */
    const chrome = await page.evaluate(() => {
      const take = (sel: string) => [...document.querySelectorAll(sel)].map((e) => e.textContent ?? '');
      return take('.canto-num').concat(
        take('.assume .a-head'), take('#content .reflect .r-label'),
        take('.pred .p-title'), take('.conf .label'), take('.speaker'), take('.science h4'),
      ).join(' | ');
    });
    for (const english of ['Canto', 'The Assumption Challenged', 'A Prediction', 'A Question For You', 'confidence']) {
      expect(chrome, english + ' should not survive into the Hindi edition').not.toContain(english);
    }
  });

  test('takes its scene readouts from content, not from the DOM afterwards', async ({ page }) => {
    await page.goto('/');
    /* canto 2 carries the entangled pair; measuring writes a readout */
    await page.locator('#canto-2 .canto-head').click();
    const scene = page.locator('#canto-2 .scene[data-scene="entangle"]');
    await expect(scene.locator('canvas')).toHaveCount(1, { timeout: 15_000 });
    await scene.locator('[data-act=measure]').click();
    await expect(scene.locator('.rl')).toContainText('मापा गया');
    await expect(scene.locator('.rl')).not.toContainText('measured');
  });

  test('renders every cluster: no dotted circles anywhere', async ({ page }) => {
    /* U+25CC is what a shaper emits when it cannot attach a matra or build a
       conjunct, so a single one in the rendered text means broken Devanagari */
    await page.goto('/');
    const dotted = await page.evaluate(() => (document.body.innerText.match(/◌/g) ?? []).length);
    expect(dotted).toBe(0);
  });

  test('uses the self-hosted Devanagari face, not a system fallback', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => document.fonts.ready);
    const loaded = await page.evaluate(() =>
      [...document.fonts].filter((f) => f.family.includes('Devanagari') && f.status === 'loaded')
        .map((f) => f.family + ' ' + f.weight));
    expect(loaded.length).toBeGreaterThan(0);
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
