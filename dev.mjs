import { spawn } from 'node:child_process';
import { createServer } from 'vite';
const python = process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python';
const api = spawn(python, ['-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1', '--port', '8001'], { stdio: 'inherit' });
const vite = await createServer();
await vite.listen();
vite.printUrls();
let closing = false;
async function close() {
  if (closing) return;
  closing = true;
  api.kill();
  await vite.close();
  process.exit();
}
process.on('SIGINT', close);
process.on('SIGTERM', close);
api.on('error', error => { console.error('Cannot start Python backend:', error.message); close(); });
api.on('exit', code => { if (!closing) { console.error('Backend exited:', code); close(); } });
