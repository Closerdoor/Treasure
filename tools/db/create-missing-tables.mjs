import Database from 'better-sqlite3';

const db = new Database('.local/treasure.db');

console.log('=== 创建缺失的表 ===\n');

// 检查现有表
const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all();
console.log('现有表:', tables.map(t => t.name).join(', '));

// 创建 work_categories 表
console.log('\n创建 work_categories 表...');
db.exec(`
  CREATE TABLE IF NOT EXISTS work_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id TEXT NOT NULL,
    type_id INTEGER NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE,
    FOREIGN KEY (type_id) REFERENCES work_types(id) ON DELETE CASCADE,
    UNIQUE(work_id, type_id)
  )
`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_work_categories_work_id ON work_categories(work_id, "order")`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_work_categories_type_id ON work_categories(type_id)`);

// 验证
const newTables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all();
console.log('\n更新后表:', newTables.map(t => t.name).join(', '));

db.close();
console.log('\n完成！');
