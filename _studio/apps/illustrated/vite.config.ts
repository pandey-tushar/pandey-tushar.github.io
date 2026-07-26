import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

const at = (p: string) => fileURLToPath(new URL(p, import.meta.url));

export default defineConfig({
  /* relative asset paths so the build runs from any path or a file server.
     This edition is published under /illustrated/, and a relative base keeps
     that out of the build: the same dist serves from any subdirectory. */
  base: './',
  resolve: {
    /* most specific first: a string alias also matches its subpaths */
    alias: [
      { find: '@qubit/tokens/tokens.css', replacement: at('../../packages/tokens/src/tokens.css') },
      { find: '@qubit/tokens', replacement: at('../../packages/tokens/src/index.ts') },
      { find: '@qubit/motifs', replacement: at('../../packages/motifs/src/index.ts') },
      { find: '@qubit/content/schema', replacement: at('../../content/schema.ts') },
      { find: '@qubit/content', replacement: at('../../content/index.ts') },
    ],
  },
  build: {
    assetsInlineLimit: 0,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      input: {
        /* the edition, and the poster harness the export and the determinism
           gate both drive. Same renderer, so a poster cannot drift from a frame. */
        main: at('index.html'),
        poster: at('poster.html'),
      },
    },
  },
  server: { port: 5175 },
  preview: { port: 4175 },
});
