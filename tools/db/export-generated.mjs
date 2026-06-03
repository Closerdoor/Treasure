import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..');
const dbPath = path.join('.local', 'treasure.db');
const generatedRoot = path.join(repoRoot, 'generated');
const entriesRoot = path.join(generatedRoot, 'entries');
const indexesRoot = path.join(generatedRoot, 'indexes');
const localAssetsRoot = path.join(repoRoot, '.local', 'assets');
const siteAssetsRoot = path.join(repoRoot, 'site', 'public', 'assets');
const sqlitePath = process.env.SQLITE3_PATH || 'D:\\ArtSoftware\\sqlite3.exe';

function queryJson(sql) {
  const result = spawnSync(sqlitePath, ['-json', dbPath, sql], {
    encoding: 'utf8',
    cwd: repoRoot,
    shell: false,
    maxBuffer: 200 * 1024 * 1024
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
  return entry.submodule
    ? `/${entry.module}/${entry.submodule}/${entry.id}`
    : `/${entry.module}/${entry.id}`;
}

function nonEmptyString(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function asStringArray(value) {
  return Array.isArray(value) ? value.map(nonEmptyString).filter(Boolean) : [];
}

function asWebUrl(value) {
  const url = nonEmptyString(value);
  return url && /^https?:\/\//i.test(url) ? url : null;
}

function hasCjk(value) {
  return typeof value === 'string' && /[\u4e00-\u9fff]/.test(value);
}

function buildBaikeUrl(title, id) {
  const cleanTitle = nonEmptyString(title);
  const cleanId = nonEmptyString(id);

  if (!cleanTitle || !cleanId) {
    return null;
  }

  return `https://baike.baidu.com/item/${encodeURIComponent(cleanTitle)}/${encodeURIComponent(cleanId)}`;
}

function normalizePerson(row) {
  return {
    personCode: row.person_id,
    name: row.name,
    nameEn: row.name_en ?? undefined,
    role: row.department === 'cast' ? row.character ?? undefined : row.role ?? undefined,
    avatarPath: row.avatar_path ?? undefined,
    profileLink: row.profile_link ?? undefined,
    notes: row.intro ?? undefined
  };
}

function normalizeBookPerson(row) {
  const roleLabels = {
    author: '作者',
    translator: '译者'
  };

  return {
    personCode: row.person_id,
    name: row.name,
    nameEn: row.name_en ?? undefined,
    role: roleLabels[row.role] ?? row.role ?? undefined,
    avatarPath: row.avatar_path ?? undefined,
    profileLink: row.profile_link ?? undefined,
    notes: row.intro ?? undefined
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

function indexCategories(categoryRows) {
  const byWorkId = new Map();

  for (const row of categoryRows) {
    if (!byWorkId.has(row.work_id)) {
      byWorkId.set(row.work_id, { genre: [], tags: [] });
    }

    const target = byWorkId.get(row.work_id);
    if (row.group === 'type') {
      target.genre.push(row.name);
    } else if (row.group === 'tag') {
      target.tags.push(row.name);
    }
  }

  return byWorkId;
}

function indexBookPeople(personRows) {
  const byBookId = new Map();

  for (const row of personRows) {
    if (!byBookId.has(row.book_id)) {
      byBookId.set(row.book_id, { authors: [], translators: [] });
    }

    const target = byBookId.get(row.book_id);
    const person = normalizeBookPerson(row);

    if (row.role === 'translator') {
      target.translators.push(person);
    } else {
      target.authors.push(person);
    }
  }

  return byBookId;
}

function indexBookCategories(categoryRows) {
  const byBookId = new Map();

  for (const row of categoryRows) {
    if (!byBookId.has(row.book_id)) {
      byBookId.set(row.book_id, { genre: [], tags: [] });
    }

    const target = byBookId.get(row.book_id);
    if (row.group === 'type') {
      if (hasCjk(row.name)) {
        target.genre.push(row.name);
      }
    } else if (hasCjk(row.name)) {
      target.tags.push(row.name);
    }
  }

  return byBookId;
}

function buildEntry(row, credits, categories) {
  const otherTitles = parseJsonText(row.other_titles, []);
  const releaseDate = parseJsonText(row.release_dates, []);
  const scores = parseJsonText(row.scores, {});
  const externalSource = parseJsonText(row.external_source, []);
  const images = normalizeImages(parseJsonText(row.images, {}));
  const videos = normalizeVideos(parseJsonText(row.videos, []));
  const reviews = parseJsonText(row.comments, []);
  const soundtrack = parseJsonText(row.soundtrack, null);
  const relations = parseJsonText(row.related, {});
  const quotes = parseJsonText(row.quotes, []);

  const links = {};
  externalSource.forEach((src) => {
    if (src.name === '豆瓣') links.douban = src.link;
    else if (src.name === 'IMDb') links.imdb = src.link;
    else if (src.name === 'TMDB') links.tmdb = src.link;
    else if (src.name === '百度百科') links.baike = src.link;
    else if (src.name === '维基百科') links.wikipedia = src.link;
  });

  const identifiers = {};
  externalSource.forEach((src) => {
    if (src.name === '豆瓣') identifiers.douban = src.id;
    else if (src.name === 'IMDb') identifiers.imdb = src.id;
    else if (src.name === 'TMDB') identifiers.tmdb = src.id;
  });

  return {
    id: row.id,
    module: row.module,
    submodule: row.submodule,
    schemaType: row.schema_type,
    path: formatEntryPath(row),
    title: row.title,
    originalTitle: row.title_original ?? undefined,
    year: row.year,
    country: row.country ?? undefined,
    language: row.language ?? undefined,
    publishCompany: row.studio ?? undefined,
    runtime: row.total_time ?? undefined,
    synopsis: { text: row.introduction ?? undefined, note: undefined },
    story: { text: row.story ?? undefined },
    director: credits.director,
    writer: credits.writer,
    cast: credits.cast,
    otherCast: credits.otherCast,
    producer: credits.producer,
    genre: categories.genre,
    tags: categories.tags,
    aka: otherTitles,
    releaseDate,
    imdbId: identifiers.imdb ?? undefined,
    doubanId: identifiers.douban ?? undefined,
    tmdbId: identifiers.tmdb ?? undefined,
    doubanRating: scores.douban ?? undefined,
    imdbRating: scores.imdb ?? undefined,
    tmdbRating: scores.tmdb ?? undefined,
    rottenTomatoes: scores.rottenTomatoes ?? undefined,
    metascore: scores.metacritic ?? undefined,
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

function buildBookEntry(row, people, categories, seriesRow) {
  const otherTitles = parseJsonText(row.other_titles, []);
  const scores = parseJsonText(row.scores, {});
  const externalSource = parseJsonText(row.external_source, []);
  const images = normalizeBookImages(parseJsonText(row.images, {}));
  const reviews = parseJsonText(row.reviews, []);
  const relations = parseJsonText(row.related, {});
  const quotes = parseJsonText(row.quotes, []);
  const excerpts = parseJsonText(row.excerpts, []);

  const links = {};
  externalSource.forEach((src) => {
    const sourceName = String(src.name ?? '');
    const key = sourceName.toLowerCase();
    const link = asWebUrl(src.link);

    if (sourceName === '豆瓣' || key.includes('douban')) {
      if (link) links.douban = link;
    } else if (sourceName === '百度百科' || key.includes('baike')) {
      const baikeLink = link ?? buildBaikeUrl(row.title, src.id);
      if (baikeLink) links.baike = baikeLink;
    } else if (sourceName === 'Wikipedia' || sourceName === '维基百科' || key.includes('wikipedia')) {
      if (link) links.wikipedia = link;
    } else if (sourceName === 'OpenLibrary' || key.includes('openlibrary')) {
      if (link) links.openlibrary = link;
    } else if (sourceName === 'Goodreads' || key.includes('goodreads')) {
      if (link) links.goodreads = link;
    } else if (sourceName.includes('当当') || key.includes('dangdang')) {
      if (link) links.dangdang = link;
    } else if (sourceName.includes('起点') || key.includes('qidian')) {
      if (link) links.qidian = link;
    }
  });

  return {
    id: row.id,
    module: 'book',
    submodule: null,
    schemaType: 'book',
    path: `/book/${row.id}`,
    title: row.title,
    originalTitle: row.title_original ?? undefined,
    otherTitles,
    isbn: row.isbn ?? undefined,
    year: row.year ?? undefined,
    country: row.country ?? undefined,
    language: row.language ?? undefined,
    wordCount: row.word_count ?? undefined,
    publisher: row.publisher ?? undefined,
    publishDate: row.publish_date ?? undefined,
    pages: row.pages ?? undefined,
    price: row.price ?? undefined,
    binding: row.binding ?? undefined,
    format: row.format ?? undefined,
    edition: row.edition ?? undefined,
    synopsis: { text: row.summary ?? undefined, note: undefined },
    story: { text: row.story ?? undefined },
    authors: people.authors,
    translators: people.translators,
    genre: categories.genre,
    tags: categories.tags,
    scores,
    doubanRating: scores.douban ?? scores.avg ?? undefined,
    goodreadsRating: scores.goodreads ?? undefined,
    openlibraryRating: scores.openlibrary ?? undefined,
    images,
    reviews,
    quotes,
    excerpts,
    series: seriesRow ? {
      id: seriesRow.id,
      title: seriesRow.name,
      order: row.series_order ?? undefined
    } : null,
    similar: Array.isArray(relations.similar) ? relations.similar : [],
    sameAuthor: Array.isArray(relations.sameAuthor) ? relations.sameAuthor : [],
    links,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    status: row.status
  };
}

function normalizeImages(images) {
  return {
    poster: nonEmptyString(images?.poster) ?? undefined,
    covers: images?.covers && typeof images.covers === 'object' ? images.covers : undefined,
    posters: asStringArray(images?.posters),
    stills: asStringArray(images?.stills),
    wallpapers: asStringArray(images?.wallpapers)
  };
}

function normalizeBookImages(images) {
  let covers = {};

  if (Array.isArray(images?.covers)) {
    covers = Object.fromEntries(
      images.covers
        .map((file, index) => [`cover${index + 1}`, file])
        .filter(([, file]) => nonEmptyString(file))
    );
  } else if (images?.covers && typeof images.covers === 'object') {
    covers = images.covers;
  }

  return {
    cover: nonEmptyString(images?.cover) ?? undefined,
    covers,
    assetDir: nonEmptyString(images?.assetDir) ?? undefined
  };
}

function normalizeVideos(videos) {
  if (!Array.isArray(videos)) {
    return [];
  }

  return videos.map((video) => ({
    ...video,
    thumbnail: nonEmptyString(video?.thumbnail) ?? undefined
  }));
}

function computeAggregateRating(entry) {
  const values = [entry.doubanRating, entry.imdbRating, entry.tmdbRating];

  if (typeof entry.rottenTomatoes === 'number') {
    values.push(entry.rottenTomatoes / 10);
  }

  const valid = values.filter((value) => typeof value === 'number' && Number.isFinite(value));

  if (valid.length === 0) {
    return null;
  }

  const average = valid.reduce((sum, value) => sum + value, 0) / valid.length;
  return Math.round(average * 10) / 10;
}

function computeBookAggregateRating(entry) {
  const values = [
    entry.scores?.douban,
    entry.scores?.goodreads,
    entry.scores?.openlibrary,
    entry.scores?.avg,
    entry.doubanRating,
    entry.goodreadsRating,
    entry.openlibraryRating
  ];

  const valid = values.filter((value) => typeof value === 'number' && Number.isFinite(value));

  if (valid.length === 0) {
    return null;
  }

  const average = valid.reduce((sum, value) => sum + value, 0) / valid.length;
  return Math.round(average * 10) / 10;
}

function buildListIndex(entry) {
  const poster = entry.images?.poster;
  const posterUrl = poster
    ? `/assets/${entry.module}/${entry.submodule}/${entry.id}/${poster}`
    : '/assets/poster-placeholder.svg';

  return {
    id: entry.id,
    path: entry.path,
    title: entry.title,
    originalTitle: entry.originalTitle ?? null,
    year: entry.year,
    posterUrl,
    aggregateRating: computeAggregateRating(entry),
    directorNames: (entry.director ?? []).map((p) => p.name).join(' / ') || null,
    castPreview: (entry.cast ?? []).slice(0, 3).map((p) => p.name),
    genre: entry.genre ?? [],
    tags: entry.tags ?? [],
    country: entry.country ?? null,
    synopsis: entry.synopsis?.text ?? null
  };
}

function buildBookListIndex(entry) {
  const cover = entry.images?.cover;
  const coverUrl = cover
    ? `/assets/book/${entry.id}/${cover}`
    : '/assets/poster-placeholder.svg';

  return {
    id: entry.id,
    path: entry.path,
    title: entry.title,
    originalTitle: entry.originalTitle ?? null,
    year: entry.year ?? null,
    coverUrl,
    aggregateRating: computeBookAggregateRating(entry),
    authorNames: (entry.authors ?? []).map((p) => p.name).join(' / ') || null,
    translatorNames: (entry.translators ?? []).map((p) => p.name).join(' / ') || null,
    genre: entry.genre ?? [],
    tags: entry.tags ?? [],
    publisher: entry.publisher ?? null,
    publishDate: entry.publishDate ?? null,
    pages: entry.pages ?? null,
    binding: entry.binding ?? null,
    synopsis: entry.synopsis?.text ?? null
  };
}

function buildSearchIndex(entry) {
  return {
    id: entry.id,
    path: entry.path,
    title: entry.title,
    originalTitle: entry.originalTitle ?? null,
    year: entry.year ?? null,
    module: entry.module,
    submodule: entry.submodule ?? null,
    country: entry.country ?? null,
    genre: entry.genre ?? [],
    tags: entry.tags ?? [],
    aka: entry.aka ?? entry.otherTitles ?? [],
    cast: (entry.cast ?? entry.authors ?? []).map((person) => person.name),
    synopsis: entry.synopsis?.text ?? null
  };
}

function buildRecentIndex(entries, limit = 12) {
  return [...entries]
    .sort((left, right) => String(right.updatedAt ?? '').localeCompare(String(left.updatedAt ?? '')) || left.id.localeCompare(right.id))
    .slice(0, limit)
    .map((entry) => entry.module === 'book' ? buildBookListIndex(entry) : buildListIndex(entry));
}

async function writeJson(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

async function cleanDirectory(dirPath) {
  try {
    await fs.rm(dirPath, { recursive: true, force: true });
  } catch {
    // 目录不存在则忽略
  }
  await fs.mkdir(dirPath, { recursive: true });
}

function toLocalAssetPath(relativePath) {
  const normalized = nonEmptyString(relativePath)?.replace(/\\/g, '/');
  if (!normalized) {
    return null;
  }

  const withoutLocalPrefix = normalized.replace(/^\.local\/assets\//, '');
  return path.join(localAssetsRoot, ...withoutLocalPrefix.split('/'));
}

async function copyAssetIfExists(sourcePath, destPath) {
  if (!sourcePath) {
    return false;
  }

  try {
    const stat = await fs.stat(sourcePath);
    if (!stat.isFile()) {
      return false;
    }
    await fs.mkdir(path.dirname(destPath), { recursive: true });
    await fs.copyFile(sourcePath, destPath);
    return true;
  } catch {
    return false;
  }
}

async function findSingleBookAvatar(sourceWorkDir, entry) {
  if (entry.module !== 'book' || (entry.authors ?? []).length !== 1) {
    return null;
  }

  try {
    const peopleDir = path.join(sourceWorkDir, 'people');
    const files = await fs.readdir(peopleDir);
    const imageFiles = files.filter((file) => /\.(jpe?g|png|webp|avif)$/i.test(file));
    return imageFiles.length === 1 ? path.join(peopleDir, imageFiles[0]) : null;
  } catch {
    return null;
  }
}

function eachCreditPerson(entry) {
  return [
    ...(entry.director ?? []),
    ...(entry.writer ?? []),
    ...(entry.cast ?? []),
    ...(entry.otherCast ?? []),
    ...(entry.producer ?? []),
    ...(entry.authors ?? []),
    ...(entry.translators ?? [])
  ];
}

async function exportEntryAssets(entry) {
  const exportedEntry = structuredClone(entry);
  const baseRelativeDir = entry.submodule
    ? `${entry.module}/${entry.submodule}/${entry.id}`
    : `${entry.module}/${entry.id}`;
  const sourceWorkDir = entry.submodule
    ? path.join(localAssetsRoot, entry.module, entry.submodule, entry.id)
    : path.join(localAssetsRoot, entry.module, entry.id);
  const destWorkDir = entry.submodule
    ? path.join(siteAssetsRoot, entry.module, entry.submodule, entry.id)
    : path.join(siteAssetsRoot, entry.module, entry.id);
  const stats = {
    workAssetsCopied: 0,
    workAssetsMissing: 0,
    avatarsCopied: 0,
    avatarsMissing: 0
  };

  const workFiles = [
    exportedEntry.images?.poster,
    exportedEntry.images?.cover,
    ...asStringArray(Object.values(exportedEntry.images?.covers ?? {})),
    ...asStringArray(exportedEntry.images?.posters),
    ...asStringArray(exportedEntry.images?.stills),
    ...asStringArray(exportedEntry.images?.wallpapers),
    ...asStringArray((exportedEntry.videos ?? []).map((video) => video.thumbnail))
  ];

  for (const file of [...new Set(workFiles.map(nonEmptyString).filter(Boolean))]) {
    const copied = await copyAssetIfExists(
      path.join(sourceWorkDir, file),
      path.join(destWorkDir, file)
    );
    if (copied) {
      stats.workAssetsCopied += 1;
    } else {
      stats.workAssetsMissing += 1;
    }
  }

  for (const person of eachCreditPerson(exportedEntry)) {
    const sourceAvatar = toLocalAssetPath(person.avatarPath)
      ?? await findSingleBookAvatar(sourceWorkDir, exportedEntry);
    const avatarFile = sourceAvatar ? path.basename(sourceAvatar) : null;
    if (!sourceAvatar || !avatarFile) {
      continue;
    }

    const localAvatarPath = `people/${avatarFile}`;
    const copied = await copyAssetIfExists(
      sourceAvatar,
      path.join(destWorkDir, localAvatarPath)
    );

    if (copied) {
      person.avatarPath = `${baseRelativeDir}/${localAvatarPath}`;
      stats.avatarsCopied += 1;
    } else {
      delete person.avatarPath;
      stats.avatarsMissing += 1;
    }
  }

  return { entry: exportedEntry, stats };
}

async function exportAssetsForEntries(entries) {
  console.log('导出静态资源...');
  const videoMovieAssetsRoot = path.join(siteAssetsRoot, 'video', 'movie');
  const bookAssetsRoot = path.join(siteAssetsRoot, 'book');
  const sharedPeopleRoot = path.join(siteAssetsRoot, 'people');
  await cleanDirectory(videoMovieAssetsRoot);
  await cleanDirectory(bookAssetsRoot);
  await fs.rm(sharedPeopleRoot, { recursive: true, force: true });

  const exportedEntries = [];
  const totals = {
    workAssetsCopied: 0,
    workAssetsMissing: 0,
    avatarsCopied: 0,
    avatarsMissing: 0
  };

  for (const entry of entries) {
    const exported = await exportEntryAssets(entry);
    exportedEntries.push(exported.entry);
    for (const key of Object.keys(totals)) {
      totals[key] += exported.stats[key];
    }
  }

  console.log(`  作品资源: copied=${totals.workAssetsCopied}, missing=${totals.workAssetsMissing}`);
  console.log(`  人物头像: copied=${totals.avatarsCopied}, missing=${totals.avatarsMissing}`);
  console.log('  共享人物资源目录: 不再导出');

  return { entries: exportedEntries, stats: totals };
}

async function exportPersons() {
  console.log('导出人物数据...');
  
  const persons = queryJson(`
    SELECT
      p.person_id,
      p.name,
      p.name_en,
      p.source_ids,
      p.profile_link,
      p.intro
    FROM person p
    ORDER BY p.person_id;
  `);
  
  const personsIndex = persons.map((row) => {
    const sourceIds = parseJsonText(row.source_ids, {});
    
    return {
      personId: row.person_id,
      name: row.name,
      nameEn: row.name_en ?? undefined,
      sourceIds,
      profileLink: row.profile_link ?? undefined,
      intro: row.intro ?? undefined
    };
  });
  
  await writeJson(path.join(generatedRoot, 'persons.json'), personsIndex);
  console.log(`  人物数据: ${personsIndex.length} 人`);
  
  return personsIndex.length;
}

async function main() {
  console.log('开始导出数据...');
  console.log('');

  // 查询数据
  const works = queryJson(`
    SELECT *
    FROM works
    WHERE module = 'video' AND submodule = 'movie' AND status != 'archived'
    ORDER BY year DESC, id ASC;
  `);

  const books = queryJson(`
    SELECT *
    FROM books
    WHERE status != 'archived'
    ORDER BY year DESC, id ASC;
  `);

  const credits = queryJson(`
    SELECT
      wp.work_id,
      wp.department,
      wp.role,
      wp.character,
      wp."order",
      wp.is_primary,
      p.person_id,
      p.name,
      p.name_en,
      p.avatar_path,
      p.profile_link,
      p.intro
    FROM work_person wp
    JOIN person p ON p.id = wp.person_id
    ORDER BY wp.work_id, wp."order", wp.id;
  `);

  const categories = queryJson(`
    SELECT
      wc.work_id,
      c."group",
      c.name,
      wc."order"
    FROM work_category wc
    JOIN category c ON c.id = wc.category_id
    ORDER BY wc.work_id, wc."order", wc.id;
  `);

  const bookPeople = queryJson(`
    SELECT
      bp.book_id,
      bp.role,
      bp.[order],
      bp.is_primary,
      p.person_id,
      p.name,
      p.name_en,
      p.avatar_path,
      p.profile_link,
      p.intro
    FROM book_person bp
    JOIN person p ON p.id = bp.person_id
    ORDER BY bp.book_id, bp.[order], bp.id;
  `);

  const bookCategories = queryJson(`
    SELECT
      bc.book_id,
      c.[group],
      c.name,
      bc.[order]
    FROM book_category bc
    JOIN category c ON c.id = bc.category_id
    ORDER BY bc.book_id, bc.[order], bc.id;
  `);

  const bookSeries = queryJson(`
    SELECT *
    FROM book_series
    ORDER BY id;
  `);

  const creditIndex = indexCredits(credits);
  const categoryIndex = indexCategories(categories);
  const bookPeopleIndex = indexBookPeople(bookPeople);
  const bookCategoryIndex = indexBookCategories(bookCategories);
  const bookSeriesIndex = new Map(bookSeries.map((row) => [row.id, row]));

  const rawEntries = works.map((row) => buildEntry(
    row,
    creditIndex.get(row.id) ?? { director: [], writer: [], cast: [], otherCast: [], producer: [] },
    categoryIndex.get(row.id) ?? { genre: [], tags: [] }
  ));

  const rawBookEntries = books.map((row) => buildBookEntry(
    row,
    bookPeopleIndex.get(row.id) ?? { authors: [], translators: [] },
    bookCategoryIndex.get(row.id) ?? { genre: [], tags: [] },
    row.series_id ? bookSeriesIndex.get(row.series_id) : null
  ));
  const rawAllEntries = [...rawEntries, ...rawBookEntries];

  // 清理旧目录
  console.log('清理旧文件...');
  await cleanDirectory(entriesRoot);
  await cleanDirectory(indexesRoot);

  const { entries } = await exportAssetsForEntries(rawAllEntries);

  // 按作品拆分 JSON
  console.log(`导出 ${entries.length} 个作品文件...`);
  const movieEntriesDir = path.join(entriesRoot, 'video', 'movie');
  const bookEntriesDir = path.join(entriesRoot, 'book');
  await fs.mkdir(movieEntriesDir, { recursive: true });
  await fs.mkdir(bookEntriesDir, { recursive: true });

  for (const entry of entries) {
    const filePath = entry.module === 'book'
      ? path.join(bookEntriesDir, `${entry.id}.json`)
      : path.join(movieEntriesDir, `${entry.id}.json`);
    await writeJson(filePath, entry);
  }

  // 生成索引文件
  console.log('生成索引文件...');
  const movieEntries = entries.filter((e) => e.module === 'video' && e.submodule === 'movie');
  const videoEntries = entries.filter((e) => e.module === 'video');
  const bookEntries = entries.filter((e) => e.module === 'book');

  // 列表索引
  await writeJson(path.join(indexesRoot, 'video-movie.json'), movieEntries.map(buildListIndex));
  await writeJson(path.join(indexesRoot, 'video.json'), videoEntries.map(buildListIndex));
  await writeJson(path.join(indexesRoot, 'book.json'), bookEntries.map(buildBookListIndex));
  await writeJson(path.join(indexesRoot, 'all.json'), entries.map(buildSearchIndex));

  // 最近更新
  await writeJson(path.join(generatedRoot, 'recent.json'), buildRecentIndex(entries));

  // 标签聚合
  const tagsPayload = {
    genres: [...new Set(movieEntries.flatMap((entry) => entry.genre ?? []))].sort(),
    tags: [...new Set(entries.flatMap((entry) => entry.tags ?? []))].sort(),
    bookGenres: [...new Set(bookEntries.flatMap((entry) => entry.genre ?? []))].sort()
  };
  await writeJson(path.join(generatedRoot, 'tags.json'), tagsPayload);

  // 导出人物数据
  console.log('');
  await exportPersons();

  console.log('');
  console.log('='.repeat(50));
  console.log('导出完成！');
  console.log('='.repeat(50));
  console.log(`  电影文件: generated/entries/video/movie/*.json (${movieEntries.length} 个)`);
  console.log(`  书籍文件: generated/entries/book/*.json (${bookEntries.length} 个)`);
  console.log(`  列表索引: generated/indexes/video-movie.json`);
  console.log(`  书籍索引: generated/indexes/book.json`);
  console.log(`  搜索索引: generated/indexes/all.json`);
  console.log(`  人物数据: generated/persons.json`);
  console.log(`  图片资源: site/public/assets/{module}/{id}/`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
