import raw from './unpolarized.json';
import frontRaw from './front.unpolarized.json';
import { validateBook, validateFront } from './schema.js';

/** An Unpolarized Life, validated at import time so bad data fails loudly.
    Its own entry point for the reason given in hi.ts. */
export const unpolarized = validateBook(raw, 'unpolarized.json');
export const frontUnpolarized = validateFront(frontRaw, 'front.unpolarized.json');
