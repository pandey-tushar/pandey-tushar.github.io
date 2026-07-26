# Spec 02: The Qubit Dialogues, Illustrated Edition

## Goal

A second edition where the art carries the book. Same text, same 22 cantos, but each canto is built around custom generative imagery and scroll-driven animation, so that reading it feels closer to turning the pages of an illuminated manuscript than scrolling a webpage. A reader who does not care about quantum computing should still want to look at it.

## Non-goals

- Not a simulator. Nobody is dragging sliders to learn physics here. That was the other option and it was not chosen.
- Not a replacement. The text edition stays at its URL, stays printable, stays canonical for search.
- Not decoration. Art that could be swapped for stock imagery without loss has failed.

## Art direction

**Stance**: astronomical plate meets illuminated manuscript. Deep ground, precise line, gold leaf. Everything drawn by algorithm and tuned by hand, never sourced.

The book already carries a palette (void, cyan, violet, gold, rose) and a mythic register. The illustrated edition holds that identity and pushes the craft far past what a single HTML file allowed.

**The motif system is the core engineering deliverable.** Twenty-two bespoke artworks is unsustainable and would look incoherent. Instead, build `packages/motifs`: a small library of parameterized generative forms drawn from images the text already uses repeatedly.

| Motif | Source in text | Parameters |
|---|---|---|
| Coin | canto 1, spinning on edge | spin rate, tilt, face bias, settle |
| Sphere | canto 1, the Bloch sphere | orientation, trace, collapse |
| Lattice | entanglement, cover art | node count, coupling, break points |
| Wall | canto 9, the wall of wires | density, gap, breach |
| Thread | connection, correlation | tension, count, severance |
| Fire | canto 21, the fire in the house | intensity, containment |
| Lock | canto 16, the unsealing | complexity, open state |
| Mirror | copying, no-cloning | fidelity, distortion |

Every canto composes one or two motifs at specific parameters. Coherence comes free because the vocabulary is shared. A new canto is a new composition, not a new artist.

**Signature image rule**: every canto must produce one still frame that works standing alone as a poster. This is the quality forcing function. If the frame only reads as a background, the canto's art is not done. Those stills become the per-canto OG cards and, optionally, a print set.

**Seeded and reproducible**: all generative art takes an explicit seed. The same canto renders identically on every load and every machine. No `Math.random()` without a seeded PRNG. This makes art reviewable, diffable, and printable.

## Scroll choreography

Each canto is a sequence of three to five beats. Text arrives in measured units; the artwork evolves continuously across them rather than restarting per section. The spinning coin slows, tilts, and settles across an entire canto rather than looping.

Rules:
- Never scroll-jack. The reader's scroll always maps to the reader's motion.
- Animation follows scroll position, not elapsed time, so stopping mid-canto leaves a composed frame rather than a random one.
- One idea in motion at a time. Two competing animations halve the effect of both.

## Performance architecture

Twenty-two live canvases is not a thing that can exist. Required:

- **Virtualized scenes**: at most three mounted at once (previous, current, next). Dispose geometries, materials, and contexts on unmount, verified by a heap check in tests.
- **Poster-first**: every canto renders its seeded still frame instantly; the live layer upgrades in place once mounted.
- **Budget**: 60fps on a mid-range laptop, no worse than 30fps on a mid-range phone, measured not assumed. Long tasks over 50ms fail the gate.
- **Reduced motion**: complete static edition, every signature frame, zero animation, fully readable. This is a first-class path, not a fallback.

## QA setup

**Automated (blocking):**
- Shared harness from `00-overview.md`.
- **Frame budget**: scripted scroll through all 22 cantos while sampling frame timing. Regressions fail.
- **Memory ceiling**: heap after a full scroll must return near baseline. A leak across 22 scenes is the predictable failure mode of this design.
- **Seed determinism**: render each canto's signature frame twice in fresh contexts, compare pixel hashes. Any drift means an unseeded random is loose.
- **Static path completeness**: with reduced-motion forced, assert every canto has visible artwork and full text.
- **Mobile gate**: the entire scroll suite runs at 375px. This edition dies on phones if it is not tested there constantly.

**Human (owner: Tushar):**
- **Poster test**, per canto: view the signature frame alone, full screen. Would you hang it? A no means that canto is unfinished.
- **Read test**: read three cantos end to end without watching for bugs. If the art fought the text, the art is too loud.

## Points that decide whether this is merely good

1. **The system beats the set.** A shared motif vocabulary with per-canto composition is what makes 22 artworks feasible and coherent. Bespoke-per-chapter will produce an inconsistent, half-finished book.
2. **Art must mean something specific.** The coin settles because that canto is about a question forcing an answer. Reversible mappings between text and image are what separate this from a screensaver.
3. **Typography still carries the book.** In art-led work, text quality is where the amateur is exposed. Measure line length, set real hierarchy, respect the reading.
4. **Performance is content.** A stuttering illuminated manuscript is worse than a clean text page. Budget enforcement is not optional polish.
5. **Ship a still edition too.** Signature frames become OG cards, a poster set, and the reduced-motion path. Three deliverables from one discipline.

## Open questions

- Ambient sound per canto, off by default? Powerful, and a common regret.
- Should the illustrated edition include the science asides and predictions, or is it the pure literary cut with those left to the text edition?
- Print: is there a physical art book here later? If yes, generate at print resolution from the start; retrofitting DPI is painful.
