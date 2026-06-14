import fs from 'node:fs/promises';
import path from 'node:path';

const repoRoot = path.resolve(process.cwd(), '..');
const generatedRoot = path.join(repoRoot, 'generated');
const entriesRoot = path.join(generatedRoot, 'entries');
const indexesRoot = path.join(generatedRoot, 'indexes');

type Person = {
  personCode?: string;
  name: string;
  nameEn?: string;
  role?: string;
  avatar?: string;
  avatarPath?: string;
  avatarSource?: string;
  avatarNote?: string;
  profileLink?: string;
  notes?: string;
  works?: string[];
};

type ReleaseDate = {
  date: string;
  location?: string;
};

type RatingInput = {
  doubanRating?: number;
  imdbRating?: number;
  tmdbRating?: number;
  rottenTomatoes?: number;
  metascore?: number;
};

export type MediaModule = 'video' | 'anime';
export type MediaSubmodule = 'movie' | 'documentary' | 'tv_series' | 'anime_movie' | 'anime_series';

export type MovieRecord = RatingInput & {
  id: string;
  path?: string;
  title: string;
  originalTitle?: string;
  schemaType?: string;
  year: number;
  director?: Person[];
  writer?: Person[];
  cast?: Person[];
  otherCast?: Person[];
  producer?: Person[];
  genre?: string[];
  tags?: string[];
  country?: string;
  language?: string;
  publishCompany?: string;
  runtime?: number;
  episodeCount?: number;
  episodeTime?: number;
  episodesStory?: Array<{ episode?: number; title?: string; plot?: string }>;
  releaseDate?: ReleaseDate[];
  aka?: string[];
  synopsis?: { text?: string; note?: string };
  story?: { text?: string };
  videos?: Array<{ title: string; duration?: string; thumbnail?: string; url?: string }>;
  images?: {
    poster?: string;
    covers?: Record<string, string>;
    posters?: string[];
    stills?: string[];
    wallpapers?: string[];
  };
  soundtrack?: {
    albums?: Array<{
      name?: string;
      note?: string;
      coverImage?: string;
      releaseDate?: string;
      type?: string;
      tracks?: Array<{ name: string; artist?: string; duration?: string }>;
    }>;
  };
  similar?: Array<{ id?: string; title: string; year?: number; rating?: number }>;
  series?: Array<{ id?: string; title: string; year?: number; rating?: number }>;
  reviews?: Array<{ source?: string; author?: string; date?: string; content?: string; url?: string; title?: string | null }>;
  links?: Record<string, string | null>;
  quotes?: Array<{ text: string; speaker?: string; note?: string }>;
  characters?: Array<{ name?: string; voiceActor?: string; actor?: string; image?: string; description?: string }>;
  module: MediaModule;
  submodule: MediaSubmodule;
  createdAt?: string;
  updatedAt?: string;
};

export type ListIndexItem = {
  id: string;
  path: string;
  title: string;
  originalTitle?: string | null;
  year: number;
  posterUrl: string;
  aggregateRating: number | null;
  directorNames: string | null;
  castPreview: string[];
  genre: string[];
  tags: string[];
  country: string | null;
  synopsis: string | null;
};

export type ArchiveMovie = MovieRecord & {
  path: string;
  posterUrl: string;
  posterGallery: string[];
  stillGallery: string[];
  wallpaperGallery: string[];
  aggregateRating: number | null;
  yearLabel: string;
  releaseDateLabel: string;
  directorNames: string;
  writerNames: string;
  mergedCreditNames: string;
  castPreview: string[];
  tags: string[];
};

export function computeAggregateRating(input: RatingInput): number | null {
  const values = [input.doubanRating, input.imdbRating, input.tmdbRating];

  if (typeof input.rottenTomatoes === 'number') {
    values.push(input.rottenTomatoes / 10);
  }

  const valid = values.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));

  if (valid.length === 0) {
    return null;
  }

  const average = valid.reduce((sum, value) => sum + value, 0) / valid.length;
  return Math.round(average * 10) / 10;
}

function buildMoviePath(movie: Pick<MovieRecord, 'module' | 'submodule' | 'id'>) {
  return `/${movie.module}/${movie.submodule}/${movie.id}`;
}

function buildPosterUrl(movie: Pick<MovieRecord, 'module' | 'submodule' | 'id' | 'images'>) {
  const poster = movie.images?.poster;
  if (!poster) {
    return '/assets/poster-placeholder.svg';
  }

  return `/assets/${movie.module}/${movie.submodule}/${movie.id}/${poster}`;
}

function buildAssetUrls(movie: Pick<MovieRecord, 'module' | 'submodule' | 'id'>, files?: string[]) {
  return (files ?? []).map((file) => `/assets/${movie.module}/${movie.submodule}/${movie.id}/${file}`);
}

function formatReleaseDateLabel(releaseDate?: ReleaseDate[]) {
  if (!releaseDate?.length) {
    return '';
  }

  return releaseDate
    .map((item) => (item.location ? `${item.date} ${item.location}` : item.date))
    .join(' / ');
}

function dedupe(values: string[]) {
  return [...new Set(values.filter(Boolean))];
}

function buildMergedCreditNames(movie: Pick<MovieRecord, 'director' | 'writer'>) {
  const merged = new Map<string, string[]>();

  for (const person of movie.director ?? []) {
    const key = person.personCode || person.nameEn || person.name;
    const labels = merged.get(key) ?? [];
    if (!labels.includes('导演')) labels.push('导演');
    merged.set(key, labels);
  }

  for (const person of movie.writer ?? []) {
    const key = person.personCode || person.nameEn || person.name;
    const labels = merged.get(key) ?? [];
    const label = person.role || '编剧';
    if (!labels.includes(label)) labels.push(label);
    merged.set(key, labels);
  }

  const orderedPeople = [...(movie.director ?? []), ...(movie.writer ?? [])]
    .filter((person, index, array) => {
      const key = person.personCode || person.nameEn || person.name;
      return array.findIndex((item) => (item.personCode || item.nameEn || item.name) === key) === index;
    });

  return orderedPeople
    .map((person) => {
      const key = person.personCode || person.nameEn || person.name;
      const labels = merged.get(key) ?? [];
      return labels.length ? `${person.name}（${labels.join(' / ')}）` : person.name;
    })
    .join(' / ');
}

function normalizeMovie(movie: MovieRecord): ArchiveMovie {
  return {
    ...movie,
    path: movie.path || buildMoviePath(movie),
    posterUrl: buildPosterUrl(movie),
    posterGallery: buildAssetUrls(movie, movie.images?.posters),
    stillGallery: buildAssetUrls(movie, movie.images?.stills),
    wallpaperGallery: buildAssetUrls(movie, movie.images?.wallpapers),
    aggregateRating: computeAggregateRating(movie),
    yearLabel: String(movie.year),
    releaseDateLabel: formatReleaseDateLabel(movie.releaseDate),
    directorNames: (movie.director ?? []).map((person) => person.name).join(' / '),
    writerNames: (movie.writer ?? []).map((person) => person.name).join(' / '),
    mergedCreditNames: buildMergedCreditNames(movie),
    castPreview: (movie.cast ?? []).slice(0, 3).map((person) => person.name),
    tags: dedupe([...(movie.tags ?? []), ...(movie.genre ?? [])])
  };
}

async function loadMediaEntryFile(module: MediaModule, submodule: MediaSubmodule, id: string): Promise<MovieRecord | null> {
  const filePath = path.join(entriesRoot, module, submodule, `${id}.json`);
  try {
    const raw = await fs.readFile(filePath, 'utf8');
    return JSON.parse(raw) as MovieRecord;
  } catch {
    return null;
  }
}

async function loadArchiveIndex(indexName: string): Promise<ListIndexItem[]> {
  const indexPath = path.join(indexesRoot, indexName);
  const raw = await fs.readFile(indexPath, 'utf8');
  return JSON.parse(raw) as ListIndexItem[];
}

async function loadArchiveEntriesFromIndex(indexName: string): Promise<ArchiveMovie[]> {
  const indexItems = await loadArchiveIndex(indexName);
  const movies: ArchiveMovie[] = [];

  for (const item of indexItems) {
    const segments = item.path.split('/').filter(Boolean);
    const [module, submodule] = segments;
    const fullRecord = await loadMediaEntryFile(module as MediaModule, submodule as MediaSubmodule, item.id);
    if (fullRecord) {
      movies.push(normalizeMovie(fullRecord));
    }
  }

  return movies.sort((left, right) => (right.year ?? 0) - (left.year ?? 0) || left.id.localeCompare(right.id));
}

export async function loadArchiveVideoWorks(): Promise<ArchiveMovie[]> {
  return loadArchiveEntriesFromIndex('video.json');
}

export async function loadArchiveMovies(): Promise<ArchiveMovie[]> {
  return loadArchiveEntriesFromIndex('video-movie.json');
}

export async function loadArchiveAnimeMovies(): Promise<ArchiveMovie[]> {
  return loadArchiveEntriesFromIndex('anime-anime_movie.json');
}

export async function loadArchiveAnimeWorks(): Promise<ArchiveMovie[]> {
  return loadArchiveEntriesFromIndex('anime.json');
}

export async function loadArchiveMovieById(id: string): Promise<ArchiveMovie | null> {
  const record = await loadMediaEntryFile('video', 'movie', id);
  if (!record) {
    return null;
  }
  return normalizeMovie(record);
}

export async function loadArchiveDocumentaryById(id: string): Promise<ArchiveMovie | null> {
  const record = await loadMediaEntryFile('video', 'documentary', id);
  if (!record) {
    return null;
  }
  return normalizeMovie(record);
}

export async function loadArchiveTvSeriesById(id: string): Promise<ArchiveMovie | null> {
  const record = await loadMediaEntryFile('video', 'tv_series', id);
  if (!record) {
    return null;
  }
  return normalizeMovie(record);
}

export async function loadArchiveAnimeMovieById(id: string): Promise<ArchiveMovie | null> {
  const record = await loadMediaEntryFile('anime', 'anime_movie', id);
  if (!record) {
    return null;
  }
  return normalizeMovie(record);
}

export async function loadArchiveAnimeSeriesById(id: string): Promise<ArchiveMovie | null> {
  const record = await loadMediaEntryFile('anime', 'anime_series', id);
  if (!record) {
    return null;
  }
  return normalizeMovie(record);
}

export async function loadArchiveMovieIndex(): Promise<ListIndexItem[]> {
  return loadArchiveIndex('video-movie.json');
}

export async function loadAllMovieIds(): Promise<string[]> {
  return (await loadArchiveIndex('video-movie.json')).map((item) => item.id);
}

export async function loadAllDocumentaryIds(): Promise<string[]> {
  return (await loadArchiveIndex('video-documentary.json')).map((item) => item.id);
}

export async function loadAllTvSeriesIds(): Promise<string[]> {
  return (await loadArchiveIndex('video-tv_series.json')).map((item) => item.id);
}

export async function loadAllAnimeMovieIds(): Promise<string[]> {
  return (await loadArchiveIndex('anime-anime_movie.json')).map((item) => item.id);
}

export async function loadAllAnimeSeriesIds(): Promise<string[]> {
  return (await loadArchiveIndex('anime-anime_series.json')).map((item) => item.id);
}

export async function syncArchiveAssets({
  targetRoot = path.join(process.cwd(), 'public', 'assets')
}: {
  targetRoot?: string;
} = {}) {
  await fs.mkdir(targetRoot, { recursive: true });
}

export async function copyArchiveAssets() {
  await syncArchiveAssets();
}
