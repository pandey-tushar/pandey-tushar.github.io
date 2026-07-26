import { test, expect, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const cantos = JSON.parse(
  readFileSync(fileURLToPath(new URL('../../../content/en.json', import.meta.url)), 'utf8'),
) as { n: number; title: string; blocks: { t: string; text?: string | string[]; kind?: string }[] }[];

/** First run of prose in a canto, used to prove the text reached the DOM. */
function firstLine(n: number): string {
  const c = cantos.find((x) => x.n === n)!;
  for (const b of c.blocks) {
    if (b.t === 'p' && typeof b.text === 'string') return b.text.slice(0, 60);
    if (b.t === 'dlg' && Array.isArray(b.text)) return b.text[0].slice(0, 60);
  }
  throw new Error('no prose in canto ' + n);
}

/** The opening canto expands over a 0.42s grid transition. Geometry read
    before it lands is meaningless, so every scroll test waits for it. */
async function settled(page: Page): Promise<void> {
  await page.waitForFunction(
    () => (document.querySelector('#canto-1 .canto-body') as HTMLElement).offsetHeight > 1000,
    null, { timeout: 10_000 },
  );
  await page.waitForTimeout(300);
}

/** Attaches a console/pageerror sink before navigation. */
function watchConsole(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('requestfailed', (r) => errors.push('requestfailed: ' + r.url() + ' ' + (r.failure()?.errorText ?? '')));
  return errors;
}

test.describe('the text edition', () => {
  test('renders all 22 cantos with no console errors', async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto('/');
    await expect(page.locator('section.canto.acc')).toHaveCount(22);

    /* every canto title is present, in order */
    const titles = await page.locator('section.canto.acc .canto-title').allTextContents();
    expect(titles).toEqual(cantos.map((c) => c.title));

    /* first and last canto prose reached the DOM, open or collapsed */
    const body = await page.locator('#content').textContent();
    expect(body).toContain(firstLine(1));
    expect(body).toContain(firstLine(22));

    /* the rail has a bead per canto and the appendix gathered every note */
    await expect(page.locator('#mala .bead')).toHaveCount(22);
    await expect(page.locator('#references .foot-note')).toHaveCount(22);

    await page.waitForTimeout(1500);
    expect(errors).toEqual([]);
  });

  test('still calls its parts cantos', async ({ page }) => {
    await page.goto('/');
    const nums = await page.locator('section.canto.acc .canto-num').allTextContents();
    expect(nums[0]).toBe('Canto 1 of 22');
    expect(nums[21]).toBe('Canto 22 of 22');
    await expect(page.locator('#mala')).toHaveAttribute('aria-label', 'Cantos');
    await expect(page.locator('#mala .bead').first()).toHaveAttribute(
      'aria-label', 'Canto 1: ' + cantos[0].title,
    );
    await expect(page.locator('#theme-toggle')).toHaveAttribute('aria-label', 'Toggle light or dark theme');
    await expect(page.locator('.assume .a-head').first()).toHaveText('The Assumption Challenged');
    /* scoped to #content: the invocation's own reflect label is front matter */
    await expect(page.locator('#content .reflect .r-label').first()).toHaveText('A Question For You');
    await expect(page.locator('#references .foot-note strong').first())
      .toHaveText('CANTO 1 · ' + cantos[0].title.toUpperCase());
  });

  test('does not scroll sideways', async ({ page }) => {
    /* #cover breaks out to full bleed; built on 100vw it counted the scrollbar
       gutter and pushed the document 15px sideways on desktop */
    await page.goto('/');
    const over = await page.evaluate(() => {
      const h = document.documentElement;
      return h.scrollWidth - h.clientWidth;
    });
    expect(over).toBeLessThanOrEqual(0);
  });

  test('renders KaTeX with the packaged stylesheet', async ({ page }) => {
    await page.goto('/');
    const math = page.locator('.katex').first();
    await expect(math).toHaveCount(1);
    /* katex.min.css came from the npm package, not an inlined blob */
    const font = await math.evaluate((el) => getComputedStyle(el).fontFamily);
    expect(font).toContain('KaTeX_Main');
    expect(await page.locator('.eqblock .katex-display').count()).toBeGreaterThan(0);
  });

  test('opens exactly one canto at a time', async ({ page }) => {
    await page.goto('/');
    await settled(page);
    await expect(page.locator('#canto-1')).toHaveClass(/expanded/);
    await expect(page.locator('section.canto.expanded')).toHaveCount(1);

    await page.locator('#canto-5 .canto-head').click();
    await expect(page.locator('#canto-5')).toHaveClass(/expanded/);
    await expect(page.locator('#canto-1')).not.toHaveClass(/expanded/);
    await expect(page.locator('section.canto.expanded')).toHaveCount(1);
    await expect(page.locator('#canto-5 .canto-head')).toHaveAttribute('aria-expanded', 'true');

    /* the settle handler must converge, not flap */
    await page.waitForTimeout(600);
    await expect(page.locator('section.canto.expanded')).toHaveCount(1);
  });

  test('opens the canto the reader scrolls into', async ({ page }) => {
    /* geometry-on-settle: the open canto is the last header above the viewport
       centre line, and the compensation scroll must converge on it */
    await page.goto('/');
    await settled(page);
    await page.evaluate(() => {
      const head = document.querySelector('#canto-3 .canto-head')!;
      scrollTo({ top: head.getBoundingClientRect().top + scrollY - innerHeight / 3, behavior: 'instant' });
    });
    await page.waitForTimeout(900);

    const open = await page.locator('section.canto.expanded').getAttribute('id');
    expect(open).not.toBe('canto-1');
    await expect(page.locator('section.canto.expanded')).toHaveCount(1);

    const predicted = await page.evaluate(() => {
      const line = scrollY + innerHeight / 2;
      let best: Element | null = null;
      for (const s of document.querySelectorAll('section.canto.acc')) {
        const t = s.querySelector('.canto-head')!.getBoundingClientRect().top + scrollY;
        if (t <= line) best = s; else break;
      }
      return best?.id ?? null;
    });
    expect(open).toBe(predicted);

    const width = await page.locator('#prog').evaluate((el) => el.style.width);
    expect(width).not.toBe('');
  });

  test('toggles theme and remembers it', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');

    const toggle = page.locator('#theme-toggle');
    await expect(toggle).toBeVisible();
    await toggle.click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
    expect(await page.evaluate(() => localStorage.getItem('qd-theme'))).toBe('light');

    /* the page background actually changed, not just the attribute */
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    expect(bg).toBe('rgb(245, 239, 226)');

    await page.reload();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
    await toggle.click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  });

  test('keeps the theme chip fixed to the viewport', async ({ page }) => {
    /* a transformed ancestor would capture position:fixed and the chip would
       scroll away with the page */
    await page.goto('/');
    const before = await page.locator('#theme-toggle').boundingBox();
    await page.evaluate(() => scrollTo({ top: 2400, behavior: 'instant' }));
    await page.waitForTimeout(400);
    const after = await page.locator('#theme-toggle').boundingBox();
    expect(after!.y).toBeCloseTo(before!.y, 0);
  });

  test('mounts an interactive scene when its canto opens', async ({ page }) => {
    await page.goto('/');
    const scene = page.locator('#canto-1 .scene[data-scene="bloch"]');
    await expect(scene).toHaveCount(1);
    await expect(scene.locator('canvas')).toHaveCount(1, { timeout: 15_000 });
    const size = await scene.locator('canvas').evaluate((c) => (c as HTMLCanvasElement).width);
    expect(size).toBeGreaterThan(0);
  });

  test('every registered scene mounts a live canvas', async ({ page }) => {
    /* scenes mount on expand, never on intersection: a scene inside a
       collapsed canto has zero height and would never initialise */
    const errors = watchConsole(page);
    await page.goto('/');
    await settled(page);

    const scenes = cantos.flatMap((c) =>
      c.blocks.filter((b) => b.t === 'scene').map((b) => ({ n: c.n, kind: b.kind ?? '' })));
    expect(scenes.length).toBe(9);

    for (const s of scenes) {
      await page.locator('#canto-' + s.n + ' .canto-head').click();
      const canvas = page.locator('#canto-' + s.n + ' .scene[data-scene="' + s.kind + '"] canvas');
      await expect(canvas, s.kind + ' in canto ' + s.n).toHaveCount(1, { timeout: 15_000 });
      const w = await canvas.evaluate((c) => (c as HTMLCanvasElement).width);
      expect(w, s.kind + ' canvas width').toBeGreaterThan(0);
    }

    await page.waitForTimeout(800);
    expect(errors).toEqual([]);
  });
});
