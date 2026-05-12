import Database from 'better-sqlite3';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const db = new Database(join(__dirname, '../.local/treasure.db'));

// 创建 books 表
db.exec(`
CREATE TABLE IF NOT EXISTS books (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  title_original TEXT,
  other_titles TEXT,
  isbn TEXT UNIQUE,
  year INTEGER,
  country TEXT,
  language TEXT,
  word_count INTEGER,
  publisher TEXT,
  summary TEXT,
  quotes TEXT,
  series_id TEXT,
  series_order INTEGER,
  scores TEXT,
  external_source TEXT,
  images TEXT,
  reviews TEXT,
  related TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL
);
`);

// 创建 book_series 表
db.exec(`
CREATE TABLE IF NOT EXISTS book_series (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  name_original TEXT,
  book_count INTEGER,
  summary TEXT,
  images TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL
);
`);

// 创建 book_person 表
db.exec(`
CREATE TABLE IF NOT EXISTS book_person (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id TEXT NOT NULL,
  person_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  "order" INTEGER NOT NULL DEFAULT 0,
  is_primary BOOLEAN NOT NULL DEFAULT 0,
  UNIQUE(book_id, person_id, role),
  FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
  FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE RESTRICT
);
`);

// 创建 book_category 表
db.exec(`
CREATE TABLE IF NOT EXISTS book_category (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id TEXT NOT NULL,
  category_id INTEGER NOT NULL,
  "order" INTEGER NOT NULL DEFAULT 0,
  UNIQUE(book_id, category_id),
  FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
  FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE CASCADE
);
`);

// 创建索引
db.exec('CREATE INDEX IF NOT EXISTS idx_books_year ON books(year)');
db.exec('CREATE INDEX IF NOT EXISTS idx_books_status ON books(status)');
db.exec('CREATE INDEX IF NOT EXISTS idx_book_person_book_id ON book_person(book_id, "order")');
db.exec('CREATE INDEX IF NOT EXISTS idx_book_category_book_id ON book_category(book_id, "order")');

console.log('Tables created successfully');

// 验证
const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'book%'").all();
console.log('Book tables:', tables.map(t => t.name));

db.close();
