# HINDI-STYLE

The language decisions for the Hindi edition, settled before mass writing.

Cantos 1 to 4 and the front matter are written. They are the reference standard
for the remaining eighteen. Everything below is enforced where a machine can
enforce it (`content/glossary-hi.json`, `apps/hindi/scripts/`) and written down
where it cannot.

The governing instruction from spec 03: **if a reader can feel the English
underneath, it failed.** Every rule here exists to serve that, and any rule can
be overturned by a native reader who says a passage sounds translated.

---

## 1. Title

**क्वांटम संवाद.**

Spec 03 leaves this open. Weighed:

- **क्यूबिट संवाद** is the literal title and is consistent with the glossary,
  which transliterates *qubit* as क्यूबिट. It reads as jargon on a cover and the
  ट‑स junction is awkward aloud.
- **संभावनाओं का संवाद** (dialogue of possibilities) borrows the subtitle and
  loses the machine entirely.
- **क्वांटम संवाद** is the phrase an Indian reader already has. संवाद is the
  native name for exactly this form, so the title states the genre as well as
  the subject. The book's unit is the qubit; its subject is the quantum.

Committed to क्वांटम संवाद. **Ratify before anything is published**, because it
becomes the brand for this edition.

## 2. Register

Modern literary Hindi (सरल साहित्यिक हिंदी). Tatsam vocabulary at moments of
weight (अनित्यता, क्षणभंगुर, प्रमेय, समाई), conversational everywhere else.

The test applied to every line of dialogue: read it aloud. Hindi tolerates
formality in narration and punishes it in speech. So the Seeker says
*"यह लैब कोट पहने हुआ अंधविश्वास है"* and not *"यह प्रयोगशाला-वस्त्रधारी
अंधविश्वास है"*. Narration is allowed to be more composed than dialogue, and is.

Sentences end with the danda (।). Comma, semicolon and question mark are the
Latin marks, as in all modern Hindi printing.

**No em-dashes and no en-dashes, in any script.** Checked by script.

## 3. Character names

**जिज्ञासु** (the Seeker) and **द्रष्टा** (the Oracle), as spec 03 recommends.
Adopted without change.

The reason to keep them: both are agent nouns of capacity, not roles in a
hierarchy. जिज्ञासु is one who desires to know, and carries the Gita's use of it
as one of four kinds who approach, not as a pupil. द्रष्टा is one who sees, and
is pointedly not आचार्य or गुरु. The rejected pair शिष्य/आचार्य would have
installed exactly the rank the book refuses. साधक/सिद्ध implies attainment, and
the Oracle has not attained anything; it is simply further along in time.

## 4. Pronouns: both speakers say तुम

This is the single decision most likely to be argued with, so the reasoning is
here in full.

Hindi forces a choice the English does not. The obvious mapping, Seeker→आप and
Oracle→तुम, is what age and seniority would produce, and it is also precisely
the guru-shishya asymmetry spec 03 says the book deliberately avoids. Both
saying आप is equal but cold, and the spec warns that Hindi punishes formality in
speech.

**Both use तुम.** Two people talking closely, as equals. The Oracle's authority
then rests entirely on what it says rather than on how it is addressed, which is
the book's actual design. It also lets the Seeker be as combative in Hindi as he
is in English.

**The reader is addressed as आप.** So `reflect` blocks, the invocation and all
front matter use आप, and dialogue uses तुम. The two registers never meet.

Reversing this later means rewriting every line of dialogue. It is cheap now and
expensive after canto five.

## 5. Technical vocabulary

The full policy and every decision live in `content/glossary-hi.json`
(201 terms, covering all 22 cantos). The rule, applied without exception:

- **Transliterate** terms working Indian physicists say in English:
  क्यूबिट, डिकोहेरेंस, एंटैंगलमेंट, कोहेरेंस, सिंड्रोम, पैरिटी, फ़िडेलिटी,
  सरफ़ेस कोड, कैट क्यूबिट, एल्गोरिदम.
- **Translate** conceptual and metaphorical language, preferring words Hindi
  physics teaching already carries over invented compounds:
  चिरसम्मत (classical), व्यतिकरण (interference), प्रायिकता (probability),
  जालक (lattice), देहली (threshold), दुर्बल मापन (weak measurement),
  शिथिलन (relaxation), सममिति (symmetry), प्रक्षेपी (projective).
- **Latin, exactly as published** for author names, company and machine names,
  journal titles and symbols: `Nature 638`, `Quantinuum Helios`, `T1`, `T2`,
  `FeMo-cofactor`, `AWS Ocelot`.

Naming rule, since it recurs: **a famous name is written in Devanagari when it
appears in running prose (बेल, आइंस्टाइन, बोर, मिनेव, ब्रगिंस्की, राउसेनडोर्फ),
and in its published Latin form inside a `note` block or a parenthetical
citation.** `apps/hindi/scripts/parity-check.mjs` accepts either form and keeps
the list of Devanagari-ised names.

### Four glossary decisions worth defending

**कला for phase.** This is the riskiest call in the edition. कला is what Hindi
physics teaching uses (कलांतर = phase difference) and it carries the moon-phase
resonance of चंद्रकला, which makes *"कला रिसती है"* land as native imagery rather
than as a rendered term. The cost is that कला is also the everyday word for
*art*, and this book says "the art of" often. So **कला is reserved: in this
edition it only ever means phase**, and art or craft is carried by कौशल or
साधना. The glossary declares the reservation and the checker reports every
occurrence for a human to confirm. If a native reader finds the double meaning
intolerable, the fallback is फ़ेज़ and the change is one glossary line plus a
find and replace, which is why it is being decided now.

**शोर for noise, and the Shor collision.** शोर is the established word for noise
and there is no good alternative. Peter Shor transliterates to the same string.
The rule for cantos 10 and 16: शोर for the person only when bound directly to
what he made (शोर एल्गोरिदम), with a Latin gloss on first use in the canto.
Flagged now so the writer of canto 16 does not discover it there.

**अध्यारोपण for superposition.** The NCERT term, and spec 03's recommendation.
It carries a Vedantic shadow: अध्यारोप is *false* superimposition, the rope
mistaken for a snake, which is the exact position canto 1 spends its length
refuting. The handling is to keep the term to the science blocks and to titles,
and to let the dialogue carry the idea in plain language (*दो सत्य एक साथ*,
*न यह है न वह, और दोनों है*). No canto argues against its own vocabulary.

**बिलियन and ट्रिलियन, not अरब and खरब.** अरब is 10⁹ and खरब is 10¹¹, so a
dollar figure quoted in the Indian series silently changes magnitude depending
on which series a source used. Transliterating keeps every figure in canto 21
checkable against its citation.

## 6. Numerals

Latin digits for years, percentages, quantities and citations: `2030`, `99.99
प्रतिशत`, `Nature 638`, `T1`, `T2`.

Devanagari digits for canto numbers only: सर्ग १ / ४. Content never contains a
Devanagari digit; the numbering is produced by `apps/hindi/src/localize.ts`.
Checked by script.

## 7. Structure: पर्व and सर्ग

- **canto → सर्ग**, the section of a Sanskrit mahakavya.
- **movement → पर्व**, the structural division of an epic.

पर्व containing सर्ग is how Indian epics are organised, so the book's own
architecture stops being a borrowed musical metaphor and becomes native. The
three movements:

| English | Hindi |
|---|---|
| MOVEMENT I / The Field | पर्व एक / क्षेत्र |
| MOVEMENT II / The Battle of Limits | पर्व दो / सीमाओं का संग्राम |
| MOVEMENT III / The Vision | पर्व तीन / दर्शन |

क्षेत्र carries the Gita's क्षेत्र/क्षेत्रज्ञ. दर्शन means seeing, vision and
philosophy at once, which is all three senses the English movement title wants.

## 8. Substituted images

Spec 03: where a native image lands harder, use it and record the substitution.

| English | Hindi | Why |
|---|---|---|
| heads / tails | चित / पट | The living Hindi pair for a coin. Transliterating would have been the translated-sounding choice. |
| The Web of All Things | सबका तानाबाना | तानाबाना is warp and weft, the native weaving image. "Web" in Hindi is a spider's, which is wrong for a fabric of relations. |
| The Measured Life | नपा-तुला जीवन | The idiom for a restrained, careful life, built on नाप, *measure*. The English pun survives intact, which it usually does not. |
| the whole cathedral stands on it | पूरा मंदिर इसी एक ईंट पर खड़ा है | A cathedral is not a Hindi image. मंदिर is, and the single brick is stronger than "primitive". |
| catch a quantum jump in the act | क्वांटम छलाँग को रंगे हाथ पकड़ना | रंगे हाथ is exactly "in the act" and has no equivalent flatness. |
| SUTRA OF THE TWO THAT ARE ONE | द्वैत में अद्वैत का सूत्र | The Advaita/Dvaita frame states entanglement's paradox in a vocabulary Hindi already argues in. The clearest place the Hindi is better than the English. |
| SUTRA OF THE GENTLE WITNESS | सौम्य साक्षी का सूत्र | साक्षी is the Vedantic term for the observer who does not disturb, which is literally the canto's physics. |
| SUTRA OF THE GUARDED FLAME | हथेली की ओट का सूत्र | ओट is the shelter of a cupped hand around a diya in wind. Everyone has done it. |
| the next hour | अगला पहर | पहर, the watch of the night, is the native unit and puts the epigraph in the right hours. |
| impermanence | अनित्यता | Buddhist, precise, and already load-bearing in the language. |
| capacity (a mind that is wide, not confused) | समाई | From समाना, to be contained. Does the work of "capacity" without the engineering sound. |

## 9. Typography

`packages/reader/src/styles/devanagari.css`, entirely scoped to
`html[lang="hi"]` so it is inert anywhere else. Decisions and their reasons:

- **Leading 1.88** on body prose against the Latin 1.65, because matras sit
  above the shirorekha and below the baseline.
- **Tracking near zero.** `reader.css` runs its labels to .5em, correct for
  wide-set Latin caps and wrong for Devanagari: the shirorekha runs across a
  whole word, so tracking reads as broken rendering rather than as style.
- **Labels get about 15 percent more size.** At 11px a stacked conjunct like
  ष्टा in द्रष्टा collapses into a smudge.
- **Label stack puts Devanagari first**, unlike the body stack, because with a
  monospace face in front U+0020 resolves to the mono advance, more than twice
  the Devanagari space, and multi-word labels drift apart.
- **Body stack puts the Latin serif first**, so Latin technical terms, years and
  citations keep the book's Palatino colour and mixed-script runs do not jump.
- **`font-synthesis: none`**, because faux bold smears conjuncts and faux
  oblique is not a thing Devanagari has.
- **`<em>` becomes weight, not slant.** With synthesis off, an italic `<em>`
  would render identically to its neighbours and the emphasis would silently
  disappear. Hindi marks emphasis with weight.
- **Hyphenation off**, and word breaking left at `normal`, so nothing splits
  inside a cluster.
- **Gradient headings get extra line box.** `background-clip: text` paints into
  the glyph box, and matras overshoot a Latin-sized one.

**Not yet done: the font is not self-hosted.** Spec 03 asks for Noto Serif
Devanagari or Mukta, subset and served from the repo. The binaries are not in
the repo and fetching them was out of scope for this pass, so the stack falls
through to the reader's system Devanagari face. No `@font-face` is declared for
a file that does not exist, because a dangling `src` is a console error and the
build gate forbids those. `devanagari.css` carries the exact `@font-face` block
commented out; drop two subset woff2 files into
`packages/reader/src/styles/fonts/` and uncomment. Nothing else changes.

## 10. How the equations are carried

Every `science` block in `en.json` holds pre-rendered KaTeX. The Hindi prose is
authored around placeholders and the KaTeX chunks are lifted out of `en.json`
byte for byte, so no equation, number or symbol can drift during authoring.
`apps/hindi/scripts/parity-check.mjs` re-verifies this on every run: it extracts
the `eqi` and `eqblock` spans from both editions and compares them as bytes.
Use the same method for cantos 5 to 22.

## 11. What is checked by machine

    node apps/hindi/scripts/glossary-check.mjs   # glossary + script hygiene
    node apps/hindi/scripts/parity-check.mjs     # structure, equations, numbers, citations
    npm run validate                             # schema, all editions

`glossary-check` fails on a rejected rendering, a non-NFC string, a token mixing
Devanagari and Latin, an undeclared Latin word in prose, an em-dash or en-dash,
and a Devanagari digit in content. `parity-check` fails on a block count or type
mismatch, a changed speaker or paragraph count, a changed scene kind, prediction
class or confidence, a KaTeX chunk that is not byte-identical, a number that
differs, or a citation name that has gone missing.

Matching by whole token, never by substring: डिकपलिंग must not read as कपलिंग,
फ़रवरी must not read as रव, and the postposition की must not read as the noun
*key*. Words that are genuinely ambiguous (निष्ठा, सिद्ध, भाग, की) are declared
as collisions in the glossary rather than banned.

## 12. What no machine can check

Spec 03 names these and they still stand, owner Tushar:

- canto-by-canto read against the rubric: composed or translated, is the
  Seeker's voice distinct from the Oracle's, would you read it aloud
- back-translation spot check on a sample of passages
- one native reader who has not seen the English

Places to look first are listed in the report accompanying this pass.
