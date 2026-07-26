# Integration record

Four editions were built in parallel, each forbidden from touching shared
files. Each recorded what it needed in an `INTEGRATION-*.md` note instead of
changing it. This file replaces those four notes: every item is listed with
what was done, and the ones that were declined say why.

Nothing below is outstanding unless it is in the last section.

## Root manifest and TypeScript config

`package.json` scripts reached only `@qubit/book`; `tsconfig.json` included
only `apps/book/src`. Every one of the four notes asked for the same thing.

- `build` now fans out across all five apps. `build:book`, `build:site`,
  `build:illustrated`, `build:hindi` and `build:unpolarized` build one each.
- `qa` chains build, typecheck, validate, parity, census, the two content
  gates, the shared Playwright suite, `qa:site` and `qa:illustrated`.
- Root `tsconfig.json` includes every package and app source tree, both
  Playwright configs, and both test directories. `allowImportingTsExtensions`
  is on, which `apps/site` needs for its Vite plugin imports.
- `@qubit/motifs` and `@qubit/reader/scenes` are in `compilerOptions.paths`.
- The per-app `tsconfig.json` files no longer redeclare paths. They extend the
  root and name their own `include`, so `npm run typecheck -w <app>` still
  works and there is one copy of the path map.

## Ports

`apps/site`, `apps/unpolarized` and `apps/hindi` had all chosen 5174/4174 and
`apps/illustrated` had taken 5175/4175. `apps/unpolarized` moved to 5176/4176
and the full table is in `PORTS.md`. `packages/qa/playwright.config.ts` sets
`reuseExistingServer: false` on every server, which caught a stray preview
server on 4177 the first time it ran.

## Content exports

Both the Hindi and the Life note asked for the new editions to be exported
from `content/index.ts` beside `en` and `frontEn`. **Done differently.**
`content/index.ts` is imported for its side effect of validating at import
time, so a barrel holding all three editions would put all three JSON files in
every app's bundle: 276 kB of `en.json` inside An Unpolarized Life, and 147 kB
of the other two inside `apps/book`. Each edition is its own entry point
instead, `@qubit/content/hi` and `@qubit/content/unpolarized`, with the same
validate-on-import contract. The raw `.json` subpaths both notes asked for are
in the `exports` map as well, so the Vite aliases that pointed at file paths
now point at package subpaths.

## The reader printed its chrome in English

Both the Hindi note and the Life note reported this; the Life edition was
displaying "Canto 1 of 12" for what are chapters, and the Hindi edition
carried a seventy-line `localize.ts` that rewrote the DOM after mount.

Two solutions were proposed. The Life note suggested a single
`front.cantoLabel ?? 'Canto'`; the Hindi note suggested a whole `labels`
object on `FrontMatter`. **The `labels` object was taken**, because one field
fixes one string and the Hindi edition needed fourteen of them.

`FrontMatter.labels` is optional and every field in it is optional. Templates
take `{n}`, `{total}` and `{title}`; `labels.digits` is a ten-character
numeral table for an edition that numbers its cantos in another script.
`packages/reader` fills every gap from `DEFAULT_LABELS`, which is the English
wording exactly as it was, so `apps/book` carries no labels and is unchanged.

`apps/hindi/src/localize.ts` is deleted, along with the `MutationObserver` it
used to catch scene readouts. Scene readouts now come from a `strings` field
on the scene block, read by the scene module through `readouts()` in
`scenes/common.ts`. `entangle`, `decohere` and `toric` take their readouts
that way; the remaining scenes write no readouts.

## Scene chunks in a text-only build

`apps/unpolarized` passes no scene mounter, and used to emit a 485 kB Three.js
chunk plus nine scene chunks that no reader ever fetched. Rollup emits a chunk
for every dynamic import it can reach, so hiding the registry behind a runtime
`if` would not have helped: the registry had to leave the reader core.

`ReaderOptions.scenes` is now a `SceneMounter` rather than a boolean, and the
reader core imports only the type. An edition that wants scenes passes the
bundled one:

```ts
import { scenes } from '@qubit/reader/scenes';
mountReader({ cantos, front, scenes });
```

`apps/unpolarized/dist` is now one 67 kB JavaScript file with no three.js.

## `--site-text-3` failed AA

`#69728e` measured 4.14:1 on `--site-ink`, and `apps/site` lifted it locally
with `color-mix(in srgb, var(--site-text-3) 80%, var(--site-text))`. That
mix evaluates to exactly `#828aa3`, so the token was set to `#828aa3` and both
copies of the workaround deleted: 5.75:1 on `--site-ink`, 5.14:1 on
`--site-surface`, and not one rendered pixel changed.

## `#cover` overflowed sideways

`width: 100vw` counts the classic scrollbar gutter, so the full-bleed cover was
15 px wider than the client area and the document scrolled sideways at 1440.
`mountReader` publishes the real client width as `--page` on `<html>` and
`reader.css` uses it, with `100vw` as the fallback. Every edition is covered,
and each Playwright suite asserts `scrollWidth <= clientWidth`.

## The Devanagari font was not self-hosted

Spec 03 asks for Noto Serif Devanagari or Mukta, self-hosted and subset. Both
faces now come from Fontsource as versioned npm packages rather than loose
binaries: `@fontsource/noto-serif-devanagari` for the body stack and
`@fontsource/noto-sans-devanagari` for the label stack, Devanagari subset
only, weights 400 and 600. The commented `@font-face` block in
`devanagari.css` is replaced by four `@import` lines.

Measured on the built page, the danda U+0964 now resolves to the self-hosted
face: advance 23.62 and left side bearing 12 at 64 px, against 27.66 and 14
for the Nirmala UI fallback it used to land on. The gap the Hindi note
reported before every sentence end is 14 percent narrower and, more to the
point, is now a property of a face in the lockfile.

## QA harness

`packages/qa` runs three editions from one config: the book at 4173 across
1440, 768 and 375, and An Unpolarized Life at 4176 and the Hindi edition at
4177 across 1440 and 375.

The site's Playwright suite, axe pass, parity gate and Lighthouse runner stay
in `apps/site`. **Declined the move to `packages/qa`.** They need the site's
own dist, its own server script and a live comparison target that no other
edition has; the site note itself said the move buys nothing but a `testDir`
and an environment variable. They are reachable from the root as `qa:site`,
which is what the request actually needed.

The four illustrated gates stay as scripts under `apps/illustrated/tools/`,
reachable from the root as `qa:illustrated`. The site note and the illustrated
note both suggested Playwright projects; the poster and determinism runners
write files and compare pixels across fresh contexts, which is not the
Playwright test model, and the illustrated note said so itself.

`apps/hindi/scripts/glossary-check.mjs` learned to skip `{n}` style
placeholders and the numeral table, which are machine values and were failing
its stray-Latin and Devanagari-digit rules.

## Census baseline

Blessed once, in the commit that accepts the prose, as the Life note asked.
`content/en.json` is unchanged at 53 hits. The new files add one:
`content/unpolarized.json` `triadic-run: 1`, on "The window dimmed, and dimmed
further, and at some angle went out altogether", which is deliberate
repetition rather than the "a, b, and c" tic the pattern hunts for.

## Left undone

- ~~**KaTeX rides along in editions with no mathematics.**~~ **Done.** The
  reader core no longer imports `katex.min.css`. `@qubit/reader/math` pairs
  KaTeX with the reader's overrides of it, in that order, inside one module, so
  the cascade is fixed locally rather than depending on the order an app happens
  to import things. `styles/math.css` holds the five `.katex` rules that used to
  sit in `reader.css`; the `.eqblock`, `.eqi` and `.eqtrail` wrappers stay in
  `reader.css`, since those exist whether or not KaTeX is loaded. `apps/book`
  and `apps/hindi` import the pair; `apps/unpolarized` imports neither and
  dropped from 1.3 MB to 88 KB with zero KaTeX files.
  `apps/illustrated` deliberately keeps a bare `katex.min.css` import and does
  **not** use the shim: it never loads `reader.css` and sets its own
  `.katex { font-size: 1em }`, which the shim's higher-specificity
  `.eqblock .katex` rule would have silently overridden.
  Verified: `apps/book`'s science block is byte-identical before and after in
  both themes (sha256 `a99a5c02…` dark, `69f4dd4f…` light) with every computed
  value on `.katex` unchanged; `npm run qa` exits 0.
  Note that the aliases are what actually resolve these subpaths: adding an
  `exports` entry is not enough, since each app resolves `@qubit/*` through its
  own `vite.config.ts` alias list, where a bare `@qubit/reader` entry also
  swallows its subpaths unless a more specific one precedes it.
- **`content/hi.json` still carries `name` on every dialogue block and `head`
  on every science block**, which `front.hi.json` `labels` now also supplies.
  The block-level value wins, so the edition is correct, but editing
  `labels.seeker` would silently do nothing. Stripping the redundant fields is
  content surgery on another workstream's prose and was left alone.
- **Lighthouse has been run only against `apps/site`.** Spec 00 gives the
  illustrated edition a looser performance budget and never a looser
  accessibility budget; no edition but the site has a Lighthouse number.
- **axe has not been run against the illustrated edition.** The book, the
  Hindi edition and the site all have a passing axe run; the illustrated
  edition has a careful argument and no measurement.
- **The site's deploy step still owns seven files this build does not
  produce** (`cv.html`, `qubit-dialogues.html`, the two OG images, the two
  résumé PDFs and `CNAME`). `apps/site/scripts/parity.mjs` fails if any of
  them goes missing from the live folder, which is the guard, not the fix.
