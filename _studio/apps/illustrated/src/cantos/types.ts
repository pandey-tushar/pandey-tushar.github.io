import type { Composition } from '@qubit/motifs';

export interface CantoArt {
  composition: Composition;
  /** Index into the canto's literary blocks at which each beat opens. The
      first entry is always 0. Three to five beats, per spec 02. */
  beats: number[];
  /** The plate caption. One line, naming what the picture means. Kept out of
      the canvas so posters stay pure art and the caption stays selectable. */
  legend: string;
}
