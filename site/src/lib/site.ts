import type { ArchiveMovie } from './archive';

type VideoView = 'grid' | 'list';

type VideoViewFilters = {
  query?: string;
  submodule?: string;
  genre?: string;
  country?: string;
  year?: string;
  tag?: string;
  view?: string;
};

export const siteMeta = {
  title: 'Treasure 资料馆',
  description: '馆长筛选的结构化收藏站，优先以影视样板验证资料馆式浏览体验。'
};

export const moduleCards = [
  {
    slug: 'video',
    title: '影视',
    description: '当前唯一落地真实内容链路的分馆。',
    href: '/video',
    state: 'active' as const
  },
  {
    slug: 'book',
    title: '书',
    description: '已接入本地数据库，采用更接近阅读产品的纯白列表与详情页。',
    href: '/book',
    state: 'active' as const
  },
  {
    slug: 'music',
    title: '音乐',
    description: '保留入口与视觉占位，暂不开放完整页面链路。',
    href: '',
    state: 'placeholder' as const
  },
  {
    slug: 'game',
    title: '游戏',
    description: '保留入口与视觉占位，延后进入 V1 之外阶段。',
    href: '',
    state: 'placeholder' as const
  }
];

const moduleLabels: Record<string, string> = {
  video: '影视',
  book: '书',
  music: '音乐',
  game: '游戏'
};

const submoduleLabels: Record<string, string> = {
  movie: '电影',
  book: '书籍'
};

const homeMovieIds = ['0101000001', '0101000004', '0101000003', '0101000002'];

function sortMoviesForHome(movies: ArchiveMovie[]) {
  const curated = homeMovieIds
    .map((id) => movies.find((movie) => movie.id === id))
    .filter((movie): movie is ArchiveMovie => Boolean(movie));
  const remaining = movies
    .filter((movie) => !homeMovieIds.includes(movie.id))
    .sort((left, right) => left.id.localeCompare(right.id));

  return [...curated, ...remaining];
}

export function pickHeroMovie(movies: ArchiveMovie[]) {
  return sortMoviesForHome(movies)[0] ?? null;
}

export function pickFeaturedMovies(movies: ArchiveMovie[], count = 3) {
  return sortMoviesForHome(movies).slice(0, count);
}

export function buildHomePageModel(movies: ArchiveMovie[]) {
  return {
    heroMovie: pickHeroMovie(movies),
    featuredMovies: pickFeaturedMovies(movies, 3),
    recentMovies: pickFeaturedMovies(movies, 4)
  };
}

export function formatArchiveLabel(module: string, submodule?: string) {
  const moduleLabel = moduleLabels[module] ?? module;

  if (!submodule) {
    return moduleLabel;
  }

  return `${moduleLabel} / ${submoduleLabels[submodule] ?? submodule}`;
}

function createVideoViewHref(filters: VideoViewFilters, view: VideoView) {
  const params = new URLSearchParams({
    q: filters.query ?? '',
    submodule: filters.submodule ?? '',
    genre: filters.genre ?? '',
    country: filters.country ?? '',
    year: filters.year ?? '',
    tag: filters.tag ?? '',
    view
  });

  return `/video?${params.toString()}`;
}

export function resolveVideoView(view?: string): VideoView {
  return view === 'list' ? 'list' : 'grid';
}

export function buildVideoViewModel(filters: VideoViewFilters) {
  const view = resolveVideoView(filters.view);

  return {
    view,
    viewLabel: view === 'grid' ? '卡片' : '列表',
    viewLinks: {
      card: createVideoViewHref(filters, 'grid'),
      list: createVideoViewHref(filters, 'list')
    }
  };
}

export function formatArchiveCardMeta(movie: Pick<ArchiveMovie, 'year' | 'country' | 'genre'>) {
  return [movie.genre?.[0], String(movie.year), movie.country].filter(Boolean).join(' · ');
}

export function formatArchiveCardRuntime(runtime?: number) {
  if (!runtime || runtime <= 0) {
    return '--:--:--';
  }

  const hours = Math.floor(runtime / 60);
  const minutes = runtime % 60;

  return `${hours}:${String(minutes).padStart(2, '0')}:00`;
}

export function formatArchiveCardMetaLeft(movie: Pick<ArchiveMovie, 'year' | 'genre'>) {
  return [String(movie.year), movie.genre?.[0]].filter(Boolean).join(' · ');
}

export function formatArchiveCardMetaRight(movie: Pick<ArchiveMovie, 'country'>) {
  return movie.country;
}

export function formatArchiveListFacts(
  movie: Pick<ArchiveMovie, 'year' | 'country' | 'genre'>
) {
  return [String(movie.year), movie.country, (movie.genre ?? []).join('/')];
}

export function formatArchiveListPlatformRatings(
  movie: Pick<ArchiveMovie, 'doubanRating' | 'imdbRating' | 'tmdbRating' | 'rottenTomatoes'>
) {
  return [
    ['豆瓣', movie.doubanRating],
    ['IMDb', movie.imdbRating],
    ['TMDB', movie.tmdbRating],
    ['烂番茄', typeof movie.rottenTomatoes === 'number' ? `${movie.rottenTomatoes}%` : undefined]
  ]
    .filter((entry): entry is [string, number | string] => typeof entry[1] === 'number' || typeof entry[1] === 'string')
    .map(([label, value]) => ({ label, value: typeof value === 'number' ? Number(value).toFixed(1) : value }));
}

export function formatArchiveRuntimeLabel(runtime?: number) {
  if (!runtime || runtime <= 0) {
    return '时长待补充';
  }

  return `${runtime} 分钟`;
}

export function formatExternalSourceLabel(name: string) {
  const labels: Record<string, string> = {
    douban: '豆瓣条目',
    imdb: 'IMDb',
    tmdb: 'TMDB',
    baike: '百度百科',
    wikipedia: 'Wikipedia',
    openlibrary: 'OpenLibrary',
    goodreads: 'Goodreads',
    dangdang: '当当'
  };

  return labels[name] ?? name;
}

export function collectMovieTags(movies: ArchiveMovie[]) {
  return [...new Set(movies.flatMap((movie) => movie.tags))].slice(0, 12);
}

export function collectYears(movies: ArchiveMovie[]) {
  return [...new Set(movies.map((movie) => movie.year))].sort((left, right) => right - left);
}

export function collectCountries(movies: ArchiveMovie[]) {
  return [...new Set(movies.map((movie) => movie.country).filter(Boolean) as string[])].sort();
}

export function filterMovies(
  movies: ArchiveMovie[],
  filters: {
    query?: string;
    submodule?: string;
    genre?: string;
    country?: string;
    year?: string;
    tag?: string;
  }
) {
  const query = filters.query?.trim().toLowerCase();

  return movies.filter((movie) => {
    if (filters.submodule && movie.submodule !== filters.submodule) {
      return false;
    }

    if (filters.genre && !(movie.genre ?? []).includes(filters.genre)) {
      return false;
    }

    if (filters.country && movie.country !== filters.country) {
      return false;
    }

    if (filters.year && String(movie.year) !== filters.year) {
      return false;
    }

    if (filters.tag && !movie.tags.includes(filters.tag)) {
      return false;
    }

    if (!query) {
      return true;
    }

    const haystack = [
      movie.title,
      movie.originalTitle,
      movie.synopsis?.text,
      movie.country,
      ...(movie.genre ?? []),
      ...(movie.cast ?? []).map((person) => person.name)
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();

    return haystack.includes(query);
  });
}
