import { PrismaClient } from '../../node_modules/.prisma/client/index.js';
import { PrismaBetterSqlite3 } from '@prisma/adapter-better-sqlite3';
import fs from 'fs';

const adapter = new PrismaBetterSqlite3({ url: '.local/treasure.db' });
const prisma = new PrismaClient({ adapter });

async function main() {
  console.log('=== 备份现有数据 ===\n');
  
  // 备份 Person 数据
  const people = await prisma.$queryRaw`SELECT * FROM people`;
  console.log(`Person: ${people.length} 条`);
  fs.writeFileSync('.local/backup/people-backup.json', JSON.stringify(people, null, 2));
  
  // 备份 Term 数据
  const terms = await prisma.$queryRaw`SELECT * FROM terms`;
  console.log(`Term: ${terms.length} 条`);
  fs.writeFileSync('.local/backup/terms-backup.json', JSON.stringify(terms, null, 2));
  
  console.log('\n备份完成，保存在 .local/backup/ 目录');
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
