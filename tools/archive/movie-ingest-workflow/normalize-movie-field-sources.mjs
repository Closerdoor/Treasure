import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  IMAGE_OPTIONAL_KEYS,
  IMAGE_REQUIRED_KEYS,
  OPTIONAL_TOP_LEVEL_KEYS,
  REQUIRED_TOP_LEVEL_KEYS,
  isPlainObject
} from './movie-ingest-contract.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..');
const movieRoot = path.join(repoRoot, '.local', 'staging', 'video', 'movie');
const sourceRoot = path.join(repoRoot, '.local', 'field-sources', 'video', 'movie');

function createEmptyFieldSource(fieldName, value) {
  const isEmptyArray = Array.isArray(value) && value.length === 0;
  return {
    value,
    source: 'system',
    note: isEmptyArray
      ? `${fieldName} 当前为空数组，保留为空并等待后续补录`
      : `${fieldName} 当前沿用系统生成或空值占位`
  };
}

function ensureTopLevelEntry(sourceData, fieldName, value) {
  if (fieldName === 'images') {
    if (!isPlainObject(sourceData.images)) {
      sourceData.images = {};
    }
    return;
  }

  if (!sourceData[fieldName]) {
    sourceData[fieldName] = createEmptyFieldSource(fieldName, value);
  }
}

function ensureImageEntry(sourceData, fieldName, value) {
  if (!sourceData.images[fieldName]) {
    sourceData.images[fieldName] = createEmptyFieldSource(`images.${fieldName}`, value);
  }
}

async function main() {
  const files = (await fs.readdir(movieRoot)).filter((name) => name.endsWith('.json')).sort();
  let updated = 0;

  for (const fileName of files) {
    const moviePath = path.join(movieRoot, fileName);
    const sourcePath = path.join(sourceRoot, fileName);
    const movie = JSON.parse(await fs.readFile(moviePath, 'utf8'));
    const source = JSON.parse(await fs.readFile(sourcePath, 'utf8'));
    let changed = false;

    for (const fieldName of [...REQUIRED_TOP_LEVEL_KEYS, ...OPTIONAL_TOP_LEVEL_KEYS]) {
      if (!(fieldName in movie)) {
        continue;
      }

      if (!source[fieldName]) {
        ensureTopLevelEntry(source, fieldName, movie[fieldName]);
        changed = true;
      }
    }

    if (isPlainObject(movie.images)) {
      if (!isPlainObject(source.images)) {
        source.images = {};
        changed = true;
      }

      for (const fieldName of [...IMAGE_REQUIRED_KEYS, ...IMAGE_OPTIONAL_KEYS]) {
        if (!(fieldName in movie.images)) {
          continue;
        }

        if (!source.images[fieldName]) {
          ensureImageEntry(source, fieldName, movie.images[fieldName]);
          changed = true;
        }
      }
    }

    if (changed) {
      await fs.writeFile(sourcePath, `${JSON.stringify(source, null, 2)}\n`, 'utf8');
      updated += 1;
    }
  }

  console.log(`updated=${updated}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
