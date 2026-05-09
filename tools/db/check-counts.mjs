import { PrismaClient } from '../../node_modules/.prisma/client/index.js';
import { PrismaBetterSqlite3 } from '@prisma/adapter-better-sqlite3';

const adapter = new PrismaBetterSqlite3({ url: '.local/treasure.db' });
const prisma = new PrismaClient({ adapter });

async function main() {
  const worksCount = await prisma.work.count();
  const personCount = await prisma.person.count();
  const categoryCount = await prisma.category.count();
  const workPersonCount = await prisma.workPerson.count();
  const workCategoryCount = await prisma.workCategory.count();
  
  console.log('Works:', worksCount);
  console.log('Person:', personCount);
  console.log('Category:', categoryCount);
  console.log('WorkPerson:', workPersonCount);
  console.log('WorkCategory:', workCategoryCount);
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
