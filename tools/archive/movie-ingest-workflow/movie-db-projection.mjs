import path from 'node:path';

export function asArray(value) {
  return Array.isArray(value) ? value : [];
}

export function nonEmptyString(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

export function uniqueStrings(values) {
  return [...new Set(asArray(values).map((value) => nonEmptyString(value)).filter(Boolean))];
}

const RELEASE_LOCATION_COUNTRY_RULES = [
  { pattern: /多伦多|toronto/i, country: '加拿大' },
  { pattern: /戛纳|cannes/i, country: '法国' },
  { pattern: /威尼斯|venice/i, country: '意大利' },
  { pattern: /柏林|berlin/i, country: '德国' },
  { pattern: /圣丹斯|sundance/i, country: '美国' },
  { pattern: /釜山|busan/i, country: '韩国' },
  { pattern: /东京|tokyo/i, country: '日本' },
  { pattern: /上海|shanghai/i, country: '中国大陆' },
  { pattern: /北京|beijing/i, country: '中国大陆' },
  { pattern: /香港|hong kong/i, country: '中国香港' },
  { pattern: /台北|taipei/i, country: '中国台湾' },
  { pattern: /洛杉矶|los angeles/i, country: '美国' },
  { pattern: /纽约|new york/i, country: '美国' },
  { pattern: /伦敦|london/i, country: '英国' },
  { pattern: /^美国$/i, country: '美国' },
  { pattern: /^英国$/i, country: '英国' },
  { pattern: /^加拿大$/i, country: '加拿大' },
  { pattern: /^中国大陆$/i, country: '中国大陆' },
  { pattern: /^中国香港$/i, country: '中国香港' },
  { pattern: /^中国台湾$/i, country: '中国台湾' },
  { pattern: /^日本$/i, country: '日本' },
  { pattern: /^韩国$/i, country: '韩国' },
  { pattern: /^法国$/i, country: '法国' },
  { pattern: /^德国$/i, country: '德国' },
  { pattern: /^意大利$/i, country: '意大利' }
];

const NON_THEATRICAL_RELEASE_MARKERS = /电影节|影展|film festival|festival|首映|premiere|screening/i;

function inferCountryFromLocation(location) {
  const text = nonEmptyString(location);
  if (!text) {
    return null;
  }

  const matchedRule = RELEASE_LOCATION_COUNTRY_RULES.find((rule) => rule.pattern.test(text));
  return matchedRule?.country ?? null;
}

function isTheatricalReleaseLocation(location) {
  const text = nonEmptyString(location);
  if (!text) {
    return false;
  }

  return !NON_THEATRICAL_RELEASE_MARKERS.test(text);
}

export function inferPrimaryCountry(movie) {
  const releaseDates = asArray(movie.releaseDate)
    .map((item) => ({
      date: nonEmptyString(item?.date),
      location: nonEmptyString(item?.location)
    }))
    .filter((item) => item.date || item.location)
    .sort((left, right) => String(left.date ?? '').localeCompare(String(right.date ?? '')));

  const theatricalReleaseDates = releaseDates.filter((item) => isTheatricalReleaseLocation(item.location));

  for (const item of theatricalReleaseDates) {
    const inferred = inferCountryFromLocation(item.location);
    if (inferred) {
      return inferred;
    }
  }

  for (const item of releaseDates) {
    const inferred = inferCountryFromLocation(item.location);
    if (inferred) {
      return inferred;
    }
  }

  const country = nonEmptyString(movie.country);
  if (!country) {
    return null;
  }

  return country.split('/').map((part) => part.trim()).filter(Boolean)[0] ?? country;
}

export function computeAggregateRating(movie) {
  const values = [movie.doubanRating, movie.imdbRating, movie.tmdbRating];
  if (typeof movie.rottenTomatoes === 'number') {
    values.push(movie.rottenTomatoes / 10);
  }

  if (typeof movie.metascore === 'number') {
    values.push(movie.metascore / 10);
  }

  const valid = values.filter((value) => typeof value === 'number' && Number.isFinite(value));
  if (!valid.length) {
    return null;
  }

  return Math.round((valid.reduce((sum, value) => sum + value, 0) / valid.length) * 10) / 10;
}

export function buildImagesJson(movie) {
  const images = movie.images ?? {};
  return {
    poster: nonEmptyString(images.poster),
    posters: asArray(images.posters),
    stills: asArray(images.stills),
    wallpapers: asArray(images.wallpapers),
    postersTotal: images.postersTotal ?? null,
    stillsTotal: images.stillsTotal ?? null,
    assetDir: `video/movie/${movie.id}`
  };
}

export function buildIdentifiersJson(movie) {
  return {
    douban: nonEmptyString(movie.doubanId),
    imdb: nonEmptyString(movie.imdbId),
    tmdb: nonEmptyString(movie.tmdbId)
  };
}

export function buildRatingsJson(movie) {
  const rottenValue = typeof movie.rottenTomatoes === 'number' ? Math.round(movie.rottenTomatoes) / 10 : null;
  const metascoreValue = typeof movie.metascore === 'number' ? Math.round(movie.metascore) / 10 : null;

  return {
    aggregate: { value: computeAggregateRating(movie), scale: 10 },
    douban: { value: movie.doubanRating ?? null, scale: 10 },
    imdb: { value: movie.imdbRating ?? null, scale: 10 },
    tmdb: { value: movie.tmdbRating ?? null, scale: 10 },
    rottenTomatoes: { value: rottenValue, scale: rottenValue === null ? null : 10 },
    metascore: { value: metascoreValue, scale: metascoreValue === null ? null : 10 },
    certification: { value: nonEmptyString(movie.rated) },
    awards: { value: nonEmptyString(movie.awards) }
  };
}

export function buildLinksJson(movie) {
  const links = movie.links ?? {};
  return {
    douban: nonEmptyString(links.douban),
    imdb: nonEmptyString(links.imdb),
    tmdb: nonEmptyString(links.tmdb)
  };
}

export function buildRelationsJson(movie) {
  return {
    series: asArray(movie.series),
    similar: asArray(movie.similar)
  };
}

export function buildSoundtrackJson(movie) {
  const soundtrack = movie.soundtrack;
  if (!soundtrack) {
    return null;
  }

  if (Array.isArray(soundtrack.albums)) {
    return {
      albums: soundtrack.albums.map((album) => ({
        name: nonEmptyString(album.name),
        note: nonEmptyString(album.note),
        coverImage: nonEmptyString(album.coverImage),
        releaseDate: nonEmptyString(album.releaseDate),
        type: nonEmptyString(album.type),
        tracks: asArray(album.tracks).map((track) => ({
          name: track.name,
          artist: nonEmptyString(track.artist),
          duration: nonEmptyString(track.duration)
        }))
      }))
    };
  }

  return {
    albums: [
      {
        name: nonEmptyString(soundtrack.name),
        note: [nonEmptyString(soundtrack.note), nonEmptyString(soundtrack.composer) ? `${soundtrack.composer}${nonEmptyString(soundtrack.composerEn) ? ` / ${soundtrack.composerEn}` : ''}` : null].filter(Boolean).join(' | ') || null,
        coverImage: nonEmptyString(soundtrack.coverImage),
        releaseDate: nonEmptyString(soundtrack.releaseDate) || (soundtrack.year ? String(soundtrack.year) : null),
        type: nonEmptyString(soundtrack.type) || 'soundtrack',
        tracks: asArray(soundtrack.tracks).map((track) => ({
          name: track.name,
          artist: nonEmptyString(track.artist),
          duration: nonEmptyString(track.duration)
        }))
      }
    ]
  };
}

export function buildReviewsJson(movie) {
  return asArray(movie.reviews).map((review) => ({
    author: nonEmptyString(review.author),
    source: nonEmptyString(review.source),
    date: nonEmptyString(review.date),
    content: nonEmptyString(review.content),
    url: nonEmptyString(review.url),
    title: nonEmptyString(review.title)
  }));
}

export function buildWorksProjection(movie) {
  const publishCompany = nonEmptyString(movie.publishCompany) || nonEmptyString(movie.publish_company) || nonEmptyString(movie.productionCompany);

  return {
    id: movie.id,
    module: 'video',
    submodule: 'movie',
    schema_type: movie.schemaType ?? 'live_action_movie',
    title: movie.title,
    original_title: movie.originalTitle ?? null,
    year: movie.year ?? null,
    country: inferPrimaryCountry(movie),
    language: movie.language ?? null,
    publish_company: publishCompany,
    runtime_minutes: movie.runtime ?? null,
    episode_count: null,
    episode_runtime_minutes: null,
    synopsis_text: movie.synopsis?.text ?? null,
    synopsis_note: movie.synopsis?.note ?? null,
    story_text: movie.story?.text ?? null,
    aliases_json: uniqueStrings(movie.aka ?? []),
    release_dates_json: asArray(movie.releaseDate),
    identifiers_json: buildIdentifiersJson(movie),
    ratings_json: buildRatingsJson(movie),
    links_json: buildLinksJson(movie),
    images_json: buildImagesJson(movie),
    videos_json: asArray(movie.videos),
    reviews_json: buildReviewsJson(movie),
    soundtrack_json: buildSoundtrackJson(movie),
    relations_json: buildRelationsJson(movie),
    quotes_json: asArray(movie.quotes),
    episode_stories_json: null,
    characters_json: null,
    status: movie.status ?? 'published',
    created_at: movie.createdAt ?? null,
    updated_at: movie.updatedAt ?? null
  };
}

export function buildDbProjection(movie) {
  return {
    works: buildWorksProjection(movie),
    credits: {
      director: asArray(movie.director),
      writer: asArray(movie.writer),
      cast: asArray(movie.cast),
      otherCast: asArray(movie.otherCast),
      producer: asArray(movie.producer)
    },
    terms: {
      genre: asArray(movie.genre),
      tags: asArray(movie.tags)
    }
  };
}

export function parseTmdbIdFromUrl(url) {
  const text = nonEmptyString(url);
  if (!text) {
    return null;
  }

  const match = text.match(/\/movie\/(\d+)/);
  return match ? match[1] : null;
}

export function normalizeForDoc(value) {
  if (value === undefined) {
    return null;
  }
  return value;
}

export function extFromAvatar(fileName) {
  return path.extname(fileName || '') || '.jpg';
}
