import fs from 'node:fs/promises';
import path from 'node:path';
import Database from 'better-sqlite3';
import { PATHS } from './paths.mjs';

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith('--')) {
      args[key] = true;
      continue;
    }
    args[key] = next;
    index += 1;
  }
  return args;
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, 'utf8'));
}

function buildExternalSource(movie) {
  const sources = [];
  
  if (movie.doubanId) {
    sources.push({
      name: '豆瓣',
      id: movie.doubanId,
      link: `https://movie.douban.com/subject/${movie.doubanId}/`
    });
  }
  
  if (movie.imdbId) {
    sources.push({
      name: 'IMDb',
      id: movie.imdbId,
      link: `https://www.imdb.com/title/${movie.imdbId}/`
    });
  }
  
  if (movie.tmdbId) {
    sources.push({
      name: 'TMDB',
      id: String(movie.tmdbId),
      link: `https://www.themoviedb.org/movie/${movie.tmdbId}`
    });
  }
  
  return sources.length > 0 ? JSON.stringify(sources) : null;
}

function buildScores(movie) {
  const scores = {};
  
  if (movie.doubanRating) scores.douban = movie.doubanRating;
  if (movie.imdbRating) scores.imdb = movie.imdbRating;
  if (movie.tmdbRating) scores.tmdb = movie.tmdbRating;
  if (movie.rottenTomatoes) scores.rottenTomatoes = movie.rottenTomatoes;
  if (movie.metascore) scores.metacritic = movie.metascore;
  if (movie.rated) scores.certification = movie.rated;
  if (movie.awards) scores.awards = movie.awards;
  
  const validRatings = [scores.douban, scores.imdb, scores.tmdb, scores.rottenTomatoes, scores.metacritic].filter(v => typeof v === 'number');
  if (validRatings.length > 0) {
    scores.avg = Math.round((validRatings.reduce((a, b) => a + b, 0) / validRatings.length) * 10) / 10;
  }
  
  return Object.keys(scores).length > 0 ? JSON.stringify(scores) : null;
}

async function importMovie(workId, db) {
  const stagingPath = path.join(PATHS.stagingDir, `${workId}.json`);
  
  try {
    const movie = await readJson(stagingPath);
    
    const stmt = db.prepare(`
      INSERT INTO works (
        id, module, submodule, schema_type, title, title_original,
        year, country, language, total_time, studio,
        introduction, story, other_titles, release_dates,
        external_source, scores, images, videos, comments,
        soundtrack, related, quotes, status, created_at, updated_at
      ) VALUES (
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?
      )
      ON CONFLICT(id) DO UPDATE SET
        title = excluded.title,
        title_original = COALESCE(excluded.title_original, works.title_original),
        year = COALESCE(excluded.year, works.year),
        country = COALESCE(excluded.country, works.country),
        language = COALESCE(excluded.language, works.language),
        total_time = COALESCE(excluded.total_time, works.total_time),
        introduction = COALESCE(excluded.introduction, works.introduction),
        story = COALESCE(excluded.story, works.story),
        images = COALESCE(excluded.images, works.images),
        videos = COALESCE(excluded.videos, works.videos),
        comments = COALESCE(excluded.comments, works.comments),
        scores = COALESCE(excluded.scores, works.scores),
        external_source = COALESCE(excluded.external_source, works.external_source),
        updated_at = excluded.updated_at
    `);
    
    const now = new Date().toISOString();
    
    stmt.run(
      movie.id || workId,
      movie.module || 'video',
      movie.submodule || 'movie',
      movie.schemaType || 'live_action_movie',
      movie.title,
      movie.originalTitle || null,
      movie.year || null,
      movie.country || null,
      movie.language || null,
      movie.runtime || null,
      movie.publishCompany || null,
      movie.synopsis || null,
      movie.story || null,
      movie.aka ? JSON.stringify(movie.aka) : null,
      movie.releaseDate ? JSON.stringify(movie.releaseDate) : null,
      buildExternalSource(movie),
      buildScores(movie),
      movie.images ? JSON.stringify(movie.images) : null,
      movie.videos ? JSON.stringify(movie.videos) : null,
      movie.reviews ? JSON.stringify(movie.reviews) : null,
      movie.soundtrack ? JSON.stringify(movie.soundtrack) : null,
      movie.similar ? JSON.stringify(movie.similar) : null,
      movie.quotes ? JSON.stringify(movie.quotes) : null,
      movie.status || 'published',
      now,
      now
    );
    
    return { success: true, workId, title: movie.title };
  } catch (error) {
    return { success: false, workId, error: error.message };
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  
  if (!args['work-id'] && !args.all) {
    console.log('Usage: node db_tools/import-movie.mjs --work-id <id>');
    console.log('       node db_tools/import-movie.mjs --all');
    process.exit(1);
  }
  
  const db = new Database(PATHS.dbPath);
  db.pragma('journal_mode = WAL');
  
  try {
    if (args.all) {
      const files = (await fs.readdir(PATHS.stagingDir)).filter(f => f.endsWith('.json'));
      const results = [];
      
      for (const file of files) {
        const workId = path.basename(file, '.json');
        const result = await importMovie(workId, db);
        results.push(result);
      }
      
      const succeeded = results.filter(r => r.success);
      const failed = results.filter(r => !r.success);
      
      console.log(JSON.stringify({
        total: results.length,
        succeeded: succeeded.length,
        failed: failed.length,
        results
      }, null, 2));
    } else {
      const result = await importMovie(args['work-id'], db);
      console.log(JSON.stringify(result, null, 2));
      
      if (!result.success) {
        process.exitCode = 1;
      }
    }
  } finally {
    db.close();
  }
}

main().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
