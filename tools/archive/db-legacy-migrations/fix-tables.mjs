import Database from 'better-sqlite3';

const db = new Database('.local/treasure.db');

console.log('=== 修复数据库表结构 ===\n');

// 检查当前表
const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").all();
console.log('当前表:', tables.map(t => t.name).join(', '));

// 检查 work_category 表结构
const workCategoryColumns = db.prepare("PRAGMA table_info(work_category)").all();
console.log('work_category 字段:', workCategoryColumns.map(c => c.name).join(', '));

// 如果有 type_id 字段，重命名为 category_id
if (workCategoryColumns.some(c => c.name === 'type_id')) {
  console.log('\n重命名字段 type_id -> category_id');
  db.exec(`ALTER TABLE work_category RENAME COLUMN type_id TO category_id`);
}

// 删除旧索引
console.log('\n删除旧索引...');
const indexes = db.prepare("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'").all();
for (const idx of indexes) {
  db.exec(`DROP INDEX IF EXISTS "${idx.name}"`);
  console.log(`  删除: ${idx.name}`);
}

// 创建新索引
console.log('\n创建新索引...');
db.exec(`CREATE INDEX idx_person_name ON person(name, name_en)`);
console.log('  创建: idx_person_name');

db.exec(`CREATE INDEX idx_work_person_work_id ON work_person(work_id, "order")`);
console.log('  创建: idx_work_person_work_id');

db.exec(`CREATE INDEX idx_work_person_person_id ON work_person(person_id)`);
console.log('  创建: idx_work_person_person_id');

db.exec(`CREATE INDEX idx_category_scope ON category("group", module, submodule, "order")`);
console.log('  创建: idx_category_scope');

db.exec(`CREATE INDEX idx_category_identity ON category("group", name, module, submodule)`);
console.log('  创建: idx_category_identity');

db.exec(`CREATE INDEX idx_work_category_work_id ON work_category(work_id, "order")`);
console.log('  创建: idx_work_category_work_id');

db.exec(`CREATE INDEX idx_work_category_category_id ON work_category(category_id)`);
console.log('  创建: idx_work_category_category_id');

// 验证
console.log('\n=== 验证结果 ===\n');

const personCount = db.prepare('SELECT COUNT(*) as count FROM person').get();
const categoryCount = db.prepare('SELECT COUNT(*) as count FROM category').get();
const workCount = db.prepare('SELECT COUNT(*) as count FROM works').get();

console.log(`数据:`);
console.log(`  person: ${personCount.count} 条`);
console.log(`  category: ${categoryCount.count} 条`);
console.log(`  works: ${workCount.count} 条`);

const newIndexes = db.prepare("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'").all();
console.log('\n索引:', newIndexes.map(i => i.name).join(', '));

const newWorkCategoryColumns = db.prepare("PRAGMA table_info(work_category)").all();
console.log('work_category 字段:', newWorkCategoryColumns.map(c => c.name).join(', '));

db.close();
console.log('\n修复完成！');