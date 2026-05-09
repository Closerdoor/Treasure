import Database from 'better-sqlite3';
import fs from 'fs';

const db = new Database('.local/treasure.db');

console.log('=== 恢复数据库 ===\n');

// 1. 读取备份
const peopleBackup = JSON.parse(fs.readFileSync('.local/backup/people-backup.json', 'utf-8'));
const termsBackup = JSON.parse(fs.readFileSync('.local/backup/terms-backup.json', 'utf-8'));
const worksBackup = JSON.parse(fs.readFileSync('.local/backup/works-backup.json', 'utf-8'));

console.log(`Person: ${peopleBackup.length} 条`);
console.log(`Term: ${termsBackup.length} 条`);
console.log(`Work: ${worksBackup.length} 条`);

// 2. 删除所有旧表
console.log('\n删除旧表...');
db.exec(`DROP TABLE IF EXISTS work_categories`);
db.exec(`DROP TABLE IF EXISTS work_terms`);
db.exec(`DROP TABLE IF EXISTS work_credits`);
db.exec(`DROP TABLE IF EXISTS work_types`);
db.exec(`DROP TABLE IF EXISTS terms`);
db.exec(`DROP TABLE IF EXISTS people`);
db.exec(`DROP TABLE IF EXISTS _prisma_migrations`);

// 3. 创建 Person 表（旧结构）
console.log('创建 Person 表...');
db.exec(`
  CREATE TABLE people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    name_en TEXT,
    avatar_path TEXT,
    profile_link TEXT,
    notes TEXT,
    extra TEXT
  )
`);
db.exec(`CREATE INDEX idx_people_name ON people(name, name_en)`);

// 4. 创建 Term 表（旧结构）
console.log('创建 Term 表...');
db.exec(`
  CREATE TABLE terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term_type TEXT NOT NULL,
    name TEXT NOT NULL,
    module_scope TEXT,
    submodule_scope TEXT,
    description TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1
  )
`);
db.exec(`CREATE INDEX idx_terms_scope ON terms(term_type, module_scope, submodule_scope, sort_order)`);
db.exec(`CREATE INDEX idx_terms_identity ON terms(term_type, name, module_scope, submodule_scope)`);

// 5. 恢复 Person 数据
console.log('\n恢复 Person 数据...');
const insertPerson = db.prepare(`
  INSERT INTO people (id, person_code, name, name_en, avatar_path, profile_link, notes, extra)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?)
`);
for (const person of peopleBackup) {
  insertPerson.run(
    person.id,
    person.person_code,
    person.name,
    person.name_en,
    person.avatar_path,
    person.profile_link,
    person.notes,
    person.extra
  );
}
console.log(`Person 恢复完成: ${peopleBackup.length} 条`);

// 6. 恢复 Term 数据
console.log('恢复 Term 数据...');
const insertTerm = db.prepare(`
  INSERT INTO terms (id, term_type, name, module_scope, submodule_scope, description, sort_order, is_active)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?)
`);
for (const term of termsBackup) {
  insertTerm.run(
    term.id,
    term.term_type,
    term.name,
    term.module_scope,
    term.submodule_scope,
    term.description,
    term.sort_order,
    term.is_active
  );
}
console.log(`Term 恢复完成: ${termsBackup.length} 条`);

// 7. 验证
const personCount = db.prepare('SELECT COUNT(*) as count FROM people').get();
const termCount = db.prepare('SELECT COUNT(*) as count FROM terms').get();

console.log('\n=== 验证 ===');
console.log(`Person: ${personCount.count} 条`);
console.log(`Term: ${termCount.count} 条`);

db.close();
console.log('\n恢复完成！');
