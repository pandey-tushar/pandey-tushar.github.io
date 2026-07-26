# Spec 03: हिंदी संस्करण, The Hindi Edition

## Goal

A Hindi edition that reads as though it was composed in Hindi. The book already imitates the samvad and sutra tradition; in Hindi that is not an imitation, it is the native form. Done well, the Hindi edition should feel more at home in its language than the English does in its.

## Non-goals

- Not a translation artifact. If a reader can feel the English underneath, it failed.
- Not Sanskritized display prose. Reaching for the most classical word available produces text that impresses and does not communicate.
- Not a separate book. Same 22 cantos, same arc, same argument.

## Language decisions to make before writing

These are load-bearing and expensive to change once 22 cantos exist.

**1. Register.** Recommend modern literary Hindi (सरल साहित्यिक हिंदी) that reaches for tatsam vocabulary at moments of weight and stays conversational in dialogue. The Seeker's doubt should sound like a person talking. The Oracle can carry the older register.

**2. Character names.** The English Seeker/Oracle needs a Hindi pair that carries the same relationship. Candidates:
- जिज्ञासु (Jigyasu, one who seeks to know) and द्रष्टा (Drashta, one who sees)
- साधक (Sadhak) and सिद्ध (Siddha)
- शिष्य and आचार्य, closer to guru-shishya but implies a formal hierarchy the book deliberately avoids

Recommend जिज्ञासु and द्रष्टा: it preserves the equality of the original, where the Oracle is ahead in time, not above in rank.

**3. Technical vocabulary policy.** Hindi scientific vocabulary is inconsistent in practice; educated Indian readers routinely use English technical terms in Devanagari script. Recommended rule, applied without exception:
- **Transliterate** established technical terms: क्यूबिट, डिकोहेरेंस, एंटैंगलमेंट.
- **Translate** conceptual and metaphorical language: superposition as अध्यारोपण where the physics is meant, but the metaphor rendered in natural Hindi imagery.
- **Maintain a glossary** (`content/glossary-hi.json`) mapping every technical term to its single approved Hindi rendering. Enforced by script.

**4. Epigraphs.** The English invents sutra-style epigraphs ("Sutra of the Unspent Coin"). In Hindi these can be genuinely beautiful rather than an English writer's gesture at Sanskrit. Highest-payoff writing in the whole edition. Spend real effort here.

**5. Numerals.** Latin numerals for years, percentages, and figures; Devanagari acceptable for canto numbers. Mixing inside a sentence looks careless.

## Typography

Devanagari is not a font swap. Required:
- Noto Serif Devanagari or Mukta as the body face, self-hosted, subset, with the Latin face retained for technical terms so mixed-script runs do not jump.
- Line height increases: matras above and below need roughly 1.8 to 1.9 where Latin took 1.65.
- Test conjunct rendering (क्ष, त्र, ज्ञ, द्ध) across Windows, macOS, Android, iOS. Broken conjuncts are the classic Devanagari web failure.
- Verify the reader's justification and hyphenation settings do not shred Devanagari. Turn hyphenation off.

## QA setup

**Automated (blocking):**
- Shared harness from `00-overview.md`.
- **Glossary consistency**: every technical term appears only in its approved form. One script, run every build, catches the single most common failure in translated technical work.
- **Script hygiene**: no stray Latin in prose except approved technical terms; no mixed-script words; no Unicode normalization mismatches (NFC enforced).
- **Structural parity**: 22 cantos, same block counts, no dropped dialogue turns, every number and citation preserved exactly against `en.json`.
- **Rendering check**: screenshot every canto at three viewports on at least two operating systems, checked for conjunct and matra breakage.

**Human, blocking (owner: Tushar):**
- **Canto-by-canto read** against a simple rubric: does it sound composed or translated; is the Seeker's voice distinct from the Oracle's; would you read this aloud to someone.
- **Back-translation spot check**: for a sample of passages, translate the Hindi back to English independently and compare meaning against the original. Catches semantic drift that fluency hides.
- Recommended: one additional native reader who has not seen the English. If they can tell it was translated, iterate.

## Points that decide whether this is merely good

1. **Write forward, do not translate.** Work canto by canto from the *idea*, with the English as reference rather than source. Sentence-by-sentence conversion is what produces text that reads translated.
2. **The dialogue must sound spoken.** Read every Seeker line aloud. Hindi tolerates formality in narration and punishes it in speech.
3. **Let the metaphors move.** A coin spinning on its edge may not be the strongest image in Hindi. Where a native image lands harder, use it, and note the substitution.
4. **The epigraphs are the signature.** They are where the Hindi edition can be plainly better than the English. Treat them as poems, not headers.
5. **One glossary, enforced by machine.** Terminology drift across 25,000 words is invisible to a human reader and obvious to a script.

## Open questions

- Devanagari title: "क्वांटम संवाद" is direct and strong. Alternatives worth weighing before committing, since it becomes the brand for this edition.
- Does the Hindi edition get its own audio (ElevenLabs supports Hindi voices), or is that a later phase?
- Should the science asides be Hindi, English, or bilingual? Technical readers may prefer English for those specific blocks.
