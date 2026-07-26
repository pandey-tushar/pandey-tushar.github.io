import { expect, test, type ConsoleMessage, type Page } from '@playwright/test';

const SCENE = /assets\/scene-[^/]+\.js$/;
const POSTER = /hero-poster(-narrow)?\.svg$/;

/** every console error and every uncaught exception, in order */
function watch(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (m: ConsoleMessage) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('requestfailed', (r) => {
    /* third party analytics can be blocked by the environment, not by us */
    if (!/googletagmanager\.com|google-analytics\.com|analytics\.google\.com/.test(r.url())) {
      errors.push('requestfailed: ' + r.url());
    }
  });
  return errors;
}

test('the server under test is this build', async ({ request }) => {
  const html = await (await request.get('/')).text();
  expect(html, 'another app in the monorepo is holding this port').toContain('Ph.D. Mathematics');
});

test('the page loads with no console errors', async ({ page }) => {
  const errors = watch(page);
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await page.evaluate(() => scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(1200);
  expect(errors).toEqual([]);
});

test('the poster is the first paint and the 3D arrives after it', async ({ page }) => {
  const order: string[] = [];
  page.on('response', (r) => {
    if (POSTER.test(r.url())) order.push('poster');
    if (SCENE.test(r.url())) order.push('scene');
  });
  await page.goto('/', { waitUntil: 'commit' });

  const poster = page.locator('#poster');
  await expect(poster).toBeVisible();
  /* the canvas does not exist yet: the hero is complete without it */
  expect(await page.locator('#scene').count()).toBe(0);
  const box = await poster.boundingBox();
  expect(box?.width).toBeGreaterThan(300);

  await page.waitForSelector('#scene', { timeout: 15_000 });
  expect(order[0]).toBe('poster');
  expect(order).toContain('scene');
});

test('the 3D upgrades in place over the poster', async ({ page }) => {
  await page.goto('/');
  await page.waitForSelector('#scene.up', { timeout: 15_000 });
  const state = await page.evaluate(() => {
    const c = document.getElementById('scene') as HTMLCanvasElement;
    const p = document.getElementById('poster') as HTMLImageElement;
    return {
      w: c.width, h: c.height,
      gl: !!c.getContext('webgl2') || !!c.getContext('webgl'),
      opacity: getComputedStyle(c).opacity,
      posterStillThere: !!p && p.isConnected,
      sameBox: JSON.stringify(c.getBoundingClientRect()) === JSON.stringify(p.getBoundingClientRect()),
    };
  });
  expect(state.w).toBeGreaterThan(0);
  expect(state.gl).toBe(true);
  expect(state.posterStillThere).toBe(true);
  expect(state.sameBox).toBe(true);
  await expect.poll(async () => page.evaluate(() =>
    getComputedStyle(document.getElementById('scene')!).opacity)).toBe('1');
});

test('the theme toggle works and persists', async ({ page }) => {
  await page.goto('/');
  const html = page.locator('html');
  await expect(html).toHaveAttribute('data-theme', 'dark');

  await page.click('#themeBtn');
  await expect(html).toHaveAttribute('data-theme', 'light');
  expect(await page.evaluate(() => localStorage.getItem('qd-theme'))).toBe('light');

  await page.reload();
  await expect(html).toHaveAttribute('data-theme', 'light');
  await expect(page.locator('#themeBtn')).toHaveText('night');

  await page.click('#themeBtn');
  await expect(html).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(html).toHaveAttribute('data-theme', 'dark');
});

test('reduced motion keeps the poster and never fetches the 3D bundle', async ({ page }) => {
  const errors = watch(page);
  const asked: string[] = [];
  page.on('request', (r) => { if (SCENE.test(r.url())) asked.push(r.url()); });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);
  await expect(page.locator('#poster')).toBeVisible();
  expect(await page.locator('#scene').count()).toBe(0);
  expect(asked).toEqual([]);
  expect(errors).toEqual([]);
});

test('a touch phone keeps the poster and never fetches the 3D bundle', async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, hasTouch: true, isMobile: true });
  const page = await ctx.newPage();
  const asked: string[] = [];
  page.on('request', (r) => { if (SCENE.test(r.url())) asked.push(r.url()); });
  await page.goto(process.env.SITE_TEST_BASE ?? 'http://localhost:4319/');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);
  await expect(page.locator('#poster')).toBeVisible();
  expect(asked).toEqual([]);
  await ctx.close();
});

test('the mobile menu opens and closes', async ({ page }, info) => {
  test.skip(info.project.name === '1440', 'the menu button only shows under 820px');
  await page.goto('/');
  const links = page.locator('#navlinks');
  await expect(links).toBeHidden();
  await page.click('#menuBtn');
  await expect(links).toBeVisible();
  await expect(page.locator('#menuBtn')).toHaveAttribute('aria-expanded', 'true');
});

test('the writing section says it is empty rather than faking a post', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#writing h2')).toHaveText('Notes, in the open.');
  await expect(page.locator('#writing .note-empty')).toBeVisible();
  expect(await page.locator('#writing .notes li').count()).toBe(0);
});

test('the feed, sitemap and robots are served', async ({ request }) => {
  for (const [path, needle] of [
    ['/feed.xml', '<rss'],
    ['/sitemap.xml', 'https://pandey-tushar.com/qubit-dialogues.html'],
    ['/robots.txt', 'Sitemap: https://pandey-tushar.com/sitemap.xml'],
  ]) {
    const res = await request.get(path);
    expect(res.status(), path).toBe(200);
    expect(await res.text(), path).toContain(needle);
  }
});
