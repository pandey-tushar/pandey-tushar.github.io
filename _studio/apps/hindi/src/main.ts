import { hi, frontHi } from '@qubit/content/hi';
import { mountReader } from '@qubit/reader';
import { scenes } from '@qubit/reader/scenes';
/* this edition has equations, so it pays for the KaTeX fonts */
import '@qubit/reader/math';
/* after the reader's own sheet, so the Devanagari overrides win */
import '@qubit/reader/devanagari.css';

/* Every string the reader used to print in English now comes from
   content/front.hi.json under `labels`, and the scene readouts come from the
   `strings` field on each scene block. The DOM rewriting this app used to do
   after mount is gone. */
mountReader({ cantos: hi, front: frontHi, scenes });
