# Spec 03: आधा उजाला, the Hindi edition

## What changed, and why this spec was rewritten

This spec originally described a Hindi edition of **The Qubit Dialogues**. Four cantos were written that way and the owner, a native reader, rejected them: *"it does not sound right. It's too literal translation which loses the meaning."* That work has been deleted.

The Hindi edition is now a translation of **An Unpolarized Life** instead. That book suits Hindi far better: it is complete at twelve chapters, it is about living rather than about machines, and it carries almost no technical vocabulary, so the translation is a literary problem rather than a terminology one.

Two lessons from the rejected attempt are now rules:

1. **Literalness is the failure mode.** Sentence-by-sentence fidelity produces text that reads translated. Work from what a passage means and does, write it as if composing in Hindi, and consult the English afterwards only to confirm nothing was lost.
2. **The register decisions were sound.** जिज्ञासु and द्रष्टा, both speakers on तुम, the reader on आप, Latin numerals for figures. Those carried over unchanged and are documented in `HINDI-STYLE.md`.

## Goal

A Hindi edition of An Unpolarized Life that reads as though it was composed in Hindi. One night on a porch, two people talking, a question the Seeker must answer by Friday that the book never names and never answers. If a native reader can tell it was translated, it has failed.

## Non-goals

- Not a Hindi edition of The Qubit Dialogues. That attempt was made and rejected.
- Not a technical translation. Six physics words appear in the whole edition, all school vocabulary. There is no glossary and none is wanted.
- Not Sanskritized display prose. The book is people talking.

## The title

**आधा उजाला** (*Half the Light*), subtitled **प्रश्नों की एक पुस्तक**.

English gets two meanings from *unpolarized*: the optical thesis, and the ordinary sense of not being forced into one of two camps. Hindi cannot carry both in one word, and the obvious routes fail:

- **अध्रुवित जीवन** is the correct textbook term but puts a physics word on a cover, and drags ध्रुवीकरण behind it, which in Hindi means communal and political polarisation. It would promise a completely different book.
- **निष्पक्ष** and **तटस्थ** mean *neutral*, a pose chapter one spends a paragraph demolishing. A title the book argues against is not available.
- **अनछना** has the right shape, but अनछना आटा is coarse flour, so it reads as *unrefined*.

आधा उजाला is optically exact rather than approximate, since a polarizer passes about half of unpolarised light and the text says so twice, and it earns itself in chapter two: *आधा उजाला जा चुका।*

**Its cost, recorded so it can be overruled:** it names the polarized life rather than its absence, so the *un-* is gone. Fallbacks in order: बिना काँच के, जो काँच ने लौटा दिया, अध्रुवित जीवन.

## Language decisions specific to this book

Full detail in `HINDI-STYLE.md` sections 13 to 19. In brief:

- **काँच carries the whole metaphor.** English alternates *the glass* and *a filter*; Hindi has no neutral everyday word for an optical filter (छन्नी is a tea strainer, फ़िल्टर is a water purifier), so both become काँच. This produces a sharper pair than the English: *काँच थमाया गया है और कहा गया है कि इसे खिड़की मानो.*
- **रुख़** for orientation, **कोण** for angle, **साबुत** reserved for the book's central illusion of wholeness.
- **पहर, not पर्व.** Twelve chapters across one night, tracking the watches of the night. Epic machinery would be pompous here.
- Images are substituted where a native one lands harder: रोटी और अचार, समोसे के दाम में, बही, भूत बुलाने की बैठक. All recorded rather than done silently.

## QA setup

**Automated (blocking):** schema validation, structural parity against `content/unpolarized.json` (chapter count, block counts and types in order, every number preserved), NFC normalisation, no mixed-script tokens, no stray Latin in prose, no dashes, build and typecheck clean, zero console errors.

**Rendering:** every named conjunct (क्ष, त्र, ज्ञ, द्ध, श्र) inspected at magnification in a real browser at 1440 and 375, plus matra clipping and horizontal overflow.

**Human, blocking (owner: Tushar):** read chapter by chapter. The test is whether the dialogue could be spoken aloud by a person on that porch. Every line should survive being read out.

## Status

All twelve chapters translated. The translator's own honest grading:

- **Would defend to a native reader:** 1, 2, 3, 7, 10, 12
- **Merely correct:** 4, 6, 9, 11, where long argumentative paragraphs stayed essayistic
- **Would redo:** 5 and 8, which lean on English abstractions (*legible*, *obliged*, *private*, *description*) that Hindi has no clean single word for

Unpublished. `robots: noindex,nofollow`, no analytics, not linked from the books hub, and the deploy script fails loudly if it ever appears at the site root.

## Open questions

- Ratify or overrule the title.
- Whether to redo chapters 5 and 8 before review, or review as is.
- Whether this edition eventually publishes alongside the English, or stays private.
