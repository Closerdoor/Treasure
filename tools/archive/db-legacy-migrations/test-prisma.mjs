import { PrismaClient } from './node_modules/.prisma/client/index.js';

// Prisma 7.x 使用 adapter 方式连接 SQLite
import { createPrisma } from './node_modules/.prisma/client/runtime/library.js';
import Database from 'better-sqlite3';

const db = new Database('.local/treasure.db');
const adapter = {
  provider: 'sqlite',
  execute: async ({ sql, args }) => {
    const stmt = db.prepare(sql);
    if (stmt.reader) {
      return stmt.all(...args);
    }
    return stmt.run(...args);
  }
};

const prisma = createPrisma({
  adapter,
  runtimeDataModel: PrismaClient._runtimeDataModel,
});

async function main() {
  // 查询作品数量
  const workCount = await prisma.work.count();
  console.log('作品总数:', workCount);
  
  // 查询所有作品
  const works = await prisma.work.findMany({
    select: {
      id: true,
      title: true,
      year: true,
      country: true,
      status: true,
    }
  });
  
  console.log('\n作品列表:');
  works.forEach(w => {
    console.log(`- ${w.id}: ${w.title} (${w.year || '未知'}) - ${w.country || '未知'} [${w.status}]`);
  });
  
  // 查询人物数量
  const personCount = await prisma.person.count();
  console.log('\n人物总数:', personCount);
  
  // 查询词项数量
  const termCount = await prisma.term.count();
  console.log('词项总数:', termCount);
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
