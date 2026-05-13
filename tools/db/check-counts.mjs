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
  const booksCount = await prisma.book.count();
  const bookSeriesCount = await prisma.bookSeries.count();
  const bookPersonCount = await prisma.bookPerson.count();
  const bookCategoryCount = await prisma.bookCategory.count();
  
  console.log('Works:', worksCount);
  console.log('Person:', personCount);
  console.log('Category:', categoryCount);
  console.log('WorkPerson:', workPersonCount);
  console.log('WorkCategory:', workCategoryCount);
  console.log('Books:', booksCount);
  console.log('BookSeries:', bookSeriesCount);
  console.log('BookPerson:', bookPersonCount);
  console.log('BookCategory:', bookCategoryCount);
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
