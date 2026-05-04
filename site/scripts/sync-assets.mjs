import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const siteRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(siteRoot, '..');
const exportScript = path.join(repoRoot, 'tools', 'db', 'export-generated.mjs');

await fs.mkdir(path.join(siteRoot, 'public', 'assets'), { recursive: true });

const result = spawnSync(process.execPath, [exportScript], {
  cwd: repoRoot,
  stdio: 'inherit'
});

if (result.status !== 0) {
  process.exit(result.status ?? 1);
}
