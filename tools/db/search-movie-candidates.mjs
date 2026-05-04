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
    if (!token.startsWith('--')) {
      continue;
    }

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

function printUsage() {
  console.log(`Usage: node tools/db/search-movie-candidates.mjs --input <file> [--output <file>] [--limit 5]\n\nSupported input formats:\n- .txt: one movie title per line\n- .json: ["title1", "title2"] or {"titles": ["title1", "title2"]}`);
}

function normalizeWhitespace(value) {
  return String(value ?? '').replace(/\s+/g, ' ').trim();
}

function normalizeText(value) {
  return normalizeWhitespace(value)
    .toLowerCase()
    .replace(/[\s·•:：'"“”‘’()（）\[\]{}.,，!！?？\-_/\\]+/g, '');
}

function splitQuery(rawQuery) {
  const query = normalizeWhitespace(rawQuery);
  const yearMatch = query.match(/(?:^|\D)((?:19|20)\d{2})(?:\D|$)/);
  const queryYear = yearMatch ? Number.parseInt(yearMatch[1], 10) : null;
  const queryTitle = normalizeWhitespace(query.replace(/(?:^|\D)(?:19|20)\d{2}(?:\D|$)/g, ' '));
  return {
    query,
    queryTitle: queryTitle || query,
    queryYear
  };
}

async function loadQueries(inputPath) {
  const absolutePath = path.resolve(repoRoot, inputPath);
  const extension = path.extname(absolutePath).toLowerCase();
  const raw = await fs.readFile(absolutePath, 'utf8');

  if (extension === '.txt') {
    return raw
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith('#'));
  }

  if (extension === '.json') {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed.map((value) => normalizeWhitespace(value)).filter(Boolean);
    }

    if (Array.isArray(parsed.titles)) {
      return parsed.titles.map((value) => normalizeWhitespace(value)).filter(Boolean);
    }
  }

  throw new Error(`Unsupported input format: ${absolutePath}`);
}

async function fetchCandidates(query) {
  const url = `https://movie.douban.com/j/subject_suggest?q=${encodeURIComponent(query)}`;
  const response = await fetch(url, {
    headers: {
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
    }
  });

  if (!response.ok) {
    throw new Error(`Douban suggest request failed: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

function buildReasons(queryInfo, candidate) {
  const reasons = [];
  const queryNorm = normalizeText(queryInfo.queryTitle);
  const titleNorm = normalizeText(candidate.title);
  const originalNorm = normalizeText(candidate.originalTitle);

  if (queryNorm && titleNorm === queryNorm) reasons.push('title_exact');
  if (queryNorm && originalNorm === queryNorm) reasons.push('original_exact');
  if (queryNorm && titleNorm.includes(queryNorm) && titleNorm !== queryNorm) reasons.push('title_contains');
  if (queryNorm && originalNorm.includes(queryNorm) && originalNorm !== queryNorm) reasons.push('original_contains');
  if (queryInfo.queryYear && candidate.year === queryInfo.queryYear) reasons.push('year_exact');
  if (candidate.type === 'movie') reasons.push('type_movie');
  return reasons;
}

function scoreCandidate(queryInfo, candidate) {
  let score = 0;
  const reasons = buildReasons(queryInfo, candidate);

  for (const reason of reasons) {
    if (reason === 'title_exact') score += 100;
    if (reason === 'original_exact') score += 80;
    if (reason === 'title_contains') score += 35;
    if (reason === 'original_contains') score += 20;
    if (reason === 'year_exact') score += 15;
    if (reason === 'type_movie') score += 10;
  }

  return { score, reasons };
}

function normalizeCandidate(entry, queryInfo) {
  const candidate = {
    doubanId: normalizeWhitespace(entry.id),
    title: normalizeWhitespace(entry.title),
    originalTitle: normalizeWhitespace(entry.sub_title),
    year: entry.year ? Number.parseInt(entry.year, 10) : null,
    type: normalizeWhitespace(entry.type) || null,
    subjectUrl: normalizeWhitespace(entry.url),
    posterUrl: normalizeWhitespace(entry.img) || null
  };

  const { score, reasons } = scoreCandidate(queryInfo, candidate);
  return {
    ...candidate,
    score,
    reasons
  };
}

function pickAutoSelection(candidates) {
  if (!candidates.length) {
    return null;
  }

  const [first, second] = candidates;
  const gap = first.score - (second?.score ?? 0);
  if (first.score >= 110 && gap >= 30) {
    return {
      doubanId: first.doubanId,
      confidence: 'high',
      reason: `auto-picked from score ${first.score} with gap ${gap}`
    };
  }

  return null;
}

function buildResultItem(queryInfo, entries, limit) {
  const candidates = entries
    .map((entry) => normalizeCandidate(entry, queryInfo))
    .sort((left, right) => right.score - left.score)
    .slice(0, limit)
    .map((candidate, index) => ({ rank: index + 1, ...candidate }));

  const autoSelection = pickAutoSelection(candidates);
  return {
    query: queryInfo.query,
    queryTitle: queryInfo.queryTitle,
    queryYear: queryInfo.queryYear,
    searchUrl: `https://movie.douban.com/j/subject_suggest?q=${encodeURIComponent(queryInfo.query)}`,
    selectedDoubanId: null,
    autoSelection,
    needsReview: !autoSelection,
    candidates
  };
}

function defaultOutputPath(inputPath) {
  const inputName = path.basename(inputPath, path.extname(inputPath));
  return path.join('.local', 'batches', `${inputName}.candidates.json`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input || args.help) {
    printUsage();
    return;
  }

  const limit = Math.max(1, Number.parseInt(String(args.limit ?? '5'), 10) || 5);
  const queries = await loadQueries(args.input);
  if (!queries.length) {
    throw new Error('No movie titles found in input file.');
  }

  const items = [];
  for (const rawQuery of queries) {
    const queryInfo = splitQuery(rawQuery);
    const entries = await fetchCandidates(queryInfo.queryTitle);
    items.push(buildResultItem(queryInfo, Array.isArray(entries) ? entries : [], limit));
  }

  const outputPath = path.resolve(repoRoot, args.output || defaultOutputPath(args.input));
  await fs.mkdir(path.dirname(outputPath), { recursive: true });

  const payload = {
    version: 1,
    generatedAt: new Date().toISOString(),
    input: path.relative(repoRoot, path.resolve(repoRoot, args.input)).replace(/\\/g, '/'),
    workflow: 'movie_candidate_search',
    totalQueries: items.length,
    autoSelected: items.filter((item) => item.autoSelection).length,
    needsReview: items.filter((item) => item.needsReview).length,
    items
  };

  await fs.writeFile(outputPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  console.log(`Generated candidate file: ${path.relative(repoRoot, outputPath).replace(/\\/g, '/')}`);
  console.log(`queries=${payload.totalQueries}, autoSelected=${payload.autoSelected}, needsReview=${payload.needsReview}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
