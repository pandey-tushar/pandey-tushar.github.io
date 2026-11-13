/* An Unpolarized Life. Same reader as apps/book, different data.

   The edition validates at import time, the same contract @qubit/content gives
   en.json, from its own entry point so that neither edition carries the
   other's JSON. */
import { unpolarized, frontUnpolarized } from '@qubit/content/unpolarized';
import { mountReader } from '@qubit/reader';
import './life.css';

/* This book has no scene blocks and no science asides, so no scene mounter is
   passed. The reader core never imports the registry, so three.js and the
   scene chunks are not in this app's module graph at all. It calls its parts
   chapters, and says so through `labels` in front.unpolarized.json. */
/* index.html ships the whole text as plain markup, in its <main>, for anything
   that runs no script (see ../static.ts). The reader builds the real page, so
   that copy goes. */
document.getElementById('main')?.remove();
mountReader({ cantos: unpolarized, front: frontUnpolarized });

/* The site header carries the theme switch (/lib/site.js, key tp-theme), so
   the reader's own chip goes. The reader's main takes the skip link's target,
   and its closing colophon stops being a second contentinfo landmark. */
document.getElementById('theme-toggle')?.remove();
const main = document.getElementById('content');
if (main) main.id = 'main';
document.querySelector('#book > footer')?.setAttribute('role', 'none');

/* the edition links and the site footer close the page, after the book */
const end = document.getElementById('end');
if (end) document.body.append(end);
