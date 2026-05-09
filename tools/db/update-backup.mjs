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

db.close();
console.log('\n备份完成！');
