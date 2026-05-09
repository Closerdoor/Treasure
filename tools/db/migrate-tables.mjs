import Database from 'better-sqlite3';
import fs from 'fs';

const db = new Database('.local/treasure.db');

console.log('=== 开始迁移数据 ===\n');

// 1. 读取备份的 Person 数据
const peopleBackup = JSON.parse(fs.readFileSync('.local/backup/people-backup.json', 'utf-8'));
console.log(`读取 Person 备份: ${peopleBackup.length} 条`);

// 2. 读取备份的 Term 数据
const termsBackup = JSON.parse(fs.readFileSync('.local/backup/terms-backup.json', 'utf-8'));
console.log(`读取 Term 备份: ${termsBackup.length} 条`);

// 3. 删除旧表
console.log('\n删除旧表...');
db.exec(`DROP TABLE IF EXISTS work_terms`);
db.exec(`DROP TABLE IF EXISTS work_credits`);
db.exec(`DROP TABLE IF EXISTS terms`);
db.exec(`DROP TABLE IF EXISTS people`);

// 4. 创建新表
console.log('创建新表...');

// Person 表
db.exec(`
  CREATE TABLE people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    name_en TEXT,
    avatar_path TEXT,
    profile_link TEXT,
    intro TEXT
  )
`);
db.exec(`CREATE INDEX idx_people_name ON people(name, name_en)`);

// WorkCredit 表
db.exec(`
  CREATE TABLE work_credits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id TEXT NOT NULL,
    person_id INTEGER NOT NULL,
    department TEXT NOT NULL,
    role TEXT,
    character TEXT,
    "order" INTEGER NOT NULL DEFAULT 0,
    is_primary INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE RESTRICT
  )
`);
db.exec(`CREATE INDEX idx_work_credits_work_id ON work_credits(work_id, "order")`);
db.exec(`CREATE INDEX idx_work_credits_person_id ON work_credits(person_id)`);

// WorkType 表
db.exec(`
  CREATE TABLE work_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    "group" TEXT NOT NULL,
    name TEXT NOT NULL,
    module TEXT,
    submodule TEXT,
    "order" INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1
  )
`);
db.exec(`CREATE INDEX idx_work_types_scope ON work_types("group", module, submodule, "order")`);
db.exec(`CREATE INDEX idx_work_types_identity ON work_types("group", name, module, submodule)`);

// WorkCategory 表
db.exec(`
  CREATE TABLE work_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id TEXT NOT NULL,
    type_id INTEGER NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE,
    FOREIGN KEY (type_id) REFERENCES work_types(id) ON DELETE CASCADE,
    UNIQUE(work_id, type_id)
  )
`);
db.exec(`CREATE INDEX idx_work_categories_work_id ON work_categories(work_id, "order")`);
db.exec(`CREATE INDEX idx_work_categories_type_id ON work_categories(type_id)`);

// 5. 迁移 Person 数据
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

// 6. 迁移 Term 数据到 WorkType
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

// 7. 验证数据
console.log('\n=== 验证迁移结果 ===\n');

const personCount = db.prepare('SELECT COUNT(*) as count FROM people').get();
const workTypeCount = db.prepare('SELECT COUNT(*) as count FROM work_types').get();

console.log(`Person: ${personCount.count} 条`);
console.log(`WorkType: ${workTypeCount.count} 条`);

// 查看一条示例数据
const samplePerson = db.prepare('SELECT * FROM people LIMIT 1').get();
console.log('\nPerson 示例:', samplePerson);

const sampleType = db.prepare('SELECT * FROM work_types LIMIT 1').get();
console.log('\nWorkType 示例:', sampleType);

db.close();
console.log('\n迁移完成！');
