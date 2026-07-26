import raw from './hi.json';
import frontRaw from './front.hi.json';
import { validateBook, validateFront } from './schema.js';

/** The Hindi edition, validated at import time so bad data fails loudly.
    Each edition is its own entry point rather than a member of index.ts: a
    barrel that imported all of them would put every edition's JSON in every
    app's bundle. */
export const hi = validateBook(raw, 'hi.json');
export const frontHi = validateFront(frontRaw, 'front.hi.json');
