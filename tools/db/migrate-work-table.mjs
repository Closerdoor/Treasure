import Database from 'better-sqlite3';
import fs from 'fs';
import path from 'path';

const db = new Database('.local/treasure.db');

// 备份原数据
const backupDir = '.local/backup';
if (!fs.existsSync(backupDir)) {
  fs.mkdirSync(backupDir, { recursive: true });
}

const oldWorks = db.prepare('SELECT * FROM works').all();
fs.writeFileSync(path.join(backupDir, 'works-backup.json'), JSON.stringify(oldWorks, null, 2));
console.log(`已备份 ${oldWorks.length} 条作品数据到 ${backupDir}/works-backup.json`);

// 数据转换函数
function transformWork(oldWork) {
  const newWork = {
    // 标识信息（不变）
    id: oldWork.id,
    module: oldWork.module,
    submodule: oldWork.submodule,
    schema_type: oldWork.schema_type,
    
    // 基本信息
    title: oldWork.title,
    title_original: oldWork.original_title,
    other_titles: oldWork.aliases_json,
    year: oldWork.year,
    country: oldWork.country,
    language: oldWork.language,
    total_time: oldWork.runtime_minutes,
    studio: oldWork.publish_company,
    release_dates: oldWork.release_dates_json,
    
    // quotes 转换：从对象数组改为字符串数组
    quotes: transformQuotes(oldWork.quotes_json),
    
    // scores（原 ratings_json）
    scores: transformScores(oldWork.ratings_json),
    
    // 剧集专用
    episode_count: oldWork.episode_count,
    episode_time: oldWork.episode_runtime_minutes,
    episodes_story: oldWork.episode_stories_json,
    
    // 内容文本
    introduction: oldWork.synopsis_text,
    story: oldWork.story_text,
    
    // externalSource 合并
    external_source: mergeExternalSource(oldWork.identifiers_json, oldWork.links_json),
    
    // 媒体资源
    images: oldWork.images_json,
    videos: oldWork.videos_json,
    
    // 评论内容
    comments: oldWork.reviews_json,
    
    // 音乐相关
    soundtrack: transformSoundtrack(oldWork.soundtrack_json),
    
    // 关联作品
    related: oldWork.relations_json,
    
    // 特殊内容
    characters: oldWork.characters_json,
    
    // 系统字段
    status: oldWork.status,
    created_at: oldWork.created_at,
    updated_at: oldWork.updated_at
  };
  
  return newWork;
}

// quotes 转换：[{text, speaker}] => ["text1", "text2"]
function transformQuotes(quotesJson) {
  if (!quotesJson) return null;
  try {
    const quotes = JSON.parse(quotesJson);
    if (!Array.isArray(quotes)) return quotesJson;
    
    // 如果已经是字符串数组，直接返回
    if (quotes.length > 0 && typeof quotes[0] === 'string') {
      return JSON.stringify(quotes);
    }
    
    // 如果是对象数组，提取 text
    const newQuotes = quotes.map(q => {
      if (typeof q === 'object' && q.text) {
        return q.text;
      }
      return q;
    });
    return JSON.stringify(newQuotes);
  } catch (e) {
    return quotesJson;
  }
}

// scores 转换：删除 certification 和 awards
function transformScores(ratingsJson) {
  if (!ratingsJson) return null;
  try {
    const ratings = JSON.parse(ratingsJson);
    const newScores = {};
    
    // 保留评分字段
    if (ratings.aggregate) newScores.avg = ratings.aggregate.value || ratings.aggregate;
    if (ratings.douban) newScores.douban = ratings.douban.value || ratings.douban;
    if (ratings.imdb) newScores.imdb = ratings.imdb.value || ratings.imdb;
    if (ratings.tmdb) newScores.tmdb = ratings.tmdb.value || ratings.tmdb;
    if (ratings.rottenTomatoes) newScores.rottenTomatoes = ratings.rottenTomatoes.value || ratings.rottenTomatoes;
    if (ratings.metascore) newScores.metacritic = ratings.metascore.value || ratings.metascore;
    
    // 删除 certification 和 awards
    
    return JSON.stringify(newScores);
  } catch (e) {
    return ratingsJson;
  }
}

// externalSource 合并：identifiers + links => [{name, id, link}]
function mergeExternalSource(identifiersJson, linksJson) {
  const sourceMap = {
    douban: '豆瓣',
    imdb: 'IMDb',
    tmdb: 'TMDB'
  };
  
  const ids = identifiersJson ? JSON.parse(identifiersJson) : {};
  const links = linksJson ? JSON.parse(linksJson) : {};
  
  const externalSource = [];
  
  for (const [key, name] of Object.entries(sourceMap)) {
    const id = ids[key] || ids.doubanId || ids.imdbId || ids.tmdbId || '';
    const link = links[key] || links.douban || links.imdb || links.tmdb || '';
    
    if (id || link) {
      externalSource.push({
        name: name,
        id: id,
        link: link
      });
    }
  }
  
  return externalSource.length > 0 ? JSON.stringify(externalSource) : null;
}

// soundtrack 转换：增加 cover 和 duration
function transformSoundtrack(soundtrackJson) {
  if (!soundtrackJson) return null;
  try {
    const soundtrack = JSON.parse(soundtrackJson);
    
    if (!soundtrack.albums) return soundtrackJson;
    
    const newAlbums = soundtrack.albums.map(album => ({
      name: album.name,
      cover: album.coverImage || album.cover || null,
      tracks: (album.tracks || []).map(track => ({
        name: track.name,
        artist: track.artist,
        duration: track.duration || null
      }))
    }));
    
    return JSON.stringify({ albums: newAlbums });
  } catch (e) {
    return soundtrackJson;
  }
}

// 开始迁移
console.log('\n开始迁移数据...\n');

// 1. 创建新表结构
db.exec(`
  -- 创建新的 works 表
  CREATE TABLE IF NOT EXISTS works_new (
    id TEXT PRIMARY KEY,
    module TEXT NOT NULL,
    submodule TEXT,
    schema_type TEXT NOT NULL,
    
    -- 基本信息
    title TEXT NOT NULL,
    title_original TEXT,
    other_titles TEXT,
    year INTEGER,
    country TEXT,
    language TEXT,
    total_time INTEGER,
    studio TEXT,
    release_dates TEXT,
    quotes TEXT,
    scores TEXT,
    
    -- 剧集专用
    episode_count INTEGER,
    episode_time INTEGER,
    episodes_story TEXT,
    
    -- 内容文本
    introduction TEXT,
    story TEXT,
    
    -- 外部来源
    external_source TEXT,
    
    -- 媒体资源
    images TEXT,
    videos TEXT,
    
    -- 评论内容
    comments TEXT,
    
    -- 音乐相关
    soundtrack TEXT,
    
    -- 关联作品
    related TEXT,
    
    -- 特殊内容
    characters TEXT,
    
    -- 系统字段
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  );
  
  -- 创建索引
  CREATE INDEX IF NOT EXISTS idx_works_new_module_submodule ON works_new (module, submodule);
  CREATE INDEX IF NOT EXISTS idx_works_new_schema_type ON works_new (schema_type);
  CREATE INDEX IF NOT EXISTS idx_works_new_status ON works_new (status);
  CREATE INDEX IF NOT EXISTS idx_works_new_year ON works_new (year);
`);

console.log('新表结构已创建');

// 2. 转换并插入数据
const insertStmt = db.prepare(`
  INSERT INTO works_new (
    id, module, submodule, schema_type,
    title, title_original, other_titles, year, country, language,
    total_time, studio, release_dates, quotes, scores,
    episode_count, episode_time, episodes_story,
    introduction, story,
    external_source,
    images, videos,
    comments,
    soundtrack,
    related,
    characters,
    status, created_at, updated_at
  ) VALUES (
    @id, @module, @submodule, @schema_type,
    @title, @title_original, @other_titles, @year, @country, @language,
    @total_time, @studio, @release_dates, @quotes, @scores,
    @episode_count, @episode_time, @episodes_story,
    @introduction, @story,
    @external_source,
    @images, @videos,
    @comments,
    @soundtrack,
    @related,
    @characters,
    @status, @created_at, @updated_at
  )
`);

const transaction = db.transaction((works) => {
  for (const oldWork of works) {
    const newWork = transformWork(oldWork);
    insertStmt.run(newWork);
    console.log(`已迁移: ${newWork.id} - ${newWork.title}`);
  }
});

transaction(oldWorks);

console.log('\n数据迁移完成');

// 3. 删除旧表，重命名新表
db.exec(`
  -- 删除旧表
  DROP TABLE works;
  
  -- 重命名新表
  ALTER TABLE works_new RENAME TO works;
`);

console.log('表已重命名');

// 4. 验证迁移结果
const newWorksCount = db.prepare('SELECT COUNT(*) as count FROM works').get();
console.log(`\n验证: 新表有 ${newWorksCount.count} 条数据`);

const sampleWork = db.prepare('SELECT id, title, quotes, scores, external_source FROM works WHERE id = ?').get('0101000001');
console.log('\n示例数据:');
console.log('ID:', sampleWork.id);
console.log('标题:', sampleWork.title);
console.log('quotes:', sampleWork.quotes);
console.log('scores:', sampleWork.scores);
console.log('external_source:', sampleWork.external_source);

db.close();

console.log('\n迁移完成！');