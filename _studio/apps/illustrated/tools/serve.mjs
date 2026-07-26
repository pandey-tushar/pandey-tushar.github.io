/* A static server for dist/, so the gates run against the built edition and
   not against the dev server's module graph. Port 0 means the OS picks a free
   one, which keeps parallel runs from fighting over a number. */

import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, resolve } from 'node:path';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
};

export async function serve(root) {
  const base = resolve(root);
  try {
    await stat(join(base, 'index.html'));
  } catch {
    throw new Error('no build found at ' + base + '. Run: npm run build -w @qubit/illustrated');
  }

  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url ?? '/', 'http://localhost');
    let file = decodeURIComponent(url.pathname);
    if (file.endsWith('/')) file += 'index.html';
    const target = resolve(join(base, file));
    if (!target.startsWith(base)) {
      res.writeHead(403).end();
      return;
    }
    try {
      const body = await readFile(target);
      res.writeHead(200, {
        'content-type': MIME[extname(target)] ?? 'application/octet-stream',
        'cache-control': 'no-store',
      });
      res.end(body);
    } catch {
      res.writeHead(404, { 'content-type': 'text/plain' }).end('not found');
    }
  });

  await new Promise((done) => server.listen(0, '127.0.0.1', done));
  const { port } = server.address();
  return {
    url: 'http://127.0.0.1:' + port,
    close: () => new Promise((done) => server.close(done)),
  };
}
