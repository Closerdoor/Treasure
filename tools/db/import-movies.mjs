import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { inferPrimaryCountry } from './movie-db-projection.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..');
const moviesRoot = path.join(repoRoot, '.local', 'staging', 'video', 'movie');
const dbPath = path.join(repoRoot, '.local', 'treasure.db');
const summaryPath = path.join(repoRoot, '.local', 'import-movies-summary.json');

function resolveSqlitePath() {
  const candidates = [process.env.SQLITE3_PATH, 'D:\\ArtSoftware\\sqlite3.exe', 'sqlite3'].filter(Boolean);
  return candidates[0];
}

const sqlitePath = resolveSqlitePath();

function runSql(sql) {
  const result = spawnSync(sqlitePath, [dbPath], {
    input: sql,
    encoding: 'utf8',
    cwd: repoRoot,
    shell: false
  });

  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || 'sqlite3 execution failed');
  }

  return result.stdout.trim();
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

function tableColumns(tableName) {
  return queryJson(`PRAGMA table_info(${tableName});`).map((column) => column.name);
}

function ensureWorksSchema() {
  const columns = tableColumns('works');
  if (!columns.includes('story_note')) {
    return;
  }

  runSql(`
BEGIN;
CREATE TABLE works__new (
  id TEXT PRIMARY KEY,
  module TEXT NOT NULL CHECK (module IN ('video', 'anime', 'book', 'music', 'game')),
  submodule TEXT CHECK (
    submodule IS NULL OR submodule IN (
      'movie',
      'tv_series',
      'documentary',
      'short_drama',
      'anime_movie',
      'anime_series'
    )
  ),
  schema_type TEXT NOT NULL CHECK (
    schema_type IN (
      'live_action_movie',
      'animated_movie',
      'live_action_series',
      'animated_series',
      'documentary_film',
      'documentary_series',
      'book',
      'music',
      'game'
    )
  ),
  title TEXT NOT NULL,
  original_title TEXT,
  year INTEGER,
  country TEXT,
  language TEXT,
  publish_company TEXT,
  runtime_minutes INTEGER,
  episode_count INTEGER,
  episode_runtime_minutes INTEGER,
  synopsis_text TEXT,
  synopsis_note TEXT,
  story_text TEXT,
  aliases_json TEXT,
  release_dates_json TEXT,
  identifiers_json TEXT,
  ratings_json TEXT,
  links_json TEXT,
  images_json TEXT,
  videos_json TEXT,
  reviews_json TEXT,
  soundtrack_json TEXT,
  relations_json TEXT,
  quotes_json TEXT,
  episode_stories_json TEXT,
  characters_json TEXT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO works__new (
  id, module, submodule, schema_type, title, original_title, year, country, language,
  publish_company, runtime_minutes, episode_count, episode_runtime_minutes,
  synopsis_text, synopsis_note, story_text,
  aliases_json, release_dates_json, identifiers_json, ratings_json, links_json,
  images_json, videos_json, reviews_json, soundtrack_json, relations_json,
  quotes_json, episode_stories_json, characters_json,
  status, created_at, updated_at
)
SELECT
  id, module, submodule, schema_type, title, original_title, year, country, language,
  publish_company, runtime_minutes, episode_count, episode_runtime_minutes,
  synopsis_text, synopsis_note, story_text,
  aliases_json, release_dates_json, identifiers_json, ratings_json, links_json,
  images_json, videos_json, reviews_json, soundtrack_json, relations_json,
  quotes_json, episode_stories_json, characters_json,
  status, created_at, updated_at
FROM works;
DROP TABLE works;
ALTER TABLE works__new RENAME TO works;
CREATE INDEX idx_works_module_submodule ON works (module, submodule);
CREATE INDEX idx_works_schema_type ON works (schema_type);
CREATE INDEX idx_works_status ON works (status);
CREATE INDEX idx_works_year ON works (year);
INSERT OR IGNORE INTO schema_migrations (version) VALUES ('0003_drop_story_note');
COMMIT;
`);
}

function sqlValue(value) {
  if (value === null || value === undefined) {
    return 'NULL';
  }

  if (typeof value === 'number') {
    return Number.isFinite(value) ? String(value) : 'NULL';
  }

  if (typeof value === 'boolean') {
    return value ? '1' : '0';
  }

  return `'${String(value).replace(/'/g, "''")}'`;
}

function jsonValue(value) {
  if (value === null || value === undefined) {
    return 'NULL';
  }

  return sqlValue(JSON.stringify(value));
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function nonEmptyString(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function uniqueStrings(values) {
  return [...new Set(asArray(values).map((value) => nonEmptyString(value)).filter(Boolean))];
}

function personKey(person) {
  return `${person.name || ''}||${person.nameEn || ''}`;
}

function normalizeCreditType(role = '', fallback) {
  if (/原著/.test(role)) return 'original_author';
  if (/译/.test(role)) return 'translator';
  if (/监制/.test(role)) return 'supervisor';
  if (/出品/.test(role)) return 'presenter';
  if (/制片/.test(role)) return 'producer';
  return fallback;
}

function computeAggregateRating(movie) {
  const values = [movie.doubanRating, movie.imdbRating, movie.tmdbRating];

  if (typeof movie.rottenTomatoes === 'number') {
    values.push(movie.rottenTomatoes / 10);
  }

  const valid = values.filter((value) => typeof value === 'number' && Number.isFinite(value));
  if (!valid.length) {
    return null;
  }

  return Math.round((valid.reduce((sum, value) => sum + value, 0) / valid.length) * 10) / 10;
}

function buildImagesJson(movie) {
  const images = movie.images ?? {};
  return {
    poster: nonEmptyString(images.poster),
    posters: asArray(images.posters),
    stills: asArray(images.stills),
    wallpapers: asArray(images.wallpapers),
    postersTotal: images.postersTotal ?? null,
    stillsTotal: images.stillsTotal ?? null,
    assetDir: `video/movie/${movie.id}`
  };
}

function buildIdentifiersJson(movie) {
  return {
    douban: nonEmptyString(movie.doubanId),
    imdb: nonEmptyString(movie.imdbId),
    tmdb: nonEmptyString(movie.tmdbId)
  };
}

function buildRatingsJson(movie) {
  const rottenValue = typeof movie.rottenTomatoes === 'number' ? Math.round(movie.rottenTomatoes) / 10 : null;
  const metascoreValue = typeof movie.metascore === 'number' ? Math.round(movie.metascore) / 10 : null;

  return {
    aggregate: { value: computeAggregateRating(movie), scale: 10 },
    douban: { value: movie.doubanRating ?? null, scale: 10 },
    imdb: { value: movie.imdbRating ?? null, scale: 10 },
    tmdb: { value: movie.tmdbRating ?? null, scale: 10 },
    rottenTomatoes: { value: rottenValue, scale: rottenValue === null ? null : 10 },
    metascore: { value: metascoreValue, scale: metascoreValue === null ? null : 10 },
    certification: { value: nonEmptyString(movie.rated) },
    awards: { value: nonEmptyString(movie.awards) }
  };
}

function buildLinksJson(movie) {
  const links = movie.links ?? {};
  return {
    douban: nonEmptyString(links.douban),
    imdb: nonEmptyString(links.imdb),
    tmdb: nonEmptyString(links.tmdb)
  };
}

function buildRelationsJson(movie) {
  return {
    series: asArray(movie.series),
    similar: asArray(movie.similar)
  };
}

function buildSoundtrackJson(movie) {
  const soundtrack = movie.soundtrack;
  if (!soundtrack) {
    return null;
  }

  if (Array.isArray(soundtrack.albums)) {
    return {
      albums: soundtrack.albums.map((album) => ({
        name: nonEmptyString(album.name),
        note: nonEmptyString(album.note),
        coverImage: nonEmptyString(album.coverImage),
        releaseDate: nonEmptyString(album.releaseDate),
        type: nonEmptyString(album.type),
        tracks: asArray(album.tracks).map((track) => ({
          name: track.name,
          artist: nonEmptyString(track.artist),
          duration: nonEmptyString(track.duration)
        }))
      }))
    };
  }

  return {
    albums: [
      {
        name: nonEmptyString(soundtrack.name),
        note: [nonEmptyString(soundtrack.note), nonEmptyString(soundtrack.composer) ? `${soundtrack.composer}${nonEmptyString(soundtrack.composerEn) ? ` / ${soundtrack.composerEn}` : ''}` : null].filter(Boolean).join(' | ') || null,
        coverImage: nonEmptyString(soundtrack.coverImage),
        releaseDate: nonEmptyString(soundtrack.releaseDate) || (soundtrack.year ? String(soundtrack.year) : null),
        type: nonEmptyString(soundtrack.type) || 'soundtrack',
        tracks: asArray(soundtrack.tracks).map((track) => ({
          name: track.name,
          artist: nonEmptyString(track.artist),
          duration: nonEmptyString(track.duration)
        }))
      }
    ]
  };
}

function buildReviewsJson(movie) {
  return asArray(movie.reviews).map((review) => ({
    author: nonEmptyString(review.author),
    source: nonEmptyString(review.source),
    date: nonEmptyString(review.date),
    content: nonEmptyString(review.content),
    url: nonEmptyString(review.url),
    title: nonEmptyString(review.title)
  }));
}

function inferAvatarPath(personCode, sourceAvatar) {
  if (!sourceAvatar) {
    return null;
  }

  const ext = path.extname(sourceAvatar) || '.jpg';
  return `people/${personCode}-avatar${ext}`;
}

async function loadMovieFiles() {
  const entries = await fs.readdir(moviesRoot, { withFileTypes: true });
  const files = entries.filter((entry) => entry.isFile() && entry.name.endsWith('.json')).map((entry) => entry.name).sort();

  const movies = [];
  for (const fileName of files) {
    const filePath = path.join(moviesRoot, fileName);
    const raw = await fs.readFile(filePath, 'utf8');
    movies.push(JSON.parse(raw));
  }

  return movies;
}

function collectPeople(movies) {
  const collected = new Map();

  for (const movie of movies) {
    const groups = [movie.director, movie.writer, movie.cast, movie.otherCast, movie.producer];
    for (const group of groups) {
      for (const person of group ?? []) {
        if (!person?.name) {
          continue;
        }

        const key = personKey(person);
        if (!collected.has(key)) {
          collected.set(key, {
            name: person.name,
            nameEn: person.nameEn ?? null,
            profileLink: person.baike ?? null,
            notes: person.avatarNote ?? null,
            sourceAvatar: nonEmptyString(person.avatar),
            extra: {
              avatarSource: nonEmptyString(person.avatarSource),
              works: asArray(person.works)
            }
          });
          continue;
        }

        const existing = collected.get(key);
        existing.profileLink ||= person.baike ?? null;
        existing.notes ||= person.avatarNote ?? null;
        existing.sourceAvatar ||= nonEmptyString(person.avatar);
        existing.extra.avatarSource ||= nonEmptyString(person.avatarSource);
        if (!existing.extra.works?.length && asArray(person.works).length) {
          existing.extra.works = asArray(person.works);
        }
      }
    }
  }

  return [...collected.values()];
}

function collectTerms(movies) {
  const terms = new Map();

  for (const movie of movies) {
    for (const genre of movie.genre ?? []) {
      const key = `genre||video||movie||${genre}`;
      if (!terms.has(key)) {
        terms.set(key, {
          termType: 'genre',
          name: genre,
          moduleScope: 'video',
          submoduleScope: 'movie',
          description: null
        });
      }
    }

    for (const tag of movie.tags ?? []) {
      const key = `tag||||${tag}`;
      if (!terms.has(key)) {
        terms.set(key, {
          termType: 'tag',
          name: tag,
          moduleScope: null,
          submoduleScope: null,
          description: null
        });
      }
    }
  }

  return [...terms.values()];
}

function nextPersonCode(existingPeople, newCount) {
  const codes = existingPeople
    .map((person) => person.person_code)
    .filter(Boolean)
    .map((code) => Number.parseInt(String(code).replace(/^p/, ''), 10))
    .filter((value) => Number.isFinite(value));

  let current = codes.length ? Math.max(...codes) : 0;
  const generated = [];
  for (let index = 0; index < newCount; index += 1) {
    current += 1;
    generated.push(`p${String(current).padStart(6, '0')}`);
  }
  return generated;
}

function buildPeopleUpserts(peopleInput, existingPeople) {
  const existingMap = new Map(existingPeople.map((person) => [`${person.name || ''}||${person.name_en || ''}`, person]));
  const missing = peopleInput.filter((person) => !existingMap.has(`${person.name || ''}||${person.nameEn || ''}`));
  const generatedCodes = nextPersonCode(existingPeople, missing.length);
  const definitions = [];

  let newIndex = 0;
  for (const person of peopleInput) {
    const key = `${person.name || ''}||${person.nameEn || ''}`;
    const existing = existingMap.get(key);
    const personCode = existing?.person_code ?? generatedCodes[newIndex++];
    const avatarPath = existing?.avatar_path || inferAvatarPath(personCode, person.sourceAvatar);

    definitions.push({
      personCode,
      name: person.name,
      nameEn: person.nameEn,
      avatarPath,
      profileLink: existing?.profile_link || person.profileLink,
      notes: existing?.notes || person.notes,
      extraJson: person.extra && (person.extra.avatarSource || person.extra.works?.length) ? person.extra : null
    });
  }

  const sql = definitions.map((person) => `
INSERT INTO people (person_code, name, name_en, avatar_path, profile_link, notes, extra_json)
VALUES (${sqlValue(person.personCode)}, ${sqlValue(person.name)}, ${sqlValue(person.nameEn)}, ${sqlValue(person.avatarPath)}, ${sqlValue(person.profileLink)}, ${sqlValue(person.notes)}, ${jsonValue(person.extraJson)})
ON CONFLICT(person_code) DO UPDATE SET
  name = excluded.name,
  name_en = COALESCE(excluded.name_en, people.name_en),
  avatar_path = COALESCE(people.avatar_path, excluded.avatar_path),
  profile_link = COALESCE(people.profile_link, excluded.profile_link),
  notes = COALESCE(people.notes, excluded.notes),
  extra_json = COALESCE(people.extra_json, excluded.extra_json);
`).join('\n');

  return { sql, definitions };
}

function buildTermsInsert(termsInput, existingTerms) {
  const existingKeys = new Set(existingTerms.map((term) => `${term.term_type}||${term.name}||${term.module_scope || ''}||${term.submodule_scope || ''}`));
  const missing = termsInput.filter((term) => !existingKeys.has(`${term.termType}||${term.name}||${term.moduleScope || ''}||${term.submoduleScope || ''}`));

  return missing.map((term) => `
INSERT INTO terms (term_type, name, module_scope, submodule_scope, description, sort_order, is_active)
VALUES (${sqlValue(term.termType)}, ${sqlValue(term.name)}, ${sqlValue(term.moduleScope)}, ${sqlValue(term.submoduleScope)}, ${sqlValue(term.description)}, 0, 1);
`).join('\n');
}

function buildCredits(movie, personLookup) {
  const rows = [];

  for (const person of movie.director ?? []) {
    rows.push({
      workId: movie.id,
      personId: personLookup.get(personKey(person)),
      department: 'direction',
      creditType: 'director',
      displayLabel: '导演',
      characterName: null,
      sortOrder: rows.length,
      isPrimary: 1,
      extraJson: person.avatarSource ? { avatarSource: person.avatarSource } : null
    });
  }

  for (const person of movie.writer ?? []) {
    const role = person.role ?? '编剧';
    const creditType = normalizeCreditType(role, 'writer');
    rows.push({
      workId: movie.id,
      personId: personLookup.get(personKey(person)),
      department: creditType === 'original_author' ? 'original_work' : 'writing',
      creditType,
      displayLabel: role,
      characterName: null,
      sortOrder: rows.length,
      isPrimary: 1,
      extraJson: null
    });
  }

  for (const person of movie.cast ?? []) {
    rows.push({
      workId: movie.id,
      personId: personLookup.get(personKey(person)),
      department: 'cast',
      creditType: 'actor',
      displayLabel: '主演',
      characterName: person.role ?? null,
      sortOrder: rows.length,
      isPrimary: 1,
      extraJson: person.avatarSource || person.avatarNote ? { avatarSource: person.avatarSource ?? null, avatarNote: person.avatarNote ?? null } : null
    });
  }

  for (const person of movie.otherCast ?? []) {
    rows.push({
      workId: movie.id,
      personId: personLookup.get(personKey(person)),
      department: 'cast',
      creditType: 'actor',
      displayLabel: '演员',
      characterName: person.role ?? null,
      sortOrder: rows.length,
      isPrimary: 0,
      extraJson: null
    });
  }

  for (const person of movie.producer ?? []) {
    const role = person.role ?? '制片人';
    rows.push({
      workId: movie.id,
      personId: personLookup.get(personKey(person)),
      department: 'production',
      creditType: normalizeCreditType(role, 'producer'),
      displayLabel: role,
      characterName: null,
      sortOrder: rows.length,
      isPrimary: 0,
      extraJson: null
    });
  }

  return rows.filter((row) => row.personId);
}

function buildWorkUpsert(movie) {
  const imagesJson = buildImagesJson(movie);
  const identifiersJson = buildIdentifiersJson(movie);
  const ratingsJson = buildRatingsJson(movie);
  const relationsJson = buildRelationsJson(movie);
  const linksJson = buildLinksJson(movie);
  const aliasesJson = uniqueStrings(movie.aka ?? []);
  const publishCompany = nonEmptyString(movie.publishCompany) || nonEmptyString(movie.publish_company) || nonEmptyString(movie.productionCompany);

  return `
INSERT INTO works (
  id, module, submodule, schema_type, title, original_title, year, country, language,
  publish_company, runtime_minutes, episode_count, episode_runtime_minutes,
  synopsis_text, synopsis_note, story_text,
  aliases_json, release_dates_json, identifiers_json, ratings_json, links_json,
  images_json, videos_json, reviews_json, soundtrack_json, relations_json,
  quotes_json, episode_stories_json, characters_json,
  status, created_at, updated_at
) VALUES (
  ${sqlValue(movie.id)},
  'video',
  'movie',
  'live_action_movie',
  ${sqlValue(movie.title)},
  ${sqlValue(movie.originalTitle ?? null)},
  ${sqlValue(movie.year ?? null)},
  ${sqlValue(inferPrimaryCountry(movie))},
  ${sqlValue(movie.language ?? null)},
  ${sqlValue(publishCompany)},
  ${sqlValue(movie.runtime ?? null)},
  NULL,
  NULL,
  ${sqlValue(movie.synopsis?.text ?? null)},
  ${sqlValue(movie.synopsis?.note ?? null)},
  ${sqlValue(movie.story?.text ?? null)},
  ${jsonValue(aliasesJson)},
  ${jsonValue(asArray(movie.releaseDate))},
  ${jsonValue(identifiersJson)},
  ${jsonValue(ratingsJson)},
  ${jsonValue(linksJson)},
  ${jsonValue(imagesJson)},
  ${jsonValue(asArray(movie.videos))},
  ${jsonValue(buildReviewsJson(movie))},
  ${jsonValue(buildSoundtrackJson(movie))},
  ${jsonValue(relationsJson)},
  ${jsonValue(asArray(movie.quotes))},
  NULL,
  NULL,
  ${sqlValue(movie.status ?? 'published')},
  ${sqlValue(movie.createdAt ?? null)},
  ${sqlValue(movie.updatedAt ?? null)}
)
ON CONFLICT(id) DO UPDATE SET
  module = excluded.module,
  submodule = excluded.submodule,
  schema_type = excluded.schema_type,
  title = excluded.title,
  original_title = excluded.original_title,
  year = excluded.year,
  country = excluded.country,
  language = excluded.language,
  publish_company = excluded.publish_company,
  runtime_minutes = excluded.runtime_minutes,
  synopsis_text = excluded.synopsis_text,
  synopsis_note = excluded.synopsis_note,
  story_text = excluded.story_text,
  aliases_json = excluded.aliases_json,
  release_dates_json = excluded.release_dates_json,
  identifiers_json = excluded.identifiers_json,
  ratings_json = excluded.ratings_json,
  links_json = excluded.links_json,
  images_json = excluded.images_json,
  videos_json = excluded.videos_json,
  reviews_json = excluded.reviews_json,
  soundtrack_json = excluded.soundtrack_json,
  relations_json = excluded.relations_json,
  quotes_json = excluded.quotes_json,
  status = excluded.status,
  created_at = COALESCE(excluded.created_at, works.created_at),
  updated_at = COALESCE(excluded.updated_at, works.updated_at);
`;
}

function buildTermReferences(movie) {
  const refs = [];

  for (const genre of movie.genre ?? []) {
    refs.push({ key: `genre||${genre}||video||movie`, sortOrder: refs.length });
  }

  for (const tag of movie.tags ?? []) {
    refs.push({ key: `tag||${tag}||||`, sortOrder: refs.length });
  }

  return refs;
}

function collectMissingFields(movie) {
  const missing = [];
  if (!nonEmptyString(movie.originalTitle)) missing.push('originalTitle');
  if (!asArray(movie.genre).length) missing.push('genre');
  if (!nonEmptyString(movie.country)) missing.push('country');
  if (typeof movie.runtime !== 'number') missing.push('runtime');
  if (!nonEmptyString(movie.imdbId)) missing.push('imdbId');
  if (!nonEmptyString(movie.doubanId)) missing.push('doubanId');
  if (!asArray(movie.director).length) missing.push('director');
  if (!asArray(movie.cast).length) missing.push('cast');
  if (!nonEmptyString(movie.synopsis?.text)) missing.push('synopsis.text');
  if (!nonEmptyString(movie.story?.text)) missing.push('story.text');
  return missing;
}

function collectWarnings(movie) {
  const warnings = [];
  const reviewCoverage = asArray(movie.reviews).reduce((acc, review) => {
    acc.total += 1;
    if (review?.source === '豆瓣长评') acc.doubanLong += 1;
    else if (review?.source === '豆瓣短评') acc.doubanShort += 1;
    else if (review?.source === 'TMDB') acc.tmdb += 1;
    else if (typeof review?.source === 'string' && review.source.startsWith('烂番茄')) acc.rottenTomatoes += 1;
    return acc;
  }, { total: 0, doubanLong: 0, doubanShort: 0, tmdb: 0, rottenTomatoes: 0 });

  if (typeof movie.runtime === 'number' && (movie.runtime < 60 || movie.runtime > 300)) {
    warnings.push(`runtime异常: ${movie.runtime}`);
  }
  if (!nonEmptyString(movie.images?.poster)) warnings.push('主海报缺失');
  if (!asArray(movie.reviews).length) warnings.push('reviews 为空');
  if (movie.status === 'published' && (reviewCoverage.total < 40 || reviewCoverage.doubanLong < 10 || reviewCoverage.doubanShort < 10 || reviewCoverage.tmdb < 10 || reviewCoverage.rottenTomatoes < 10)) {
    warnings.push(`reviews 未达到高标准基线(total=${reviewCoverage.total}, doubanLong=${reviewCoverage.doubanLong}, doubanShort=${reviewCoverage.doubanShort}, tmdb=${reviewCoverage.tmdb}, rottenTomatoes=${reviewCoverage.rottenTomatoes})`);
  }
  return warnings;
}

function buildMovieSummary(movie) {
  const allPeople = [...asArray(movie.director), ...asArray(movie.writer), ...asArray(movie.cast), ...asArray(movie.otherCast), ...asArray(movie.producer)];
  const peopleWithAvatar = allPeople.filter((person) => nonEmptyString(person.avatar)).length;
  const peopleMissingAvatar = allPeople.filter((person) => !nonEmptyString(person.avatar)).length;
  const links = buildLinksJson(movie);
  const reviewCoverage = asArray(movie.reviews).reduce((acc, review) => {
    acc.total += 1;
    if (review?.source === '豆瓣长评') acc.doubanLong += 1;
    else if (review?.source === '豆瓣短评') acc.doubanShort += 1;
    else if (review?.source === 'TMDB') acc.tmdb += 1;
    else if (typeof review?.source === 'string' && review.source.startsWith('烂番茄')) acc.rottenTomatoes += 1;
    return acc;
  }, { total: 0, doubanLong: 0, doubanShort: 0, tmdb: 0, rottenTomatoes: 0 });

  return {
    id: movie.id,
    title: movie.title,
    module: 'video',
    submodule: 'movie',
    schemaType: 'live_action_movie',
    status: movie.status ?? 'published',
    sourceFiles: {
      stagingData: path.relative(repoRoot, path.join(moviesRoot, `${movie.id}.json`)).replace(/\\/g, '/'),
      workAssetDir: `site/public/assets/video/movie/${movie.id}/`
    },
    sources: Object.entries(links).filter(([, value]) => Boolean(value)).map(([name, url]) => ({ name, url })),
    assets: {
      poster: nonEmptyString(movie.images?.poster),
      posters: asArray(movie.images?.posters).length,
      stills: asArray(movie.images?.stills).length,
      wallpapers: asArray(movie.images?.wallpapers).length,
      peopleWithAvatar,
      peopleMissingAvatar
    },
    reviewCoverage,
    missingFields: collectMissingFields(movie),
    warnings: collectWarnings(movie),
    retryHints: [
      !nonEmptyString(movie.rated) ? 'rated 可在 OMDb / IMDb 补齐' : null,
      !nonEmptyString(movie.awards) ? 'awards 可在 OMDb / IMDb 补齐' : null,
      peopleMissingAvatar > 0 ? '缺失头像的人物可后续补传到 site/public/assets/people/' : null
    ].filter(Boolean)
  };
}

async function writeImportSummary({ movies, counts }) {
  await fs.mkdir(path.dirname(summaryPath), { recursive: true });
  const payload = {
    version: 1,
    generatedAt: new Date().toISOString(),
    dbPath: path.relative(repoRoot, dbPath).replace(/\\/g, '/'),
    summaryType: 'movie_import',
    importedWorks: movies.length,
    counts,
    works: movies.map(buildMovieSummary)
  };

  await fs.writeFile(summaryPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

async function main() {
  const movies = await loadMovieFiles();
  if (!movies.length) {
    console.log('No movie records found.');
    return;
  }

  ensureWorksSchema();

  const existingPeople = queryJson('SELECT id, person_code, name, name_en, avatar_path, profile_link, notes FROM people;');
  const peopleInput = collectPeople(movies);
  const { sql: peopleSql } = buildPeopleUpserts(peopleInput, existingPeople);
  if (peopleSql.trim()) {
    runSql(`BEGIN;\n${peopleSql}\nCOMMIT;`);
  }

  const currentPeople = queryJson('SELECT id, person_code, name, name_en FROM people;');
  const personLookup = new Map(currentPeople.map((person) => [`${person.name || ''}||${person.name_en || ''}`, person.id]));

  const existingTerms = queryJson('SELECT id, term_type, name, module_scope, submodule_scope FROM terms;');
  const termsSql = buildTermsInsert(collectTerms(movies), existingTerms);
  if (termsSql.trim()) {
    runSql(`BEGIN;\n${termsSql}\nCOMMIT;`);
  }

  const currentTerms = queryJson('SELECT id, term_type, name, module_scope, submodule_scope FROM terms;');
  const termLookup = new Map(currentTerms.map((term) => [`${term.term_type}||${term.name}||${term.module_scope || ''}||${term.submodule_scope || ''}`, term.id]));

  let sql = 'BEGIN;\n';

  for (const movie of movies) {
    sql += `DELETE FROM work_credits WHERE work_id = ${sqlValue(movie.id)};\n`;
    sql += `DELETE FROM work_terms WHERE work_id = ${sqlValue(movie.id)};\n`;
    sql += buildWorkUpsert(movie);

    const credits = buildCredits(movie, personLookup);
    for (const credit of credits) {
      sql += `
INSERT INTO work_credits (
  work_id, person_id, department, credit_type, display_label, character_name,
  sort_order, is_primary, link_override, extra_json
) VALUES (
  ${sqlValue(credit.workId)},
  ${sqlValue(credit.personId)},
  ${sqlValue(credit.department)},
  ${sqlValue(credit.creditType)},
  ${sqlValue(credit.displayLabel)},
  ${sqlValue(credit.characterName)},
  ${sqlValue(credit.sortOrder)},
  ${sqlValue(credit.isPrimary)},
  NULL,
  ${jsonValue(credit.extraJson)}
);
`;
    }

    for (const termRef of buildTermReferences(movie)) {
      const termId = termLookup.get(termRef.key);
      if (!termId) {
        continue;
      }

      sql += `INSERT INTO work_terms (work_id, term_id, sort_order, note) VALUES (${sqlValue(movie.id)}, ${sqlValue(termId)}, ${sqlValue(termRef.sortOrder)}, NULL);\n`;
    }
  }

  sql += 'COMMIT;\n';
  runSql(sql);

  const counts = queryJson(`
SELECT
  (SELECT COUNT(*) FROM works) AS works_count,
  (SELECT COUNT(*) FROM people) AS people_count,
  (SELECT COUNT(*) FROM work_credits) AS credits_count,
  (SELECT COUNT(*) FROM terms) AS terms_count,
  (SELECT COUNT(*) FROM work_terms) AS work_terms_count;
`)[0];

  await writeImportSummary({ movies, counts });

  console.log(`Imported ${movies.length} movies into ${dbPath}`);
  console.log(`works=${counts.works_count}, people=${counts.people_count}, work_credits=${counts.credits_count}, terms=${counts.terms_count}, work_terms=${counts.work_terms_count}`);
  console.log(`summary=${summaryPath}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
