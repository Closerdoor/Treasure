# Contracts

> Purpose: 记录当前前台消费数据、资源路径和字段语义契约。
> Status: active
> Scope: generated 契约、资源路径、关键字段语义、页面消费边界
> Out of scope: 数据库 schema 全量字段、视觉样式、爬虫解析细节
> Update triggers: generated 结构变化、前台读取字段变化、资源路径变化、关键字段语义变化
> Priority: 2

## 契约总览

当前正式前台数据契约是：

```text
SQLite
  -> generated JSON
  -> site/src/lib/*
  -> Astro pages
```

前台不直接读取：

- `.local/treasure.db`
- `.local/staging/`
- `temp-script/`
- 旧 `content/video/movie/*/data.json`

## 页面与数据源

| 页面 | 当前数据源 | 说明 |
|---|---|---|
| `/` | `loadArchiveMovies()` | 首页精选与模块入口 |
| `/video` | `loadArchiveMovies()` | 电影列表、筛选、分页 |
| `/video/movie/{id}` | `loadArchiveMovieById(id)` | 电影详情 |
| `/about` | 静态 Astro 页面 | 关于页 |
| `/search` | 静态 Astro 页面 / 预留入口 | 当前不是完整搜索实现 |

当前读取层：

```text
site/src/lib/archive.ts
site/src/lib/site.ts
```

## generated 文件契约

### 电影详情

```text
generated/entries/video/movie/{id}.json
```

详情 JSON 用于详情页，允许包含较完整的演职员、评论、图片、外部来源、关联作品等数据。

### 电影列表索引

```text
generated/indexes/video-movie.json
```

列表索引用于列表页和首页预览，应保持轻量。

当前列表索引字段包括：

- `id`
- `path`
- `title`
- `originalTitle`
- `year`
- `posterUrl`
- `aggregateRating`
- `directorNames`
- `castPreview`
- `genre`
- `tags`
- `country`
- `synopsis`

### 全站索引

```text
generated/indexes/all.json
```

当前作为未来搜索页的数据基础，完整搜索功能尚未落地。

## 资源路径契约

### 作品图片

数据库/generated 中的本地作品图片应以文件名保存，例如：

```json
{
  "poster": "poster-main.webp",
  "posters": ["poster-01.webp"],
  "stills": ["still-01.webp"]
}
```

前台 URL 由读取层拼接：

```text
/assets/{module}/{submodule}/{id}/{filename}
```

实体文件必须存在于：

```text
site/public/assets/{module}/{submodule}/{id}/{filename}
```

### 人物头像

人物头像路径使用相对 `site/public/assets/` 的路径：

```text
people/tmdb-4027-avatar.jpg
```

前台 URL：

```text
/assets/people/tmdb-4027-avatar.jpg
```

如果头像文件缺失，前台应能回退到：

```text
/assets/avatar-placeholder.svg
```

## 关键字段语义

### `id`

作品稳定主标识。标题变化不应影响 ID 和详情页路由。

### `module` / `submodule`

用于生成路径和资源目录。

当前电影：

```json
{
  "module": "video",
  "submodule": "movie"
}
```

### `path`

前台详情页路径。

电影示例：

```text
/video/movie/0101000001
```

### `title` / `originalTitle`

`title` 是中文展示标题。  
`originalTitle` 是原名或源语言标题。

### `synopsis`

短简介，用于：

- 首页
- 列表卡片
- 详情页顶部摘要

不应直接用 `story` 替代。

### `story`

详情页剧情/内容介绍，属于长文本。

### `genre`

类型分类，来自相对标准化的外部类型或人工整理。

### `tags`

标签集合，可用于搜索、聚合或馆长维护。不等同于 `genre`。

### `scores`

数据库中的多平台评分对象。

导出后前台常用字段：

- `doubanRating`
- `imdbRating`
- `tmdbRating`
- `rottenTomatoes`
- `metascore`
- `aggregateRating`

当前综合评分规则：

- 豆瓣 / IMDb / TMDB 使用 10 分制原值。
- 烂番茄百分制除以 10 后参与平均。
- 缺失平台跳过。
- 最终保留 1 位小数。

### `director` / `writer` / `cast` / `otherCast`

从 `work_person` 和 `person` 导出。

人物对象核心字段：

- `personCode`
- `name`
- `nameEn`
- `role`
- `avatarPath`
- `profileLink`

### `images.poster`

主海报。列表页、首页和详情页顶部优先依赖它。

### `images.posters` / `images.stills` / `images.wallpapers`

补充图片集合。

当前推荐契约：正式 generated 中只放本地文件名字符串。外链对象应留在 raw/source/staging 层，除非前台读取层明确支持外链对象。

### `reviews`

评论集合。当前用于详情页评论区域。

### `related` / `series` / `similar`

关联作品。导出时可根据外部 ID 尝试匹配站内作品 ID。

未匹配站内 ID 的条目允许展示为不可点击占位。

## 当前已知契约问题

最近核验时间：2026-05-12

- `0101000001`《肖申克的救赎》部分 `images.posters/stills` 项为 TMDB 外链对象，不符合“本地文件名字符串”契约。
- `0101000178`《绿里奇迹》主海报引用存在，但实体文件缺失。
- 人物头像缺失 3927/12999，前台必须依赖占位图回退或后续补齐。

## 契约变更规则

如果修改 generated 结构或字段语义，必须同步检查：

- `tools/db/export-generated.mjs`
- `site/src/lib/archive.ts`
- `site/src/lib/site.ts`
- `site/src/pages/video/index.astro`
- `site/src/pages/video/movie/[id].astro`
- `docs/GENERATED-DATA.md`
- `docs/STATUS.md`

如果修改资源路径策略，必须同步检查：

- `.local/assets/`
- `site/public/assets/`
- `site/scripts/sync-assets.mjs`
- 前台图片 URL 拼接逻辑
