import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';
import { sitePlugin } from './vite/plugin.ts';

const at = (p: string): string => fileURLToPath(new URL(p, import.meta.url));

export default defineConfig({
  /* the site is served from the apex root, and the feed and sitemap need
     absolute paths, so no relative base here */
  base: '/',
  plugins: [sitePlugin()],
  resolve: {
    /* most specific first: a string alias also matches its subpaths */
    alias: [
      { find: '@qubit/tokens/tokens.css', replacement: at('../../packages/tokens/src/tokens.css') },
      { find: '@qubit/tokens', replacement: at('../../packages/tokens/src/index.ts') },
    ],
  },
  build: {
    assetsInlineLimit: 0,
    /* three.js is the deferred chunk and is meant to be large */
    chunkSizeWarningLimit: 700,
  },
  server: { port: 5174 },
  preview: { port: 4174 },
});
