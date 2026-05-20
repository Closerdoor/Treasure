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

export type MovieRecord = RatingInput & {
  id: string;
  path?: string;
  title: string;
  originalTitle?: string;
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
  module: 'video';
  submodule: 'movie';
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

async function loadMovieEntryFile(id: string): Promise<MovieRecord | null> {
  const filePath = path.join(entriesRoot, 'video', 'movie', `${id}.json`);
  try {
    const raw = await fs.readFile(filePath, 'utf8');
    return JSON.parse(raw) as MovieRecord;
  } catch {
    return null;
  }
}

export async function loadArchiveMovies(): Promise<ArchiveMovie[]> {
  const indexPath = path.join(indexesRoot, 'video-movie.json');
  const raw = await fs.readFile(indexPath, 'utf8');
  const indexItems = JSON.parse(raw) as ListIndexItem[];

  const movies: ArchiveMovie[] = [];

  for (const item of indexItems) {
    const fullRecord = await loadMovieEntryFile(item.id);
    if (fullRecord) {
      movies.push(normalizeMovie(fullRecord));
    }
  }

  return movies.sort((left, right) => right.year - left.year || left.id.localeCompare(right.id));
}

export async function loadArchiveMovieById(id: string): Promise<ArchiveMovie | null> {
  const record = await loadMovieEntryFile(id);
  if (!record) {
    return null;
  }
  return normalizeMovie(record);
}

export async function loadArchiveMovieIndex(): Promise<ListIndexItem[]> {
  const indexPath = path.join(indexesRoot, 'video-movie.json');
  const raw = await fs.readFile(indexPath, 'utf8');
  return JSON.parse(raw) as ListIndexItem[];
}

export async function loadAllMovieIds(): Promise<string[]> {
  const indexPath = path.join(indexesRoot, 'video-movie.json');
  const raw = await fs.readFile(indexPath, 'utf8');
  const indexItems = JSON.parse(raw) as ListIndexItem[];
  return indexItems.map((item) => item.id);
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
