import Database from 'better-sqlite3';

const db = new Database('.local/treasure.db');

console.log('=== 更新数据库图片路径 ===\n');

// 1. 更新 Person 表的 avatarPath
console.log('更新 Person 表...');
const people = db.prepare('SELECT id, person_id, avatar_path FROM people WHERE avatar_path IS NOT NULL').all();
console.log(`找到 ${people.length} 条有头像的人物记录`);

for (const person of people) {
  // 旧路径: people/p000001-avatar.png
  // 新路径: .local/assets/people/p000001-avatar.png
  const oldPath = person.avatar_path;
  const newPath = `.local/assets/${oldPath}`;
  
  db.prepare('UPDATE people SET avatar_path = ? WHERE id = ?').run(newPath, person.id);
}
console.log('Person 表更新完成');

// 2. 更新 Work 表的 images 字段
console.log('\n更新 Work 表...');
const works = db.prepare("SELECT id, images FROM works WHERE images IS NOT NULL").all();
console.log(`找到 ${works.length} 条有图片的作品记录`);

for (const work of works) {
  if (!work.images) continue;
  
  const imagesObj = JSON.parse(work.images);
  
  // 更新 assetDir
  if (imagesObj.assetDir) {
    imagesObj.assetDir = `.local/assets/${imagesObj.assetDir}`;
  }
  
  // poster 路径不需要更新（相对路径）
  // posters, stills, wallpapers 数组中的路径也不需要更新（相对路径）
  
  db.prepare('UPDATE works SET images = ? WHERE id = ?').run(JSON.stringify(imagesObj), work.id);
}
console.log('Work 表更新完成');

// 3. 验证更新结果
console.log('\n=== 验证更新结果 ===\n');

const samplePerson = db.prepare('SELECT person_id, avatar_path FROM people WHERE avatar_path IS NOT NULL LIMIT 3').all();
console.log('Person 示例:');
samplePerson.forEach(p => console.log(`  ${p.person_id}: ${p.avatar_path}`));

const sampleWork = db.prepare("SELECT id, images FROM works WHERE images IS NOT NULL LIMIT 1").get();
if (sampleWork) {
  const images = JSON.parse(sampleWork.images);
  console.log(`\nWork 示例 (${sampleWork.id}):`);
  console.log(`  assetDir: ${images.assetDir}`);
  console.log(`  poster: ${images.poster}`);
  console.log(`  posters count: ${images.posters?.length || 0}`);
}

db.close();
console.log('\n路径更新完成！');
