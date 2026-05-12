import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const scriptRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(__dirname, '..', '..', '..');

export const PATHS = {
  scriptRoot,
  repoRoot,
  dataDir: path.join(scriptRoot, 'data'),
  rawDir: path.join(scriptRoot, 'data', 'raw'),
  stagingDir: path.join(scriptRoot, 'data', 'staging'),
  assetsDir: path.join(scriptRoot, 'data', 'assets'),
  workAssetsDir: path.join(scriptRoot, 'data', 'assets', 'works'),
  peopleAssetsDir: path.join(scriptRoot, 'data', 'assets', 'people'),
  dbPath: path.join(repoRoot, '.local', 'treasure.db'),
  batchesDir: path.join(repoRoot, '.local', 'batches'),
  siteAssetsDir: path.join(repoRoot, 'site', 'public', 'assets'),
  generatedDir: path.join(repoRoot, 'generated')
};

export function resolveRepoPath(relativePath) {
  return path.resolve(repoRoot, relativePath);
}

export function resolveScriptPath(relativePath) {
  return path.resolve(scriptRoot, relativePath);
}
