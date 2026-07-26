import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

const at = (p: string) => fileURLToPath(new URL(p, import.meta.url));

export default defineConfig({
  /* relative asset paths so the build runs from any path or a file server */
  base: './',
  resolve: {
    /* most specific first: a string alias also matches its subpaths */
    alias: [
      { find: '@qubit/tokens/tokens.css', replacement: at('../../packages/tokens/src/tokens.css') },
      { find: '@qubit/tokens', replacement: at('../../packages/tokens/src/index.ts') },
      { find: '@qubit/reader/devanagari.css', replacement: at('../../packages/reader/src/styles/devanagari.css') },
      { find: '@qubit/reader/scenes', replacement: at('../../packages/reader/src/scenes/index.ts') },
      { find: '@qubit/reader/math', replacement: at('../../packages/reader/src/math.ts') },
      { find: '@qubit/reader', replacement: at('../../packages/reader/src/index.ts') },
      { find: '@qubit/content/schema', replacement: at('../../content/schema.ts') },
      { find: '@qubit/content/hi', replacement: at('../../content/hi.ts') },
    ],
  },
  build: {
    /* KaTeX fonts and any other asset stay real files, never base64 blobs */
    assetsInlineLimit: 0,
    chunkSizeWarningLimit: 800,
  },
  /* see PORTS.md */
  server: { port: 5177 },
  preview: { port: 4177 },
});
