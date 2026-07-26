import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('.', import.meta.url));
/* a port of its own: other apps in this monorepo hold the 4173 to 4179 range */
const PORT = Number(process.env.SITE_TEST_PORT ?? 4319);
const baseURL = 'http://localhost:' + PORT;

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  timeout: 60_000,
  use: { baseURL, trace: 'retain-on-failure' },
  projects: [
    { name: '1440', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: '768', use: { ...devices['Desktop Chrome'], viewport: { width: 768, height: 1024 } } },
    { name: '375', use: { ...devices['Desktop Chrome'], viewport: { width: 375, height: 812 } } },
  ],
  webServer: {
    command: 'node scripts/serve.mjs ' + PORT,
    cwd: root,
    url: baseURL,
    /* never reuse: a stranger on this port would be tested instead of this build */
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
