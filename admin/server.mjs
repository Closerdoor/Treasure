import { createServer } from 'node:http';
import { createReadStream, existsSync } from 'node:fs';
import { mkdir, copyFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Database from 'better-sqlite3';

const __filename = fileURLToPath(import.meta.url);
const ADMIN_DIR = path.dirname(__filename);
const REPO_ROOT = path.resolve(ADMIN_DIR, '..');
const PUBLIC_DIR = path.join(ADMIN_DIR, 'public');
const DB_PATH = path.join(REPO_ROOT, '.local', 'treasure.db');
const ASSETS_ROOT = path.join(REPO_ROOT, '.local', 'assets');
const PORT = Number(process.env.TREASURE_ADMIN_PORT || process.env.PORT || 4317);

const db = new Database(DB_PATH);
db.pragma('foreign_keys = ON');

const JSON_FIELDS = new Set([
  'other_titles',
  'release_dates',
  'quotes',
  'scores',
  'episodes_story',
  'external_source',
  'images',
  'videos',
  'comments',
  'soundtrack',
  'related',
  'characters'
]);

const WORK_FIELDS = [
  'module',
  'submodule',
  'schema_type',
  'title',
  'title_original',
  'other_titles',
  'year',
  'country',
  'language',
  'total_time',
  'studio',
  'release_dates',
  'quotes',
  'scores',
  'episode_count',
  'episode_time',
  'episodes_story',
  'introduction',
  'story',
  'external_source',
  'images',
  'videos',
  'comments',
  'soundtrack',
  'related',
  'characters',
  'status'
];

const PERSON_FIELDS = [
  'person_id',
  'name',
  'name_en',
  'avatar_path',
  'profile_link',
  'intro',
  'source_ids',
  'tmdb_avatar_path',
  'douban_avatar_path'
];

const WORK_PERSON_FIELDS = ['department', 'role', 'character', 'character_en', 'order', 'is_primary'];
const CATEGORY_FIELDS = ['group', 'name', 'module', 'submodule', 'order', 'enabled'];
const BOOK_FIELDS = [
  'title',
  'title_original',
  'other_titles',
  'isbn',
  'year',
  'country',
  'language',
  'word_count',
  'publisher',
  'summary',
  'quotes',
  'excerpts',
  'series_id',
  'series_order',
  'scores',
  'external_source',
  'images',
  'reviews',
  'related',
  'status'
];
const BOOK_JSON_FIELDS = new Set(['other_titles', 'quotes', 'excerpts', 'scores', 'external_source', 'images', 'reviews', 'related']);

await ensureBackup();

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url || '/', `http://${req.headers.host || `localhost:${PORT}`}`);
    if (url.pathname.startsWith('/api/')) {
      await handleApi(req, res, url);
      return;
    }
    if (url.pathname.startsWith('/assets-local/')) {
      serveLocalAsset(res, decodeURIComponent(url.pathname.replace('/assets-local/', '')));
      return;
    }
    await serveStatic(res, url.pathname);
  } catch (error) {
    sendJson(res, error.status || 500, { error: error.message || String(error) });
  }
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Treasure Admin running at http://127.0.0.1:${PORT}`);
});

async function ensureBackup() {
  const backupDir = path.join(REPO_ROOT, '.local', 'backup');
  await mkdir(backupDir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 12);
  const target = path.join(backupDir, `treasure-admin-${stamp}.db`);
  if (!existsSync(target) && existsSync(DB_PATH)) {
    await copyFile(DB_PATH, target);
  }
}

async function handleApi(req, res, url) {
  const parts = url.pathname.split('/').filter(Boolean);
  const method = req.method || 'GET';

  if (method === 'GET' && url.pathname === '/api/summary') {
    sendJson(res, 200, getSummary());
    return;
  }

  if (parts[1] === 'works') {
    if (method === 'GET' && parts.length === 2) {
      sendJson(res, 200, listWorks(url.searchParams));
      return;
    }
    if (method === 'POST' && parts.length === 2) {
      sendJson(res, 201, createWork(await readJson(req)));
      return;
    }
    const workId = parts[2];
    if (method === 'GET' && parts.length === 3) {
      sendJson(res, 200, getWorkDetail(workId));
      return;
    }
    if ((method === 'PATCH' || method === 'PUT') && parts.length === 3) {
      sendJson(res, 200, updateWork(workId, await readJson(req)));
      return;
    }
    if (method === 'DELETE' && parts.length === 3) {
      sendJson(res, 200, deleteWork(workId, url.searchParams.get('confirm')));
      return;
    }
    if (method === 'POST' && parts[3] === 'people') {
      sendJson(res, 201, addWorkPerson(workId, await readJson(req)));
      return;
    }
    if (method === 'POST' && parts[3] === 'categories') {
      sendJson(res, 201, addWorkCategory(workId, await readJson(req)));
      return;
    }
  }

  if (parts[1] === 'books') {
    if (method === 'GET' && parts.length === 2) {
      sendJson(res, 200, listBooks(url.searchParams));
      return;
    }
    if (method === 'POST' && parts.length === 2) {
      sendJson(res, 201, createBook(await readJson(req)));
      return;
    }
    const bookId = parts[2];
    if (method === 'GET' && parts.length === 3) {
      sendJson(res, 200, getBookDetail(bookId));
      return;
    }
    if ((method === 'PATCH' || method === 'PUT') && parts.length === 3) {
      sendJson(res, 200, updateBook(bookId, await readJson(req)));
      return;
    }
    if (method === 'DELETE' && parts.length === 3) {
      sendJson(res, 200, deleteBook(bookId, url.searchParams.get('confirm')));
      return;
    }
  }

  if (parts[1] === 'work-people') {
    const id = Number(parts[2]);
    if (method === 'PATCH') {
      sendJson(res, 200, updateWorkPerson(id, await readJson(req)));
      return;
    }
    if (method === 'DELETE') {
      sendJson(res, 200, deleteById('work_person', id));
      return;
    }
  }

  if (parts[1] === 'work-categories') {
    const id = Number(parts[2]);
    if (method === 'PATCH') {
      sendJson(res, 200, updateWorkCategory(id, await readJson(req)));
      return;
    }
    if (method === 'DELETE') {
      sendJson(res, 200, deleteById('work_category', id));
      return;
    }
  }

  if (parts[1] === 'persons') {
    if (method === 'GET' && parts.length === 2) {
      sendJson(res, 200, listPersons(url.searchParams));
      return;
    }
    if (method === 'POST' && parts.length === 2) {
      sendJson(res, 201, createPerson(await readJson(req)));
      return;
    }
    if (method === 'PATCH' && parts.length === 3) {
      sendJson(res, 200, updatePerson(Number(parts[2]), await readJson(req)));
      return;
    }
  }

  if (parts[1] === 'categories') {
    if (method === 'GET' && parts.length === 2) {
      sendJson(res, 200, listCategories(url.searchParams));
      return;
    }
    if (method === 'POST' && parts.length === 2) {
      sendJson(res, 201, createCategory(await readJson(req)));
      return;
    }
  }

  sendJson(res, 404, { error: 'not_found' });
}

function getSummary() {
  const scalar = (sql, params = {}) => db.prepare(sql).get(params)?.count ?? 0;
  return {
    works: scalar('select count(*) as count from works'),
    movies: scalar("select count(*) as count from works where module = 'video' and submodule = 'movie'"),
    people: scalar('select count(*) as count from person'),
    categories: scalar('select count(*) as count from category'),
    missingPoster: scalar("select count(*) as count from works where images is null or images not like '%poster%'"),
    updatedAt: db.prepare('select max(updated_at) as updatedAt from works').get()?.updatedAt || null
  };
}

function listWorks(params) {
  const limit = clamp(Number(params.get('limit') || 48), 1, 200);
  const offset = Math.max(0, Number(params.get('offset') || 0));
  const query = (params.get('q') || '').trim();
  const module = params.get('module') || '';
  const submodule = params.get('submodule') || '';
  const status = params.get('status') || '';
  const filters = [];
  const values = {};

  if (query) {
    filters.push('(title like @query or title_original like @query or introduction like @query or country like @query)');
    values.query = `%${query}%`;
  }
  if (module) {
    filters.push('module = @module');
    values.module = module;
  }
  if (submodule) {
    filters.push('submodule = @submodule');
    values.submodule = submodule;
  }
  if (status) {
    filters.push('status = @status');
    values.status = status;
  }

  const where = filters.length ? `where ${filters.join(' and ')}` : '';
  const total = db.prepare(`select count(*) as count from works ${where}`).get(values).count;
  const rows = db.prepare(`
    select *
    from works
    ${where}
    order by updated_at desc, id desc
    limit @limit offset @offset
  `).all({ ...values, limit, offset });

  return {
    total,
    limit,
    offset,
    items: rows.map((row) => enrichWork(row, { compact: true }))
  };
}

function listBooks(params) {
  const limit = clamp(Number(params.get('limit') || 48), 1, 200);
  const offset = Math.max(0, Number(params.get('offset') || 0));
  const query = (params.get('q') || '').trim();
  const status = params.get('status') || '';
  const filters = [];
  const values = {};

  if (query) {
    filters.push('(title like @query or title_original like @query or summary like @query or publisher like @query)');
    values.query = `%${query}%`;
  }
  if (status) {
    filters.push('status = @status');
    values.status = status;
  }

  const where = filters.length ? `where ${filters.join(' and ')}` : '';
  const total = db.prepare(`select count(*) as count from books ${where}`).get(values).count;
  const rows = db.prepare(`
    select *
    from books
    ${where}
    order by updated_at desc, id desc
    limit @limit offset @offset
  `).all({ ...values, limit, offset });

  return {
    total,
    limit,
    offset,
    items: rows.map(enrichBook)
  };
}

function getWorkDetail(id) {
  const work = db.prepare('select * from works where id = ?').get(id);
  if (!work) {
    throw new HttpError(404, 'work_not_found');
  }
  return {
    work: enrichWork(work),
    people: db.prepare(`
      select wp.*, p.person_id as public_person_id, p.name, p.name_en, p.avatar_path, p.profile_link
      from work_person wp
      join person p on p.id = wp.person_id
      where wp.work_id = ?
      order by
        case wp.department
          when 'direction' then 1
          when 'writing' then 2
          when 'original_work' then 3
          when 'cast' then 4
          when 'production' then 5
          when 'music' then 6
          else 9
        end,
        wp."order",
        wp.id
    `).all(id).map(enrichPersonRelation),
    categories: db.prepare(`
      select wc.*, c."group", c.name, c.module, c.submodule, c.enabled
      from work_category wc
      join category c on c.id = wc.category_id
      where wc.work_id = ?
      order by c."group", wc."order", c.name
    `).all(id)
  };
}

function getBookDetail(id) {
  const book = db.prepare('select * from books where id = ?').get(id);
  if (!book) throw new HttpError(404, 'book_not_found');
  return { book: enrichBook(book) };
}

function createWork(payload) {
  const id = String(payload.id || '').trim();
  if (!id) throw new HttpError(400, 'id_required');
  if (db.prepare('select 1 from works where id = ?').get(id)) {
    throw new HttpError(409, 'work_exists');
  }
  const data = sanitizeWorkPayload({
    module: 'video',
    submodule: 'movie',
    schema_type: 'live_action_movie',
    status: 'draft',
    ...payload
  });
  if (!data.title) throw new HttpError(400, 'title_required');
  const now = nowSql();
  const fields = ['id', ...Object.keys(data), 'created_at', 'updated_at'];
  const placeholders = fields.map((field) => `@${field}`).join(', ');
  db.prepare(`insert into works (${fields.join(', ')}) values (${placeholders})`).run({
    id,
    ...data,
    created_at: now,
    updated_at: now
  });
  return getWorkDetail(id);
}

function createBook(payload) {
  const id = String(payload.id || '').trim();
  if (!id) throw new HttpError(400, 'id_required');
  if (db.prepare('select 1 from books where id = ?').get(id)) throw new HttpError(409, 'book_exists');
  const data = sanitizeBookPayload({ status: 'draft', ...payload });
  if (!data.title) throw new HttpError(400, 'title_required');
  const now = nowSql();
  const fields = ['id', ...Object.keys(data), 'created_at', 'updated_at'];
  const placeholders = fields.map((field) => `@${field}`).join(', ');
  db.prepare(`insert into books (${fields.join(', ')}) values (${placeholders})`).run({
    id,
    ...data,
    created_at: now,
    updated_at: now
  });
  return getBookDetail(id);
}

function updateWork(id, payload) {
  if (!db.prepare('select 1 from works where id = ?').get(id)) {
    throw new HttpError(404, 'work_not_found');
  }
  const data = sanitizeWorkPayload(payload);
  const fields = Object.keys(data);
  if (!fields.length) return getWorkDetail(id);
  const setSql = fields.map((field) => `${field} = @${field}`).join(', ');
  db.prepare(`update works set ${setSql}, updated_at = @updated_at where id = @id`).run({
    id,
    ...data,
    updated_at: nowSql()
  });
  return getWorkDetail(id);
}

function updateBook(id, payload) {
  if (!db.prepare('select 1 from books where id = ?').get(id)) throw new HttpError(404, 'book_not_found');
  const data = sanitizeBookPayload(payload);
  const fields = Object.keys(data);
  if (!fields.length) return getBookDetail(id);
  const setSql = fields.map((field) => `${field} = @${field}`).join(', ');
  db.prepare(`update books set ${setSql}, updated_at = @updated_at where id = @id`).run({
    id,
    ...data,
    updated_at: nowSql()
  });
  return getBookDetail(id);
}

function deleteWork(id, confirm) {
  if (confirm !== id) throw new HttpError(400, 'confirm_id_required');
  const info = db.prepare('delete from works where id = ?').run(id);
  return { deleted: info.changes };
}

function deleteBook(id, confirm) {
  if (confirm !== id) throw new HttpError(400, 'confirm_id_required');
  const info = db.prepare('delete from books where id = ?').run(id);
  return { deleted: info.changes };
}

function addWorkPerson(workId, payload) {
  if (!payload.person_id) throw new HttpError(400, 'person_id_required');
  const data = sanitizeSubset(payload, WORK_PERSON_FIELDS);
  db.prepare(`
    insert into work_person (work_id, person_id, department, role, character, character_en, "order", is_primary)
    values (@work_id, @person_id, @department, @role, @character, @character_en, @order, @is_primary)
  `).run({
    work_id: workId,
    person_id: Number(payload.person_id),
    department: data.department || 'cast',
    role: data.role || null,
    character: data.character || null,
    character_en: data.character_en || null,
    order: Number(data.order || 0),
    is_primary: boolToInt(data.is_primary)
  });
  touchWork(workId);
  return getWorkDetail(workId);
}

function updateWorkPerson(id, payload) {
  const row = db.prepare('select work_id from work_person where id = ?').get(id);
  if (!row) throw new HttpError(404, 'relation_not_found');
  const data = sanitizeSubset(payload, WORK_PERSON_FIELDS);
  if ('is_primary' in data) data.is_primary = boolToInt(data.is_primary);
  if ('order' in data) data.order = Number(data.order || 0);
  updateTableById('work_person', id, data);
  touchWork(row.work_id);
  return getWorkDetail(row.work_id);
}

function addWorkCategory(workId, payload) {
  if (!payload.category_id) throw new HttpError(400, 'category_id_required');
  db.prepare(`
    insert or ignore into work_category (work_id, category_id, "order")
    values (?, ?, ?)
  `).run(workId, Number(payload.category_id), Number(payload.order || 0));
  touchWork(workId);
  return getWorkDetail(workId);
}

function updateWorkCategory(id, payload) {
  const row = db.prepare('select work_id from work_category where id = ?').get(id);
  if (!row) throw new HttpError(404, 'category_relation_not_found');
  updateTableById('work_category', id, { order: Number(payload.order || 0) });
  touchWork(row.work_id);
  return getWorkDetail(row.work_id);
}

function deleteById(table, id) {
  const row = db.prepare(`select * from ${table} where id = ?`).get(id);
  if (!row) throw new HttpError(404, 'row_not_found');
  const info = db.prepare(`delete from ${table} where id = ?`).run(id);
  if (row.work_id) touchWork(row.work_id);
  return { deleted: info.changes, workId: row.work_id };
}

function listPersons(params) {
  const query = (params.get('q') || '').trim();
  const limit = clamp(Number(params.get('limit') || 20), 1, 80);
  if (!query) return { items: [] };
  const rows = db.prepare(`
    select *
    from person
    where name like @query or name_en like @query or person_id like @query
    order by name
    limit @limit
  `).all({ query: `%${query}%`, limit });
  return { items: rows.map(enrichPerson) };
}

function createPerson(payload) {
  const data = sanitizeSubset(payload, PERSON_FIELDS);
  if (!data.name) throw new HttpError(400, 'name_required');
  if (!data.person_id) data.person_id = nextPersonId();
  const fields = Object.keys(data);
  const placeholders = fields.map((field) => `@${field}`).join(', ');
  const info = db.prepare(`insert into person (${fields.join(', ')}) values (${placeholders})`).run(data);
  return enrichPerson(db.prepare('select * from person where id = ?').get(info.lastInsertRowid));
}

function updatePerson(id, payload) {
  const data = sanitizeSubset(payload, PERSON_FIELDS);
  updateTableById('person', id, data);
  return enrichPerson(db.prepare('select * from person where id = ?').get(id));
}

function listCategories(params) {
  const group = params.get('group') || '';
  const module = params.get('module') || '';
  const rows = db.prepare(`
    select *
    from category
    where (@group = '' or "group" = @group)
      and (@module = '' or module is null or module = @module)
    order by "group", "order", name
  `).all({ group, module });
  return { items: rows };
}

function createCategory(payload) {
  const data = sanitizeSubset(payload, CATEGORY_FIELDS);
  if (!data.group || !data.name) throw new HttpError(400, 'group_and_name_required');
  data.order = Number(data.order || 0);
  data.enabled = boolToInt(data.enabled ?? true);
  const fields = Object.keys(data);
  const placeholders = fields.map((field) => `@${field}`).join(', ');
  const info = db.prepare(`insert into category (${fields.join(', ')}) values (${placeholders})`).run(data);
  return db.prepare('select * from category where id = ?').get(info.lastInsertRowid);
}

function sanitizeWorkPayload(payload) {
  const data = sanitizeSubset(payload, WORK_FIELDS);
  for (const field of ['year', 'total_time', 'episode_count', 'episode_time']) {
    if (field in data) data[field] = data[field] === '' || data[field] == null ? null : Number(data[field]);
  }
  for (const field of JSON_FIELDS) {
    if (field in data) data[field] = normalizeJsonField(data[field], field);
  }
  return data;
}

function sanitizeBookPayload(payload) {
  const data = sanitizeSubset(payload, BOOK_FIELDS);
  for (const field of ['year', 'word_count', 'series_order']) {
    if (field in data) data[field] = data[field] === '' || data[field] == null ? null : Number(data[field]);
  }
  for (const field of BOOK_JSON_FIELDS) {
    if (field in data) data[field] = normalizeJsonField(data[field], field);
  }
  return data;
}

function sanitizeSubset(payload, allowed) {
  const data = {};
  for (const field of allowed) {
    if (field in payload) {
      data[field] = payload[field] === '' ? null : payload[field];
    }
  }
  return data;
}

function normalizeJsonField(value, field) {
  if (value === '' || value == null) return null;
  if (typeof value !== 'string') return JSON.stringify(value);
  try {
    JSON.parse(value);
    return value;
  } catch {
    throw new HttpError(400, `invalid_json:${field}`);
  }
}

function enrichWork(row, options = {}) {
  const images = parseJson(row.images, {});
  const scores = parseJson(row.scores, {});
  const people = options.compact ? compactPeople(row.id) : undefined;
  const categories = options.compact ? compactCategories(row.id) : undefined;
  return {
    ...row,
    imagesParsed: images,
    scoresParsed: scores,
    posterUrl: buildWorkPosterUrl(row, images),
    aggregateRating: typeof scores.avg === 'number' ? scores.avg : null,
    people,
    categories
  };
}

function enrichBook(row) {
  const images = parseJson(row.images, {});
  const scores = parseJson(row.scores, {});
  return {
    ...row,
    recordType: 'book',
    imagesParsed: images,
    scoresParsed: scores,
    module: 'book',
    submodule: null,
    introduction: row.summary,
    posterUrl: buildBookCoverUrl(row, images),
    aggregateRating: typeof scores.avg === 'number' ? scores.avg : null,
    people: { directors: [], cast: [] },
    categories: []
  };
}

function compactPeople(workId) {
  const rows = db.prepare(`
    select wp.department, p.name
    from work_person wp
    join person p on p.id = wp.person_id
    where wp.work_id = ?
    order by wp.department, wp."order", wp.id
  `).all(workId);
  return {
    directors: rows.filter((row) => row.department === 'direction').map((row) => row.name).slice(0, 3),
    cast: rows.filter((row) => row.department === 'cast').map((row) => row.name).slice(0, 4)
  };
}

function compactCategories(workId) {
  return db.prepare(`
    select c."group", c.name
    from work_category wc
    join category c on c.id = wc.category_id
    where wc.work_id = ?
    order by c."group", wc."order", c.name
  `).all(workId);
}

function enrichPerson(row) {
  if (!row) return null;
  return {
    ...row,
    avatarUrl: buildPersonAvatarUrl(row)
  };
}

function enrichPersonRelation(row) {
  return {
    ...row,
    is_primary: Boolean(row.is_primary),
    avatarUrl: buildPersonAvatarUrl({
      avatar_path: row.avatar_path,
      tmdb_avatar_path: row.tmdb_avatar_path,
      douban_avatar_path: row.douban_avatar_path
    })
  };
}

function buildWorkPosterUrl(work, images) {
  const poster = images?.poster || images?.posters?.[0];
  const assetDir = normalizeAssetDir(images?.assetDir || `.local/assets/${work.module}/${work.submodule || 'default'}/${work.id}`);
  if (!poster) return '/poster-placeholder.svg';
  if (/^https?:\/\//.test(poster)) return poster;
  return `/assets-local/${encodeURIComponent(path.posix.join(assetDir, poster).replaceAll('\\', '/'))}`;
}

function buildBookCoverUrl(book, images) {
  const cover = images?.cover || images?.covers?.[0];
  const assetDir = normalizeAssetDir(images?.assetDir || `.local/assets/book/${book.id}`);
  if (!cover) return '/poster-placeholder.svg';
  if (/^https?:\/\//.test(cover)) return cover;
  return `/assets-local/${encodeURIComponent(path.posix.join(assetDir, cover).replaceAll('\\', '/'))}`;
}

function buildPersonAvatarUrl(person) {
  const avatar = person?.avatar_path || person?.tmdb_avatar_path || person?.douban_avatar_path;
  if (!avatar) return '/avatar-placeholder.svg';
  if (/^https?:\/\//.test(avatar)) return avatar;
  const base = String(avatar).replaceAll('\\', '/').startsWith('people/')
    ? '.local/assets'
    : '.local/assets/people';
  return `/assets-local/${encodeURIComponent(path.posix.join(base, avatar).replaceAll('\\', '/'))}`;
}

function normalizeAssetDir(assetDir) {
  return String(assetDir || '').replace(/^\.\//, '').replaceAll('\\', '/');
}

function updateTableById(table, id, data) {
  const fields = Object.keys(data);
  if (!fields.length) return;
  const setSql = fields.map((field) => `${field} = @${field}`).join(', ');
  db.prepare(`update ${table} set ${setSql} where id = @id`).run({ id, ...data });
}

function touchWork(workId) {
  db.prepare('update works set updated_at = ? where id = ?').run(nowSql(), workId);
}

function nextPersonId() {
  const rows = db.prepare("select person_id from person where person_id like 'p%'").all();
  const max = rows.reduce((memo, row) => {
    const num = Number(String(row.person_id || '').replace(/^p/, ''));
    return Number.isFinite(num) ? Math.max(memo, num) : memo;
  }, 0);
  return `p${String(max + 1).padStart(6, '0')}`;
}

function parseJson(value, fallback) {
  if (!value) return fallback;
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function boolToInt(value) {
  return value === true || value === 1 || value === '1' || value === 'true' ? 1 : 0;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, Number.isFinite(value) ? value : min));
}

function nowSql() {
  return new Date().toISOString();
}

async function readJson(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  if (!chunks.length) return {};
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

async function serveStatic(res, pathname) {
  const file = pathname === '/' ? 'index.html' : pathname.replace(/^\//, '');
  const filePath = path.join(PUBLIC_DIR, file);
  if (!filePath.startsWith(PUBLIC_DIR) || !existsSync(filePath)) {
    sendJson(res, 404, { error: 'not_found' });
    return;
  }
  streamFile(res, filePath);
}

function serveLocalAsset(res, assetPath) {
  const normalized = assetPath.replaceAll('\\', '/').replace(/^\.\//, '');
  const localRelative = normalized.startsWith('.local/assets/')
    ? normalized.replace('.local/assets/', '')
    : normalized;
  const filePath = path.resolve(ASSETS_ROOT, localRelative);
  if (!filePath.startsWith(ASSETS_ROOT) || !existsSync(filePath)) {
    streamFile(res, path.join(PUBLIC_DIR, 'poster-placeholder.svg'));
    return;
  }
  streamFile(res, filePath);
}

function streamFile(res, filePath) {
  res.writeHead(200, { 'Content-Type': contentType(filePath) });
  createReadStream(filePath).pipe(res);
}

function sendJson(res, status, payload) {
  if (payload?.error && status === 500 && payload.error instanceof HttpError) {
    status = payload.error.status;
  }
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(payload));
}

function contentType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  return {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.webp': 'image/webp',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png'
  }[ext] || 'application/octet-stream';
}

class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}
