import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

const at = (p: string) => fileURLToPath(new URL(p, import.meta.url));

export default defineConfig({
  /* relative asset paths so the build runs from any path or a file server.
     This edition is published under /life/, and a relative base keeps that out
     of the build: the same dist serves from any subdirectory. */
  base: './',
  resolve: {
    /* most specific first: a string alias also matches its subpaths */
    alias: [
      { find: '@qubit/tokens/tokens.css', replacement: at('../../packages/tokens/src/tokens.css') },
      { find: '@qubit/tokens', replacement: at('../../packages/tokens/src/index.ts') },
      { find: '@qubit/content/schema', replacement: at('../../content/schema.ts') },
      { find: '@qubit/content/unpolarized', replacement: at('../../content/unpolarized.ts') },
      { find: '@qubit/reader', replacement: at('../../packages/reader/src/index.ts') },
    ],
  },
  build: {
    /* KaTeX fonts and any other asset stay real files, never base64 blobs */
    assetsInlineLimit: 0,
    chunkSizeWarningLimit: 800,
  },
  /* see PORTS.md */
  server: { port: 5176 },
  preview: { port: 4176 },
});
