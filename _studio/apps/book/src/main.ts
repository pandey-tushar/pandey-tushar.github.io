import { en, frontEn } from '@qubit/content';
import { mountReader } from '@qubit/reader';
/* the bundled scene registry: opting in here is what puts three.js in this
   app's graph and keeps it out of the text-only editions */
import { scenes } from '@qubit/reader/scenes';
/* likewise KaTeX: this edition has equations, so it pays for the fonts */
import '@qubit/reader/math';

mountReader({ cantos: en, front: frontEn, scenes });
