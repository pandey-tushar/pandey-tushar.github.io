# Ports

Assigned centrally. Three apps had independently chosen 5174/4174 and one more
had taken 5175/4175, so only one of them could bind at a time. Every port below
is unique, so every edition can run at once, and the QA harness never reuses an
existing server: a stranger on the port would be tested instead of the build
under test.

| App | Workspace | Dev (`vite`) | Preview (`vite preview`) |
|---|---|---|---|
| Text edition | `@qubit/book` | 5173 | 4173 |
| Website | `@qubit/site` | 5174 | 4174 |
| Illustrated edition | `@qubit/illustrated` | 5175 | 4175 |
| An Unpolarized Life | `@qubit/unpolarized` | 5176 | 4176 |
| आधा उजाला (Hindi, An Unpolarized Life) | `@qubit/hindi-unpolarized` | 5178 | 4178 |

Test servers, which are separate processes started by a test runner and must
not collide with a preview server a person left running:

| Runner | Port | Config |
|---|---|---|
| `packages/qa` book suite | 4173 | `packages/qa/playwright.config.ts` |
| `packages/qa` unpolarized suite | 4176 | `packages/qa/playwright.config.ts` |
| `packages/qa` hindi-unpolarized suite | 4178 | not yet written; reserved |
| `apps/site` Playwright suite | 4319 | `apps/site/playwright.config.ts`, override with `SITE_TEST_PORT` |
| `apps/site` Lighthouse | 4320 | `apps/site/scripts/lighthouse.mjs` |
| `apps/illustrated` gate runners | ephemeral | `apps/illustrated/tools/serve.mjs` picks a free port |

The QA harness builds each app before it previews it, and every `webServer`
entry sets `reuseExistingServer: false` and `--strictPort`, so a run either
tests the build it just made or fails loudly.

Adding an app: take the next free pair (5179/4179) and add a row here.
