import fs from 'node:fs';
import path from 'node:path';
import { PrismaClient } from '../../node_modules/.prisma/client/index.js';
import { PrismaBetterSqlite3 } from '@prisma/adapter-better-sqlite3';

const DB_PATH = '.local/treasure.db';
const TAG_NAME = '豆瓣TOP250';
const EXPECTED_TARGET_COUNT = 250;
const EXCLUDED_WORK_IDS = new Set([
  // 2026-05-20 单部电影工作流样本，不属于豆瓣 TOP250 存量批次。
  '0101000251'
]);

const apply = process.argv.includes('--apply');

function timestamp() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, '0');
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
    '-',
    pad(now.getHours()),
    pad(now.getMinutes()),
    pad(now.getSeconds())
  ].join('');
}

function normalizeJson(value) {
  return JSON.parse(JSON.stringify(value, (_, item) => (
    typeof item === 'bigint' ? Number(item) : item
  )));
}

function backupDatabase() {
  const backupDir = path.join('.local', 'backup');
  fs.mkdirSync(backupDir, { recursive: true });
  const backupPath = path.join(backupDir, `treasure-before-douban-top250-tag-${timestamp()}.db`);
  fs.copyFileSync(DB_PATH, backupPath);
  return backupPath;
}

const prisma = new PrismaClient({
  adapter: new PrismaBetterSqlite3({ url: DB_PATH })
});

try {
  const targetWorks = await prisma.work.findMany({
    where: {
      status: { not: 'archived' },
      module: { in: ['video', 'anime'] },
      id: { notIn: [...EXCLUDED_WORK_IDS] }
    },
    select: {
      id: true,
      title: true,
      module: true,
      submodule: true,
      schemaType: true
    },
    orderBy: { id: 'asc' }
  });

  const excludedWorks = await prisma.work.findMany({
    where: { id: { in: [...EXCLUDED_WORK_IDS] } },
    select: { id: true, title: true, module: true, submodule: true, schemaType: true },
    orderBy: { id: 'asc' }
  });

  if (targetWorks.length !== EXPECTED_TARGET_COUNT) {
    throw new Error(`目标作品数量应为 ${EXPECTED_TARGET_COUNT}，实际为 ${targetWorks.length}。请先核对 TOP250 边界。`);
  }

  const existingTag = await prisma.category.findFirst({
    where: { group: 'tag', name: TAG_NAME, module: null, submodule: null },
    orderBy: { id: 'asc' }
  });

  const existingLinkedCount = existingTag
    ? await prisma.workCategory.count({ where: { categoryId: existingTag.id } })
    : 0;

  const targetIds = targetWorks.map((work) => work.id);
  const alreadyLinked = existingTag
    ? await prisma.workCategory.findMany({
      where: {
        categoryId: existingTag.id,
        workId: { in: targetIds }
      },
      select: { workId: true }
    })
    : [];

  const alreadyLinkedIds = new Set(alreadyLinked.map((row) => row.workId));
  const pendingWorks = targetWorks.filter((work) => !alreadyLinkedIds.has(work.id));

  let backupPath = null;
  let tagId = existingTag?.id ?? null;
  let insertedLinks = 0;

  if (apply) {
    backupPath = backupDatabase();

    await prisma.$transaction(async (tx) => {
      const tag = existingTag ?? await tx.category.create({
        data: {
          group: 'tag',
          name: TAG_NAME,
          module: null,
          submodule: null,
          order: 0,
          enabled: true
        }
      });
      tagId = tag.id;

      const maxOrders = await tx.$queryRawUnsafe(`
        SELECT work_id AS workId, COALESCE(MAX("order"), -1) + 1 AS nextOrder
        FROM work_category
        WHERE work_id IN (${targetIds.map(() => '?').join(',')})
        GROUP BY work_id
      `, ...targetIds);

      const orderByWorkId = new Map(
        maxOrders.map((row) => [row.workId, Number(row.nextOrder)])
      );

      for (const work of pendingWorks) {
        await tx.workCategory.create({
          data: {
            workId: work.id,
            categoryId: tag.id,
            order: orderByWorkId.get(work.id) ?? 0
          }
        });
        insertedLinks += 1;
      }
    });
  }

  const finalLinkedCount = tagId
    ? await prisma.workCategory.count({ where: { categoryId: tagId } })
    : 0;

  console.log(JSON.stringify(normalizeJson({
    mode: apply ? 'apply' : 'dry-run',
    tagName: TAG_NAME,
    tagId,
    targetCount: targetWorks.length,
    excludedWorks,
    existingLinkedCount,
    pendingCount: pendingWorks.length,
    insertedLinks,
    finalLinkedCount,
    backupPath,
    targetDistribution: await prisma.$queryRawUnsafe(`
      SELECT module, submodule, schema_type AS schemaType, COUNT(*) AS count
      FROM works
      WHERE id IN (${targetIds.map(() => '?').join(',')})
      GROUP BY module, submodule, schema_type
      ORDER BY module, submodule, schema_type
    `, ...targetIds),
    samples: targetWorks.slice(0, 5)
  }), null, 2));
} finally {
  await prisma.$disconnect();
}
