import Database from 'better-sqlite3';
import fs from 'fs';

const db = new Database('.local/treasure.db');

console.log('=== 迁移数据 ===\n');

// 读取备份
const peopleBackup = JSON.parse(fs.readFileSync('.local/backup/people-backup.json', 'utf-8'));
const termsBackup = JSON.parse(fs.readFileSync('.local/backup/terms-backup.json', 'utf-8'));

console.log(`Person 备份: ${peopleBackup.length} 条`);
console.log(`Term 备份: ${termsBackup.length} 条`);

// 清空表
console.log('\n清空表...');
db.exec(`DELETE FROM work_categories`);
db.exec(`DELETE FROM work_credits`);
db.exec(`DELETE FROM work_types`);
db.exec(`DELETE FROM people`);

// 迁移 Person 数据
console.log('\n迁移 Person 数据...');
const insertPerson = db.prepare(`
  INSERT INTO people (id, person_id, name, name_en, avatar_path, profile_link, intro)
  VALUES (?, ?, ?, ?, ?, ?, ?)
`);
for (const person of peopleBackup) {
  insertPerson.run(
    person.id,
    person.person_code,
    person.name,
    person.name_en,
    person.avatar_path,
    person.profile_link,
    person.notes || null
  );
}
console.log(`Person 迁移完成: ${peopleBackup.length} 条`);

// 迁移 Term 数据到 WorkType
console.log('\n迁移 Term 数据到 WorkType...');
const insertType = db.prepare(`
  INSERT INTO work_types (id, "group", name, module, submodule, "order", enabled)
  VALUES (?, ?, ?, ?, ?, ?, ?)
`);
for (const term of termsBackup) {
  insertType.run(
    term.id,
    term.term_type === 'genre' ? 'type' : 'tag',
    term.name,
    term.module_scope,
    term.submodule_scope,
    term.sort_order,
    term.is_active ? 1 : 0
  );
}
console.log(`WorkType 迁移完成: ${termsBackup.length} 条`);

// 验证
console.log('\n=== 验证 ===\n');
const personCount = db.prepare('SELECT COUNT(*) as count FROM people').get();
const workTypeCount = db.prepare('SELECT COUNT(*) as count FROM work_types').get();
console.log(`Person: ${personCount.count} 条`);
console.log(`WorkType: ${workTypeCount.count} 条`);

// 示例数据
const samplePerson = db.prepare('SELECT * FROM people LIMIT 1').get();
console.log('\nPerson 示例:', samplePerson);

const sampleType = db.prepare('SELECT * FROM work_types').all();
console.log('\nWorkType 全部:', sampleType);

db.close();
console.log('\n迁移完成！');
