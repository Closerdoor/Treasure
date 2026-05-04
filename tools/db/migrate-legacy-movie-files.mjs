import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..');
const legacyMoviesRoot = path.join(repoRoot, 'content', 'video', 'movie');
const stagingRoot = path.join(repoRoot, '.local', 'staging', 'video', 'movie');
const snapshotsRoot = path.join(repoRoot, '.local', 'source-snapshots', 'video', 'movie');
const workAssetsRoot = path.join(repoRoot, 'site', 'public', 'assets', 'video', 'movie');
const peopleAssetsRoot = path.join(repoRoot, 'site', 'public', 'assets', 'people');
const dbPath = path.join(repoRoot, '.local', 'treasure.db');
const sqlitePath = process.env.SQLITE3_PATH || 'D:\\ArtSoftware\\sqlite3.exe';

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function nonEmptyString(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function personKey(person) {
  return `${person.name || ''}||${person.nameEn || ''}`;
}

function queryJson(sql) {
  const result = spawnSync(sqlitePath, ['-json', dbPath, sql], {
    encoding: 'utf8',
    cwd: repoRoot,
    shell: false
  });

  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || 'sqlite3 query failed');
  }

  const text = result.stdout.trim();
  return text ? JSON.parse(text) : [];
}

async function pathExists(targetPath) {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function ensureDir(dirPath) {
  await fs.mkdir(dirPath, { recursive: true });
}

async function copyFileSafe(sourcePath, targetPath) {
  await ensureDir(path.dirname(targetPath));
  await fs.copyFile(sourcePath, targetPath);
}

async function copyDirRecursive(sourceDir, targetDir) {
  if (!(await pathExists(sourceDir))) {
    return 0;
  }

  await ensureDir(targetDir);
  const entries = await fs.readdir(sourceDir, { withFileTypes: true });
  let copied = 0;

  for (const entry of entries) {
    const sourcePath = path.join(sourceDir, entry.name);
    const targetPath = path.join(targetDir, entry.name);

    if (entry.isDirectory()) {
      copied += await copyDirRecursive(sourcePath, targetPath);
      continue;
    }

    if (!entry.isFile()) {
      continue;
    }

    await copyFileSafe(sourcePath, targetPath);
    copied += 1;
  }

  return copied;
}

async function loadLegacyMovies() {
  const entries = await fs.readdir(legacyMoviesRoot, { withFileTypes: true });
  const ids = entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort();
  const movies = [];

  for (const id of ids) {
    const dataPath = path.join(legacyMoviesRoot, id, 'data.json');
    if (!(await pathExists(dataPath))) {
      continue;
    }

    const raw = await fs.readFile(dataPath, 'utf8');
    movies.push({
      id,
      legacyDir: path.join(legacyMoviesRoot, id),
      movie: JSON.parse(raw)
    });
  }

  return movies;
}

function cleanMovieAssetReferences(movie, existingNames) {
  const imageFiles = new Set(existingNames);
  const nextMovie = structuredClone(movie);
  const images = nextMovie.images ?? {};

  if (nonEmptyString(images.poster) && !imageFiles.has(images.poster)) {
    images.poster = null;
  }

  images.posters = asArray(images.posters).filter((file) => imageFiles.has(file));
  images.stills = asArray(images.stills).filter((file) => imageFiles.has(file));
  images.wallpapers = asArray(images.wallpapers).filter((file) => imageFiles.has(file));
  nextMovie.images = images;

  nextMovie.videos = asArray(nextMovie.videos).map((video) => {
    const thumbnail = nonEmptyString(video?.thumbnail);
    if (thumbnail && !imageFiles.has(thumbnail)) {
      return { ...video, thumbnail: null };
    }

    return video;
  });

  return nextMovie;
}

async function main() {
  const peopleRows = queryJson('SELECT person_code, name, name_en, avatar_path FROM people;');
  const peopleLookup = new Map(peopleRows.map((person) => [`${person.name || ''}||${person.name_en || ''}`, person]));
  const legacyMovies = await loadLegacyMovies();

  await ensureDir(stagingRoot);
  await ensureDir(snapshotsRoot);
  await ensureDir(workAssetsRoot);
  await ensureDir(peopleAssetsRoot);

  const summary = {
    staged: 0,
    rawFilesCopied: 0,
    workFilesCopied: 0,
    peopleFilesCopied: 0,
    videoThumbnailsCleared: 0
  };

  for (const item of legacyMovies) {
    const { id, legacyDir } = item;
    const imagesDir = path.join(legacyDir, 'images');
    const imageEntries = (await pathExists(imagesDir)) ? await fs.readdir(imagesDir, { withFileTypes: true }) : [];
    const imageFileNames = imageEntries.filter((entry) => entry.isFile()).map((entry) => entry.name);
    const workFileNames = imageFileNames.filter((name) => !/^avatar-/i.test(name));
    const cleanedMovie = cleanMovieAssetReferences(item.movie, imageFileNames);

    const originalVideoThumbs = asArray(item.movie.videos).filter((video) => nonEmptyString(video?.thumbnail)).length;
    const cleanedVideoThumbs = asArray(cleanedMovie.videos).filter((video) => nonEmptyString(video?.thumbnail)).length;
    summary.videoThumbnailsCleared += originalVideoThumbs - cleanedVideoThumbs;

    await fs.writeFile(path.join(stagingRoot, `${id}.json`), `${JSON.stringify(cleanedMovie, null, 2)}\n`, 'utf8');
    summary.staged += 1;

    summary.rawFilesCopied += await copyDirRecursive(path.join(legacyDir, 'raw'), path.join(snapshotsRoot, id));

    const workTargetDir = path.join(workAssetsRoot, id);
    await ensureDir(workTargetDir);
    for (const fileName of workFileNames) {
      await copyFileSafe(path.join(imagesDir, fileName), path.join(workTargetDir, fileName));
      summary.workFilesCopied += 1;
    }

    const personGroups = [cleanedMovie.director, cleanedMovie.writer, cleanedMovie.cast, cleanedMovie.otherCast, cleanedMovie.producer];
    for (const group of personGroups) {
      for (const person of group ?? []) {
        const sourceAvatar = nonEmptyString(person?.avatar);
        if (!sourceAvatar) {
          continue;
        }

        const resolved = peopleLookup.get(personKey(person));
        const avatarPath = nonEmptyString(resolved?.avatar_path);
        if (!avatarPath) {
          continue;
        }

        const sourcePath = path.join(imagesDir, sourceAvatar);
        if (!(await pathExists(sourcePath))) {
          continue;
        }

        await copyFileSafe(sourcePath, path.join(repoRoot, 'site', 'public', 'assets', ...avatarPath.split('/')));
        summary.peopleFilesCopied += 1;
      }
    }
  }

  console.log(`Staged ${summary.staged} movies into ${stagingRoot}`);
  console.log(`Copied raw=${summary.rawFilesCopied}, work_assets=${summary.workFilesCopied}, people_assets=${summary.peopleFilesCopied}`);
  console.log(`cleared_missing_video_thumbnails=${summary.videoThumbnailsCleared}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
