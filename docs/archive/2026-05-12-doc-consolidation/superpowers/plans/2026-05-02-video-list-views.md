# Video List Views Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/video` default to the card view, expose a real `卡片 / 列表` toggle, and align both render modes with the `movie-list-card.html` reference.

**Architecture:** Keep the existing `/video` route and `view=grid|list` query shape to minimize scope. Implement the behavior in the page layer, keep card/list presentation inside `MovieGridCard.astro` and `MovieListCard.astro`, and verify behavior with a focused page-model helper test in `site/tests/archive.test.ts`.

**Tech Stack:** Astro, TypeScript, Vitest, global CSS

---

### Task 1: Add page-model helpers for `/video` view switching

**Files:**
- Modify: `site/src/lib/site.ts`
- Test: `site/tests/archive.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --runInBand`
Expected: FAIL with `buildVideoViewModel is not defined` or import error from `site.ts`

- [ ] **Step 3: Write minimal implementation**

```ts
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

export function buildVideoViewModel(filters: VideoViewFilters) {
  const view: VideoView = filters.view === 'list' ? 'list' : 'grid';

  return {
    view,
    viewLabel: view === 'grid' ? '卡片' : '列表',
    viewLinks: {
      card: createVideoViewHref(filters, 'grid'),
      list: createVideoViewHref(filters, 'list')
    }
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --runInBand`
Expected: PASS for the new `buildVideoViewModel` tests

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/site.ts site/tests/archive.test.ts
git commit -m "test: add video view model coverage"
```

### Task 2: Switch `/video` to card-first behavior and card/list labels

**Files:**
- Modify: `site/src/pages/video/index.astro`
- Modify: `site/src/lib/site.ts`
- Test: `site/tests/archive.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
describe('buildVideoViewModel', () => {
  it('treats missing or unsupported view values as card view', () => {
    expect(buildVideoViewModel({}).view).toBe('grid');
    expect(buildVideoViewModel({ view: 'card' }).view).toBe('grid');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --runInBand`
Expected: FAIL until the helper logic and page usage match the new default behavior

- [ ] **Step 3: Write minimal implementation**

```astro
---
const viewModel = buildVideoViewModel({
  query,
  submodule,
  genre,
  country,
  year,
  tag,
  view: Astro.url.searchParams.get('view') ?? ''
});
const view = viewModel.view;
---

<div class="listing-toolbar__views">
  <a class:list={[view === 'grid' && 'is-active']} href={viewModel.viewLinks.card}>卡片</a>
  <a class:list={[view === 'list' && 'is-active']} href={viewModel.viewLinks.list}>列表</a>
</div>

<section class:list={["shell", view === 'grid' ? 'grid-cards' : 'list-cards']}>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --runInBand`
Expected: PASS with the helper defaulting to `grid`

- [ ] **Step 5: Commit**

```bash
git add site/src/pages/video/index.astro site/src/lib/site.ts site/tests/archive.test.ts
git commit -m "feat: make video archive default to card view"
```

### Task 3: Rebuild the card view component to match the reference interaction

**Files:**
- Modify: `site/src/components/MovieGridCard.astro`
- Modify: `site/src/styles/global.css`
- Test: `site/tests/archive.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
describe('formatArchiveCardMeta', () => {
  it('formats compact metadata for card overlays', () => {
    expect(formatArchiveCardMeta({ year: 1994, country: '美国', runtime: 142 })).toBe('1994 / 美国 / 142 分钟');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --runInBand`
Expected: FAIL with `formatArchiveCardMeta is not defined`

- [ ] **Step 3: Write minimal implementation**

```ts
export function formatArchiveCardMeta(movie: Pick<ArchiveMovie, 'year' | 'country' | 'runtime'>) {
  return `${movie.year} / ${movie.country} / ${movie.runtime} 分钟`;
}
```

```astro
---
import { formatArchiveCardMeta } from '../lib/site';

const hoverMeta = formatArchiveCardMeta(movie);
const castLine = movie.castPreview.join(' / ');
---

<article class="movie-grid-card">
  <a class="movie-grid-card__frame" href={movie.path}>
    <img class="movie-grid-card__poster-bg" src={movie.posterUrl} alt="" aria-hidden="true" loading="lazy" />
    <div class="movie-grid-card__poster-shell">
      <img class="movie-grid-card__poster" src={movie.posterUrl} alt={`${movie.title} 海报`} loading="lazy" />
      <span class="movie-grid-card__rating">{movie.aggregateRating ? movie.aggregateRating.toFixed(1) : '--'}</span>
      <span class="movie-grid-card__runtime">{movie.runtime} 分钟</span>
    </div>

    <div class="movie-grid-card__body">
      <strong class="movie-grid-card__title">{movie.title}</strong>
      <span class="movie-grid-card__meta">{movie.year} · {movie.country}</span>
    </div>

    <div class="movie-grid-card__hover">
      <strong class="movie-grid-card__hover-title">{movie.title}</strong>
      <p class="movie-grid-card__hover-meta">{hoverMeta}</p>
      <p class="movie-grid-card__hover-cast">主演：{castLine}</p>
      <p class="movie-grid-card__hover-summary">{movie.synopsis?.text}</p>
    </div>
  </a>
</article>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --runInBand`
Expected: PASS for the new compact metadata formatter test

- [ ] **Step 5: Commit**

```bash
git add site/src/components/MovieGridCard.astro site/src/styles/global.css site/src/lib/site.ts site/tests/archive.test.ts
git commit -m "feat: restyle video archive card view"
```

### Task 4: Rebuild the list view component to match the reference row layout

**Files:**
- Modify: `site/src/components/MovieListCard.astro`
- Modify: `site/src/styles/global.css`

- [ ] **Step 1: Write the failing test**

```ts
describe('formatArchiveListFacts', () => {
  it('formats the facts row for list cards', () => {
    expect(
      formatArchiveListFacts({
        year: 1994,
        country: '美国',
        genre: ['剧情', '犯罪'],
        directorNames: '弗兰克·德拉邦特'
      })
    ).toEqual(['1994', '美国', '剧情 / 犯罪', '导演：弗兰克·德拉邦特']);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --runInBand`
Expected: FAIL with `formatArchiveListFacts is not defined`

- [ ] **Step 3: Write minimal implementation**

```ts
export function formatArchiveListFacts(
  movie: Pick<ArchiveMovie, 'year' | 'country' | 'genre' | 'directorNames'>
) {
  return [String(movie.year), movie.country, (movie.genre ?? []).join(' / '), `导演：${movie.directorNames}`];
}
```

```astro
---
import { formatArchiveListFacts } from '../lib/site';

const facts = formatArchiveListFacts(movie);
---

<article class="movie-list-card">
  <a class="movie-list-card__poster" href={movie.path}>
    <img src={movie.posterUrl} alt={`${movie.title} 海报`} loading="lazy" />
  </a>

  <div class="movie-list-card__body">
    <div class="movie-list-card__topline">
      <div class="movie-list-card__titles">
        <a class="movie-list-card__title" href={movie.path}>{movie.title}</a>
        <p class="movie-list-card__subtitle">{movie.originalTitle}</p>
      </div>
      <div class="movie-list-card__score">
        <span>综合</span>
        <strong>{movie.aggregateRating ? movie.aggregateRating.toFixed(1) : '--'}</strong>
      </div>
    </div>

    <div class="movie-list-card__facts">
      {facts.map((fact) => <span>{fact}</span>)}
    </div>

    <p class="movie-list-card__summary">{movie.synopsis?.text}</p>

    <div class="movie-list-card__credits">
      <span>主演：{movie.castPreview.join(' / ')}</span>
      <span>{movie.runtime} 分钟</span>
    </div>

    <div class="movie-list-card__platforms">
      {ratingPairs.map(([label, value]) => (
        <span class="movie-list-card__badge">{label} {Number(value).toFixed(1)}</span>
      ))}
    </div>
  </div>
</article>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --runInBand`
Expected: PASS for the facts-row formatter test

- [ ] **Step 5: Commit**

```bash
git add site/src/components/MovieListCard.astro site/src/styles/global.css site/src/lib/site.ts site/tests/archive.test.ts
git commit -m "feat: restyle video archive list rows"
```

### Task 5: Final verification and cleanup

**Files:**
- Verify: `site/src/pages/video/index.astro`
- Verify: `site/src/components/MovieGridCard.astro`
- Verify: `site/src/components/MovieListCard.astro`
- Verify: `site/src/styles/global.css`
- Verify: `site/tests/archive.test.ts`

- [ ] **Step 1: Run the full test suite**

Run: `npm test`
Expected: PASS with all archive and view-model tests green

- [ ] **Step 2: Run the production build**

Run: `npm run build`
Expected: PASS with `/video` and movie detail routes generated successfully

- [ ] **Step 3: Inspect the resulting behaviors manually**

Check:

```text
1. /video without query params opens in card view
2. toolbar labels read "卡片" and "列表"
3. switching views preserves q/submodule/genre/country/year/tag params
4. card view has poster-first hover reveal
5. list view has left-poster right-info row layout
```

- [ ] **Step 4: Commit**

```bash
git add site/src/pages/video/index.astro site/src/components/MovieGridCard.astro site/src/components/MovieListCard.astro site/src/styles/global.css site/src/lib/site.ts site/tests/archive.test.ts
git commit -m "feat: implement video archive card and list views"
```
