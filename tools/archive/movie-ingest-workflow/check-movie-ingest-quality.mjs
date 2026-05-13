import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateRecordShape } from './validate-movie-record.mjs';

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

function normalizeMode(value) {
  return value === 'new-flow' ? 'new-flow' : 'staging';
}

function rootsForMode(mode) {
  if (mode === 'new-flow') {
    return {
      movieRoot: path.join(repoRoot, '.local', 'new-flow', 'video', 'movie'),
      sourceRoot: path.join(repoRoot, '.local', 'new-flow-field-sources', 'video', 'movie')
    };
  }

  return {
    movieRoot: path.join(repoRoot, '.local', 'staging', 'video', 'movie'),
    sourceRoot: path.join(repoRoot, '.local', 'field-sources', 'video', 'movie')
  };
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, 'utf8'));
}

function classifyReviewSource(source) {
  if (source === '豆瓣长评') return 'doubanLong';
  if (source === '豆瓣短评') return 'doubanShort';
  if (source === 'TMDB') return 'tmdb';
  if (typeof source === 'string' && source.startsWith('烂番茄')) return 'rottenTomatoes';
  return 'other';
}

function buildReviewCoverage(reviews) {
  const coverage = {
    total: 0,
    doubanLong: 0,
    doubanShort: 0,
    tmdb: 0,
    rottenTomatoes: 0,
    other: 0
  };

  for (const review of Array.isArray(reviews) ? reviews : []) {
    coverage.total += 1;
    coverage[classifyReviewSource(review.source)] += 1;
  }

  return coverage;
}

function hasEarliestTheatricalCountryNote(sourceData) {
  const note = sourceData?.country?.note;
  return typeof note === 'string' && note.includes('最早公映地区推断');
}

function hasTmdbPosterSource(sourceData) {
  return sourceData?.images?.poster?.source === 'tmdb';
}

function hasMergedReviewsSource(sourceData) {
  if (sourceData?.reviews?.source !== 'merged' || !Array.isArray(sourceData?.reviews?.sources)) {
    return false;
  }

  const names = new Set(sourceData.reviews.sources.map((item) => item?.source).filter(Boolean));
  return names.has('douban') && names.has('tmdb') && names.has('rottentomatoes');
}

function hasHighStandardReviewCoverage(coverage) {
  return coverage.total >= 40
    && coverage.doubanLong >= 10
    && coverage.doubanShort >= 10
    && coverage.tmdb >= 10
    && coverage.rottenTomatoes >= 10;
}

function checkMovieQuality(movie, sourceData, { strict = true, enforceHighStandard = false } = {}) {
  const { errors: contractErrors } = validateRecordShape(movie, sourceData);
  const coverage = buildReviewCoverage(movie.reviews);
  const errors = [...contractErrors];
  const warnings = [];
  const highStandardFindings = [];

  if (!movie?.story || Object.keys(movie.story).some((key) => key !== 'text')) {
    errors.push('story must contain only text field');
  }

  if (movie?.soundtrack && !Array.isArray(movie.soundtrack?.albums)) {
    errors.push('soundtrack must use albums[] structure');
  }

  const reviews = Array.isArray(movie?.reviews) ? movie.reviews : [];
  reviews.forEach((review, index) => {
    if (!review?.author) errors.push(`reviews[${index}] missing author`);
    if (!review?.source) errors.push(`reviews[${index}] missing source`);
    if (!review?.date) errors.push(`reviews[${index}] missing date`);
    if (!review?.content) errors.push(`reviews[${index}] missing content`);
  });

  if (!hasMergedReviewsSource(sourceData)) {
    highStandardFindings.push('field sources reviews must be merged and include douban/tmdb/rottentomatoes');
  }

  if (!hasTmdbPosterSource(sourceData)) {
    highStandardFindings.push('images.poster source must be tmdb');
  }

  if (!hasEarliestTheatricalCountryNote(sourceData)) {
    highStandardFindings.push('country source note must describe earliest theatrical release rule');
  }

  if (!hasHighStandardReviewCoverage(coverage)) {
    const message = `reviews coverage below high standard: total=${coverage.total}, doubanLong=${coverage.doubanLong}, doubanShort=${coverage.doubanShort}, tmdb=${coverage.tmdb}, rottenTomatoes=${coverage.rottenTomatoes}`;
    highStandardFindings.push(message);
  }

  if (enforceHighStandard) {
    errors.push(...highStandardFindings);
  } else {
    warnings.push(...highStandardFindings);
  }

  return {
    id: movie.id,
    title: movie.title,
    reviewCoverage: coverage,
    highStandardPassed: highStandardFindings.length === 0,
    posterSource: sourceData?.images?.poster?.source ?? null,
    countryNote: sourceData?.country?.note ?? null,
    errors,
    warnings,
    passed: errors.length === 0
  };
}

async function collectIds(args, movieRoot) {
  if (args.ids) {
    return String(args.ids).split(',').map((value) => value.trim()).filter(Boolean);
  }

  if (args.movie) {
    return [path.basename(args.movie, '.json')];
  }

  if (args.all) {
    return (await fs.readdir(movieRoot)).filter((name) => name.endsWith('.json')).map((name) => path.basename(name, '.json')).sort();
  }

  throw new Error('Usage: node tools/db/check-movie-ingest-quality.mjs --ids <id1,id2> [--mode staging|new-flow] [--strict]');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const mode = normalizeMode(args.mode);
  const strict = Boolean(args.strict);
  const enforceHighStandard = Boolean(args['enforce-high-standard']);
  const { movieRoot, sourceRoot } = rootsForMode(mode);
  const ids = await collectIds(args, movieRoot);

  const results = [];
  for (const id of ids) {
    const movie = await readJson(path.join(movieRoot, `${id}.json`));
    const sourceData = await readJson(path.join(sourceRoot, `${id}.json`));
    results.push(checkMovieQuality(movie, sourceData, { strict, enforceHighStandard }));
  }

  const payload = {
    version: 1,
    generatedAt: new Date().toISOString(),
    mode,
    strict,
    enforceHighStandard,
    total: results.length,
    passed: results.filter((item) => item.passed).length,
    failed: results.filter((item) => !item.passed).length,
    highStandardPassed: results.filter((item) => item.highStandardPassed).length,
    highStandardFailed: results.filter((item) => !item.highStandardPassed).length,
    results
  };

  console.log(JSON.stringify(payload, null, 2));
  if (payload.failed > 0) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
