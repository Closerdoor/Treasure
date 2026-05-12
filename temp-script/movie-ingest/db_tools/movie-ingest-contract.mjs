export const REQUIRED_TOP_LEVEL_KEYS = [
  'aka',
  'cast',
  'country',
  'createdAt',
  'director',
  'doubanId',
  'doubanRating',
  'genre',
  'id',
  'images',
  'imdbId',
  'language',
  'links',
  'module',
  'originalTitle',
  'otherCast',
  'producer',
  'releaseDate',
  'reviews',
  'runtime',
  'similar',
  'story',
  'submodule',
  'synopsis',
  'title',
  'updatedAt',
  'videos',
  'writer',
  'year'
];

export const OPTIONAL_TOP_LEVEL_KEYS = [
  'awards',
  'imdbRating',
  'metascore',
  'rated',
  'rottenTomatoes',
  'runtimeEn',
  'soundtrack'
];

export const EXTENDED_TOP_LEVEL_KEYS = [
  'publishCompany',
  'quotes',
  'schemaType',
  'series',
  'status',
  'tags',
  'tmdbId'
];

export const ALLOWED_TOP_LEVEL_KEYS = [...REQUIRED_TOP_LEVEL_KEYS, ...OPTIONAL_TOP_LEVEL_KEYS, ...EXTENDED_TOP_LEVEL_KEYS].sort();

export const IMAGE_REQUIRED_KEYS = ['poster', 'posters', 'stills', 'wallpapers'];
export const IMAGE_OPTIONAL_KEYS = ['postersTotal', 'stillsTotal'];

export function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

export function allowedTopLevelKeySet() {
  return new Set(ALLOWED_TOP_LEVEL_KEYS);
}

export function requiredTopLevelKeySet() {
  return new Set(REQUIRED_TOP_LEVEL_KEYS);
}

export function imageKeySet() {
  return new Set([...IMAGE_REQUIRED_KEYS, ...IMAGE_OPTIONAL_KEYS]);
}
