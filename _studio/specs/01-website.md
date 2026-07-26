# Spec 01: pandey-tushar.com, modular rebuild

## Goal

Rebuild the personal site as a modular Vite application that keeps everything the current site earns (the knot hero, the two-act structure, the voice) and raises the ceiling on performance, structure, and what can be added next. A visitor should not notice a "rewrite". They should notice it got faster and there is more worth reading.

## Non-goals

- Not a redesign. The positioning work (QEC lead, AI second, math as origin) was decided by persona panels and holds. Copy changes only where content is added.
- Not a CMS. Content stays as typed data in the repo.
- Not a blog engine. If writing gets added, it is markdown compiled at build, no runtime fetching.

## Approach

**Stack**: Vite + TypeScript, no UI framework unless a section genuinely needs state (the current site needs none). Three.js as a real dependency, tree-shaken and lazy-loaded rather than inlined at 600KB.

**Structure**: `apps/site` consuming `packages/tokens`. Sections as modules, content as typed objects:

```ts
export const research: Entry[] = [
  { title, venue, year, href, blurb, tags }
]
```

**The hero must earn its weight.** Current knot loads Three.js before anything renders. New behavior:
- Static poster image renders instantly as LCP element.
- Three.js chunk loads after first paint, canvas fades in over the poster.
- Under `prefers-reduced-motion`, or on low-power/mobile heuristics, the poster stays and never loads the 3D bundle.
- Net effect: same signature moment, dramatically faster first paint, no penalty for mobile visitors.

**What to add** (the real argument for rebuilding):
- **Writing/Notes section**: short posts compiled from markdown. Currently there is nowhere to put a thought that is not a paper.
- **Book cross-promotion**: The Qubit Dialogues deserves more than a nav link once there are four editions.
- **Per-page OG cards**: generated at build from a template, not hand-made once.
- **Sitemap, robots, RSS** for the writing section.

## QA setup

**Automated (CI, blocking):**
- Full shared harness from `00-overview.md`.
- **Parity gate**: scripted comparison against the current live site before cutover. Every heading, every link target, every meta tag, every résumé PDF path present in the new build. Missing item fails the build.
- Performance budgets are stricter here than anywhere else: this page is a first impression. LCP under 1.5s on simulated 4G, total JS under 150KB before the deferred 3D chunk.
- Visual regression on hero, both themes, three viewports.

**Human (named owner: Tushar):**
- Thirty-second scroll in both themes on a real phone. Automated tests do not detect "feels wrong".
- Read every line of copy once with fresh eyes before cutover.

**Cutover protocol:**
1. Deploy to a preview URL, not the apex domain.
2. Run parity gate against production.
3. Human pass on preview.
4. Cut over, then immediately verify with curl: 200s on `/`, `/cv.html`, `/qubit-dialogues.html`, both résumé PDFs, both OG images.
5. Keep the previous commit tagged so rollback is one command.

## Points that decide whether this is merely good

1. **Speed is a design feature.** The current site is beautiful and heavy. If the rebuild is not measurably faster, it failed regardless of code quality.
2. **The knot is the brand.** Do not replace it, do not add competing animations. Make it load smarter and behave better on touch.
3. **Content architecture is the actual deliverable.** Adding a paper, a talk, or a post must be one object in one file. If it requires touching markup, the rebuild bought nothing.
4. **Add a reason to return.** A portfolio nobody revisits is a business card. The writing section is what makes the site a place rather than a page.
5. **Do not lose the receipts.** GA4, canonical URLs, OG cards, the résumé paths people already have links to, the Wayback snapshots. Continuity is invisible when it works and catastrophic when it does not.

## Open questions

- Writing section: start with real posts, or ship the section empty and fill it later? (Empty sections read as abandonment. Recommend: three posts written before it goes live, or defer the section.)
- Keep `cv.html` as a separate page, or fold into the site as a route?
