import Database from 'better-sqlite3';

const db = new Database('.local/treasure.db');

// 查询作品数量
const workCount = db.prepare('SELECT COUNT(*) as count FROM works').get();
console.log('作品总数:', workCount.count);

// 查询所有作品
const works = db.prepare(`
  SELECT id, title, year, country, status 
  FROM works
`).all();

console.log('\n作品列表:');
works.forEach(w => {
  console.log(`- ${w.id}: ${w.title} (${w.year || '未知'}) - ${w.country || '未知'} [${w.status}]`);
});

// 查询人物数量
const personCount = db.prepare('SELECT COUNT(*) as count FROM people').get();
console.log('\n人物总数:', personCount.count);

// 查询词项数量
const termCount = db.prepare('SELECT COUNT(*) as count FROM terms').get();
console.log('词项总数:', termCount.count);

// 查询作品人物关系数量
const creditCount = db.prepare('SELECT COUNT(*) as count FROM work_credits').get();
console.log('作品人物关系总数:', creditCount.count);

db.close();