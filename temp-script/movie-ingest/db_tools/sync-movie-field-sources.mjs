import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { PATHS } from './paths.mjs';

const repoRoot = PATHS.repoRoot;
const legacyRoot = path.join(repoRoot, 'content', 'video', 'movie');
const targetRoot = PATHS.stagingDir;

async function main() {
  const entries = await fs.readdir(legacyRoot, { withFileTypes: true });
  let copied = 0;

  for (const entry of entries) {
    if (!entry.isDirectory()) {
      continue;
    }

    const sourcePath = path.join(legacyRoot, entry.name, 'source.json');
    try {
      await fs.access(sourcePath);
    } catch {
      continue;
    }

    await fs.mkdir(targetRoot, { recursive: true });
    const targetPath = path.join(targetRoot, `${entry.name}.json`);
    await fs.copyFile(sourcePath, targetPath);
    copied += 1;
  }

  console.log(`synced=${copied}`);
  console.log(`target=${path.relative(repoRoot, targetRoot).replace(/\\/g, '/')}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
