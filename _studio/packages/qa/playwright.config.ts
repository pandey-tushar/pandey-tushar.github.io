import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const repoRoot = fileURLToPath(new URL('../..', import.meta.url));

/* One port per app, assigned in PORTS.md. Every server here is started fresh:
   reuseExistingServer would let a preview server somebody left running be
   tested instead of the build under test, which has already cost one full red
   run in this repo. --strictPort makes a taken port a loud failure. */
const PORTS = { book: 4173, unpolarized: 4176, hindi: 4177 } as const;
const url = (p: number): string => 'http://localhost:' + p;

const server = (workspace: string, port: number) => ({
  command: 'npm run preview -w ' + workspace + ' -- --port ' + port + ' --strictPort',
  cwd: repoRoot,
  url: url(port),
  reuseExistingServer: false,
  timeout: 120_000,
});

const chrome = (width: number, height: number) => ({
  ...devices['Desktop Chrome'],
  viewport: { width, height },
});

export default defineConfig({
  testDir: './tests',
  /* the accordion is driven by real scrolling, so keep runs deterministic */
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  timeout: 60_000,
  use: { trace: 'retain-on-failure' },
  projects: [
    /* the English text edition, the reference behaviour: three viewports */
    { name: 'book-1440', testMatch: /(book|a11y)\.spec\.ts/, use: { ...chrome(1440, 900), baseURL: url(PORTS.book) } },
    { name: 'book-768', testMatch: /(book|a11y)\.spec\.ts/, use: { ...chrome(768, 1024), baseURL: url(PORTS.book) } },
    { name: 'book-375', testMatch: /(book|a11y)\.spec\.ts/, use: { ...chrome(375, 812), baseURL: url(PORTS.book) } },
    /* the two editions that reuse the reader: desktop and phone */
    { name: 'unpolarized-1440', testMatch: /unpolarized\.spec\.ts/, use: { ...chrome(1440, 900), baseURL: url(PORTS.unpolarized) } },
    { name: 'unpolarized-375', testMatch: /unpolarized\.spec\.ts/, use: { ...chrome(375, 812), baseURL: url(PORTS.unpolarized) } },
    { name: 'hindi-1440', testMatch: /hindi\.spec\.ts/, use: { ...chrome(1440, 900), baseURL: url(PORTS.hindi) } },
    { name: 'hindi-375', testMatch: /hindi\.spec\.ts/, use: { ...chrome(375, 812), baseURL: url(PORTS.hindi) } },
  ],
  webServer: [
    server('@qubit/book', PORTS.book),
    server('@qubit/unpolarized', PORTS.unpolarized),
    server('@qubit/hindi', PORTS.hindi),
  ],
});
