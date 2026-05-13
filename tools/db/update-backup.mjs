import Database from 'better-sqlite3';
import fs from 'fs';

const db = new Database('.local/treasure.db');

console.log('=== 更新备份文件 ===\n');

// 备份 Person
const people = db.prepare('SELECT * FROM person').all();
fs.writeFileSync('.local/backup/person-backup.json', JSON.stringify(people, null, 2));
console.log(`Person: ${people.length} 条`);

// 备份 Category
const categories = db.prepare('SELECT * FROM category').all();
fs.writeFileSync('.local/backup/category-backup.json', JSON.stringify(categories, null, 2));
console.log(`Category: ${categories.length} 条`);

// 备份 Work
const works = db.prepare('SELECT * FROM works').all();
fs.writeFileSync('.local/backup/works-backup.json', JSON.stringify(works, null, 2));
console.log(`Work: ${works.length} 条`);

const books = db.prepare('SELECT * FROM books').all();
fs.writeFileSync('.local/backup/books-backup.json', JSON.stringify(books, null, 2));
console.log(`Book: ${books.length} 条`);

const bookSeries = db.prepare('SELECT * FROM book_series').all();
fs.writeFileSync('.local/backup/book-series-backup.json', JSON.stringify(bookSeries, null, 2));
console.log(`BookSeries: ${bookSeries.length} 条`);

const bookPerson = db.prepare('SELECT * FROM book_person').all();
fs.writeFileSync('.local/backup/book-person-backup.json', JSON.stringify(bookPerson, null, 2));
console.log(`BookPerson: ${bookPerson.length} 条`);

const bookCategory = db.prepare('SELECT * FROM book_category').all();
fs.writeFileSync('.local/backup/book-category-backup.json', JSON.stringify(bookCategory, null, 2));
console.log(`BookCategory: ${bookCategory.length} 条`);

db.close();
console.log('\n备份完成！');
