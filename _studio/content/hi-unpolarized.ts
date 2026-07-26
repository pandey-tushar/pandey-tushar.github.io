import raw from './hi-unpolarized.json';
import frontRaw from './front.hi-unpolarized.json';
import { validateBook, validateFront } from './schema.js';

/** आधा उजाला, the Hindi edition of An Unpolarized Life, validated at import
    time so bad data fails loudly. Its own entry point for the reason given in
    hi.ts: a barrel importing every edition would put all of them in every
    app's bundle. */
export const hiUnpolarized = validateBook(raw, 'hi-unpolarized.json');
export const frontHiUnpolarized = validateFront(frontRaw, 'front.hi-unpolarized.json');
