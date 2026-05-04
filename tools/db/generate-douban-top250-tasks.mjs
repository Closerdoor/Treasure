import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..');

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

function decodeHtml(value) {
  return String(value ?? '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function normalizeText(value) {
  return decodeHtml(value).replace(/\s+/g, ' ').trim();
}

function cleanTitle(value) {
  return normalizeText(value).replace(/^[/|｜]+\s*/, '').trim() || null;
}

async function fetchHtml(url) {
  const response = await fetch(url, {
    headers: {
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`);
  }

  return response.text();
}

async function fetchTop250Page(start) {
  return fetchHtml(`https://movie.douban.com/top250?start=${start}&filter=`);
}

function stripTags(value) {
  return decodeHtml(String(value ?? '').replace(/<[^>]+>/g, ' '));
}

function extractListItems(html) {
  const listMatch = html.match(/<ol class="grid_view">([\s\S]*?)<\/ol>/i);
  if (!listMatch) {
    throw new Error('Unable to locate Top250 list container');
  }

  return [...listMatch[1].matchAll(/<li>\s*<div class="item">([\s\S]*?)<\/div>\s*<\/li>/gi)].map((match) => match[1]);
}

function parseTitleLine(block) {
  const titleMatches = [...block.matchAll(/<span class="title">([\s\S]*?)<\/span>/gi)].map((match) => cleanTitle(match[1]));
  const [title, originalTitle] = titleMatches;
  return {
    title: title ?? null,
    originalTitle: originalTitle ?? null
  };
}

function parseMetaLine(block) {
  const metaMatch = block.match(/<p>\s*([\s\S]*?)<\/p>/i);
  const raw = String(metaMatch?.[1] ?? '').replace(/<br\s*\/?>/gi, '\n');
  const lines = raw.split('\n').map((line) => normalizeText(line)).filter(Boolean);
  const infoLine = lines.at(-1) ?? '';
  const text = normalizeText(lines.join(' / '));
  const yearMatch = infoLine.match(/(?:^|\s)((?:19|20)\d{2})(?:\s|\/|$)/);
  const year = yearMatch ? Number.parseInt(yearMatch[1], 10) : null;

  let countries = [];
  let genres = [];
  const parts = infoLine.split('/').map((part) => part.trim()).filter(Boolean);
  if (parts.length >= 3) {
    countries = parts[1].split(/\s+/).filter(Boolean);
    genres = parts[2].split(/\s+/).filter(Boolean);
  }

  return { text, year, countries, genres };
}

function parseItem(block) {
  const subjectUrl = block.match(/<a href="(https:\/\/movie\.douban\.com\/subject\/(\d+)\/?)"/i);
  const posterUrl = block.match(/<img [^>]*src="([^"]+)"/i);
  const rankMatch = block.match(/<em>(\d+)<\/em>/i);
  const ratingMatch = block.match(/<span class="rating_num"[^>]*>([^<]+)<\/span>/i);
  const quoteMatch = block.match(/<p class="quote">[\s\S]*?<span>([\s\S]*?)<\/span>[\s\S]*?<\/p>/i);
  const { title, originalTitle } = parseTitleLine(block);
  const meta = parseMetaLine(block);

  if (!subjectUrl || !title) {
    throw new Error('Unable to parse Top250 item');
  }

  return {
    rank: rankMatch ? Number.parseInt(rankMatch[1], 10) : null,
    doubanId: subjectUrl[2],
    subjectUrl: subjectUrl[1],
    posterUrl: posterUrl?.[1] ?? null,
    title,
    originalTitle,
    year: meta.year,
    rating: ratingMatch ? Number.parseFloat(ratingMatch[1]) : null,
    quote: normalizeText(quoteMatch?.[1] ?? ''),
    countries: meta.countries,
    genres: meta.genres,
    metaText: meta.text
  };
}

async function loadExistingMovies() {
  const roots = [
    path.join(repoRoot, '.local', 'staging', 'video', 'movie'),
    path.join(repoRoot, '.local', 'new-flow', 'video', 'movie')
  ];

  const byDoubanId = new Map();
  let maxSequence = 0;

  for (const root of roots) {
    try {
      const files = (await fs.readdir(root)).filter((name) => name.endsWith('.json'));
      for (const fileName of files) {
        const filePath = path.join(root, fileName);
        const movie = JSON.parse(await fs.readFile(filePath, 'utf8'));
        const id = String(movie.id ?? '').trim();
        const doubanId = String(movie.doubanId ?? '').trim();
        if (/^0101\d{6}$/.test(id)) {
          maxSequence = Math.max(maxSequence, Number.parseInt(id.slice(4), 10));
        }
        if (doubanId && id && !byDoubanId.has(doubanId)) {
          byDoubanId.set(doubanId, id);
        }
      }
    } catch {
      // ignore missing roots
    }
  }

  return { byDoubanId, maxSequence };
}

function formatMovieId(sequence) {
  return `0101${String(sequence).padStart(6, '0')}`;
}

function defaultOutputPath() {
  return path.join('.local', 'batches', 'douban-top250.tasks.json');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const maxItems = Math.max(1, Math.min(250, Number.parseInt(String(args.limit ?? '250'), 10) || 250));
  const pageCount = Math.ceil(maxItems / 25);
  const items = [];

  for (let pageIndex = 0; pageIndex < pageCount; pageIndex += 1) {
    const start = pageIndex * 25;
    const html = await fetchTop250Page(start);
    const parsed = extractListItems(html).map(parseItem).filter((item) => item.title);
    items.push(...parsed);
  }

  const sliced = items.sort((left, right) => (left.rank ?? 999) - (right.rank ?? 999)).slice(0, maxItems);
  const { byDoubanId, maxSequence } = await loadExistingMovies();

  let nextSequence = maxSequence + 1;
  const tasks = sliced.map((item) => {
    const id = byDoubanId.get(item.doubanId) ?? formatMovieId(nextSequence++);
    return {
      id,
      rank: item.rank,
      query: item.title,
      doubanId: item.doubanId,
      title: item.title,
      originalTitle: item.originalTitle,
      year: item.year,
      subjectUrl: item.subjectUrl,
      posterUrl: item.posterUrl,
      doubanRating: item.rating,
      quote: item.quote || null,
      countries: item.countries,
      genres: item.genres,
      source: byDoubanId.has(item.doubanId) ? 'existing-id' : 'top250'
    };
  });

  const outputPath = path.resolve(repoRoot, args.output || defaultOutputPath());
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const payload = {
    version: 1,
    generatedAt: new Date().toISOString(),
    workflow: 'douban_top250_tasks',
    totalTasks: tasks.length,
    tasks
  };
  await fs.writeFile(outputPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  console.log(`Generated task file: ${path.relative(repoRoot, outputPath).replace(/\\/g, '/')}`);
  console.log(`tasks=${tasks.length}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
