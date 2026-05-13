import Database from 'better-sqlite3';

const db = new Database('.local/treasure.db');

console.log('=== 重命名数据库表 ===\n');

// 1. 重命名 people -> person
console.log('1. people -> person');
db.exec(`ALTER TABLE people RENAME TO person`);

// 2. 重命名 work_credits -> work_person
console.log('2. work_credits -> work_person');
db.exec(`ALTER TABLE work_credits RENAME TO work_person`);

// 3. 重命名 work_types -> category
console.log('3. work_types -> category');
db.exec(`ALTER TABLE work_types RENAME TO category`);

// 4. 重命名 work_categories -> work_category
console.log('4. work_categories -> work_category');
db.exec(`ALTER TABLE work_categories RENAME TO work_category`);

// 5. 重命名字段 type_id -> category_id
console.log('\n重命名字段 type_id -> category_id');
db.exec(`ALTER TABLE work_category RENAME COLUMN type_id TO category_id`);

// 6. 更新索引名称
console.log('\n更新索引名称...');

// 删除旧索引
db.exec(`DROP INDEX IF EXISTS idx_people_name`);
db.exec(`DROP INDEX IF EXISTS idx_work_credits_work_id`);
db.exec(`DROP INDEX IF EXISTS idx_work_credits_person_id`);
db.exec(`DROP INDEX IF EXISTS idx_work_types_scope`);
db.exec(`DROP INDEX IF EXISTS idx_work_types_identity`);
db.exec(`DROP INDEX IF EXISTS idx_work_categories_work_id`);
db.exec(`DROP INDEX IF EXISTS idx_work_categories_type_id`);

// 创建新索引
db.exec(`CREATE INDEX idx_person_name ON person(name, name_en)`);
db.exec(`CREATE INDEX idx_work_person_work_id ON work_person(work_id, "order")`);
db.exec(`CREATE INDEX idx_work_person_person_id ON work_person(person_id)`);
db.exec(`CREATE INDEX idx_category_scope ON category("group", module, submodule, "order")`);
db.exec(`CREATE INDEX idx_category_identity ON category("group", name, module, submodule)`);
db.exec(`CREATE INDEX idx_work_category_work_id ON work_category(work_id, "order")`);
db.exec(`CREATE INDEX idx_work_category_category_id ON work_category(category_id)`);

// 7. 验证
console.log('\n=== 验证表结构 ===\n');
const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").all();
console.log('表列表:', tables.map(t => t.name).join(', '));

// 验证数据
const personCount = db.prepare('SELECT COUNT(*) as count FROM person').get();
const categoryCount = db.prepare('SELECT COUNT(*) as count FROM category').get();
const workCount = db.prepare('SELECT COUNT(*) as count FROM works').get();

console.log(`\n数据验证:`);
console.log(`  person: ${personCount.count} 条`);
console.log(`  category: ${categoryCount.count} 条`);
console.log(`  works: ${workCount.count} 条`);

// 验证 work_category 表结构
const workCategoryColumns = db.prepare("PRAGMA table_info(work_category)").all();
console.log('\nwork_category 表字段:', workCategoryColumns.map(c => c.name).join(', '));

db.close();
console.log('\n表重命名完成！');
