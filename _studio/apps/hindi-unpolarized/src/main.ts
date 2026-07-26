/* आधा उजाला. The Hindi edition of An Unpolarized Life.

   Same reader as apps/book and apps/unpolarized, same Devanagari sheet as
   apps/hindi. The edition validates at import time from its own entry point,
   so neither Hindi edition carries the other's JSON. */
import { hiUnpolarized, frontHiUnpolarized } from '@qubit/content/hi-unpolarized';
import { mountReader } from '@qubit/reader';
/* after the reader's own sheet, so the Devanagari overrides win. It is scoped
   to html[lang="hi"], which index.html declares. */
import '@qubit/reader/devanagari.css';

/* No scene blocks, no science asides and no equations in this book, so no
   scene mounter and no KaTeX import: three.js and the maths chunk stay out of
   this app's module graph entirely. Every string the reader would otherwise
   print in English comes from `labels` in front.hi-unpolarized.json. */
mountReader({ cantos: hiUnpolarized, front: frontHiUnpolarized });
