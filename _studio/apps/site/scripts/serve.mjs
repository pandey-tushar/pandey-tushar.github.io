/* Static server for dist. Gzips text the way Pages does, so a local Lighthouse
   run measures the site rather than the absence of a CDN.
   Usage: node scripts/serve.mjs [port] */

import { createServer } from 'node:http';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createGzip } from 'node:zlib';

const ROOT = fileURLToPath(new URL('../dist', import.meta.url));
const PORT = Number(process.argv[2] || process.env.SITE_TEST_PORT || 4319);

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.xml': 'application/xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.pdf': 'application/pdf',
};
const ZIP = new Set(['.html', '.js', '.css', '.svg', '.xml', '.txt', '.json']);

createServer((req, res) => {
  const url = decodeURIComponent((req.url || '/').split('?')[0]);
  let file = join(ROOT, normalize(url).replace(/^(\.\.[/\\])+/, ''));
  if (existsSync(file) && statSync(file).isDirectory()) file = join(file, 'index.html');
  if (!file.startsWith(ROOT) || !existsSync(file)) {
    res.writeHead(404, { 'content-type': 'text/plain' });
    res.end('404');
    return;
  }
  const ext = extname(file);
  const head = {
    'content-type': TYPES[ext] || 'application/octet-stream',
    /* hashed assets are immutable, everything else revalidates */
    'cache-control': file.includes('assets') ? 'public, max-age=31536000, immutable' : 'no-cache',
    'x-content-type-options': 'nosniff',
  };
  const gzip = ZIP.has(ext) && /\bgzip\b/.test(req.headers['accept-encoding'] || '');
  if (gzip) head['content-encoding'] = 'gzip';
  else head['content-length'] = statSync(file).size;
  res.writeHead(200, head);
  const stream = createReadStream(file);
  if (gzip) stream.pipe(createGzip()).pipe(res); else stream.pipe(res);
})
  /* loud, not silent: a busy port means another app would be measured */
  .on('error', (e) => { console.error('serve: ' + e.message); process.exit(1); })
  .listen(PORT, () => console.log('serving dist on http://localhost:' + PORT));
