import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..');
const generatedEntriesRoot = path.join(repoRoot, 'generated', 'entries');
const assetsRoot = path.join(repoRoot, 'site', 'public', 'assets');
const reportPath = path.join(repoRoot, '.local', 'asset-check-report.json');

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function nonEmptyString(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

async function fileExists(filePath) {
  try {
    const stat = await fs.stat(filePath);
    return stat.isFile();
  } catch {
    return false;
  }
}

async function walkJsonFiles(dir) {
  const result = [];

  async function walk(current) {
    let entries;
    try {
      entries = await fs.readdir(current, { withFileTypes: true });
    } catch (error) {
      if (error?.code === 'ENOENT') {
        return;
      }
      throw error;
    }

    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath);
      } else if (entry.isFile() && entry.name.endsWith('.json')) {
        result.push(fullPath);
      }
    }
  }

  await walk(dir);
  return result.sort();
}

async function loadGeneratedEntries() {
  const files = await walkJsonFiles(generatedEntriesRoot);
  const entries = [];

  for (const file of files) {
    const raw = await fs.readFile(file, 'utf8');
    entries.push(JSON.parse(raw));
  }

  return { entries, files };
}

function buildWorkAssetRefs(entry) {
  const baseDir = `${entry.module}/${entry.submodule}/${entry.id}`;
  const images = entry.images ?? {};
  const refs = [];

  const pushWorkFile = (kind, file) => {
    const name = nonEmptyString(file);
    if (!name) {
      return;
    }

    refs.push({
      type: kind,
      relativePath: `${baseDir}/${name}`,
      workId: entry.id,
      title: entry.title
    });
  };

  pushWorkFile('poster', images.poster);
  asArray(images.posters).forEach((file) => pushWorkFile('poster_gallery', file));
  asArray(images.stills).forEach((file) => pushWorkFile('still', file));
  asArray(images.wallpapers).forEach((file) => pushWorkFile('wallpaper', file));
  asArray(entry.videos).forEach((video) => pushWorkFile('video_thumbnail', video?.thumbnail));

  return refs;
}

function buildPeopleAssetRefs(entry) {
  const refs = [];
  const groups = [entry.director, entry.writer, entry.cast, entry.otherCast, entry.producer];

  for (const group of groups) {
    for (const person of asArray(group)) {
      const avatarPath = nonEmptyString(person?.avatarPath);
      if (!avatarPath) {
        continue;
      }

      refs.push({
        type: 'person_avatar',
        relativePath: avatarPath.replace(/\\/g, '/'),
        workId: entry.id,
        title: entry.title,
        personName: person.name,
        personCode: person.personCode ?? null
      });
    }
  }

  return refs;
}

function dedupeRefs(refs) {
  const seen = new Set();
  const result = [];

  for (const ref of refs) {
    const key = `${ref.type}||${ref.relativePath}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    result.push(ref);
  }

  return result;
}

async function main() {
  const { entries, files } = await loadGeneratedEntries();

  const allRefs = dedupeRefs(entries.flatMap((entry) => [
    ...buildWorkAssetRefs(entry),
    ...buildPeopleAssetRefs(entry)
  ]));

  const checked = [];
  for (const ref of allRefs) {
    const absolutePath = path.join(assetsRoot, ...ref.relativePath.split('/'));
    checked.push({
      ...ref,
      exists: await fileExists(absolutePath),
      absolutePath
    });
  }

  const missing = checked.filter((item) => !item.exists);
  const existing = checked.filter((item) => item.exists);
  const byWork = new Map();

  for (const item of checked) {
    if (!byWork.has(item.workId)) {
      byWork.set(item.workId, {
        workId: item.workId,
        title: item.title,
        existingCount: 0,
        missingCount: 0,
        missing: []
      });
    }

    const bucket = byWork.get(item.workId);
    if (item.exists) {
      bucket.existingCount += 1;
    } else {
      bucket.missingCount += 1;
      bucket.missing.push({
        type: item.type,
        relativePath: item.relativePath,
        personName: item.personName ?? null
      });
    }
  }

  const report = {
    version: 1,
    generatedAt: new Date().toISOString(),
    assetsRoot: path.relative(repoRoot, assetsRoot).replace(/\\/g, '/'),
    entriesSource: path.relative(repoRoot, generatedEntriesRoot).replace(/\\/g, '/'),
    entriesCount: entries.length,
    filesCount: files.length,
    totals: {
      checked: checked.length,
      existing: existing.length,
      missing: missing.length
    },
    missingByType: missing.reduce((acc, item) => {
      acc[item.type] = (acc[item.type] ?? 0) + 1;
      return acc;
    }, {}),
    works: [...byWork.values()].sort((left, right) => left.workId.localeCompare(right.workId))
  };

  await fs.mkdir(path.dirname(reportPath), { recursive: true });
  await fs.writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');

  console.log(`Checked ${checked.length} asset references.`);
  console.log(`existing=${existing.length}, missing=${missing.length}`);
  console.log(`report=${reportPath}`);

  if (missing.length) {
    process.exitCode = 2;
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
