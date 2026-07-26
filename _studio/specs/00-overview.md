# Qubit Dialogues + Site: Program Overview

Four deliverables, one stack, one QA harness. Read this before any individual spec.

## The four

| # | Deliverable | Shape | Spec |
|---|---|---|---|
| 1 | pandey-tushar.com | Rebuilt as modular Vite project | `01-website.md` |
| 2 | Illustrated edition | The Qubit Dialogues, art-led, scroll-animated | `02-illustrated-edition.md` |
| 3 | Hindi edition | Re-authored in Hindi, not translated | `03-hindi-edition.md` |
| 4 | An Unpolarized Life | New standalone book, minimal science | `04-life-edition.md` |

## Shared architecture

**Monorepo, Vite, TypeScript.** One repo, npm workspaces:

```
qubit/
  packages/
    tokens/        design tokens (color, type, spacing) as CSS vars + TS
    reader/        canto renderer: takes book data, renders chapters, themes, accordion, print
    motifs/        generative art system (coin, sphere, lattice, wall, lock, fire)
    qa/            test harness, tell-census, glossary checker, link checker
  content/
    en.json        existing 22 cantos (source of truth, already written)
    hi.json        Hindi edition
    life.json      Life edition
  apps/
    site/          pandey-tushar.com
    book/          text edition (current experience, ported)
    illustrated/   art-led edition
  .github/workflows/deploy.yml
```

Rationale: the Hindi and Life editions are new *content* against the same renderer, not new codebases. Only the illustrated edition needs genuinely new engine work. Build once, publish four.

**Content stays data.** Every edition is a JSON/TS file validated against one schema. Adding a canto is adding an object. No prose lives in markup, ever.

**Deployment, current decision.** Only the website publishes. The three new editions are built and reviewed locally and stay unpublished until a separate decision. GitHub Actions builds and deploys `apps/site` to Pages, keeping the `CNAME`, GA4 `G-DVPGC1C44Z`, and every existing URL alive. New editions build to preview output that runs on a local server and is never pushed to a public route.

Consequences to respect while building:
- No new edition may be linked from the live site, sitemap, or any OG tag until it is published deliberately.
- `pandey-tushar.com/qubit-dialogues.html` keeps working exactly as it does today, untouched.
- `qubitdialogues.com` stays a redirect for now.
- Build the editions as if they will be public, since they will be. Publishing later should be a config change, not a rewrite.

**URL plan, proposed and deferred.** Agree this before the first edition publishes, since changing it afterward costs search ranking.

| URL | Content | Status |
|---|---|---|
| pandey-tushar.com | Site | live |
| pandey-tushar.com/qubit-dialogues.html | Current text edition | live, must keep working |
| qubitdialogues.com | Book hub | proposed |
| qubitdialogues.com/read | Text edition (canonical) | proposed |
| qubitdialogues.com/illustrated | Illustrated edition | proposed |
| qubitdialogues.com/hindi | Hindi edition | proposed |
| qubitdialogues.com/unpolarized | Life edition | proposed |

## Shared QA harness (`packages/qa`)

Every deliverable runs the same gates in CI. A build that fails a gate does not deploy.

1. **Playwright suite**: real browser, real viewports (1440, 768, 375). Screenshots per route committed as baselines; diffs above threshold fail.
2. **Lighthouse CI budgets**: performance 90+, accessibility 100, LCP under 2.5s, CLS under 0.1, TBT under 200ms. Illustrated edition gets its own looser performance budget but never a looser a11y budget.
3. **axe-core**: zero critical violations, every theme, every route.
4. **Console sweep**: zero errors or warnings on load and after scripted interaction.
5. **Tell census** (`qa/census.ts`): regex sweep for AI fingerprints (em-dashes, "not X but Y" chains, quietly/simply/whisper/delve/tapestry/testament, triadic runs). Prints counts, fails on regressions.
6. **Link and meta check**: no dead links, every route has title/description/canonical/og:image resolving 200.
7. **Reduced-motion path**: every animated route renders complete, readable, static content with `prefers-reduced-motion: reduce`.
8. **Print check**: text edition still exports a valid PDF, all cantos present (pypdf page and text extraction, as already scripted).

**Non-automatable gates** are named explicitly in each spec with a human owner. Literary quality and visual judgment are reviewed by a person, and those reviews block release exactly the way a failing test does.

## Sequencing and honest effort

Do not attempt these in parallel. Suggested order:

1. **Monorepo + tokens + reader + QA harness, port text edition** as-is. Nothing user-visible changes; you get the foundation and prove parity. *Largest infrastructure risk, lowest creative payoff. Do it first anyway.*
2. **Website** (`01`). Smallest scope on a stack that now exists.
3. **Life edition** (`04`). New writing, reuses the reader unchanged. Highest reward per unit effort and the most distinct artifact.
4. **Hindi edition** (`03`). Needs your review cycles; runs alongside anything.
5. **Illustrated edition** (`02`). Largest, most novel, most likely to slip. Do it when the base is stable.

Rough effort, agent-assisted: step 1 is days, the website days, each book edition weeks (writing dominates, not code), illustrated edition weeks to months depending on art ambition. This is a program, not a sprint.

## Rules that apply to everything

- No em-dashes in any prose or code comment, any language.
- Commit messages plain. No AI attribution, no co-author trailers.
- One stable filename per artifact. Iterate in place, never fork `-v2`.
- Every "done" claim carries evidence: passing gate, screenshot, or live URL.
- Existing URLs keep working. A rebuild that 404s the book is a failed rebuild.
