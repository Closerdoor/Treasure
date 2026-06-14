import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Database from 'better-sqlite3';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..');
const dbPath = path.join(repoRoot, '.local', 'treasure.db');
const localAssetsRoot = path.join(repoRoot, '.local', 'assets');
const backupRoot = path.join(repoRoot, '.local', 'backup');
const planRoot = path.join(repoRoot, 'temp-script', 'movie-ingest', 'data', 'migration-plans');
const planJsonPath = path.join(planRoot, '2026-06-12-work-classification-migration.json');
const planMdPath = path.join(planRoot, '2026-06-12-work-classification-migration.md');

const animationType = '\u52a8\u753b';
const documentaryType = '\u7eaa\u5f55\u7247';

function nowStamp() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, '0');
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate())
  ].join('') + '-' + [
    pad(now.getHours()),
    pad(now.getMinutes()),
    pad(now.getSeconds())
  ].join('');
}

function parseJsonText(text, fallback) {
  if (!text) return fallback;
  try {
    return JSON.parse(text);
  } catch {
    return fallback;
  }
}

function stringifyJson(value) {
  return `${JSON.stringify(value, null, 2)}`;
}

function replaceIdsDeep(value, idMap) {
  if (Array.isArray(value)) {
    let changed = false;
    const next = value.map((item) => {
      const result = replaceIdsDeep(item, idMap);
      changed ||= result.changed;
      return result.value;
    });
    return { value: next, changed };
  }

  if (value && typeof value === 'object') {
    let changed = false;
    const next = {};
    for (const [key, item] of Object.entries(value)) {
      if (key === 'id' && typeof item === 'string' && idMap.has(item)) {
        next[key] = idMap.get(item);
        changed = true;
      } else {
        const result = replaceIdsDeep(item, idMap);
        next[key] = result.value;
        changed ||= result.changed;
      }
    }
    return { value: next, changed };
  }

  return { value, changed: false };
}

function buildAssetDir(module, submodule, id) {
  return `.local/assets/${module}/${submodule}/${id}`;
}

function buildPlan(db) {
  const rows = db.prepare(`
    SELECT
      w.id,
      w.title,
      w.year,
      w.module,
      w.submodule,
      w.schema_type AS schemaType,
      w.images,
      group_concat(c.name, '|') AS categoryText
    FROM works w
    LEFT JOIN work_category wc ON wc.work_id = w.id
    LEFT JOIN category c ON c.id = wc.category_id
    WHERE w.module = 'video'
      AND w.submodule = 'movie'
      AND w.schema_type = 'live_action_movie'
    GROUP BY w.id
    ORDER BY w.id ASC
  `).all();

  const hasCategory = (row, name) => String(row.categoryText ?? '').split('|').includes(name);
  const animationRows = rows.filter((row) => hasCategory(row, animationType));
  const documentaryRows = rows.filter((row) => hasCategory(row, documentaryType));

  const items = [
    ...animationRows.map((row, index) => ({
      kind: 'animated_movie',
      oldId: row.id,
      newId: `0301${String(index + 1).padStart(6, '0')}`,
      title: row.title,
      year: row.year,
      from: {
        module: row.module,
        submodule: row.submodule,
        schemaType: row.schemaType,
        assetDir: buildAssetDir(row.module, row.submodule, row.id)
      },
      to: {
        module: 'anime',
        submodule: 'anime_movie',
        schemaType: 'animated_movie',
        assetDir: buildAssetDir('anime', 'anime_movie', `0301${String(index + 1).padStart(6, '0')}`)
      }
    })),
    ...documentaryRows.map((row, index) => ({
      kind: 'documentary_film',
      oldId: row.id,
      newId: `0103${String(index + 1).padStart(6, '0')}`,
      title: row.title,
      year: row.year,
      from: {
        module: row.module,
        submodule: row.submodule,
        schemaType: row.schemaType,
        assetDir: buildAssetDir(row.module, row.submodule, row.id)
      },
      to: {
        module: 'video',
        submodule: 'documentary',
        schemaType: 'documentary_film',
        assetDir: buildAssetDir('video', 'documentary', `0103${String(index + 1).padStart(6, '0')}`)
      }
    }))
  ];

  return {
    version: 1,
    generatedAt: new Date().toISOString(),
    policy: {
      oldIdsDeprecated: true,
      preserveLegacyRoutes: false,
      order: 'old_id_ascending'
    },
    totals: {
      animatedMovie: animationRows.length,
      documentaryFilm: documentaryRows.length,
      total: items.length
    },
    items
  };
}

async function writePlan(plan) {
  await fs.mkdir(planRoot, { recursive: true });
  await fs.writeFile(planJsonPath, `${JSON.stringify(plan, null, 2)}\n`, 'utf8');

  const lines = [
    '# Work Classification Migration Plan',
    '',
    `Generated: ${plan.generatedAt}`,
    '',
    '| Old ID | New ID | Title | Target |',
    '|---|---|---|---|'
  ];
  for (const item of plan.items) {
    lines.push(`| ${item.oldId} | ${item.newId} | ${item.title} | ${item.to.module}/${item.to.submodule}/${item.to.schemaType} |`);
  }
  await fs.writeFile(planMdPath, `${lines.join('\n')}\n`, 'utf8');
}

async function pathExists(filePath) {
  try {
    await fs.stat(filePath);
    return true;
  } catch {
    return false;
  }
}

async function backupDatabase() {
  await fs.mkdir(backupRoot, { recursive: true });
  const backupPath = path.join(backupRoot, `treasure-before-work-classification-${nowStamp()}.db`);
  await fs.copyFile(dbPath, backupPath);
  return backupPath;
}

function ensureSafeAssetPath(relativeAssetDir) {
  const absolute = path.resolve(repoRoot, relativeAssetDir);
  const root = path.resolve(localAssetsRoot);
  if (!absolute.startsWith(root + path.sep)) {
    throw new Error(`Unsafe asset path: ${relativeAssetDir}`);
  }
  return absolute;
}

async function preflight(plan, db) {
  const existingNewIds = plan.items
    .map((item) => item.newId)
    .filter((id) => db.prepare('SELECT 1 FROM works WHERE id = ?').get(id));
  if (existingNewIds.length) {
    throw new Error(`Target IDs already exist: ${existingNewIds.join(', ')}`);
  }

  const duplicatedNewIds = plan.items
    .map((item) => item.newId)
    .filter((id, index, array) => array.indexOf(id) !== index);
  if (duplicatedNewIds.length) {
    throw new Error(`Duplicate target IDs in plan: ${duplicatedNewIds.join(', ')}`);
  }

  const assets = [];
  for (const item of plan.items) {
    const source = ensureSafeAssetPath(item.from.assetDir);
    const target = ensureSafeAssetPath(item.to.assetDir);
    assets.push({
      oldId: item.oldId,
      newId: item.newId,
      source,
      target,
      sourceExists: await pathExists(source),
      targetExists: await pathExists(target)
    });
  }

  const existingTargets = assets.filter((item) => item.targetExists);
  if (existingTargets.length) {
    throw new Error(`Target asset directories already exist: ${existingTargets.map((item) => item.target).join(', ')}`);
  }

  return { assets };
}

function ensureCategory(db, name, group, module, submodule) {
  const existing = db.prepare(`
    SELECT id
    FROM category
    WHERE name = ?
      AND "group" = ?
      AND module = ?
      AND submodule = ?
    LIMIT 1
  `).get(name, group, module, submodule);
  if (existing) return existing.id;

  const result = db.prepare(`
    INSERT INTO category ("group", name, module, submodule, "order", enabled)
    VALUES (?, ?, ?, ?, 0, 1)
  `).run(group, name, module, submodule);
  return result.lastInsertRowid;
}

function updateCategoryScopes(db, item) {
  const rows = db.prepare(`
    SELECT wc.id AS relationId, c.name, c."group"
    FROM work_category wc
    JOIN category c ON c.id = wc.category_id
    WHERE wc.work_id = ?
      AND c."group" = 'type'
    ORDER BY wc."order", wc.id
  `).all(item.newId);

  for (const row of rows) {
    const targetCategoryId = ensureCategory(db, row.name, row.group, item.to.module, item.to.submodule);
    db.prepare('UPDATE work_category SET category_id = ? WHERE id = ?').run(targetCategoryId, row.relationId);
  }
}

function updateRelatedIds(db, idMap) {
  const rows = db.prepare('SELECT id, related FROM works WHERE related IS NOT NULL').all();
  let updated = 0;
  for (const row of rows) {
    const related = parseJsonText(row.related, null);
    if (!related) continue;
    const result = replaceIdsDeep(related, idMap);
    if (result.changed) {
      db.prepare('UPDATE works SET related = ? WHERE id = ?').run(JSON.stringify(result.value, null, 2), row.id);
      updated += 1;
    }
  }
  return updated;
}

async function moveAssets(assetPlan) {
  let moved = 0;
  let missingSources = 0;
  for (const item of assetPlan) {
    if (!item.sourceExists) {
      missingSources += 1;
      continue;
    }
    await fs.mkdir(path.dirname(item.target), { recursive: true });
    await fs.rename(item.source, item.target);
    moved += 1;
  }
  return { moved, missingSources };
}

async function applyPlan(plan) {
  const db = new Database(dbPath);
  const backupPath = await backupDatabase();
  const preflightResult = await preflight(plan, db);
  const idMap = new Map(plan.items.map((item) => [item.oldId, item.newId]));

  db.pragma('foreign_keys = OFF');
  const migrateTransaction = db.transaction(() => {
    for (const item of plan.items) {
      const row = db.prepare('SELECT images FROM works WHERE id = ?').get(item.oldId);
      if (!row) {
        throw new Error(`Missing source work: ${item.oldId}`);
      }
      const images = parseJsonText(row.images, {});
      images.assetDir = item.to.assetDir;

      db.prepare(`
        UPDATE works
        SET id = ?,
            module = ?,
            submodule = ?,
            schema_type = ?,
            images = ?,
            updated_at = datetime('now')
        WHERE id = ?
      `).run(item.newId, item.to.module, item.to.submodule, item.to.schemaType, JSON.stringify(images, null, 2), item.oldId);

      db.prepare('UPDATE work_person SET work_id = ? WHERE work_id = ?').run(item.newId, item.oldId);
      db.prepare('UPDATE work_category SET work_id = ? WHERE work_id = ?').run(item.newId, item.oldId);
      updateCategoryScopes(db, item);
    }

    const relatedUpdated = updateRelatedIds(db, idMap);
    const fkProblems = db.prepare('PRAGMA foreign_key_check').all();
    if (fkProblems.length) {
      throw new Error(`Foreign key problems after migration: ${JSON.stringify(fkProblems)}`);
    }
    return { relatedUpdated };
  });

  const dbResult = migrateTransaction();
  db.pragma('foreign_keys = ON');
  db.close();

  const assetResult = await moveAssets(preflightResult.assets);
  return {
    backupPath,
    migrated: plan.items.length,
    relatedUpdated: dbResult.relatedUpdated,
    assets: assetResult
  };
}

async function main() {
  const apply = process.argv.includes('--apply');
  const db = new Database(dbPath, { readonly: true });
  const plan = buildPlan(db);
  db.close();
  await writePlan(plan);

  if (!apply) {
    console.log(JSON.stringify({
      mode: 'plan',
      planJsonPath,
      planMdPath,
      totals: plan.totals
    }, null, 2));
    return;
  }

  const result = await applyPlan(plan);
  console.log(JSON.stringify({
    mode: 'apply',
    planJsonPath,
    planMdPath,
    ...result
  }, null, 2));
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
