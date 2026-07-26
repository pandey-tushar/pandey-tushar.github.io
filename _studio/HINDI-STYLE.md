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

---

# आधा उजाला: the Hindi edition of An Unpolarized Life

Everything above was settled for **क्वांटम संवाद**, the Hindi edition of The
Qubit Dialogues. This section covers the second Hindi edition,
`apps/hindi-unpolarized`, and records only what differs. Where it is silent, the
rules above apply.

The register decisions carry over intact and are not re-argued: modern literary
Hindi reaching for tatsam at moments of weight, जिज्ञासु and द्रष्टा, both
speakers saying तुम while the reader is addressed as आप, Latin digits for
figures and Devanagari digits for chapter numbers only.

**What does not carry over is the method.** The first edition was rejected by a
native reader with the words *too literal a translation, it loses the meaning*.
This edition was composed forward from what each passage means and does, and the
English was consulted afterwards to confirm nothing had gone missing, never to
shape a sentence. Any line here that can be back-mapped clause for clause onto
the English is a defect, not a success.

## 13. Title

**आधा उजाला**, with the sub प्रश्नों की एक पुस्तक.

The English title does two things at once. *Unpolarized* carries the optical
thesis, and it also carries the ordinary sense of not being forced into one of
two camps, which is exactly chapter one: yes or no, by Friday. A Hindi title
should carry both. Weighed:

- **अध्रुवित जीवन** is the literal term, the one NCERT optics uses
  (अध्रुवित प्रकाश). It is a physics word on a cover, which is the mistake
  क्यूबिट संवाद was rejected for. It also drags ध्रुवीकरण behind it, which in
  Hindi means communal and political polarisation and very little else, so the
  cover would promise a different book.
- The ordinary-sense route is a trap in Hindi in a way it is not in English.
  The ready-made words for an unpolarised person are निष्पक्ष and तटस्थ, both
  meaning *neutral*, and chapter one spends a paragraph destroying exactly that
  pose: *यह खेत में खड़ा वह आदमी है जो अपने खुले दिमाग़ को निहार रहा है*. A title
  the book argues against is not available.
- **अनछना जीवन** (unsifted) has the right morphology, अन- on the participle of
  the filtering verb, and छानना is the most domestic verb in the language. But
  अनछना आटा is coarse flour, so the adjective reads as *unrefined*, which
  inverts the title.
- **बिना काँच के** (Without the Glass) keeps the negation and the object, and is
  closest to spec 04's *Without a Polarizer*. काँच alone is ambiguous before
  chapter one has been read.

**आधा उजाला** is the committed choice. It is optically exact rather than
approximate: a polarizer passes about half of unpolarised light, and the book
states that twice in its own words. It asks no physics of the reader, and it has
no political echo and no devotional echo. It is also seeded in the text, so it
earns itself by the second chapter: *आधा उजाला जा चुका।*

The cost, stated plainly so it can be overruled: it names the polarized life
rather than the unpolarized one, so the *un-* of the English is gone. That is
defensible for this book, whose closing position is that nobody gets a better
filter, only the knowledge that they are holding one. But it is the owner's call.
Fallbacks in order: बिना काँच के, जो काँच ने लौटा दिया, अध्रुवित जीवन.

**Ratify before anything is published**, as with the other edition.

## 14. काँच carries the whole metaphor

The English alternates two words: *the glass* for the object on the table, and
*a filter* for the category. Hindi has no neutral everyday noun for an optical
filter. छन्नी is a tea strainer and makes the sentence comic; फ़िल्टर is a water
purifier before it is anything else, and either would be the one imported term
in a book whose premise is that it needs none.

So the Hindi collapses both words into **काँच** and lets the object carry the
metaphor throughout. *That is a filter* becomes **वह भी यही काँच है**, and *you
have been handed a filter and asked to agree that it is a window* becomes
**तुम्हारे हाथ में काँच थमाया गया है और कहा गया है कि इसे खिड़की मानो**, where
काँच against खिड़की is a sharper native pair than glass against window.

Two supporting terms, both chosen to stay out of the physics register:

- **रुख़** for *orientation*. The everyday word for which way a thing faces
  (हवा का रुख़). *This glass admits one orientation* becomes
  **यह काँच एक ही रुख़ भीतर आने देता है**, which is speech, not optics.
- **कोण** for *angle*, the school word, correct in both the geometric and the
  ordinary sense, so the epigraphs about angle stay exact.

**साबुत** is reserved the way कला is reserved in the other edition. It carries
the book's central illusion, *it looks whole*, and appears only in that sense:
साबुत दिखता है, साबुत लगेगा, वह साबुत लगी.

## 15. Structure: पहर, not पर्व

The other edition uses पर्व containing सर्ग, correct for a mahakavya-shaped book
of twenty-two cantos. This one is twelve chapters over a single night, and that
machinery would be pompous on it. Its parts are **अध्याय**, plainly, and its
three movements are **पहर**, the watch of the night, which HINDI-STYLE already
carries as the native unit for these hours.

| English | Hindi |
|---|---|
| MOVEMENT I / The Turning | पहर एक / मोड़ |
| MOVEMENT II / The Cost of Looking | पहर दो / देखने की क़ीमत |
| MOVEMENT III / What Comes Through | पहर तीन / जो पार आता है |

पहर does work the English movement numbers cannot. The chapters track real
hours, from a sun still well up to first grey light, and the three watches put
the reader inside them. मोड़ carries both the turning of the glass and the
ordinary ज़िंदगी का मोड़.

**FROM THE LONG WATCH**, the epigraph attribution on all twelve chapters,
becomes **लंबे पहर से**, tying the invented source to the same unit.

## 16. Substituted images

Spec 04, and the owner's instruction during this pass: where a native image
lands harder, use it and record it.

| English | Hindi | Why |
|---|---|---|
| bread and a heel of cheese | रोटी और अचार | The scene needs food set down without ceremony. Cheese is not that in Hindi. रोटी और अचार is, and it suits a house above a valley. Chapter five's later *cut more bread* becomes और रोटी तोड़ी. |
| for the price of a sandwich | समोसे के दाम में | The same move, in the afterword. The point is only that the glass is trivially cheap. |
| No spreadsheet shifts | किसी बही में कुछ नहीं बदलता | बही is the native account book and older than the thing it stands for, which suits an Oracle who has watched a long time. |
| A fact is lighter. A fact does not grow. | पक्की बात हल्की होती है। वह बढ़ती नहीं। | तथ्य is a written word. पक्की बात is what a person says at two in the morning, and it keeps the flatness of the English. |
| A correlation is not contact. | एक जैसा निकल आना और बात हो जाना, ये दो चीज़ें हैं। | सहसंबंध would import exactly the jargon this book refuses. The Hindi states the distinction as two ordinary things instead of naming a technical one. |
| a consolation prize | ढाढ़स | The Hindi noun for comfort offered in place of what was wanted. No prize needed. |
| This is not a séance. | यह भूत बुलाने की बैठक नहीं है। | प्रेतसभा is archaic and would sound composed. This is what a person would actually say. |
| Watch who is willing to be embarrassed. | देखते रहो कि भद्द पिटवाने को कौन तैयार है। | भद्द पिटना is public embarrassment with a bite that शर्मिंदगी does not have. |
| one man with one bucket running between four fires | एक बाल्टी लेकर चार आग के बीच दौड़ता एक आदमी, और नाम दे रखा है दमकल | Verb-final image, then a flat tail. That is how the joke lands in Hindi. |
| the residue | बचा-खुचा | Used at both places the English uses *residue*, so the chapter four and chapter eight echo survives. |
| made out of some material that resists duplication | किसी और ही मिट्टी के बने होते | माल reads as merchandise. मिट्टी is what a person is made of in Hindi, and the chapter's flat reply, *तुम आम मिट्टी के बने हो*, lands where *the usual material* does not. |
| wide question / narrow question | चौड़ा प्रश्न / सँकरा प्रश्न | Kept literal on purpose. The filter admits or turns away, and चौड़ा against सँकरा keeps the optical sense running under the human one. |

Three terms are carried over from the other edition deliberately, so that the
two Hindi books share vocabulary where they share an idea: **समाई** for capacity
(chapter three), **ओट** for cover or shelter (chapter five), **कौशल** for skill
(chapter seven).

## 17. The framing rule in Hindi

Spec 04's rule governs every page: the book never claims that quantum mechanics
runs a human life. Three passages state the limit out loud, and each was written
to be blunter in Hindi than in English, because a hedge reads as evasion in
Hindi speech.

- Chapter four: **पूरी मशीन बस यही फ़र्क़ है।** मशीन rather than तंत्र, so the
  sentence cannot be read as naming a physical mechanism.
- Chapter six refuses Landauer without naming him, and keeps भौतिक तंत्र at
  arm's length: *उसे खींचकर तुम्हारे पिता की आवाज़ पर तान दूँ, तो मैं जितना हूँ
  उससे ज़्यादा समझदार सुनाई दूँगा*.
- Chapter nine, the hardest, keeps every clause of the English refusal including
  *not one bit of information, not ever*, as **ज़रा-सी ख़बर भी नहीं, कभी नहीं**.
  सूचना was rejected in favour of ख़बर: सूचना is the information-theoretic term
  and would smuggle the technical claim back in through the vocabulary.

Six physics words appear in the whole edition, all of them school vocabulary a
general reader has met: भौतिकी, कण, परमाणु, ऊर्जा, प्रकाशिकी, and प्रमेय once in
chapter eight. There is no glossary for this edition and
`content/glossary-hi.json` is not read by its checker, because importing that
book's vocabulary is precisely the failure mode.

## 18. What is checked by machine

    node apps/hindi-unpolarized/scripts/parity-check.mjs
    npm run validate

One script rather than two, because there is no glossary to enforce. It does the
structural parity of `content/hi-unpolarized.json` against
`content/unpolarized.json` (chapter count, block count and types in order,
speaker and paragraph count on every dialogue turn, movement and epigraph
presence, and every number as a per-block multiset) and the script hygiene that
the other edition's `glossary-check` does (NFC, no mixed-script token, no Latin
word in prose, no em-dash or en-dash, no Devanagari digit outside the `digits`
table).

`content/validate.ts` had to be widened to accept a hyphen in an edition
filename, and `glossary-hi.json` had to be added to its skip list as a
consequence, since it matches the edition pattern and is not an edition.

## 19. What no machine can check

The same list as section 12, the same owner. For this edition the passages to
read first are named in the report accompanying this pass, where the chapters
the writer would defend are listed separately from the ones the writer would
not. That separation is the useful part of the report.
