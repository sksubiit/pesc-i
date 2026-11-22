import http from 'node:http';
import { readFile, realpath, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = await realpath(fileURLToPath(new URL('../web/', import.meta.url)));
const args = process.argv.slice(2);
const port = args.length === 0 ? 8000 : args.length === 2 && args[0] === '--port' ? Number(args[1]) : NaN;
if (!Number.isInteger(port) || port < 0 || port > 65535) {
  console.error('Usage: npm start -- [--port 0..65535]');
  process.exit(1);
}
try {
  await stat(path.join(root, 'vendor/manifest.json'));
} catch {
  console.error('Browser assets missing. Run npm ci and npm run build:web first.');
  process.exit(1);
}
const types = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.wasm': 'application/wasm', '.json': 'application/json', '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8', '.gz': 'application/gzip',
};
const server = http.createServer(async (req, res) => {
  try {
    if (!['GET', 'HEAD'].includes(req.method)) {
      res.writeHead(405, { Allow: 'GET, HEAD' }).end();
      return;
    }
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const requested = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
    const target = await realpath(requested);
    const relative = path.relative(root, target);
    if (relative.startsWith('..') || path.isAbsolute(relative)) {
      res.writeHead(403).end();
      return;
    }
    const info = await stat(target);
    if (!info.isFile()) {
      res.writeHead(404).end();
      return;
    }
    const body = req.method === 'HEAD' ? null : await readFile(target);
    res.writeHead(200, {
      'Content-Type': types[path.extname(target)] || 'application/octet-stream',
      'Content-Length': info.size,
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
    });
    res.end(body);
  } catch (err) {
    res.writeHead(err instanceof URIError ? 400 : 404).end();
  }
});
const listen = candidate => new Promise((resolve, reject) => {
  server.once('error', reject);
  server.listen(candidate, '127.0.0.1', () => {
    server.removeListener('error', reject);
    resolve();
  });
});
let listening = false;
for (let candidate = port; candidate <= Math.min(port + 19, 65535); candidate++) {
  try {
    await listen(candidate);
    listening = true;
    break;
  } catch (err) {
    if (err.code !== 'EADDRINUSE') throw err;
    console.log('Port ' + candidate + ' is busy; trying the next port.');
  }
}
if (!listening) {
  console.error('No free port. Choose another with --port.');
  process.exit(1);
}
console.log('PESC-I browser demo: http://127.0.0.1:' + server.address().port + '/');
console.log('Ctrl+C stops this file server. Pause or close the page to stop its engines.');
