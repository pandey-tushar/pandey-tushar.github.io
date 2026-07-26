import raw from './en.json';
import frontRaw from './front.en.json';
import { validateBook, validateFront } from './schema.js';

export * from './schema.js';

/** The English edition, validated at import time so bad data fails loudly.
    The other editions are separate entry points, `@qubit/content/hi` and
    `@qubit/content/unpolarized`, so that importing one does not drag the
    other two hundred kilobytes of JSON into the bundle. */
export const en = validateBook(raw, 'en.json');
export const frontEn = validateFront(frontRaw, 'front.en.json');
