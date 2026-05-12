# Generated Data

> Purpose: 记录 `generated/` 目录的当前结构、前台消费契约和资源引用规则。
> Status: active
> Scope: generated 目录、索引文件、详情文件、资源路径、发布前校验项
> Out of scope: 数据库 schema 全量字段、爬虫原始数据格式、UI 视觉实现
> Update triggers: 导出脚本变化、前台读取字段变化、资源路径策略变化
> Priority: 2

## 定位

`generated/` 是 SQLite 数据库面向 Astro 前台的静态数据投影。

前台不直接读取 `.local/treasure.db`，也不直接读取 `temp-script/` 或旧 `content/` 目录作为正式数据源。

## 当前目录结构

```text
generated/
  entries/
    video/
      movie/
        0101000001.json
        ...
        0101000250.json
  indexes/
    video-movie.json
    video.json
    all.json
  recent.json
  tags.json
```

当前状态：

- `generated/entries/video/movie/*.json`：250 个电影详情文件
- `generated/indexes/video-movie.json`：250 条电影列表记录
- `generated/indexes/video.json`：250 条影视模块记录
- `generated/indexes/all.json`：当前搜索/全站索引候选

## 详情 JSON 与索引 JSON

### 详情 JSON

详情 JSON 承载单个作品详情页需要的完整结构化数据。

当前电影详情页读取路径：

```text
generated/entries/video/movie/{id}.json
```

前台读取逻辑位于：

```text
site/src/lib/archive.ts
```

### 索引 JSON

索引 JSON 承载列表页、首页预览、搜索入口等轻量字段。

当前电影列表索引：

```text
generated/indexes/video-movie.json
```

索引字段应保持轻量，不应把完整评论、完整剧照列表等详情页专用数据塞入列表索引。

## 资源路径契约

### 作品资源

作品私有资源源目录：

```text
.local/assets/{module}/{submodule}/{id}/
```

前台发布目录：

```text
site/public/assets/{module}/{submodule}/{id}/
```

前台 URL：

```text
/assets/{module}/{submodule}/{id}/{filename}
```

### 人物头像

人物头像源目录：

```text
.local/assets/people/
```

前台发布目录：

```text
site/public/assets/people/
```

前台 URL：

```text
/assets/people/{filename}
```

数据库中的 `person.avatar_path` 当前可能使用：

```text
people/tmdb-{tmdbId}-avatar.jpg
```

因此前台拼接时使用：

```text
/assets/${avatarPath}
```

## 图片字段约定

当前前台代码默认 `images.poster`、`images.posters`、`images.stills`、`images.wallpapers` 中的本地资源项是文件名字符串。

例如：

```json
{
  "poster": "poster-main.webp",
  "posters": ["poster-01.webp"],
  "stills": ["still-01.webp"],
  "wallpapers": []
}
```

如果导出结果中出现外链对象，例如：

```json
{ "url": "https://image.tmdb.org/...", "width": 2000, "height": 3000 }
```

则必须明确处理策略：

- 要么导出阶段过滤掉，不进入前台正式 generated。
- 要么前台读取层显式支持外链对象。

当前推荐方向：正式前台 generated 只引用本地已同步资源；外链对象保留在 raw/source/staging 数据中。

## 当前校验快照

最近一次校验时间：2026-05-12

```text
数据库电影数：250
generated 电影详情 JSON：250
video-movie 索引记录：250
关键字段不一致：0
索引缺详情：0
详情缺索引：0
人物引用总数：12999
人物编号找不到数据库记录：0
主海报引用：250
主海报缺失：1
人物头像引用：12999
人物头像缺失：3927
Astro 构建页面：254
Astro 构建状态：成功
```

已知资源/契约问题只记录在文档中，未在本次整理中修复：

- `0101000178`《绿里奇迹》缺少 `poster-main.webp`。
- `0101000001`《肖申克的救赎》的部分 `images.posters/stills` 项为 TMDB 外链对象，不是本地文件名字符串。
- 人物头像引用覆盖率约 69.8%，缺失项主要来自 `.local/assets/people/` 中不存在的 TMDB 头像文件。

## 后续建议

建议新增稳定校验脚本：

```text
tools/db/check-generated-integrity.mjs
```

该脚本应输出量化报告：

- 数据记录总量
- generated 完成量
- 资源引用总量
- 资源存在量
- 覆盖率
- 缺失样本
- 是否阻断发布
