/* An Unpolarized Life. Same reader as apps/book, different data.

   The edition validates at import time, the same contract @qubit/content gives
   en.json, from its own entry point so that neither edition carries the
   other's JSON. */
import { unpolarized, frontUnpolarized } from '@qubit/content/unpolarized';
import { mountReader } from '@qubit/reader';

/* This book has no scene blocks and no science asides, so no scene mounter is
   passed. The reader core never imports the registry, so three.js and the
   scene chunks are not in this app's module graph at all. It calls its parts
   chapters, and says so through `labels` in front.unpolarized.json. */
mountReader({ cantos: unpolarized, front: frontUnpolarized });
