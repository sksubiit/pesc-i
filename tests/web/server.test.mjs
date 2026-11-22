import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import http from 'node:http';
import { once } from 'node:events';

test('preview serves assets with MIME types and skips an occupied port', async t => {
  const occupied = http.createServer();
  occupied.listen(0, '127.0.0.1');
  await once(occupied, 'listening');
  t.after(() => occupied.close());
  const child = spawn(process.execPath, ['scripts/serve-web.mjs', '--port', String(occupied.address().port)], {
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  t.after(() => child.kill());
  const url = await new Promise((resolve, reject) => {
    let output = '';
    const timer = setTimeout(() => reject(new Error('preview startup timed out: ' + output)), 10000);
    child.stdout.on('data', chunk => {
      output += chunk;
      const match = output.match(/http:[/][/]127[.]0[.]0[.]1:[0-9]+[/]/);
      if (match) { clearTimeout(timer); resolve(match[0]); }
    });
    child.once('error', err => { clearTimeout(timer); reject(err); });
    child.once('exit', code => { clearTimeout(timer); reject(new Error('preview exited: ' + code)); });
  });
  assert.notEqual(new URL(url).port, String(occupied.address().port));
  const page = await fetch(url);
  assert.equal(page.status, 200);
  assert.match(page.headers.get('content-type'), /text[/]html/);
  const module = await fetch(new URL('app.mjs', url));
  assert.match(module.headers.get('content-type'), /javascript/);
  const manifest = await fetch(new URL('vendor/manifest.json', url));
  assert.equal(manifest.status, 200);
  const assets = await manifest.json();
  const wasm = await fetch(new URL('vendor/' + assets.engine.replace('.js', '.wasm'), url), { method: 'HEAD' });
  assert.equal(wasm.status, 200);
  assert.equal(wasm.headers.get('content-type'), 'application/wasm');
  const hidden = await fetch(new URL('package.json', url));
  assert.equal(hidden.status, 404);
  const post = await fetch(url, { method: 'POST' });
  assert.equal(post.status, 405);
});
