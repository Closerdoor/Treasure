import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { computeAggregateRating, loadArchiveMovies, syncArchiveAssets } from '../src/lib/archive';
import {
  buildHomePageModel,
  buildVideoViewModel,
  formatArchiveRuntimeLabel,
  formatArchiveCardMeta,
  formatArchiveCardMetaLeft,
  formatArchiveCardMetaRight,
  formatArchiveCardRuntime,
  formatArchiveLabel,
  formatExternalSourceLabel,
  formatArchiveListPlatformRatings,
  formatArchiveListFacts,
  resolveVideoView
} from '../src/lib/site';

const tempDirs: string[] = [];
const videoIndexPath = path.join(process.cwd(), 'src', 'pages', 'video', 'index.astro');
const movieDetailPath = path.join(process.cwd(), 'src', 'pages', 'video', 'movie', '[id].astro');

afterEach(async () => {
  await Promise.all(
    tempDirs.splice(0).map(async (dir) => {
      await fs.rm(dir, { recursive: true, force: true });
    })
  );
});

describe('computeAggregateRating', () => {
  it('averages available platform scores on a 10-point scale', () => {
    expect(
      computeAggregateRating({
        doubanRating: 9.7,
        imdbRating: 9.3,
        tmdbRating: 8.9,
        rottenTomatoes: 91
      })
    ).toBe(9.3);
  });

  it('ignores missing platforms', () => {
    expect(
      computeAggregateRating({
        doubanRating: 9.7,
        imdbRating: undefined,
        tmdbRating: undefined,
        rottenTomatoes: undefined
      })
    ).toBe(9.7);
  });
});

describe('loadArchiveMovies', () => {
  it('loads the current movie sample from repo content', async () => {
    const movies = await loadArchiveMovies();

    expect(movies.length).toBeGreaterThanOrEqual(4);
    expect(movies[0]).toMatchObject({
      module: 'video',
      submodule: 'movie'
    });
    expect(movies.some((movie) => movie.id === '0101000001')).toBe(true);
  });

  it('creates stable site paths and local poster paths', async () => {
    const movies = await loadArchiveMovies();
    const shawshank = movies.find((movie) => movie.id === '0101000001');

    expect(shawshank).toBeDefined();
    expect(shawshank?.path).toBe('/video/movie/0101000001');
    expect(shawshank?.posterUrl).toBe('/assets/video/movie/0101000001/poster-main.jpg');
  });

  it('maps wallpaper assets for the secondary image rail', async () => {
    const movies = await loadArchiveMovies();
    const shawshank = movies.find((movie) => movie.id === '0101000001');

    expect(shawshank?.wallpaperGallery).toEqual([
      '/assets/video/movie/0101000001/wallpaper-01.png',
      '/assets/video/movie/0101000001/wallpaper-02.png',
      '/assets/video/movie/0101000001/wallpaper-03.png',
      '/assets/video/movie/0101000001/wallpaper-04.png'
    ]);
  });
});

describe('buildHomePageModel', () => {
  it('creates a home hero model from the current movie archive', async () => {
    const movies = await loadArchiveMovies();
    const model = buildHomePageModel(movies);

    expect(model.heroMovie?.id).toBe('0101000001');
    expect(model.featuredMovies).toHaveLength(3);
    expect(model.recentMovies).toHaveLength(4);
    expect(model.featuredMovies.map((movie) => movie.id)).toEqual(['0101000001', '0101000004', '0101000003']);
    expect(model.recentMovies.map((movie) => movie.title)).toEqual(['肖申克的救赎', '霸王别姬', '阿甘正传', '迈克尔·杰克逊：巨星之路']);
  });
});

describe('formatArchiveLabel', () => {
  it('formats module and submodule labels for display', () => {
    expect(formatArchiveLabel('video', 'movie')).toBe('影视 / 电影');
  });

  it('falls back to raw values when a label is unknown', () => {
    expect(formatArchiveLabel('video', 'short')).toBe('影视 / short');
  });
});

describe('buildVideoViewModel', () => {
  it('defaults to card view and preserves filters in view links', () => {
    const model = buildVideoViewModel({
      query: '阿甘',
      submodule: 'movie',
      genre: '剧情',
      country: '美国',
      year: '1994',
      tag: '经典'
    });

    expect(model.view).toBe('grid');
    expect(model.viewLabel).toBe('卡片');
    expect(model.viewLinks.card).toContain('view=grid');
    expect(model.viewLinks.card).toContain('q=%E9%98%BF%E7%94%98');
    expect(model.viewLinks.list).toContain('view=list');
    expect(model.viewLinks.list).toContain('genre=%E5%89%A7%E6%83%85');
  });

  it('accepts explicit list view', () => {
    const model = buildVideoViewModel({ view: 'list' });

    expect(model.view).toBe('list');
    expect(model.viewLabel).toBe('列表');
  });
});

describe('resolveVideoView', () => {
  it('normalizes unsupported values to card view', () => {
    expect(resolveVideoView()).toBe('grid');
    expect(resolveVideoView('card')).toBe('grid');
    expect(resolveVideoView('grid')).toBe('grid');
    expect(resolveVideoView('list')).toBe('list');
  });
});

describe('formatArchiveCardMeta', () => {
  it('formats compact metadata for card overlays', () => {
    expect(formatArchiveCardMeta({ year: 1994, country: '美国', genre: ['剧情', '犯罪'] })).toBe('剧情 · 1994 · 美国');
  });
});

describe('formatArchiveCardMetaLeft', () => {
  it('formats year and genre for the card footer left side', () => {
    expect(formatArchiveCardMetaLeft({ year: 1994, genre: ['剧情', '犯罪'] })).toBe('1994 · 剧情');
  });
});

describe('formatArchiveCardMetaRight', () => {
  it('returns the country for the card footer right side', () => {
    expect(formatArchiveCardMetaRight({ country: '美国' })).toBe('美国');
  });
});

describe('formatArchiveCardRuntime', () => {
  it('formats runtime as reference-style timecode for the card corner', () => {
    expect(formatArchiveCardRuntime(142)).toBe('2:22:00');
  });
});

describe('formatArchiveRuntimeLabel', () => {
  it('formats runtime for detail-page archive labels', () => {
    expect(formatArchiveRuntimeLabel(142)).toBe('142 分钟');
    expect(formatArchiveRuntimeLabel()).toBe('时长待补充');
  });
});

describe('formatExternalSourceLabel', () => {
  it('maps known source keys to reader-facing labels', () => {
    expect(formatExternalSourceLabel('douban')).toBe('豆瓣条目');
    expect(formatExternalSourceLabel('imdb')).toBe('IMDb');
    expect(formatExternalSourceLabel('tmdb')).toBe('TMDB');
    expect(formatExternalSourceLabel('wikipedia')).toBe('wikipedia');
  });
});

describe('formatArchiveListFacts', () => {
  it('formats the list meta row as year country and genre only', () => {
    expect(
      formatArchiveListFacts({
        year: 1994,
        country: '美国',
        genre: ['剧情', '犯罪'],
        directorNames: '弗兰克·德拉邦特'
      })
    ).toEqual(['1994', '美国', '剧情/犯罪']);
  });
});

describe('formatArchiveListPlatformRatings', () => {
  it('formats right-column platform scores for list view', () => {
    expect(
      formatArchiveListPlatformRatings({
        doubanRating: 9.7,
        imdbRating: 9.3,
        tmdbRating: 8.5,
        rottenTomatoes: 91
      })
    ).toEqual([
      { label: '豆瓣', value: '9.7' },
      { label: 'IMDb', value: '9.3' },
      { label: 'TMDB', value: '8.5' },
      { label: '烂番茄', value: '91%' }
    ]);
  });
});

describe('list view structure', () => {
  it('renders icon-style fact tags and reference-like rating fields', async () => {
    const source = await fs.readFile(path.join(process.cwd(), 'src', 'components', 'MovieListCard.astro'), 'utf8');

    expect(source).toContain('movie-list-card__fact-chip');
    expect(source).toContain('<svg viewBox="0 0 24 24" aria-hidden="true"><path d={factIcons[index] ?? factIcons[0]}></path></svg>');
    expect(source).toContain('movie-list-card__rating-source');
    expect(source).toContain('movie-list-card__rating-value');
  });
});

describe('syncArchiveAssets', () => {
  it('copies movie image assets into the site public directory', async () => {
    const root = await fs.mkdtemp(path.join(os.tmpdir(), 'treasure-site-'));
    tempDirs.push(root);

    const sourceImagesDir = path.join(root, 'content', 'video', 'movie', '0101000001', 'images');
    const targetAssetsDir = path.join(root, 'site', 'public', 'assets', 'video', 'movie');

    await fs.mkdir(sourceImagesDir, { recursive: true });
    await fs.mkdir(targetAssetsDir, { recursive: true });
    await fs.writeFile(path.join(sourceImagesDir, 'poster-main.jpg'), 'poster');
    await fs.writeFile(path.join(sourceImagesDir, 'still-01.jpg'), 'still');

    await syncArchiveAssets({
      sourceRoot: path.join(root, 'content', 'video', 'movie'),
      targetRoot: targetAssetsDir
    });

    expect(await fs.readFile(path.join(targetAssetsDir, '0101000001', 'poster-main.jpg'), 'utf8')).toBe('poster');
    expect(await fs.readFile(path.join(targetAssetsDir, '0101000001', 'still-01.jpg'), 'utf8')).toBe('still');
  });
});

describe('video index page', () => {
  it('renders card and list containers side by side for client-only view switching', async () => {
    const source = await fs.readFile(videoIndexPath, 'utf8');

    expect(source).toContain('data-view-panel="grid"');
    expect(source).toContain('data-view-panel="list"');
    expect(source).toContain('<MovieGridCard movie={movie} />');
    expect(source).toContain('<MovieListCard movie={movie} />');
  });

  it('renders compact filter rows and pagination UI', async () => {
    const source = await fs.readFile(videoIndexPath, 'utf8');

    expect(source).toContain('archive-search-bar');
    expect(source).toContain('submodule-filter-panel');
    expect(source).toContain('filter-link-rows');
    expect(source).toContain('pagination-bar');
    expect(source).toContain('当前第 {currentPage} / {totalPages} 页');
    expect(source).not.toContain("{ label: '热度'");
    expect(source).not.toContain("{ label: '标签'");
  });
});

describe('movie detail page', () => {
  it('renders a simplified hero with ordered archive facts inside the main information board', async () => {
    const source = await fs.readFile(movieDetailPath, 'utf8');

    expect(source).toContain('class="detail-breadcrumb"');
    expect(source).toContain('href="/video"');
    expect(source).toContain('detail-hero__poster-column');
    expect(source).toContain('detail-hero__info-board');
    expect(source).toContain('detail-hero__masthead');
    expect(source).toContain('detail-hero__title-line');
    expect(source).toContain('detail-hero__score-line');
    expect(source).toContain('detail-hero__facts detail-hero__facts--credits');
    expect(source).toContain('detail-hero__facts detail-hero__facts--meta');
    expect(source).toContain('detail-hero__fact-row"><dt>{item.label}</dt><dd>{item.value}</dd></div>');
    expect(source).toContain('detail-hero__summary');
    expect(source).toContain('detail-hero__fact-row detail-hero__fact-row--summary');
    expect(source).toContain('<dt>简介</dt>');
    expect(source).toContain('const heroSynopsis = movie.synopsis?.text?.replace(/\\n\\s*\\n+/g, \'\\n\').trim();');
    expect(source).toContain('heroSynopsis');
    expect(source).toContain('aria-label="影片核心资料"');
    expect(source).toContain('aria-label="影片主创资料"');
    expect(source).toContain('const heroMetaRows = [');
    expect(source).toContain('const heroCreditRows = [');
    expect(source.indexOf("{ label: '导演'")).toBeLessThan(source.indexOf("{ label: '编剧'"));
    expect(source.indexOf("{ label: '编剧'")).toBeLessThan(source.indexOf("{ label: '主演'"));
    expect(source.indexOf("{ label: '主演'")).toBeLessThan(source.indexOf("{ label: '地区'"));
    expect(source.indexOf("{ label: '地区'")).toBeLessThan(source.indexOf("{ label: '语言'"));
    expect(source.indexOf("{ label: '语言'")).toBeLessThan(source.indexOf("{ label: '片长'"));
    expect(source.indexOf("{ label: '片长'")).toBeLessThan(source.indexOf("{ label: '上映日期'"));
    expect(source.indexOf("{ label: '上映日期'")).toBeLessThan(source.indexOf("{ label: '更多片名'"));
    expect(source).not.toContain('detail-scorecard');
    expect(source).not.toContain('platform-strip');
    expect(source).not.toContain('档案卡');
    expect(source).not.toContain('外部索引');
    expect(source).not.toContain('Poster File');
    expect(source).not.toContain('编号 {movie.id}');
  });

  it('keeps detail tabs in archive-first order', async () => {
    const source = await fs.readFile(path.join(process.cwd(), 'src', 'components', 'DetailTabs.astro'), 'utf8');

    expect(source.indexOf("{ id: 'images', label: '图片'")).toBeLessThan(source.indexOf("{ id: 'reviews', label: '精彩影评'"));
    expect(source).toContain('media-rail media-rail--credits');
    expect(source).toContain('data-rail-shell');
    expect(source).toContain('data-rail-track');
    expect(source).toContain('video-rail-card');
    expect(source).toContain('image-rail-stack');
    expect(source).toContain('image-rail image-rail--primary');
    expect(source).toContain('image-rail image-rail--secondary');
    expect(source).toContain('data-rail-sync');
    expect(source).toContain('formatExternalSourceLabel');
  });
  it('uses hover-revealed advance buttons for image rails instead of visible scrollbars', async () => {
    const source = await fs.readFile(path.join(process.cwd(), 'src', 'components', 'DetailTabs.astro'), 'utf8');
    const styles = await fs.readFile(path.join(process.cwd(), 'src', 'styles', 'global.css'), 'utf8');

    expect(source).toContain('data-rail-prev');
    expect(source).toContain('data-rail-next');
    expect(source).toContain("prevButton.hidden = isAtStart;");
    expect(source).toContain("nextButton.hidden = maxScroll <= 8 || isAtEnd;");
    expect(source).toContain("rail.scrollBy({ left: step, behavior: 'smooth' });");
    expect(source).toContain("rail.scrollBy({ left: -step, behavior: 'smooth' });");
    expect(source).toContain("if (syncing || !shell.hasAttribute('data-rail-sync')) {");
    expect(source).toContain('new ResizeObserver(queueSync)');
    expect(source).toContain("image.addEventListener('load', queueSync, { once: true });");
    expect(source).toContain('window.setTimeout(queueSync, 120);');
    expect(styles).toContain('.media-rail::-webkit-scrollbar,');
    expect(styles).toContain('scrollbar-width: none;');
    expect(styles).toContain('.image-rail::-webkit-scrollbar {');
    expect(styles).toContain('.rail-advance {');
    expect(styles).toContain('.rail-advance--prev {');
    expect(styles).toContain('.rail-advance--next {');
    expect(styles).toContain('.rail-fade {');
    expect(styles).toContain('.media-rail-shell,');
    expect(styles).toContain('max-width: 100%;');
    expect(styles).toContain('overflow: hidden;');
    expect(styles).toContain('[data-can-scroll-left]:hover .rail-fade--left');
    expect(styles).toContain('.media-rail-shell:hover .rail-advance');
    expect(styles).toContain('.rail-advance--stacked');
  });
  it('adds a sticky archive index with scroll-aware tab state hooks', async () => {
    const source = await fs.readFile(path.join(process.cwd(), 'src', 'components', 'DetailTabs.astro'), 'utf8');
    const styles = await fs.readFile(path.join(process.cwd(), 'src', 'styles', 'global.css'), 'utf8');

    expect(source).toContain('aria-label="标题索引导航栏"');
    expect(source).toContain('data-detail-index');
    expect(source).toContain('data-detail-tab={item.id}');
    expect(source).toContain('data-detail-top');
    expect(source).toContain('window.scrollTo({ top: 0, behavior: \'smooth\' });');
    expect(source).toContain('IntersectionObserver');
    expect(styles).toContain('top: var(--sticky-offset);');
    expect(styles).toContain('--header-height: 76px;');
    expect(styles).toContain('--detail-index-height: 68px;');
    expect(styles).toContain('.detail-panel[id] {');
    expect(styles).toContain('scroll-margin-top: calc(var(--header-height) + var(--detail-index-height) + 18px);');
    expect(styles).toContain('.detail-tabs__top-button {');
  });
});

describe('list view styles', () => {
  it('uses a wider mainstream-style poster column in list view', async () => {
    const source = await fs.readFile(path.join(process.cwd(), 'src', 'styles', 'global.css'), 'utf8');

    expect(source).toContain('display: flex;');
    expect(source).toContain('width: 142px;');
    expect(source).toContain('min-height: 200px;');
    expect(source).toContain('width: 100px;');
  });
});

describe('grid view styles', () => {
  it('keeps card height fixed while widening the poster viewport', async () => {
    const source = await fs.readFile(path.join(process.cwd(), 'src', 'styles', 'global.css'), 'utf8');

    expect(source).toContain('grid-template-columns: repeat(auto-fit, minmax(214px, 214px));');
    expect(source).toContain('width: 214px;');
    expect(source).toContain('height: 302px;');
    expect(source).toContain('transform: scale(1.18);');
    expect(source).toContain('object-fit: cover;');
    expect(source).toContain('padding: 14px;');
  });
});
