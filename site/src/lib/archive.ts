import fs from 'node:fs/promises';
import path from 'node:path';

const repoRoot = path.resolve(process.cwd(), '..');
const moviesRoot = path.join(repoRoot, 'content', 'video', 'movie');
const defaultAssetsRoot = path.join(process.cwd(), 'public', 'assets', 'video', 'movie');

type Person = {
  name: string;
  nameEn?: string;
  role?: string;
  avatar?: string;
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
};

export type MovieRecord = RatingInput & {
  id: string;
  title: string;
  originalTitle?: string;
  year: number;
  director?: Person[];
  writer?: Person[];
  cast?: Person[];
  otherCast?: Person[];
  producer?: Person[];
  genre?: string[];
  country?: string;
  language?: string;
  runtime?: number;
  releaseDate?: ReleaseDate[];
  aka?: string[];
  synopsis?: { text?: string; note?: string };
  story?: { text?: string; note?: string };
  videos?: Array<{ title: string; duration?: string; thumbnail?: string; url?: string }>;
  images?: {
    poster?: string;
    posters?: string[];
    stills?: string[];
  };
  soundtrack?: {
    name?: string;
    composer?: string;
    composerEn?: string;
    year?: number;
    tracks?: Array<{ index?: number; name: string; artist?: string; duration?: string }>;
  };
  similar?: Array<{ id?: string; title: string; year?: number; rating?: number }>;
  series?: Array<{ id?: string; title: string; year?: number; rating?: number }>;
  reviews?: Array<{ source?: string; author?: string; date?: string; rating?: string; content?: string }>;
  links?: Record<string, string | null>;
  module: 'video';
  submodule: 'movie';
  createdAt?: string;
  updatedAt?: string;
};

export type ArchiveMovie = MovieRecord & {
  path: string;
  posterUrl: string;
  posterGallery: string[];
  stillGallery: string[];
  aggregateRating: number | null;
  yearLabel: string;
  releaseDateLabel: string;
  directorNames: string;
  writerNames: string;
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

function normalizeMovie(movie: MovieRecord): ArchiveMovie {
  return {
    ...movie,
    path: buildMoviePath(movie),
    posterUrl: buildPosterUrl(movie),
    posterGallery: buildAssetUrls(movie, movie.images?.posters),
    stillGallery: buildAssetUrls(movie, movie.images?.stills),
    aggregateRating: computeAggregateRating(movie),
    yearLabel: String(movie.year),
    releaseDateLabel: formatReleaseDateLabel(movie.releaseDate),
    directorNames: (movie.director ?? []).map((person) => person.name).join(' / '),
    writerNames: (movie.writer ?? []).map((person) => person.name).join(' / '),
    castPreview: (movie.cast ?? []).slice(0, 3).map((person) => person.name),
    tags: dedupe([...(movie.genre ?? [])])
  };
}

export async function loadArchiveMovies() {
  const entries = await fs.readdir(moviesRoot, { withFileTypes: true });
  const ids = entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort();

  const movies = await Promise.all(
    ids.map(async (id) => {
      const filePath = path.join(moviesRoot, id, 'data.json');
      const raw = await fs.readFile(filePath, 'utf8');
      return normalizeMovie(JSON.parse(raw) as MovieRecord);
    })
  );

  return movies.sort((left, right) => right.year - left.year || left.id.localeCompare(right.id));
}

export async function loadArchiveMovieById(id: string) {
  const movies = await loadArchiveMovies();
  return movies.find((movie) => movie.id === id) ?? null;
}

export async function syncArchiveAssets({
  sourceRoot = moviesRoot,
  targetRoot = defaultAssetsRoot
}: {
  sourceRoot?: string;
  targetRoot?: string;
} = {}) {
  await fs.mkdir(targetRoot, { recursive: true });

  const entries = await fs.readdir(sourceRoot, { withFileTypes: true });

  for (const entry of entries) {
    if (!entry.isDirectory()) {
      continue;
    }

    const sourceDir = path.join(sourceRoot, entry.name, 'images');
    const targetDir = path.join(targetRoot, entry.name);

    try {
      await fs.mkdir(targetDir, { recursive: true });
      const files = await fs.readdir(sourceDir, { withFileTypes: true });

      for (const file of files) {
        if (!file.isFile()) {
          continue;
        }

        await fs.copyFile(path.join(sourceDir, file.name), path.join(targetDir, file.name));
      }
    } catch {
      // Ignore entries that don't have image folders yet.
    }
  }
}

export async function copyArchiveAssets() {
  await syncArchiveAssets();
}
