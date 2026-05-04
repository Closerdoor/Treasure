import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..');
const dbPath = path.join(repoRoot, '.local', 'treasure.db');
const generatedRoot = path.join(repoRoot, 'generated');
const generatedModulesRoot = path.join(generatedRoot, 'modules');
const sqlitePath = process.env.SQLITE3_PATH || 'D:\\ArtSoftware\\sqlite3.exe';

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

function parseJsonText(text, fallback) {
  if (!text) {
    return fallback;
  }

  try {
    return JSON.parse(text);
  } catch {
    return fallback;
  }
}

function formatEntryPath(entry) {
  return `/${entry.module}/${entry.submodule}/${entry.id}`;
}

function normalizePerson(row) {
  const extra = parseJsonText(row.extra_json, null) ?? {};

  return {
    personCode: row.person_code,
    name: row.name,
    nameEn: row.name_en ?? undefined,
    role: row.department === 'cast' ? row.character_name ?? undefined : row.display_label ?? undefined,
    avatarPath: row.avatar_path ?? undefined,
    profileLink: row.profile_link ?? undefined,
    notes: row.notes ?? undefined,
    avatarSource: extra.avatarSource ?? undefined,
    avatarNote: extra.avatarNote ?? undefined,
    works: Array.isArray(extra.works) ? extra.works : undefined
  };
}

function indexCredits(creditRows) {
  const byWorkId = new Map();

  for (const row of creditRows) {
    if (!byWorkId.has(row.work_id)) {
      byWorkId.set(row.work_id, { director: [], writer: [], cast: [], otherCast: [], producer: [] });
    }

    const target = byWorkId.get(row.work_id);
    const person = normalizePerson(row);

    if (row.department === 'direction') {
      target.director.push(person);
    } else if (row.department === 'writing' || row.department === 'original_work') {
      target.writer.push(person);
    } else if (row.department === 'cast') {
      if (row.is_primary) {
        target.cast.push(person);
      } else {
        target.otherCast.push(person);
      }
    } else if (row.department === 'production') {
      target.producer.push(person);
    }
  }

  return byWorkId;
}

function indexTerms(termRows) {
  const byWorkId = new Map();

  for (const row of termRows) {
    if (!byWorkId.has(row.work_id)) {
      byWorkId.set(row.work_id, { genre: [], tags: [] });
    }

    const target = byWorkId.get(row.work_id);
    if (row.term_type === 'genre') {
      target.genre.push(row.name);
    } else if (row.term_type === 'tag') {
      target.tags.push(row.name);
    }
  }

  return byWorkId;
}

function buildEntry(row, credits, terms) {
  const aliases = parseJsonText(row.aliases_json, []);
  const releaseDate = parseJsonText(row.release_dates_json, []);
  const identifiers = parseJsonText(row.identifiers_json, {});
  const ratings = parseJsonText(row.ratings_json, {});
  const links = parseJsonText(row.links_json, {});
  const images = parseJsonText(row.images_json, {});
  const videos = parseJsonText(row.videos_json, []);
  const reviews = parseJsonText(row.reviews_json, []);
  const soundtrack = parseJsonText(row.soundtrack_json, null);
  const relations = parseJsonText(row.relations_json, {});
  const quotes = parseJsonText(row.quotes_json, []);

  return {
    id: row.id,
    module: row.module,
    submodule: row.submodule,
    schemaType: row.schema_type,
    path: formatEntryPath(row),
    title: row.title,
    originalTitle: row.original_title ?? undefined,
    year: row.year,
    country: row.country ?? undefined,
    language: row.language ?? undefined,
    publishCompany: row.publish_company ?? undefined,
    runtime: row.runtime_minutes ?? undefined,
    synopsis: { text: row.synopsis_text ?? undefined, note: row.synopsis_note ?? undefined },
    story: { text: row.story_text ?? undefined },
    director: credits.director,
    writer: credits.writer,
    cast: credits.cast,
    otherCast: credits.otherCast,
    producer: credits.producer,
    genre: terms.genre,
    tags: terms.tags,
    aka: aliases,
    releaseDate,
    imdbId: identifiers.imdb ?? undefined,
    doubanId: identifiers.douban ?? undefined,
    tmdbId: identifiers.tmdb ?? undefined,
    doubanRating: ratings.douban?.value ?? undefined,
    imdbRating: ratings.imdb?.value ?? undefined,
    tmdbRating: ratings.tmdb?.value ?? undefined,
    rottenTomatoes: ratings.rottenTomatoes?.value ?? undefined,
    metascore: ratings.metascore?.value ?? undefined,
    rated: ratings.certification?.value ?? undefined,
    awards: ratings.awards?.value ?? undefined,
    images,
    videos,
    reviews,
    soundtrack,
    series: Array.isArray(relations.series) ? relations.series : [],
    similar: Array.isArray(relations.similar) ? relations.similar : [],
    links,
    quotes,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    status: row.status
  };
}

function buildSearchIndex(entries) {
  return entries.map((entry) => ({
    id: entry.id,
    path: entry.path,
    title: entry.title,
    originalTitle: entry.originalTitle ?? null,
    year: entry.year ?? null,
    module: entry.module,
    submodule: entry.submodule,
    country: entry.country ?? null,
    genre: entry.genre ?? [],
    tags: entry.tags ?? [],
    aka: entry.aka ?? [],
    cast: (entry.cast ?? []).map((person) => person.name),
    synopsis: entry.synopsis?.text ?? null
  }));
}

function buildRecent(entries) {
  return [...entries]
    .sort((left, right) => String(right.updatedAt ?? '').localeCompare(String(left.updatedAt ?? '')) || left.id.localeCompare(right.id))
    .slice(0, 12);
}

async function writeJson(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

async function main() {
  const works = queryJson(`
SELECT *
FROM works
WHERE module = 'video' AND submodule = 'movie' AND status != 'archived'
ORDER BY year DESC, id ASC;
`);

  const credits = queryJson(`
SELECT
  wc.work_id,
  wc.department,
  wc.display_label,
  wc.character_name,
  wc.sort_order,
  wc.is_primary,
  wc.extra_json,
  p.person_code,
  p.name,
  p.name_en,
  p.avatar_path,
  p.profile_link,
  p.notes
FROM work_credits wc
JOIN people p ON p.id = wc.person_id
ORDER BY wc.work_id, wc.sort_order, wc.id;
`);

  const terms = queryJson(`
SELECT
  wt.work_id,
  t.term_type,
  t.name,
  wt.sort_order,
  wt.note
FROM work_terms wt
JOIN terms t ON t.id = wt.term_id
ORDER BY wt.work_id, t.term_type, wt.sort_order, wt.id;
`);

  const creditIndex = indexCredits(credits);
  const termIndex = indexTerms(terms);

  const entries = works.map((row) => buildEntry(
    row,
    creditIndex.get(row.id) ?? { director: [], writer: [], cast: [], otherCast: [], producer: [] },
    termIndex.get(row.id) ?? { genre: [], tags: [] }
  ));

  const videoEntries = entries.filter((entry) => entry.module === 'video');
  const movieEntries = videoEntries.filter((entry) => entry.submodule === 'movie');
  const tagsPayload = {
    genres: [...new Set(movieEntries.flatMap((entry) => entry.genre ?? []))].sort(),
    tags: [...new Set(movieEntries.flatMap((entry) => entry.tags ?? []))].sort()
  };

  await writeJson(path.join(generatedRoot, 'entries.json'), entries);
  await writeJson(path.join(generatedModulesRoot, 'video.json'), videoEntries);
  await writeJson(path.join(generatedModulesRoot, 'video-movie.json'), movieEntries);
  await writeJson(path.join(generatedRoot, 'tags.json'), tagsPayload);
  await writeJson(path.join(generatedRoot, 'search-index.json'), buildSearchIndex(entries));
  await writeJson(path.join(generatedRoot, 'recent.json'), buildRecent(entries));

  console.log(`Exported ${entries.length} entries to ${generatedRoot}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
