# Treasure 项目结构与工作流

Treasure 是一个个人收藏馆项目，用来收录影视、书籍、音乐、游戏等作品。它的核心定位是“精选型收藏站”，不是全量资料库。

当前工程采用 DB-first 的静态站流程：

```text
数据获取与整理
  -> SQLite 主数据
  -> generated 静态 JSON
  -> Astro 静态站
  -> GitHub Pages
```

## 快速定位

| 你要找什么 | 位置 |
|---|---|
| 本地 SQLite 数据库 | `.local/treasure.db` |
| Prisma schema | `prisma/schema.prisma` |
| 数据库统计脚本 | `tools/db/check-counts.mjs` |
| 数据库表结构查看 | `tools/db/view-schema.mjs` |
| generated 导出入口 | `tools/db/export-generated.mjs` |
| 资源同步入口 | `site/scripts/sync-assets.mjs` |
| 前台数据读取层 | `site/src/lib/archive.ts` |
| Astro 首页 | `site/src/pages/index.astro` |
| 影视列表页 | `site/src/pages/video/index.astro` |
| 电影详情页 | `site/src/pages/video/movie/[id].astro` |
| 全局样式 | `site/src/styles/global.css` |
| Astro 配置 | `site/astro.config.mjs` |
| 当前状态快照 | `docs/STATUS.md` |

## 1. temp-script：数据获取与实验区

目录：

```text
temp-script/
```

职责：

- 放置爬虫、解析、批处理和实验脚本。
- 从公开数据源、网页、Markdown、JSON 等来源获取作品数据。
- 最终目标是把确认后的结构化数据写入 `.local/treasure.db`。

约定：

- `temp-script/` 是实验区，不是稳定构建链路。
- 这里的中间文件、日志、网页样本、调试产物不能被 Astro 站点直接依赖。
- 成熟、可重复执行、会长期使用的脚本，应逐步沉淀到 `tools/`。
- `temp-script/` 的具体清理和分类由用户处理；未被要求时不要主动改动。
- 涉及数据完整性的限制必须显式说明，例如只抓取前 N 条、跳过某数据源、降级使用低质量候选等。

## 2. 数据库与 Prisma：结构化主数据

核心文件：

```text
.local/treasure.db
prisma/schema.prisma
prisma.config.ts
```

职责：

- `.local/treasure.db` 是本地结构化主数据源。
- `prisma/schema.prisma` 定义表结构和字段关系。
- 数据库只服务本地内容工坊，不会部署到 GitHub Pages。

当前核心表：

```text
works
person
category
work_person
work_category
books
book_series
book_person
book_category
```

当前模块状态：

| 模块 | 状态 | 说明 |
|---|---|---|
| 影视 / 电影 | active | 已跑通数据库、导出和 Astro 构建链路 |
| 书籍 | draft | 已有少量数据库草稿，尚未接入 generated 和站点 |
| 音乐 | planned | 尚未正式建模 |
| 游戏 | planned | 尚未正式建模 |

ID 规则：

```text
MMSSNNNNNN
```

- `MM`：一级模块编号。
- `SS`：子模块编号。
- `NNNNNN`：该子模块下递增序号。

示例：

```text
0101000001 = 影视 / 电影 / 第 1 条
0200000001 = 书籍 / 当前无子模块 / 第 1 条
```

常用命令：

```bash
node tools/db/check-counts.mjs
node tools/db/view-schema.mjs Work
node tools/db/view-schema.mjs Person
```

## 3. 中转站：导出 generated 与同步静态资源

核心目录：

```text
tools/db/
generated/
.local/assets/
site/public/assets/
```

职责：

- `tools/db/export-generated.mjs` 从 SQLite 导出 Astro 可读取的静态 JSON。
- `generated/` 是前台站点的数据中转层。
- `.local/assets/` 是本地私有资源源目录。
- `site/public/assets/` 是 Astro 构建和 GitHub Pages 可发布的资源目录。

主链路：

```text
.local/treasure.db
  -> tools/db/export-generated.mjs
  -> generated/
  -> site/src/lib/archive.ts
  -> Astro pages
```

资源链路：

```text
.local/assets/
  -> site/public/assets/
  -> /assets/*
```

当前 generated 结构：

```text
generated/
  entries/
    video/
      movie/
        0101000001.json
        ...
  indexes/
    video-movie.json
    video.json
    all.json
  persons.json
  recent.json
  tags.json
```

约定：

- 列表页读取轻量索引 JSON。
- 详情页读取单条详情 JSON。
- 前台只消费 `generated/` 和 `site/public/assets/`。
- 正式 generated 中的本地图片字段应能在 `site/public/assets/` 找到实体文件，或者前台必须有明确回退策略。

常用命令：

```bash
node tools/db/export-generated.mjs

cd site
npm.cmd run sync
```

## generated 最小契约

当前前台读取逻辑主要在 `site/src/lib/archive.ts`。

电影列表索引：

```text
generated/indexes/video-movie.json
```

列表项至少应包含：

```text
id
path
title
year
posterUrl
aggregateRating
directorNames
castPreview
genre
tags
country
synopsis
```

电影详情：

```text
generated/entries/video/movie/{id}.json
```

详情记录至少应包含：

```text
id
module
submodule
title
year
images.poster
director
writer
cast
genre
tags
country
runtime
synopsis
```

当前图片字段约定：

```text
images.poster      单个主海报文件名
images.posters     海报文件名数组
images.stills      剧照文件名数组
images.wallpapers  壁纸文件名数组
```

这些字段当前应优先使用本地文件名字符串，例如 `poster-main.webp`。如果出现 TMDB 外链对象，必须明确是导出阶段过滤、转换，还是前台读取层支持；不要让两种形态长期混用。

## 4. Astro 站点：公开静态站

目录：

```text
site/
```

关键子目录：

```text
site/src/pages/
site/src/components/
site/src/layouts/
site/src/lib/
site/src/styles/
site/public/assets/
```

职责：

- 使用 Astro 生成静态页面。
- 消费 `generated/` 中的 JSON 数据。
- 消费 `site/public/assets/` 中的静态资源。
- 构建产物部署到 GitHub Pages。

当前已落地路由：

```text
/
/about
/search
/video
/video/movie/{id}
```

计划但尚未正式落地：

```text
/book
/book/{id}
/music
/game
```

构建命令：

```bash
cd site
npm.cmd run build
```

Astro 配置：

```text
site/astro.config.mjs
site: https://closerdoor.github.io/Treasure
output: static
```

线上不应依赖：

- SQLite 数据库。
- `.local/`。
- `temp-script/`。
- Playwright 或爬虫运行时。

## 标准工作流

新增或更新作品数据时：

1. 在 `temp-script/` 中抓取、解析、清洗或人工整理数据。
2. 确认数据后写入 `.local/treasure.db`。
3. 如涉及结构变化，更新 `prisma/schema.prisma`。
4. 运行 `node tools/db/export-generated.mjs` 导出静态 JSON。
5. 运行 `cd site && npm.cmd run sync` 同步资源和数据。
6. 运行 `cd site && npm.cmd run build` 验证 Astro 静态构建。
7. 更新 `docs/STATUS.md` 中的数据量、校验结果和已知风险。

## 发布前校验

发布前至少确认：

- 数据库记录数与 generated 详情数量一致。
- generated 索引记录数与详情数量一致。
- 每个索引项都能找到详情 JSON。
- 每个详情 JSON 都能被对应索引覆盖。
- 关键字段如 `id`、`title`、`year`、`module`、`submodule` 与数据库一致。
- 主海报引用存在，或前台有明确占位图。
- 人物头像引用存在，或前台有明确占位图。
- `cd site && npm.cmd run build` 成功。

## 架构原则

- SQLite 是本地事实源，generated 是前台事实源。
- Astro 不直接读取数据库。
- `temp-script/` 不能成为发布链路的隐式依赖。
- 新模块先稳定数据库和 generated 契约，再接入页面。
- 可重复的校验应脚本化，避免靠人工记忆判断是否可发布。
