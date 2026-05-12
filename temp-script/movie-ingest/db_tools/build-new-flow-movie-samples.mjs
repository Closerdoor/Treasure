import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { inferPrimaryCountry, parseTmdbIdFromUrl } from './movie-db-projection.mjs';

import { PATHS } from './paths.mjs';

const repoRoot = PATHS.repoRoot;
const legacyMovieRoot = PATHS.stagingDir;
const legacySourceRoot = PATHS.stagingDir;
const newMovieRoot = PATHS.stagingDir;
const newSourceRoot = PATHS.stagingDir;

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function makeSystemEntry(value, note) {
  return {
    value,
    source: 'system',
    note
  };
}

function makeDerivedEntry(value, sourceUrl, note) {
  return {
    value,
    source: 'derived',
    sourceUrl,
    note
  };
}

function normalizeStory(story) {
  if (!story) {
    return { text: null };
  }

  return {
    text: story.text ?? null
  };
}

function normalizeSoundtrack(soundtrack) {
  if (!soundtrack) {
    return null;
  }

  return {
    albums: [
      {
        name: soundtrack.name ?? null,
        note: [soundtrack.note ?? null, soundtrack.composer ? `${soundtrack.composer}${soundtrack.composerEn ? ` / ${soundtrack.composerEn}` : ''}` : null].filter(Boolean).join(' | ') || null,
        coverImage: soundtrack.coverImage ?? null,
        releaseDate: soundtrack.releaseDate ?? (soundtrack.year ? String(soundtrack.year) : null),
        type: soundtrack.type ?? 'soundtrack',
        tracks: Array.isArray(soundtrack.tracks)
          ? soundtrack.tracks.map((track) => ({
              name: track.name,
              artist: track.artist ?? null,
              duration: track.duration ?? null
            }))
          : []
      }
    ]
  };
}

function buildReviewMetadataByMovieId(movieId) {
  if (movieId === '0101000001') {
    return [
      { title: '十年·肖申克的救赎', url: 'https://movie.douban.com/review/1000369/' },
      { title: '终于找到了郁闷人生的原因――观《肖申克的救赎》有�?, url: 'https://movie.douban.com/review/1001258/' },
      { title: '《肖申克的救赎》到底“救赎”了什么？', url: 'https://movie.douban.com/review/10350620/' },
      { title: '《肖申克的救赎》：1994�?007，希望就是现�?, url: 'https://movie.douban.com/review/1127585/' }
    ];
  }

  if (movieId === '0101000003') {
    return [
      { title: '阿甘的爱�?, url: 'https://movie.douban.com/review/1436379/' },
      { title: '飘飞的羽�?, url: 'https://movie.douban.com/review/1000747/' },
      { title: '一羽人�?, url: 'https://movie.douban.com/review/1012226/' },
      { title: '每个人心中都有自己的阿甘', url: 'https://movie.douban.com/review/2803231/' }
    ];
  }

  if (movieId === '0101000002') {
    return [
      { title: '优秀的制作，勉强及格的MJ，不合格的电影�?, url: 'https://movie.douban.com/review/17567525/' },
      { title: '老粉的失�?, url: 'https://movie.douban.com/review/17567438/' },
      { title: '值得去影院一听，但作为电影配不上流行音乐之王的地�?, url: 'https://movie.douban.com/review/17566820/' },
      { title: '终于懂了！为什么我的偶像会说MJ是他们的偶像�?, url: 'https://movie.douban.com/review/17565826/' }
    ];
  }

  if (movieId === '0101000004') {
    return [
      { title: '最懂蝶衣袁四爷', url: 'https://movie.douban.com/review/1380398/' },
      { title: '关于《霸王别姬�?', url: 'https://movie.douban.com/review/1025873/' },
      { title: '迷恋与背叛——[霸王别姬]', url: 'https://movie.douban.com/review/1049362/' },
      { title: '胡说霸王别姬', url: 'https://movie.douban.com/review/1356540/' }
    ];
  }

  return [];
}

function normalizeReviews(movie) {
  const metadata = buildReviewMetadataByMovieId(movie.id);
  return (Array.isArray(movie.reviews) ? movie.reviews : []).map((review, index) => ({
    author: review.author ?? null,
    source: review.source ?? null,
    date: review.date ?? null,
    content: review.content ?? null,
    url: review.url ?? metadata[index]?.url ?? null,
    title: review.title ?? metadata[index]?.title ?? null
  }));
}

function inferPublishCompany(movie, fieldSources) {
  if (movie.publishCompany ?? movie.publish_company ?? movie.productionCompany) {
    return movie.publishCompany ?? movie.publish_company ?? movie.productionCompany;
  }

  if (movie.id === '0101000002') {
    return ['狮门电影公司', '环球影片公司'];
  }

  if (movie.id === '0101000003') {
    return 'The Tisch Company';
  }

  return null;
}

async function main() {
  const files = (await fs.readdir(legacyMovieRoot)).filter((name) => name.endsWith('.json')).sort();
  await fs.mkdir(newMovieRoot, { recursive: true });
  await fs.mkdir(newSourceRoot, { recursive: true });

  for (const fileName of files) {
    const movie = JSON.parse(await fs.readFile(path.join(legacyMovieRoot, fileName), 'utf8'));
    const fieldSources = JSON.parse(await fs.readFile(path.join(legacySourceRoot, fileName), 'utf8'));

    const tmdbId = movie.tmdbId ?? parseTmdbIdFromUrl(movie.links?.tmdb);
    const publishCompany = inferPublishCompany(movie, fieldSources);
    const newMovie = {
      ...movie,
      schemaType: 'live_action_movie',
      status: movie.status ?? 'published',
      publishCompany,
      tags: Array.isArray(movie.tags) ? movie.tags : [],
      series: Array.isArray(movie.series) ? movie.series : [],
      tmdbId,
      quotes: Array.isArray(movie.quotes) ? movie.quotes : [],
      country: inferPrimaryCountry(movie),
      story: normalizeStory(movie.story),
      soundtrack: normalizeSoundtrack(movie.soundtrack),
      reviews: normalizeReviews(movie)
    };

    const newSources = clone(fieldSources);
    newSources.schemaType = makeSystemEntry('live_action_movie', '电影样板当前固定写入 live_action_movie');
    newSources.status = makeSystemEntry(newMovie.status, '当前电影样板默认�?published 导入');
    if (movie.id === '0101000002') {
      newSources.publishCompany = {
        value: publishCompany,
        source: 'baike',
        sourceUrl: 'content/video/movie/0101000002/raw/baike-full.json',
        note: '来自百度百科基本信息�?发行公司'
      };
    } else if (movie.id === '0101000003') {
      newSources.publishCompany = {
        value: publishCompany,
        source: 'wikipedia',
        sourceUrl: 'content/video/movie/0101000003/raw/wikipedia-en-full.html',
        note: '来自英文维基 infobox Production company'
      };
    } else {
      newSources.publishCompany = makeSystemEntry(newMovie.publishCompany, '当前样板缺少稳定出品公司来源，先保留空�?);
    }
    newSources.tags = makeSystemEntry(newMovie.tags, '当前4条样板尚未建立标签体系，先保留空数组');
    newSources.series = makeSystemEntry(newMovie.series, '当前4条样板未录入系列关系，先保留空数�?);
    newSources.quotes = makeSystemEntry(newMovie.quotes, '当前4条样板未整理 quotes，先保留空数�?);
    newSources.tmdbId = tmdbId
      ? makeDerivedEntry(tmdbId, newMovie.links?.tmdb ?? null, '�?links.tmdb URL 解析�?TMDB movie id')
      : makeSystemEntry(null, '当前样板未提供可解析�?TMDB id');

    if (newSources.story?.value && typeof newSources.story.value === 'object' && 'note' in newSources.story.value) {
      delete newSources.story.value.note;
      if (newSources.story.note) {
        newSources.story.note = `${newSources.story.note}；story.note 不再进入数据库主字段`;
      } else {
        newSources.story.note = 'story.note 不再进入数据库主字段';
      }
    }

    if (newSources.reviews?.source === 'douban') {
      newSources.reviews.note = `${newSources.reviews.note || '豆瓣影评页长�?}；已�?review.url/title，全文保留，rating 不再进入数据库`;
    }

    if (newSources.country) {
      newSources.country.value = newMovie.country;
      newSources.country.note = '地区按最早公映地区推断，仅保留单一地区值；电影节与首映场次不作为首发地区依�?;
    }

    if (newSources.soundtrack) {
      newSources.soundtrack.note = `${newSources.soundtrack.note || '原声带信�?}；已重组�?albums[] 结构`;
    }

    await fs.writeFile(path.join(newMovieRoot, fileName), `${JSON.stringify(newMovie, null, 2)}\n`, 'utf8');
    await fs.writeFile(path.join(newSourceRoot, fileName), `${JSON.stringify(newSources, null, 2)}\n`, 'utf8');
  }

  console.log(`movies=${files.length}`);
  console.log(`records=${path.relative(repoRoot, newMovieRoot).replace(/\\/g, '/')}`);
  console.log(`sources=${path.relative(repoRoot, newSourceRoot).replace(/\\/g, '/')}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
