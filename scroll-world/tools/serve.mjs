// Tiny static server with Cache-Control: no-store (Windows-safe paths)
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const PORT = 8139;

const types = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.webp': 'image/webp',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.json': 'application/json',
  '.svg': 'image/svg+xml'
};

createServer(async (req, res) => {
  try {
    let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    if (p.endsWith('/')) p += 'index.html';
    p = p.replace(/^\/([a-zA-Z]:)/, '$1');           // windows drive quirk
    const file = normalize(join(root, p));
    if (!file.startsWith(normalize(root))) { res.writeHead(403); res.end(); return; }
    const data = await readFile(file);

    // Range support (video seeking)
    const range = req.headers.range;
    if (range) {
      const m = /bytes=(\d*)-(\d*)/.exec(range);
      if (m) {
        const size = data.length;
        let start = m[1] === '' ? NaN : parseInt(m[1], 10);
        let end = m[2] === '' ? size - 1 : parseInt(m[2], 10);
        if (isNaN(start)) { start = size - end; end = size - 1; }
        end = Math.min(end, size - 1);
        if (start >= 0 && start <= end) {
          res.writeHead(206, {
            'Content-Type': types[extname(file).toLowerCase()] || 'application/octet-stream',
            'Content-Range': `bytes ${start}-${end}/${size}`,
            'Accept-Ranges': 'bytes',
            'Content-Length': end - start + 1,
            'Cache-Control': 'no-store'
          });
          res.end(data.subarray(start, end + 1));
          return;
        }
      }
    }

    res.writeHead(200, {
      'Content-Type': types[extname(file).toLowerCase()] || 'application/octet-stream',
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'no-store'
    });
    res.end(data);
  } catch {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('not found');
  }
}).listen(PORT, '127.0.0.1', () => console.log(`serving ${root} on http://127.0.0.1:${PORT}`));
