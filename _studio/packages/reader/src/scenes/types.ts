/* Types only. The reader core imports this and never imports the registry, so
   an edition that does not ask for scenes keeps three.js out of its graph
   entirely, rather than shipping chunks nothing fetches. */

export type SceneFn = (el: HTMLElement) => void;

/** What `mountReader` needs from a scene implementation. `@qubit/reader/scenes`
    exports the bundled one; an edition passes it in to switch scenes on. */
export interface SceneMounter {
  /** Mounts every unmounted `.scene[data-scene]` inside `root`. */
  mountScenes(root: ParentNode): void;
  /** Starfield and cover lattice, after first paint. */
  mountBackground(canvas: HTMLCanvasElement | null, coverMount: HTMLElement | null): void;
}
