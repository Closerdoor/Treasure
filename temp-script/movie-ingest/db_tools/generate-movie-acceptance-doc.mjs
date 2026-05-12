import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  buildDbProjection,
  buildIdentifiersJson,
  buildLinksJson,
  buildRelationsJson,
  buildRatingsJson,
  buildSoundtrackJson,
  buildImagesJson,
  normalizeForDoc,
  uniqueStrings,
  asArray
} from './movie-db-projection.mjs';

import { PATHS } from './paths.mjs';

const repoRoot = PATHS.repoRoot;
const legacyMovieRoot = PATHS.stagingDir;
const legacySourceRoot = PATHS.stagingDir;
const newMovieRoot = PATHS.stagingDir;
const newSourceRoot = PATHS.stagingDir;
const outputPath = path.join(repoRoot, 'docs', 'MOVIE-INGEST-ACCEPTANCE.md');

const FIELD_DEFS = [
  { key: 'works.id', old: (m) => m.id, next: (m) => buildDbProjection(m).works.id, source: (s) => summarize(s.id) },
  { key: 'works.module', old: (m) => m.module, next: (m) => buildDbProjection(m).works.module, source: (s) => summarize(s.module) },
  { key: 'works.submodule', old: (m) => m.submodule, next: (m) => buildDbProjection(m).works.submodule, source: (s) => summarize(s.submodule) },
  { key: 'works.schema_type', old: () => null, next: (m) => buildDbProjection(m).works.schema_type, source: (s) => summarize(s.schemaType) },
  { key: 'works.title', old: (m) => m.title, next: (m) => buildDbProjection(m).works.title, source: (s) => summarize(s.title) },
  { key: 'works.original_title', old: (m) => m.originalTitle, next: (m) => buildDbProjection(m).works.original_title, source: (s) => summarize(s.originalTitle) },
  { key: 'works.year', old: (m) => m.year, next: (m) => buildDbProjection(m).works.year, source: (s) => summarize(s.year) },
  { key: 'works.country', old: (m) => m.country, next: (m) => buildDbProjection(m).works.country, source: (s) => summarize(s.country) },
  { key: 'works.language', old: (m) => m.language, next: (m) => buildDbProjection(m).works.language, source: (s) => summarize(s.language) },
  { key: 'works.publish_company', old: () => null, next: (m) => buildDbProjection(m).works.publish_company, source: (s) => summarize(s.publishCompany) },
  { key: 'works.runtime_minutes', old: (m) => m.runtime, next: (m) => buildDbProjection(m).works.runtime_minutes, source: (s) => summarize(s.runtime) },
  { key: 'works.synopsis_text', old: (m) => m.synopsis?.text ?? null, next: (m) => buildDbProjection(m).works.synopsis_text, source: (s) => summarize(s.synopsis) },
  { key: 'works.synopsis_note', old: (m) => m.synopsis?.note ?? null, next: (m) => buildDbProjection(m).works.synopsis_note, source: (s) => summarize(s.synopsis) },
  { key: 'works.story_text', old: (m) => m.story?.text ?? null, next: (m) => buildDbProjection(m).works.story_text, source: (s) => summarize(s.story) },
  { key: 'works.aliases_json', old: (m) => uniqueStrings(m.aka ?? []), next: (m) => buildDbProjection(m).works.aliases_json, source: (s) => summarize(s.aka) },
  { key: 'works.release_dates_json', old: (m) => asArray(m.releaseDate), next: (m) => buildDbProjection(m).works.release_dates_json, source: (s) => summarize(s.releaseDate) },
  { key: 'works.identifiers_json', old: (m) => buildIdentifiersJson(m), next: (m) => buildDbProjection(m).works.identifiers_json, source: (s) => summarizeCombinedIdentifiers(s) },
  { key: 'works.ratings_json', old: (m) => buildRatingsJson(m), next: (m) => buildDbProjection(m).works.ratings_json, source: (s) => summarizeCombinedRatings(s) },
  { key: 'works.links_json', old: (m) => buildLinksJson(m), next: (m) => buildDbProjection(m).works.links_json, source: (s) => summarize(s.links) },
  { key: 'works.images_json', old: (m) => buildImagesJson(m), next: (m) => buildDbProjection(m).works.images_json, source: (s) => summarizeImages(s.images) },
  { key: 'works.videos_json', old: (m) => asArray(m.videos), next: (m) => buildDbProjection(m).works.videos_json, source: (s) => summarize(s.videos) },
  { key: 'works.reviews_json', old: (m) => asArray(m.reviews), next: (m) => buildDbProjection(m).works.reviews_json, source: (s) => summarize(s.reviews) },
  { key: 'works.soundtrack_json', old: (m) => buildSoundtrackJson(m), next: (m) => buildDbProjection(m).works.soundtrack_json, source: (s) => summarize(s.soundtrack) },
  { key: 'works.relations_json', old: (m) => buildRelationsJson(m), next: (m) => buildDbProjection(m).works.relations_json, source: (s) => summarizeCombinedRelations(s) },
  { key: 'works.quotes_json', old: () => [], next: (m) => buildDbProjection(m).works.quotes_json, source: (s) => summarize(s.quotes) },
  { key: 'works.status', old: () => 'published', next: (m) => buildDbProjection(m).works.status, source: (s) => summarize(s.status) },
  { key: 'works.created_at', old: (m) => m.createdAt, next: (m) => buildDbProjection(m).works.created_at, source: (s) => summarize(s.createdAt) },
  { key: 'works.updated_at', old: (m) => m.updatedAt, next: (m) => buildDbProjection(m).works.updated_at, source: (s) => summarize(s.updatedAt) },
  { key: 'credits.director', old: (m) => asArray(m.director), next: (m) => buildDbProjection(m).credits.director, source: (s) => summarize(s.director) },
  { key: 'credits.writer', old: (m) => asArray(m.writer), next: (m) => buildDbProjection(m).credits.writer, source: (s) => summarize(s.writer) },
  { key: 'credits.cast', old: (m) => asArray(m.cast), next: (m) => buildDbProjection(m).credits.cast, source: (s) => summarize(s.cast) },
  { key: 'credits.otherCast', old: (m) => asArray(m.otherCast), next: (m) => buildDbProjection(m).credits.otherCast, source: (s) => summarize(s.otherCast) },
  { key: 'credits.producer', old: (m) => asArray(m.producer), next: (m) => buildDbProjection(m).credits.producer, source: (s) => summarize(s.producer) },
  { key: 'terms.genre', old: (m) => asArray(m.genre), next: (m) => buildDbProjection(m).terms.genre, source: (s) => summarize(s.genre) },
  { key: 'terms.tags', old: () => [], next: (m) => buildDbProjection(m).terms.tags, source: (s) => summarize(s.tags) },
  { key: 'derived.tmdbId', old: () => null, next: (m) => m.tmdbId ?? null, source: (s) => summarize(s.tmdbId) }
];

function pretty(value) {
  return JSON.stringify(normalizeForDoc(value), null, 2);
}

function summarize(entry) {
  if (!entry) {
    return '无来源记�?;
  }

  if (entry.source === 'merged' && Array.isArray(entry.sources)) {
    return `merged: ${entry.sources.map((item) => `${item.source}${item.fields ? `(${item.fields.join('/')})` : ''}`).join(' + ')}${entry.note ? `; ${entry.note}` : ''}`;
  }

  return `${entry.source ?? 'unknown'}${entry.note ? `; ${entry.note}` : ''}`;
}

function summarizeImages(images) {
  if (!images) {
    return '无来源记�?;
  }

  const parts = [];
  for (const key of ['poster', 'posters', 'postersTotal', 'stills', 'stillsTotal', 'wallpapers']) {
    if (images[key]) {
      parts.push(`${key}:${images[key].source ?? 'unknown'}`);
    }
  }
  return parts.join('; ');
}

function summarizeCombinedIdentifiers(sources) {
  return [
    `doubanId:${summarize(sources.doubanId)}`,
    `imdbId:${summarize(sources.imdbId)}`,
    `tmdbId:${summarize(sources.tmdbId)}`
  ].join('; ');
}

function summarizeCombinedRatings(sources) {
  const items = [
    ['doubanRating', sources.doubanRating],
    ['imdbRating', sources.imdbRating],
    ['rated', sources.rated],
    ['awards', sources.awards],
    ['rottenTomatoes', sources.rottenTomatoes],
    ['metascore', sources.metascore]
  ].filter(([, value]) => Boolean(value));
  return items.map(([key, value]) => `${key}:${summarize(value)}`).join('; ');
}

function summarizeCombinedRelations(sources) {
  return [
    `series:${summarize(sources.series)}`,
    `similar:${summarize(sources.similar)}`
  ].join('; ');
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, 'utf8'));
}

async function main() {
  const files = (await fs.readdir(newMovieRoot)).filter((name) => name.endsWith('.json')).sort();
  const lines = [];

  lines.push('# Movie Ingest Acceptance');
  lines.push('');
  lines.push('> 本文档用于验收当�?4 条电影样板在“旧数据 -> 新流程数�?-> 数据库目标字段”这一层是否对齐�?);
  lines.push('> 旧的当前数据内容：来�?`.local/staging/video/movie/*.json`�?);
  lines.push('> 新流程数据内容：来自 `.local/new-flow/video/movie/*.json`�?);
  lines.push('> 数据来源或处理逻辑：来�?`.local/new-flow-field-sources/video/movie/*.json`，并补充必要的派生说明�?);
  lines.push('');

  for (const fileName of files) {
    const legacyMovie = await readJson(path.join(legacyMovieRoot, fileName));
    const newMovie = await readJson(path.join(newMovieRoot, fileName));
    const newSources = await readJson(path.join(newSourceRoot, fileName));

    lines.push(`## ${legacyMovie.id} ${legacyMovie.title}`);
    lines.push('');

    for (const field of FIELD_DEFS) {
      lines.push(`### \`${field.key}\``);
      lines.push('');
      lines.push('旧的当前数据内容�?);
      lines.push('```json');
      lines.push(pretty(field.old(legacyMovie)));
      lines.push('```');
      lines.push('');
      lines.push('新流程数据内容：');
      lines.push('```json');
      lines.push(pretty(field.next(newMovie)));
      lines.push('```');
      lines.push('');
      lines.push(`数据来源或处理逻辑�?{field.source(newSources)}`);
      lines.push('');
    }
  }

  await fs.writeFile(outputPath, `${lines.join('\n')}\n`, 'utf8');
  console.log(`doc=${path.relative(repoRoot, outputPath).replace(/\\/g, '/')}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
