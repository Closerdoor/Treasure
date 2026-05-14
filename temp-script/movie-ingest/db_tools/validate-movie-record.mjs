import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { PATHS } from './paths.mjs';
import {
  ALLOWED_TOP_LEVEL_KEYS,
  IMAGE_OPTIONAL_KEYS,
  IMAGE_REQUIRED_KEYS,
  REQUIRED_TOP_LEVEL_KEYS,
  isPlainObject
} from './movie-ingest-contract.mjs';

const repoRoot = PATHS.repoRoot;

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) {
      continue;
    }

    const key = token.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith('--')) {
      args[key] = true;
      continue;
    }

    args[key] = next;
    index += 1;
  }
  return args;
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, 'utf8'));
}

function validateImageSources(imagesSource, imagesValue, errors) {
  if (!isPlainObject(imagesValue)) {
    errors.push('images must be an object');
    return;
  }

  if (!isPlainObject(imagesSource)) {
    errors.push('field sources missing images object');
    return;
  }

  for (const key of IMAGE_REQUIRED_KEYS) {
    if (!(key in imagesValue)) {
      errors.push(`images missing required key: ${key}`);
    }
    if (key in imagesValue && !imagesSource[key]?.source) {
      errors.push(`field sources missing images.${key}`);
    }
  }

  for (const key of IMAGE_OPTIONAL_KEYS) {
    if (key in imagesValue && !imagesSource[key]?.source) {
      errors.push(`field sources missing images.${key}`);
    }
  }
}

function validateSourceCoverage(movie, sources) {
  const errors = [];
  const keys = Object.keys(movie);

  for (const key of keys) {
    if (key === 'images') {
      validateImageSources(sources.images, movie.images, errors);
      continue;
    }

    if (!sources[key]) {
      errors.push(`field sources missing top-level key: ${key}`);
      continue;
    }

    if (!sources[key].source && !Array.isArray(sources[key].sources)) {
      errors.push(`field source entry invalid for key: ${key}`);
    }
  }

  return errors;
}

export function validateRecordShape(movie, sources) {
  const errors = [];
  const warnings = [];
  const movieKeys = Object.keys(movie).sort();

  for (const key of REQUIRED_TOP_LEVEL_KEYS) {
    if (!(key in movie)) {
      errors.push(`missing required top-level key: ${key}`);
    }
  }

  for (const key of movieKeys) {
    if (!ALLOWED_TOP_LEVEL_KEYS.includes(key)) {
      errors.push(`unexpected top-level key: ${key}`);
    }
  }

  errors.push(...validateSourceCoverage(movie, sources));

  return { topLevelKeys: movieKeys, errors, warnings };
}

function compareWithBaseline(candidate, baseline) {
  const same = [];
  const different = [];
  const missing = [];
  const extra = [];

  for (const key of Object.keys(baseline).sort()) {
    if (!(key in candidate)) {
      missing.push(key);
      continue;
    }

    if (JSON.stringify(candidate[key]) === JSON.stringify(baseline[key])) {
      same.push(key);
      continue;
    }

    different.push(key);
  }

  for (const key of Object.keys(candidate).sort()) {
    if (!(key in baseline)) {
      extra.push(key);
    }
  }

  return { same, different, missing, extra };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.movie || !args.sources) {
    console.log('Usage: node tools/db/validate-movie-record.mjs --movie <file> --sources <file> [--baseline-id <id>]');
    return;
  }

  const moviePath = path.resolve(repoRoot, args.movie);
  const sourcesPath = path.resolve(repoRoot, args.sources);
  const movie = await readJson(moviePath);
  const sources = await readJson(sourcesPath);

  const { topLevelKeys: movieKeys, errors, warnings } = validateRecordShape(movie, sources);

  const result = {
    version: 1,
    generatedAt: new Date().toISOString(),
    movie: path.relative(repoRoot, moviePath).replace(/\\/g, '/'),
    sources: path.relative(repoRoot, sourcesPath).replace(/\\/g, '/'),
    topLevelKeys: movieKeys,
    requiredTopLevelKeys: REQUIRED_TOP_LEVEL_KEYS,
    optionalTopLevelKeys: ALLOWED_TOP_LEVEL_KEYS.filter((key) => !REQUIRED_TOP_LEVEL_KEYS.includes(key)),
    errors,
    warnings
  };

  if (args['baseline-id']) {
    const baselinePath = path.join(PATHS.stagingDir, `${args['baseline-id']}.json`);
    const baseline = await readJson(baselinePath);
    result.baselineId = args['baseline-id'];
    result.compare = compareWithBaseline(movie, baseline);
  }

  console.log(JSON.stringify(result, null, 2));
  if (errors.length) {
    process.exitCode = 1;
  }
}

const __filename = fileURLToPath(import.meta.url);

const isDirectRun = process.argv[1] && path.resolve(process.argv[1]) === __filename;

if (isDirectRun) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
