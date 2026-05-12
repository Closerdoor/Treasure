import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { PATHS } from './paths.mjs';
import { buildDbProjection, buildRatingsJson, buildImagesJson, buildLinksJson, buildRelationsJson, buildSoundtrackJson, inferPrimaryCountry } from './movie-db-projection.mjs';
import { validateRecordShape } from './validate-movie-record.mjs';
import { MOVIE_INTAKE_CONFIGS_BY_DOUBAN_ID } from './movie-intake-registry.mjs';

const repoRoot = PATHS.repoRoot;

function normalizeOutputMode(value) {
  return value === 'staging' ? 'staging' : 'new-flow';
}

function resolveOutputRoots(mode) {
  if (mode === 'staging') {
    return {
      outputRoot: PATHS.stagingDir,
      sourceRoot: PATHS.stagingDir
    };
  }

  return {
    outputRoot: PATHS.stagingDir,
    sourceRoot: PATHS.stagingDir
  };
}

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

async function readJsonIfExists(filePath) {
  try {
    return await readJson(filePath);
  } catch (error) {
    if (error?.code === 'ENOENT') {
      return null;
    }
    throw error;
  }
}

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function replaceTitleInText(text, fromTitle, toTitle) {
  if (typeof text !== 'string' || !text) {
    return text;
  }
  return text.split(fromTitle).join(toTitle);
}

function normalizeWhitespace(value) {
  return String(value ?? '').replace(/\s+/g, ' ').trim();
}

function safeFileName(value) {
  return normalizeWhitespace(value).replace(/[\\/:*?"<>|]/g, '-');
}

function slugifySegment(value) {
  return normalizeWhitespace(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function pickPrimaryName(value) {
  const normalized = normalizeWhitespace(value);
  if (!normalized) return null;
  return normalized.split(/[\/，,、]/)[0]?.trim() || normalized;
}

function toIsoDate(value) {
  const normalized = normalizeWhitespace(value);
  if (!normalized || normalized === 'N/A') return null;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString().slice(0, 10);
}

function parseRuntimeMinutes(value) {
  const match = String(value ?? '').match(/(\d+)/);
  return match ? Number.parseInt(match[1], 10) : null;
}

function splitOmdbNames(value) {
  return normalizeWhitespace(value)
    .split(',')
    .map((item) => normalizeWhitespace(item))
    .filter(Boolean)
    .map((name) => ({ name, nameEn: name }));
}

function pickRating(ratings, source) {
  const entry = Array.isArray(ratings) ? ratings.find((item) => item?.Source === source) : null;
  return entry?.Value ?? null;
}

function parseRatingValue(value) {
  const normalized = normalizeWhitespace(value);
  if (!normalized || normalized === 'N/A') return null;
  if (normalized.includes('/10')) {
    const number = Number.parseFloat(normalized.split('/')[0]);
    return Number.isFinite(number) ? number : null;
  }
  if (normalized.endsWith('%')) {
    const number = Number.parseFloat(normalized.slice(0, -1));
    return Number.isFinite(number) ? Math.round(number) : null;
  }
  return null;
}

async function fetchJson(url) {
  const response = await fetch(url, {
    headers: {
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

async function downloadBinary(url, outputPath) {
  const response = await fetch(url, {
    headers: {
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
      referer: 'https://movie.douban.com/'
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to download asset ${url}: ${response.status} ${response.statusText}`);
  }

  const buffer = Buffer.from(await response.arrayBuffer());
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, buffer);
}

async function fetchDoubanChallengePage(url) {
  const headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
  };
  const first = await fetch(url, { headers });
  const html = await first.text();
  if (!html.includes('name="sec"') || !html.includes('id="cha"')) {
    return html;
  }

  const tok = html.match(/id="tok" name="tok" value="([^"]+)"/i)?.[1];
  const cha = html.match(/id="cha" name="cha" value="([^"]+)"/i)?.[1];
  const red = html.match(/id="red" name="red" value="([^"]+)"/i)?.[1] ?? url;
  if (!tok || !cha) {
    return html;
  }

  let nonce = 0;
  let hash = '';
  do {
    nonce += 1;
    hash = crypto.createHash('sha512').update(`${cha}${nonce}`).digest('hex');
  } while (!hash.startsWith('0000'));

  const body = new URLSearchParams({ tok, cha, sol: String(nonce), red });
  const second = await fetch('https://movie.douban.com/c', {
    method: 'POST',
    headers: {
      ...headers,
      'content-type': 'application/x-www-form-urlencoded'
    },
    body,
    redirect: 'manual'
  });

  const cookie = second.headers.get('set-cookie')?.split(';')[0] ?? '';
  const targetUrl = second.headers.get('location') ?? red;
  const finalResponse = await fetch(targetUrl, {
    headers: {
      ...headers,
      cookie
    }
  });
  return finalResponse.text();
}

function extractDoubanSubjectInfo(html) {
  const compact = html.replace(/\r/g, '');
  const infoBlock = compact.match(/<div id="info">([\s\S]*?)<\/div>/i)?.[1] ?? '';
  const plotBlock = compact.match(/<span property="v:summary"[^>]*>([\s\S]*?)<\/span>/i)?.[1] ?? '';
  const ratingValue = compact.match(/<strong class="ll rating_num"[^>]*>([^<]+)<\/strong>/i)?.[1] ?? null;
  const titleYear = compact.match(/<span class="year">\((\d{4})\)<\/span>/i)?.[1] ?? null;

  const lines = infoBlock
    .replace(/<br\s*\/?>/gi, '\n')
    .split('\n')
    .map((line) => line.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' '))
    .map((line) => normalizeWhitespace(line))
    .filter(Boolean);

  const info = {};
  for (const line of lines) {
    const match = line.match(/^([^:：]+)[:：]\s*(.+)$/);
    if (!match) continue;
    info[match[1]] = match[2];
  }

  return {
    year: titleYear ? Number.parseInt(titleYear, 10) : null,
    doubanRating: ratingValue ? Number.parseFloat(ratingValue.trim()) : null,
    director: splitOmdbNames(info['导演']),
    writer: splitOmdbNames(info['编剧']).map((item) => ({ ...item, role: '编剧' })),
    cast: splitOmdbNames(info['主演']),
    genre: normalizeWhitespace(info['类型']).split('/').map((item) => item.trim()).filter(Boolean),
    countryText: info['制片国家/地区'] ?? null,
    languageText: info['语言'] ?? null,
    aka: normalizeWhitespace(info['又名']).split('/').map((item) => item.trim()).filter(Boolean),
    imdbId: info['IMDb'] ?? null,
    storyText: normalizeWhitespace(plotBlock).replace(/\s{2,}/g, ' '),
    releaseDate: [...compact.matchAll(/<span property="v:initialReleaseDate"[^>]*content="([^"]+)"[^>]*>([^<]*)<\/span>/gi)].map((match) => ({
      date: match[1],
      location: normalizeWhitespace(match[2].match(/\(([^)]+)\)/)?.[1] ?? '') || pickPrimaryName(info['制片国家/地区'])
    }))
  };
}

function extractDoubanComments(html, limit = 5) {
  const blocks = [...html.matchAll(/<div class="comment-item"[\s\S]*?<span class="short">([\s\S]*?)<\/span>[\s\S]*?<span class="comment-time "[^>]*title="([^"]+)"/gi)];
  return blocks.slice(0, limit).map((match) => ({
    author: null,
    source: '豆瓣短评',
    date: normalizeWhitespace(match[2]),
    content: normalizeWhitespace(match[1]),
    url: null,
    title: null
  }));
}

async function fetchOmdbByTask(task) {
  const imdbId = normalizeWhitespace(task.imdbId);
  const title = normalizeWhitespace(task.originalTitle || task.title);
  const year = task.year ? `&y=${task.year}` : '';
  const url = imdbId
    ? `https://www.omdbapi.com/?apikey=trilogy&i=${encodeURIComponent(imdbId)}`
    : `https://www.omdbapi.com/?apikey=trilogy&t=${encodeURIComponent(title)}${year}`;
  const payload = await fetchJson(url);
  if (payload?.Response === 'False') {
    throw new Error(`OMDb lookup failed for ${task.title}: ${payload?.Error || 'unknown error'}`);
  }
  return payload;
}

async function buildGenericRecord(task) {
  if (!task.id) {
    throw new Error(`Generic intake requires task.id for ${task.doubanId || task.query}`);
  }

  const detailHtml = await fetchDoubanChallengePage(task.subjectUrl);
  const commentsHtml = await fetchDoubanChallengePage(`${task.subjectUrl.replace(/\/$/, '')}/comments?status=P`);
  const douban = extractDoubanSubjectInfo(detailHtml);
  const omdb = await fetchOmdbByTask({ ...task, imdbId: douban.imdbId || task.imdbId });
  const reviews = extractDoubanComments(commentsHtml, 5);

  const assetDir = path.join(PATHS.workAssetsDir, task.id);
  const posterOutputPath = path.join(assetDir, 'poster-main.jpg');
  const posterUrl = omdb.Poster && omdb.Poster !== 'N/A' ? omdb.Poster : task.posterUrl;
  if (posterUrl) {
    await downloadBinary(posterUrl, posterOutputPath);
  }

  const imdbRating = parseRatingValue(omdb.imdbRating);
  const rottenTomatoes = parseRatingValue(pickRating(omdb.Ratings, 'Rotten Tomatoes'));
  const metascore = Number.isFinite(Number.parseInt(omdb.Metascore, 10)) ? Number.parseInt(omdb.Metascore, 10) : null;
  const runtime = parseRuntimeMinutes(omdb.Runtime);
  const releaseDate = douban.releaseDate.length
    ? douban.releaseDate
    : [{ date: toIsoDate(omdb.Released), location: pickPrimaryName(douban.countryText || omdb.Country) }].filter((item) => item.date);

  const record = {
    id: task.id,
    title: task.title,
    originalTitle: task.originalTitle || omdb.Title || task.title,
    year: task.year || douban.year || (omdb.Year ? Number.parseInt(String(omdb.Year).slice(0, 4), 10) : null),
    director: douban.director.length ? douban.director : splitOmdbNames(omdb.Director),
    writer: douban.writer.length ? douban.writer : splitOmdbNames(omdb.Writer).map((item) => ({ ...item, role: '编剧' })),
    cast: douban.cast.length ? douban.cast : splitOmdbNames(omdb.Actors),
    otherCast: [],
    producer: [],
    genre: (douban.genre.length ? douban.genre : normalizeWhitespace(omdb.Genre).split(',').map((item) => normalizeWhitespace(item)).filter(Boolean)),
    country: pickPrimaryName(douban.countryText || omdb.Country),
    language: pickPrimaryName(douban.languageText || omdb.Language),
    runtime,
    releaseDate,
    aka: douban.aka,
    imdbId: normalizeWhitespace(douban.imdbId || omdb.imdbID) || null,
    doubanId: task.doubanId,
    doubanRating: task.doubanRating ?? douban.doubanRating ?? null,
    synopsis: {
      text: task.quote || normalizeWhitespace(omdb.Plot)
    },
    story: {
      text: douban.storyText || normalizeWhitespace(omdb.Plot)
    },
    videos: [],
    images: {
      poster: 'poster-main.jpg',
      posters: [],
      stills: [],
      wallpapers: []
    },
    similar: [],
    reviews,
    links: {
      douban: task.subjectUrl,
      imdb: recordImdbUrl(normalizeWhitespace(douban.imdbId || omdb.imdbID) || null),
      tmdb: null
    },
    module: 'video',
    submodule: 'movie',
    createdAt: new Date().toISOString().slice(0, 10),
    updatedAt: new Date().toISOString().slice(0, 10),
    schemaType: 'live_action_movie',
    status: 'published',
    publishCompany: null,
    tags: [],
    series: [],
    tmdbId: null,
    quotes: [],
    rated: normalizeWhitespace(omdb.Rated) || null,
    awards: normalizeWhitespace(omdb.Awards) || null,
    imdbRating,
    rottenTomatoes,
    metascore
  };

  const sourceData = {
    id: makeSystemEntry(record.id, '系统自动生成或来自任务文件固定 id'),
    title: makeSourceEntry(record.title, 'douban', { sourceUrl: task.subjectUrl }),
    originalTitle: makeSourceEntry(record.originalTitle, 'merged', {
      sources: [
        { source: 'douban', fields: ['originalTitle'], sourceUrl: task.subjectUrl },
        { source: 'omdb', fields: ['Title'], sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }
      ]
    }),
    year: makeSourceEntry(record.year, 'merged', {
      sources: [
        { source: 'douban', fields: ['year'], sourceUrl: task.subjectUrl },
        { source: 'omdb', fields: ['Year'], sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }
      ]
    }),
    director: makeSourceEntry(record.director, 'merged', {
      sources: [
        { source: 'douban', fields: ['director'], sourceUrl: task.subjectUrl },
        { source: 'omdb', fields: ['Director'], sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }
      ]
    }),
    writer: makeSourceEntry(record.writer, 'merged', {
      sources: [
        { source: 'douban', fields: ['writer'], sourceUrl: task.subjectUrl },
        { source: 'omdb', fields: ['Writer'], sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }
      ]
    }),
    cast: makeSourceEntry(record.cast, 'merged', {
      sources: [
        { source: 'douban', fields: ['cast'], sourceUrl: task.subjectUrl },
        { source: 'omdb', fields: ['Actors'], sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }
      ]
    }),
    otherCast: makeSystemEntry(record.otherCast, '当前通用录入流程未扩展更多演员，先保留空数组'),
    producer: makeSystemEntry(record.producer, '当前通用录入流程未稳定抽到制片人，先保留空数组'),
    genre: makeSourceEntry(record.genre, 'merged', {
      sources: [
        { source: 'douban_top250', fields: ['genres'], sourceUrl: 'https://movie.douban.com/top250' },
        { source: 'omdb', fields: ['Genre'], sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }
      ]
    }),
    country: makeSourceEntry(record.country, 'merged', {
      sources: [
        { source: 'douban', fields: ['country'], sourceUrl: task.subjectUrl },
        { source: 'omdb', fields: ['Country'], sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }
      ],
      note: '当前通用录入流程按豆瓣详情/OMDb 首项归并为单值，后续可再人工校正'
    }),
    language: makeSourceEntry(record.language, 'merged', {
      sources: [
        { source: 'douban', fields: ['language'], sourceUrl: task.subjectUrl },
        { source: 'omdb', fields: ['Language'], sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }
      ]
    }),
    runtime: makeSourceEntry(record.runtime, 'omdb', {
      sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy`,
      note: '单位：分钟'
    }),
    releaseDate: makeSourceEntry(record.releaseDate, 'merged', {
      sources: [
        { source: 'douban', fields: ['releaseDate'], sourceUrl: task.subjectUrl },
        { source: 'omdb', fields: ['Released'], sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }
      ]
    }),
    aka: makeSourceEntry(record.aka, 'douban', { sourceUrl: task.subjectUrl }),
    imdbId: makeSourceEntry(record.imdbId, 'merged', {
      sources: [
        { source: 'douban', fields: ['IMDb'], sourceUrl: task.subjectUrl },
        { source: 'omdb', fields: ['imdbID'], sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }
      ]
    }),
    doubanId: makeSourceEntry(record.doubanId, 'known', { note: '来自任务文件中的豆瓣 subject id' }),
    doubanRating: makeSourceEntry(record.doubanRating, 'merged', {
      sources: [
        { source: 'douban_top250', fields: ['rating'], sourceUrl: 'https://movie.douban.com/top250' },
        { source: 'douban', fields: ['rating'], sourceUrl: task.subjectUrl }
      ]
    }),
    synopsis: makeSourceEntry(record.synopsis, task.quote ? 'douban_top250' : 'omdb', {
      sourceUrl: task.quote ? 'https://movie.douban.com/top250' : `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy`,
      note: task.quote ? '列表短句先作为简短导语' : '简介先使用 OMDb Plot'
    }),
    story: makeSourceEntry(record.story, douban.storyText ? 'douban' : 'omdb', {
      sourceUrl: douban.storyText ? task.subjectUrl : `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy`,
      note: '当前通用录入流程优先用豆瓣剧情简介，否则退回 OMDb Plot'
    }),
    videos: makeSystemEntry(record.videos, '当前通用录入流程未抓取视频，先保留空数组'),
    images: {
      poster: makeSourceEntry(record.images.poster, posterUrl ? 'merged' : 'system', {
        sourceUrl: posterUrl || task.subjectUrl,
        note: posterUrl ? '主海报优先使用 OMDb Poster，缺失时回退到豆瓣 Top250 列表海报' : '当前未能下载主海报，文件需后续补齐'
      }),
      posters: makeSystemEntry(record.images.posters, '当前通用录入流程暂未抓取海报画廊'),
      stills: makeSystemEntry(record.images.stills, '当前通用录入流程暂未抓取剧照'),
      wallpapers: makeSystemEntry(record.images.wallpapers, '当前通用录入流程暂未抓取壁纸')
    },
    similar: makeSystemEntry(record.similar, '当前通用录入流程暂未整理相似作品'),
    reviews: makeSourceEntry(record.reviews, 'douban', {
      sourceUrl: `${task.subjectUrl.replace(/\/$/, '')}/comments?status=P`,
      note: record.reviews.length ? '当前仅抓取少量豆瓣热门短评，满足轻量录入' : '当前未抓到短评，先保留空数组'
    }),
    links: makeSourceEntry(record.links, 'merged', {
      sources: [
        { source: 'known', fields: ['douban'] },
        { source: 'omdb', fields: ['imdb'], sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }
      ]
    }),
    module: makeSystemEntry(record.module, '影视模块'),
    submodule: makeSystemEntry(record.submodule, '电影子模块'),
    createdAt: makeSystemEntry(record.createdAt, '录入时间'),
    updatedAt: makeSystemEntry(record.updatedAt, '最后更新时间'),
    schemaType: makeSystemEntry(record.schemaType, '电影录入默认使用 live_action_movie'),
    status: makeSystemEntry(record.status, '通用录入默认按 published 写入'),
    publishCompany: makeSystemEntry(record.publishCompany, '当前通用录入流程未稳定抓取出品公司'),
    tags: makeSystemEntry(record.tags, '当前未建立标签，先保留空数组'),
    series: makeSystemEntry(record.series, '当前未识别系列关系，先保留空数组'),
    tmdbId: makeSystemEntry(record.tmdbId, '当前通用录入流程尚未接 TMDB 搜索'),
    quotes: makeSystemEntry(record.quotes, '当前未整理 quotes，先保留空数组'),
    rated: makeSourceEntry(record.rated, 'omdb', { sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }),
    awards: makeSourceEntry(record.awards, 'omdb', { sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }),
    imdbRating: makeSourceEntry(record.imdbRating, 'omdb', { sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }),
    rottenTomatoes: makeSourceEntry(record.rottenTomatoes, 'omdb', { sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` }),
    metascore: makeSourceEntry(record.metascore, 'omdb', { sourceUrl: `https://www.omdbapi.com/?i=${record.imdbId || ''}&apikey=trilogy` })
  };

  return { record, sourceData };
}

function recordImdbUrl(imdbId) {
  return imdbId ? `https://www.imdb.com/title/${imdbId}/` : null;
}

function mapReviewMetadataByDoubanId(doubanId) {
  if (doubanId === '1292052') {
    return [
      { title: '十年·肖申克的救赎', url: 'https://movie.douban.com/review/1000369/' },
      { title: '终于找到了郁闷人生的原因――观《肖申克的救赎》有感', url: 'https://movie.douban.com/review/1001258/' },
      { title: '《肖申克的救赎》到底“救赎”了什么？', url: 'https://movie.douban.com/review/10350620/' },
      { title: '《肖申克的救赎》：1994—2007，希望就是现实', url: 'https://movie.douban.com/review/1127585/' }
    ];
  }

  if (doubanId === '1889243') {
    return [
      { title: '不要温顺地走进那个良夜', url: 'https://movie.douban.com/review/7174365/' },
      { title: '爱是一切的答案', url: 'https://movie.douban.com/review/7179303/' },
      { title: '诺兰的宇宙诗学', url: 'https://movie.douban.com/review/7183355/' },
      { title: '时间、重力与告别', url: 'https://movie.douban.com/review/7189240/' }
    ];
  }

  return [];
}

function makeSystemEntry(value, note) {
  return { value, source: 'system', note };
}

function makeSourceEntry(value, source, extras = {}) {
  return { value, source, ...extras };
}

function buildInterstellarRecord(task, config) {
  const record = {
    id: config.id,
    title: '星际穿越',
    originalTitle: 'Interstellar',
    year: 2014,
    director: [
      {
        name: '克里斯托弗·诺兰',
        nameEn: 'Christopher Nolan',
        avatar: 'christopher-nolan.jpg',
        avatarSource: 'wikipedia',
        works: ['盗梦空间', '敦刻尔克', '奥本海默']
      }
    ],
    writer: [
      {
        name: '乔纳森·诺兰',
        nameEn: 'Jonathan Nolan',
        role: '编剧',
        avatar: 'jonathan-nolan.jpg',
        avatarSource: 'wikipedia'
      },
      {
        name: '克里斯托弗·诺兰',
        nameEn: 'Christopher Nolan',
        role: '编剧',
        avatar: 'christopher-nolan.jpg',
        avatarSource: 'wikipedia'
      }
    ],
    cast: [
      {
        name: '马修·麦康纳',
        nameEn: 'Matthew McConaughey',
        role: '库珀 Cooper',
        avatar: 'matthew-mcconaughey.jpg',
        avatarSource: 'wikipedia'
      },
      {
        name: '安妮·海瑟薇',
        nameEn: 'Anne Hathaway',
        role: '艾米莉亚·布兰德 Amelia Brand',
        avatar: 'anne-hathaway.jpg',
        avatarSource: 'wikipedia'
      },
      {
        name: '杰西卡·查斯坦',
        nameEn: 'Jessica Chastain',
        role: '成年墨菲 Murph',
        avatar: 'jessica-chastain.jpg',
        avatarSource: 'wikipedia'
      },
      {
        name: '迈克尔·凯恩',
        nameEn: 'Michael Caine',
        role: '布兰德教授 Professor Brand',
        avatar: 'michael-caine.jpg',
        avatarSource: 'wikipedia'
      },
      {
        name: '卡西·阿弗莱克',
        nameEn: 'Casey Affleck',
        role: '成年汤姆 Tom',
        avatar: 'casey-affleck.jpg',
        avatarSource: 'wikipedia'
      },
      {
        name: '韦斯·本特利',
        nameEn: 'Wes Bentley',
        role: '道尔 Doyle',
        avatar: 'wes-bentley.jpg',
        avatarSource: 'wikipedia'
      },
      {
        name: '麦肯吉·弗依',
        nameEn: 'Mackenzie Foy',
        role: '幼年墨菲 Murph (10 Yrs.)',
        avatar: 'mackenzie-foy.jpg',
        avatarSource: 'wikipedia'
      },
      {
        name: '大卫·吉雅西',
        nameEn: 'David Gyasi',
        role: '罗米利 Romilly',
        avatar: 'david-gyasi.jpg',
        avatarSource: 'tmdb'
      },
      {
        name: '比尔·欧文',
        nameEn: 'Bill Irwin',
        role: 'TARS（配音）',
        avatar: 'bill-irwin.jpg',
        avatarSource: 'wikipedia'
      }
    ],
    otherCast: [
      {
        name: '艾伦·伯斯汀',
        nameEn: 'Ellen Burstyn',
        role: '年老墨菲 Murph (older)',
        avatar: 'ellen-burstyn.jpg',
        avatarSource: 'wikipedia'
      },
      {
        name: '约翰·利思戈',
        nameEn: 'John Lithgow',
        role: '唐纳德 Donald',
        avatar: 'john-lithgow.jpg',
        avatarSource: 'wikipedia'
      },
      {
        name: '提摩西·柴勒梅德',
        nameEn: 'Timothee Chalamet',
        role: '少年汤姆 Tom (15 Yrs.)',
        avatar: 'timothee-chalamet.jpg',
        avatarSource: 'wikipedia'
      },
      {
        name: '马特·达蒙',
        nameEn: 'Matt Damon',
        role: '曼恩 Mann',
        avatar: 'matt-damon.jpg',
        avatarSource: 'wikipedia'
      },
      {
        name: '托弗·戈瑞斯',
        nameEn: 'Topher Grace',
        role: '盖蒂 Getty',
        avatar: 'topher-grace.jpg',
        avatarSource: 'wikipedia'
      },
      {
        name: '乔什·斯图尔特',
        nameEn: 'Josh Stewart',
        role: 'CASE（配音）',
        avatar: 'josh-stewart.jpg',
        avatarSource: 'wikipedia'
      }
    ],
    producer: [
      {
        name: '艾玛·托马斯',
        nameEn: 'Emma Thomas',
        role: '制片人'
      },
      {
        name: '琳达·奥布斯特',
        nameEn: 'Lynda Obst',
        role: '制片人'
      },
      {
        name: '克里斯托弗·诺兰',
        nameEn: 'Christopher Nolan',
        role: '制片人',
        avatar: 'christopher-nolan.jpg',
        avatarSource: 'wikipedia'
      }
    ],
    genre: ['剧情', '科幻', '冒险'],
    country: '美国 / 英国 / 加拿大',
    language: '英语',
    runtime: 169,
    runtimeEn: 169,
    rated: 'PG-13',
    awards: 'Won 1 Oscar. 45 wins & 148 nominations total',
    releaseDate: [
      { date: '2014-10-26', location: '洛杉矶首映' },
      { date: '2014-11-05', location: '美国' },
      { date: '2014-11-07', location: '英国' }
    ],
    aka: ['星际启示录', '星际效应'],
    imdbId: 'tt0816692',
    tmdbId: '157336',
    doubanId: task.doubanId,
    doubanRating: null,
    imdbRating: 8.7,
    rottenTomatoes: 73,
    metascore: 74,
    synopsis: {
      text: '在作物枯萎、尘暴肆虐的近未来地球，人类正逼近生存边缘。前 NASA 飞行员库珀受命率领队伍穿越土星附近的虫洞，前往遥远星系寻找新的可居住家园。'
    },
    story: {
      text: '不久的将来，地球上的农作物因为气候转变及枯萎病而失收。前美国国家航空航天局工程师和航天飞机驾驶员约瑟·库珀（Joseph Cooper，马修·麦康纳饰）被迫成为农民以协助解决粮食危机。库珀的10岁女儿墨菲（Murphy，麦肯基·弗依饰）发现其房间的书架上的书本无故掉到地上，认为这是灵异现象。不久后，一场沙尘暴在墨菲的房间中留下二进制坐标，二人开车到达坐标位置后发现那是北美空防司令部，现已成为美国国家航空航天局的秘密基地。\n\n秘密基地负责人布兰德教授（Dr. Brand）向库珀透露土星附近出现了虫洞，认为外星智慧生命有意协助人类前往遥远星系移居。总署在约十年前已派遣了十二名科学家穿越该虫洞，各自降落在多个被认为有居住可能性的行星上，传送回来的资料显示其中一个以黑洞“卡冈图雅”（Gargantua）为中心的行星系统中有三颗星球可能适合人类移居。行星各自以降落在当地的科学家名字命名：米勒（Miller）、埃德蒙斯（Edmunds）和曼恩（Mann）。\n\n库珀答应布兰德教授的要求，担任航天器永恒号（Endurance）的驾驶员前往执行拉撒路计划（Lazarus mission）：A计划为确认星球适合人类居住后，透过布兰德教授的重力方程协助地球人前往殖民；B计划为带着多个人类胚胎殖民外星，留在地球的人类则会灭绝。墨菲因担心库珀一去不回而深感愤怒，库珀亦不顾劝阻与布兰德教授的女儿艾米莉亚（Amelia，安妮·海瑟薇饰）、物理学家罗密利（Romilly）、地质学家道尔（Doyle）和两个机器人塔斯（TARS）与凯斯（CASE）前往太空登上永恒号启程。\n\n众人先通过虫洞前往米勒星，除罗密利与塔斯外的一众成员乘坐徘徊者号（Ranger）降落星球后，发现地表只有一片汪洋，黑洞的潮汐力引起的巨型海啸使道尔丧生并延误了回程，二人返回永恒号后发现，他们在星球上大约停留了三个钟头，然而对永恒号上的罗密利来说则是二十三年之久。\n\n众人经一番争论后决定前往曼恩星球，该星球严寒且大气中充满氨气。此时墨菲（杰西卡·查斯坦饰）已是库珀离开地球的年龄，加入了美国国家航空航天局协助布兰德教授解开拯救地球人所需要的重力方程，但教授在健康恶化弥留之际向墨菲承认A计划不可能实现。另一边，曼恩博士（马特·达蒙饰）被众人从人工睡眠中唤醒后表示方程因缺乏黑洞引力奇点的数据而无法完成，因此永恒号的真正目的并非拯救地球人类。库珀因此十分愤怒，打算放弃计划。在稍后的任务中，曼恩表示所有宜居数据均假，目的是希望宇航局能派人前来救他，并在打斗中打破库珀的氧气面罩。\n\n曼恩丢下库珀等死后夺取徘徊者号驶向永恒号，同时罗密利因试图从被曼恩拆解的机器人奇普（KIPP）中取得资料，触动其设下的陷阱引发爆炸身亡。艾米莉亚救回库珀后，二人乘坐着陆器追赶曼恩。曼恩在永恒号未完全对接的情况下打开气闸，产生的失控减压使他身亡并导致永恒号失控旋转，库珀成功对接永恒号并努力使其稳定下来。永恒号上的资源已不足以返回地球，且其已被卡冈图雅黑洞的引力捕获。两人于是发射出塔斯，让它收集黑洞引力奇点的数据，并计划通过重力助推将永恒号推向埃德蒙斯星实行B计划。为减少永恒号质量以让艾米莉亚逃生，库珀让自己驾驶的徘徊者号于耗尽燃料后分离进入黑洞。\n\n其弹射逃生后，发现自己进入一个由未来人类创造的四维超正方体，得知自己正是儿时墨菲遇上的“幽灵”。他利用重力与儿时的墨菲交流，引导自己参与拉撒路计划以拯救人类，并把塔斯取得的黑洞数据通过引力波以摩斯密码的形式传送给墨菲的手表。成年墨菲在回忆此事时终于发现父亲留给她的讯息，完成了布兰德教授的方程使人类得以离开地球，前往一个环绕着土星运行的空间站居住。四维超正方体空间在数据传送完毕后关闭，库珀通过虫洞被传送回土星并被人类救起。库珀在空间站上与年老垂死的墨菲重逢，墨菲说服他去宜居的埃德蒙斯星球上寻找艾米莉亚。最终库珀与塔斯搭乘一艘次世代漫游者号前往埃德蒙斯星。'
    },
    videos: [],
    images: {
      poster: 'poster-main.jpg',
      posters: ['poster-01.jpg', 'poster-02.jpg', 'poster-03.jpg', 'poster-04.jpg'],
      postersTotal: 250,
      stills: ['still-01.jpg', 'still-02.jpg', 'still-03.jpg', 'still-04.jpg', 'still-05.jpg', 'still-06.jpg'],
      stillsTotal: 169,
      wallpapers: []
    },
    soundtrack: {
      albums: [
        {
          name: 'Interstellar (Original Motion Picture Soundtrack)',
          note: 'Hans Zimmer',
          coverImage: null,
          releaseDate: '2014-11-18',
          type: 'soundtrack',
          tracks: [
            { name: 'Dreaming of the Crash', artist: 'Hans Zimmer', duration: null },
            { name: 'Cornfield Chase', artist: 'Hans Zimmer', duration: null },
            { name: 'Stay', artist: 'Hans Zimmer', duration: null },
            { name: 'No Time for Caution', artist: 'Hans Zimmer', duration: null },
            { name: 'S.T.A.Y.', artist: 'Hans Zimmer', duration: null },
            { name: 'Where We\'re Going', artist: 'Hans Zimmer', duration: null }
          ]
        }
      ]
    },
    similar: [
      { title: '2001太空漫游', year: 1968, rating: 8.9 },
      { title: '地心引力', year: 2013, rating: 7.9 },
      { title: '火星救援', year: 2015, rating: 8.5 },
      { title: '降临', year: 2016, rating: 7.9 },
      { title: '盗梦空间', year: 2010, rating: 9.3 }
    ],
    series: [],
    reviews: [
      {
        author: 'QuiteThrilling',
        source: '豆瓣长评',
        date: '2014-11-07 00:31:01',
        content: '先推一篇视角独特的影评：被忽略的阿弗莱克 http://www.douban.com/note/450035111/ =================================== 图书管理员又在历史上留下了可歌可泣的一页。五星只代表力荐，不代表满分。嫌这部电影不够硬的同学，不管你是文科生、理科生，还是特别特别厉害的、',
        url: 'https://movie.douban.com/review/7181757/',
        title: '当你想描写一个触手可及的未来，然而却……'
      },
      {
        author: '便便',
        source: '豆瓣长评',
        date: '2014-11-05 15:13:13',
        content: '11.4号70mm IMAX场，提前接近一个月就订好了票，连基友都没有带就准备一个人静静地观赏这场电影，免得到时候在回去的路上听人balabala说哪里不好看、又比不上哪部电影之类的废话。好吧，其实是因为基友品味太差，只喜欢R.I.P.D这种类型的片，实在提不起兴趣提前一个月订这种',
        url: 'https://movie.douban.com/review/7179454/',
        title: 'Interstellar 观影感+全剧透+2刷发现果然没漏洞。。'
      },
      {
        author: '更深的白色',
        source: '豆瓣长评',
        date: '2014-11-06 22:35:00',
        content: 'Spoiler Alert 在我们进入对“Interstellar”的具体讨论之前，也许需要对诺兰导演进行一个小小的总结和分析，他也许是我们这个时代最能兼具票房号召力和影迷人气的导演。如果我们抛开影视工业的层面，仅仅从个人才华上分析诺兰的成功，那么他最大的优点和长处在哪？或者说',
        url: 'https://movie.douban.com/review/7181668/',
        title: '诺兰的维度'
      },
      {
        author: 'perceptor',
        source: '豆瓣长评',
        date: '2014-11-09 01:20:42',
        content: '小时候居住的城市有着令人惊叹的重工业和灰黄色的天空，在夜晚，除了朦胧的月球，偶尔也只能一瞥天狼星和金星摇曳的身姿。第一次与银河的会面是在天文馆的投影穹幕里，外表奇异的投影仪冷静的转动，将无数光点铺满头顶。这固然比不上若干年后在海滨散步时与这条雄伟光带真身那',
        url: 'https://movie.douban.com/review/7184428/',
        title: '银河彼端，群星尽头'
      },
      {
        author: '没电影活不了',
        source: '豆瓣长评',
        date: '2014-05-02 16:37:42',
        content: '诺兰的新作「星际穿越」基于美国理论物理学家基普·索恩的理论成果，而他的理论成果基本都在他的著作「黑洞与时间弯曲」一书中，本文的科学知识基本都是我在这本著作中看到总结的。该片剧情将涉很多的科学概念，包括虫洞、黑洞理论、相对论，万有引力等等。一、黑洞 基帕',
        url: 'https://movie.douban.com/review/6655287/',
        title: '科普黑洞虫洞，备战星际穿越'
      },
      {
        author: '比岁月含蓄',
        source: '豆瓣短评',
        date: '2014-11-06 23:27:12',
        content: '时间可以伸缩和折叠，唯独不能倒退。你的鹤发或许是我的童颜，而我一次呼吸能抵过你此生的岁月。',
        url: null,
        title: null
      },
      {
        author: '影志',
        source: '豆瓣短评',
        date: '2014-11-12 10:28:53',
        content: '太壮阔了，无以言表！40\'渐入佳境，80\'叹为观止，120\'泪流满面，160\'恍如隔世…不曾如此贴近浩瀚星空，被它环抱；不曾如此触摸生命之弦，遁入五维幻境。瑕不掩瑜的科幻神作，刷新视觉的IMAX体验，观影前撒好尿，准备接受近三小时的泪腺洗礼。“爱是一种力量，让我们超越时空感知它的存在”',
        url: null,
        title: null
      },
      {
        author: 'fanndd',
        source: 'TMDB',
        date: '2025-09-23',
        content: '我心中能进入TOP3的影片（2000年之后的电影中）',
        url: 'https://www.themoviedb.org/movie/157336-interstellar/reviews',
        title: null
      },
      {
        author: 'Matt Brunson',
        source: '烂番茄 · Film Frenzy',
        date: 'Nov 3',
        content: 'Deeply flawed but also wholly absorbing, Interstellar further marked writer-director Christopher Nolan as one of our most ambitious, go-for-broke directors, unafraid to attempt Sistine Chapel ceilings while his fellow filmmakers are working with Crayolas.',
        url: 'https://www.rottentomatoes.com/m/interstellar_2014/reviews',
        title: null
      },
      {
        author: 'Paul Emmanuel Enicola',
        source: '烂番茄 · The Movie Buff',
        date: '2025-02-26',
        content: 'While detractors have often accused Nolan of being all brains and no heart, Interstellar shows that his intellect and his emotions are not at odds, they are inextricably linked.',
        url: 'https://www.rottentomatoes.com/m/interstellar_2014/reviews',
        title: null
      }
    ],
    links: {
      douban: task.subjectUrl,
      imdb: 'https://www.imdb.com/title/tt0816692/',
      tmdb: 'https://www.themoviedb.org/movie/157336-interstellar'
    },
    module: 'video',
    submodule: 'movie',
    schemaType: 'live_action_movie',
    status: 'published',
    tags: [],
    quotes: [],
    createdAt: '2026-05-04',
    updatedAt: '2026-05-04'
  };

  const sourceData = {
    id: makeSystemEntry(record.id, '系统自动生成，递增序号'),
    title: makeSourceEntry(record.title, 'wikipedia', {
      sourceUrl: 'https://zh.wikipedia.org/wiki/星际穿越',
      note: '标题以中文维基条目为准'
    }),
    originalTitle: makeSourceEntry(record.originalTitle, 'wikipedia', {
      sourceUrl: 'https://en.wikipedia.org/wiki/Interstellar_(film)'
    }),
    year: makeSourceEntry(record.year, 'omdb', {
      sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy'
    }),
    director: makeSourceEntry(record.director, 'merged', {
      sources: [
        { source: 'wikipedia', fields: ['name', 'nameEn', 'avatar', 'works'], sourceUrl: 'https://en.wikipedia.org/wiki/Christopher_Nolan' },
        { source: 'omdb', fields: ['nameEn'], sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy' }
      ]
    }),
    writer: makeSourceEntry(record.writer, 'merged', {
      sources: [
        { source: 'omdb', fields: ['nameEn'], sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy' },
        { source: 'wikipedia', fields: ['name', 'avatar'], sourceUrl: 'https://en.wikipedia.org/wiki/Jonathan_Nolan' }
      ]
    }),
    cast: makeSourceEntry(record.cast, 'merged', {
      sources: [
        { source: 'tmdb', fields: ['name', 'role'], sourceUrl: 'https://www.themoviedb.org/movie/157336-interstellar/cast' },
        { source: 'wikipedia', fields: ['nameEn', 'avatar'], sourceUrl: 'https://en.wikipedia.org/wiki/Interstellar_(film)' }
      ],
      note: '主演头像同时使用 Wikipedia 与 TMDB 补齐'
    }),
    otherCast: makeSourceEntry(record.otherCast, 'merged', {
      sources: [
        { source: 'tmdb', fields: ['name', 'role'], sourceUrl: 'https://www.themoviedb.org/movie/157336-interstellar/cast' },
        { source: 'wikipedia', fields: ['nameEn', 'avatar'], sourceUrl: 'https://en.wikipedia.org/wiki/Interstellar_(film)' }
      ],
      note: '补充重要配角与配音阵容'
    }),
    producer: makeSourceEntry(record.producer, 'wikipedia', {
      sourceUrl: 'https://en.wikipedia.org/wiki/Interstellar_(film)'
    }),
    genre: makeSourceEntry(record.genre, 'omdb', {
      sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy'
    }),
    country: makeSourceEntry(record.country, 'omdb', {
      sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy'
    }),
    language: makeSourceEntry(record.language, 'omdb', {
      sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy'
    }),
    runtime: makeSourceEntry(record.runtime, 'omdb', {
      sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy',
      note: '单位：分钟'
    }),
    runtimeEn: makeSourceEntry(record.runtimeEn, 'omdb', {
      sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy'
    }),
    rated: makeSourceEntry(record.rated, 'omdb', {
      sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy'
    }),
    awards: makeSourceEntry(record.awards, 'omdb', {
      sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy'
    }),
    releaseDate: makeSourceEntry(record.releaseDate, 'merged', {
      sources: [
        { source: 'wikipedia', fields: ['date', 'location'], sourceUrl: 'https://en.wikipedia.org/wiki/Interstellar_(film)' },
        { source: 'omdb', fields: ['date'], sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy' }
      ]
    }),
    aka: makeSourceEntry(record.aka, 'wikipedia', {
      sourceUrl: 'https://zh.wikipedia.org/wiki/星际穿越'
    }),
    imdbId: makeSourceEntry(record.imdbId, 'omdb', {
      sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy'
    }),
    doubanId: makeSourceEntry(record.doubanId, 'known', {
      note: '由豆瓣 suggest 结果自动选中'
    }),
    doubanRating: makeSourceEntry(record.doubanRating, 'pending', {
      note: '豆瓣页面当前有反爬限制，暂未稳定抓取评分'
    }),
    imdbRating: makeSourceEntry(record.imdbRating, 'omdb', {
      sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy'
    }),
    rottenTomatoes: makeSourceEntry(record.rottenTomatoes, 'omdb', {
      sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy'
    }),
    metascore: makeSourceEntry(record.metascore, 'omdb', {
      sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy'
    }),
    synopsis: makeSourceEntry(record.synopsis, 'wikipedia', {
      sourceUrl: 'https://zh.wikipedia.org/wiki/星际穿越',
      note: '列表页短简介由 Wiki 条目摘要整理'
    }),
    story: makeSourceEntry(record.story, 'wikipedia', {
      sourceUrl: 'https://zh.wikipedia.org/wiki/星际穿越',
      note: '详情介绍使用中文维基“剧情”章节原文；story.note 不进入数据库主字段'
    }),
    soundtrack: makeSourceEntry(record.soundtrack, 'manual', {
      sourceUrl: 'https://en.wikipedia.org/wiki/Interstellar_(film)',
      note: '原声带曲目按公开 OST 信息整理为 albums[]'
    }),
    videos: makeSystemEntry(record.videos, '当前无稳定视频来源，先保留空数组'),
    similar: makeSourceEntry(record.similar, 'manual', {
      note: '按题材和气质补充相近作品'
    }),
    reviews: makeSourceEntry(record.reviews, 'merged', {
      sources: [
        { source: 'douban', fields: ['reviews'], sourceUrl: 'https://movie.douban.com/subject/1889243/' },
        { source: 'tmdb', fields: ['reviews'], sourceUrl: 'https://www.themoviedb.org/movie/157336-interstellar/reviews' },
        { source: 'rottentomatoes', fields: ['reviews'], sourceUrl: 'https://www.rottentomatoes.com/m/interstellar_2014/reviews' }
      ],
      note: '已合并豆瓣长评/短评、TMDB 用户评价、烂番茄评论摘录'
    }),
    images: {
      poster: makeSourceEntry(record.images.poster, 'tmdb', {
        sourceUrl: 'https://www.themoviedb.org/movie/157336-interstellar/images/posters',
        downloadedFrom: 'https://image.tmdb.org/t/p/original/yQvGrMoipbRoddT0ZR8tPoR7NfX.jpg',
        note: '主海报当前使用 TMDB 高清海报原图'
      }),
      posters: makeSourceEntry(record.images.posters, 'tmdb', {
        sourceUrl: 'https://www.themoviedb.org/movie/157336-interstellar/images/posters',
        note: '海报画廊改为 TMDB 多张海报组合获取'
      }),
      postersTotal: makeSourceEntry(record.images.postersTotal, 'tmdb', {
        sourceUrl: 'https://www.themoviedb.org/movie/157336-interstellar/images/posters'
      }),
      stills: makeSourceEntry(record.images.stills, 'tmdb', {
        sourceUrl: 'https://www.themoviedb.org/movie/157336-interstellar/images/backdrops',
        note: '剧照改为 TMDB backdrops 组合获取'
      }),
      stillsTotal: makeSourceEntry(record.images.stillsTotal, 'tmdb', {
        sourceUrl: 'https://www.themoviedb.org/movie/157336-interstellar/images/backdrops'
      }),
      wallpapers: makeSourceEntry(record.images.wallpapers, 'system', {
        note: '当前未单独维护 wallpapers，先保留空数组'
      })
    },
    links: makeSourceEntry(record.links, 'merged', {
      sources: [
        { source: 'known', fields: ['douban'] },
        { source: 'omdb', fields: ['imdb'], sourceUrl: 'https://www.omdbapi.com/?i=tt0816692&apikey=trilogy' },
        { source: 'tmdb', fields: ['tmdb'], sourceUrl: 'https://www.themoviedb.org/movie/157336-interstellar' }
      ]
    }),
    module: makeSystemEntry(record.module, '影视模块'),
    submodule: makeSystemEntry(record.submodule, '电影子模块'),
    createdAt: makeSystemEntry(record.createdAt, '录入时间'),
    updatedAt: makeSystemEntry(record.updatedAt, '最后更新时间'),
    schemaType: makeSystemEntry(record.schemaType, '电影录入默认使用 live_action_movie'),
    status: makeSystemEntry(record.status, '新录入条目默认 published'),
    tags: makeSystemEntry(record.tags, '当前未建立标签，先保留空数组'),
    series: makeSystemEntry(record.series, '当前未识别系列关系，先保留空数组'),
    quotes: makeSystemEntry(record.quotes, '当前未整理 quotes，先保留空数组'),
    tmdbId: makeSourceEntry(record.tmdbId, 'tmdb', {
      sourceUrl: 'https://www.themoviedb.org/movie/157336-interstellar'
    })
  };

  return { record, sourceData };
}

function patchSourcesForNewFields(sourceData, record) {
  sourceData.schemaType = { value: 'live_action_movie', source: 'system', note: '电影录入默认使用 live_action_movie' };
  sourceData.status = { value: record.status, source: 'system', note: '新录入条目默认 published' };
  sourceData.tags = { value: record.tags ?? [], source: 'system', note: '当前未建立标签，先保留空数组' };
  sourceData.series = { value: record.series ?? [], source: 'system', note: '当前未识别系列关系，先保留空数组' };
  sourceData.quotes = { value: record.quotes ?? [], source: 'system', note: '当前未整理 quotes，先保留空数组' };
  if (!sourceData.publishCompany) {
    sourceData.publishCompany = makeSystemEntry(record.publishCompany ?? null, '当前无稳定出品公司来源或待后续补充');
  }
  if (!sourceData.tmdbId) {
    sourceData.tmdbId = makeSystemEntry(record.tmdbId ?? null, '当前未补到 TMDB id');
  }
  if ('soundtrack' in record && !sourceData.soundtrack) {
    sourceData.soundtrack = makeSystemEntry(record.soundtrack ?? null, '历史样板缺少 soundtrack 来源占位，先按当前记录补齐');
  }
  if ('awards' in record && !sourceData.awards) {
    sourceData.awards = makeSystemEntry(record.awards ?? null, '历史样板缺少 awards 来源占位，先按当前记录补齐');
  }
  if ('rated' in record && !sourceData.rated) {
    sourceData.rated = makeSystemEntry(record.rated ?? null, '历史样板缺少 rated 来源占位，先按当前记录补齐');
  }
  if ('imdbRating' in record && !sourceData.imdbRating) {
    sourceData.imdbRating = makeSystemEntry(record.imdbRating ?? null, '历史样板缺少 imdbRating 来源占位，先按当前记录补齐');
  }
  if ('rottenTomatoes' in record && !sourceData.rottenTomatoes) {
    sourceData.rottenTomatoes = makeSystemEntry(record.rottenTomatoes ?? null, '历史样板缺少 rottenTomatoes 来源占位，先按当前记录补齐');
  }
  if ('metascore' in record && !sourceData.metascore) {
    sourceData.metascore = makeSystemEntry(record.metascore ?? null, '历史样板缺少 metascore 来源占位，先按当前记录补齐');
  }
}

function normalizeReviews(record, doubanId) {
  const metadata = mapReviewMetadataByDoubanId(doubanId);
  record.reviews = (record.reviews ?? []).map((review, index) => ({
    author: review.author ?? null,
    source: review.source ?? null,
    date: review.date ?? null,
    content: review.content ?? null,
    url: review.url ?? metadata[index]?.url ?? null,
    title: review.title ?? metadata[index]?.title ?? null
  }));
}

function normalizeCountry(record, sourceData) {
  const primaryCountry = inferPrimaryCountry(record);
  record.country = primaryCountry;

  if (!sourceData?.country) {
    return;
  }

  sourceData.country.value = primaryCountry;
  if (Array.isArray(record.releaseDate) && record.releaseDate.length > 1) {
    sourceData.country.note = '地区按最早公映地区推断，仅保留单一地区值；电影节与首映场次不作为首发地区依据';
  }
}

function normalizeSoundtrack(record) {
  if (!record.soundtrack) {
    return;
  }

  if (Array.isArray(record.soundtrack.albums)) {
    return;
  }

  record.soundtrack = {
    albums: [
      {
        name: record.soundtrack.name ?? null,
        note: [record.soundtrack.note ?? null, record.soundtrack.composer ? `${record.soundtrack.composer}${record.soundtrack.composerEn ? ` / ${record.soundtrack.composerEn}` : ''}` : null].filter(Boolean).join(' | ') || null,
        coverImage: record.soundtrack.coverImage ?? null,
        releaseDate: record.soundtrack.releaseDate ?? (record.soundtrack.year ? String(record.soundtrack.year) : null),
        type: record.soundtrack.type ?? 'soundtrack',
        tracks: (record.soundtrack.tracks ?? []).map((track) => ({
          name: track.name ?? track.title,
          artist: track.artist ?? null,
          duration: track.duration ?? null
        }))
      }
    ]
  };
}

async function buildRecordFromSample(task, config) {
  if (config.mode === 'builder' && config.builder === 'interstellar') {
    return buildInterstellarRecord(task, config);
  }

  const sampleMoviePath = path.join(legacySampleRoot, `${config.sampleId}.json`);
  const sampleSourcePath = path.join(legacySourceRoot, `${config.sampleId}.json`);
  const record = deepClone(await readJson(sampleMoviePath));
  const sourceData = deepClone(await readJson(sampleSourcePath));

  record.id = config.id;
  record.title = config.title;
  record.originalTitle = config.originalTitle ?? record.originalTitle;
  record.doubanId = task.doubanId;
  record.links = {
    ...record.links,
    douban: task.subjectUrl,
    imdb: record.links?.imdb ?? null,
    tmdb: record.links?.tmdb ?? null
  };
  record.module = 'video';
  record.submodule = 'movie';
  record.schemaType = 'live_action_movie';
  record.status = 'published';
  record.tags = record.tags ?? [];
  record.series = record.series ?? [];
  record.tmdbId = record.tmdbId ?? null;
  record.quotes = record.quotes ?? [];

  if (config.renameFromTitle) {
    record.synopsis = {
      ...record.synopsis,
      text: replaceTitleInText(record.synopsis?.text, config.renameFromTitle, config.title),
      note: replaceTitleInText(record.synopsis?.note, config.renameFromTitle, config.title)
    };
    record.story = {
      text: replaceTitleInText(record.story?.text, config.renameFromTitle, config.title)
    };
  } else if (record.story?.note) {
    record.story = { text: record.story.text };
  }

  normalizeReviews(record, task.doubanId);
  normalizeSoundtrack(record);
  patchSourcesForNewFields(sourceData, record);
  normalizeCountry(record, sourceData);

  sourceData.id.value = config.id;
  sourceData.title.value = config.title;
  sourceData.title.note = config.titleNote ?? sourceData.title.note;
  sourceData.doubanId.value = task.doubanId;
  sourceData.links.value.douban = task.subjectUrl;
  if (sourceData.story?.value && typeof sourceData.story.value === 'object') {
    sourceData.story.value = { text: record.story?.text ?? null };
    sourceData.story.note = `${sourceData.story.note || ''}${sourceData.story.note ? '；' : ''}story.note 不再进入数据库主字段`;
  }
  if (sourceData.reviews) {
    sourceData.reviews.note = `${sourceData.reviews.note || '豆瓣影评页数据'}；已补 review.url/title，全文保留，rating 不进入数据库`;
  }
  if (sourceData.soundtrack) {
    sourceData.soundtrack.note = `${sourceData.soundtrack.note || '原声带信息'}；已转为 albums[] 结构`;
  }

  return { record, sourceData };
}

async function buildRecordForTask(task) {
  const config = MOVIE_INTAKE_CONFIGS_BY_DOUBAN_ID[task.doubanId];
  if (config) {
    return buildRecordFromSample(task, config);
  }

  const existingMovie = await readJsonIfExists(path.join(legacySampleRoot, `${task.id}.json`));
  const existingSource = await readJsonIfExists(path.join(legacySourceRoot, `${task.id}.json`));
  if (existingMovie && existingSource) {
    patchSourcesForNewFields(existingSource, existingMovie);
    normalizeReviews(existingMovie, task.doubanId);
    normalizeSoundtrack(existingMovie);
    normalizeCountry(existingMovie, existingSource);
    return {
      record: deepClone(existingMovie),
      sourceData: deepClone(existingSource)
    };
  }

  return buildGenericRecord(task);
}

async function writeOutput(record, sourceData, mode) {
  const { outputRoot: resolvedOutputRoot, sourceRoot: resolvedSourceRoot } = resolveOutputRoots(mode);
  await fs.mkdir(resolvedOutputRoot, { recursive: true });
  await fs.mkdir(resolvedSourceRoot, { recursive: true });
  await fs.writeFile(path.join(resolvedOutputRoot, `${record.id}.json`), `${JSON.stringify(record, null, 2)}\n`, 'utf8');
  await fs.writeFile(path.join(resolvedSourceRoot, `${record.id}.json`), `${JSON.stringify(sourceData, null, 2)}\n`, 'utf8');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input) {
    console.log('Usage: node db_tools/run-movie-intake-from-tasks.mjs --input <tasks.json> [--output-mode staging]');
    return;
  }

  const payload = await readJson(path.resolve(repoRoot, args.input));
  const tasks = Array.isArray(payload.tasks) ? payload.tasks : [];

  const outputMode = normalizeOutputMode(args['output-mode']);

  const created = [];
  const skipped = [];
  for (const task of tasks) {
    const { record, sourceData } = await buildRecordForTask(task);
    const { errors } = validateRecordShape(record, sourceData);
    if (errors.length) {
      throw new Error(`Validation failed for ${record.id} ${record.title}: ${errors.join('; ')}`);
    }
    await writeOutput(record, sourceData, outputMode);
    created.push({ id: record.id, title: record.title, doubanId: record.doubanId });
  }

  console.log(JSON.stringify({ outputMode, created, skipped }, null, 2));
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
