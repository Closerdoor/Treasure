import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ALLOWED_TOP_LEVEL_KEYS,
  EXTENDED_TOP_LEVEL_KEYS,
  OPTIONAL_TOP_LEVEL_KEYS,
  REQUIRED_TOP_LEVEL_KEYS
} from './movie-ingest-contract.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..');
const stagingRoot = path.join(repoRoot, '.local', 'staging', 'video', 'movie');
const legacyRoot = path.join(repoRoot, 'content', 'video', 'movie');
const outputPath = path.join(repoRoot, '.local', 'movie-baseline-report.json');

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, 'utf8'));
}

function makeFieldCoverageMap(keys) {
  return Object.fromEntries(keys.map((key) => [key, []]));
}

function hasSourceEntry(sourceData, key) {
  if (key === 'images') {
    return Boolean(sourceData.images && typeof sourceData.images === 'object');
  }

  return Boolean(sourceData[key]);
}

async function main() {
  const files = (await fs.readdir(stagingRoot)).filter((name) => name.endsWith('.json')).sort();
  const coverage = makeFieldCoverageMap(ALLOWED_TOP_LEVEL_KEYS);
  const movies = [];

  for (const fileName of files) {
    const moviePath = path.join(stagingRoot, fileName);
    const movie = await readJson(moviePath);
    const sourcePath = path.join(legacyRoot, movie.id, 'source.json');
    const source = await readJson(sourcePath);

    const keys = Object.keys(movie).sort();
    for (const key of keys) {
      if (coverage[key]) {
        coverage[key].push(movie.id);
      }
    }

    const missingSourceKeys = keys.filter((key) => !hasSourceEntry(source, key));
    const extraMovieKeys = keys.filter((key) => !ALLOWED_TOP_LEVEL_KEYS.includes(key));

    movies.push({
      id: movie.id,
      title: movie.title,
      keyCount: keys.length,
      keys,
      missingSourceKeys,
      extraMovieKeys
    });
  }

  const payload = {
    version: 1,
    generatedAt: new Date().toISOString(),
    workflow: 'movie_staging_baseline',
    requiredTopLevelKeys: REQUIRED_TOP_LEVEL_KEYS,
    optionalTopLevelKeys: OPTIONAL_TOP_LEVEL_KEYS,
    extendedTopLevelKeys: EXTENDED_TOP_LEVEL_KEYS,
    fieldCoverage: coverage,
    movies
  };

  await fs.writeFile(outputPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  console.log(`baseline=${path.relative(repoRoot, outputPath).replace(/\\/g, '/')}`);
  console.log(`movies=${movies.length}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
