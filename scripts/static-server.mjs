import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.avif': 'image/avif',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
};

export function createStaticServer(rootDir, port, name = 'StaticServer') {
  const server = http.createServer((req, res) => {
    // Parse URL and strip query/hash
    const parsedUrl = new URL(req.url, `http://localhost:${port}`);
    let pathname = decodeURIComponent(parsedUrl.pathname);

    // Default to index.html if pointing to root or directory
    if (pathname.endsWith('/')) {
      pathname += 'index.html';
    }

    let filePath = path.join(rootDir, pathname);

    // Prevent directory traversal
    if (!filePath.startsWith(rootDir)) {
      res.writeHead(403, { 'Content-Type': 'text/plain' });
      res.end('403 Forbidden');
      return;
    }

    // Check if path exists and is file
    fs.stat(filePath, (err, stats) => {
      if (err || !stats.isFile()) {
        // Fallback to index.html if path has no extension (SPA-like or directory)
        if (!path.extname(pathname)) {
          const indexHtml = path.join(filePath, 'index.html');
          if (fs.existsSync(indexHtml)) {
            filePath = indexHtml;
          } else {
            res.writeHead(404, { 'Content-Type': 'text/plain' });
            res.end('404 Not Found');
            return;
          }
        } else {
          res.writeHead(404, { 'Content-Type': 'text/plain' });
          res.end('404 Not Found');
          return;
        }
      }

      const ext = path.extname(filePath).toLowerCase();
      const contentType = MIME_TYPES[ext] || 'application/octet-stream';

      // Standard production static headers
      const headers = {
        'Content-Type': contentType,
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'public, max-age=0, must-revalidate',
      };

      res.writeHead(200, headers);
      fs.createReadStream(filePath).pipe(res);
    });
  });

  return new Promise((resolve, reject) => {
    server.listen(port, '127.0.0.1', () => {
      console.log(`[${name}] Serving ${rootDir} at http://localhost:${port}`);
      resolve(server);
    });
    server.on('error', reject);
  });
}

// If run directly: node scripts/static-server.mjs
if (process.argv[1] === __filename) {
  const websiteDir = path.join(projectRoot, 'uis', 'website');
  const backofficeDir = path.join(projectRoot, 'uis', 'backoffice');

  Promise.all([
    createStaticServer(websiteDir, 5500, 'Website'),
    createStaticServer(backofficeDir, 5502, 'Backoffice'),
  ]).then(() => {
    console.log('Both servers running. Press Ctrl+C to stop.');
  }).catch((err) => {
    console.error('Failed to start servers:', err);
    process.exit(1);
  });
}

