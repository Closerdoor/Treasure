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
| `.local` 职责说明 | `.local/README.md` |
| Prisma schema | `prisma/schema.prisma` |
| Prisma 迁移基线 | `prisma/migrations/` |
| 数据库统计脚本 | `tools/db/check-counts.mjs` |
| 数据库表结构查看 | `tools/db/view-schema.mjs` |
| generated 与资源导出入口 | `tools/db/export-generated.mjs` |
| DB 工具说明 | `tools/db/README.md` |
| 历史工具归档 | `tools/archive/README.md` |
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
prisma/migrations/
```

职责：

- `.local/treasure.db` 是本地结构化主数据源。
- `prisma/schema.prisma` 定义表结构和字段关系。
- `prisma/migrations/` 记录可从空库复现当前结构的 SQLite 迁移基线。
- `prisma.config.ts` 指向当前 schema、migrations 和 `.local/treasure.db`。
- 数据库只服务本地内容工坊，不会部署到 GitHub Pages。

文件分工：

```text
.local/treasure.db                  本地真实数据，不提交 Git
.local/assets/                      本地资源主源，不提交 Git
.local/backup/                      本地备份，不参与构建
prisma/schema.prisma                数据库结构契约，提交 Git
prisma/migrations/                  当前结构迁移基线，提交 Git
tools/db/                           当前 DB 主链路工具
tools/archive/db-legacy-migrations/ 历史修库/迁移脚本
tools/archive/movie-ingest-workflow/旧电影采集过程/样板脚本
```

`tools/db/` 不再承载采集过程工具、旧修库脚本或一次性实验脚本。当前只保留数据库统计、表结构查看、generated 导出、资源引用检查和本地备份等主链路能力；其余历史脚本放入 `tools/archive/`，后续完整跑工作流时再确认是否恢复或删除。

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

当前数据库采用“关系型拆表 + 展示型复合信息 JSON 化”的策略。

关系型拆表：

- `person`
- `category`
- `work_person`
- `work_category`
- `book_person`
- `book_category`

JSON 化字段主要承载：

- 多平台评分
- 外部来源
- 图片集合
- 视频集合
- 评论
- 关联作品
- 名言 / 摘录
- 原声带

补充说明：

- `person` 是跨模块复用的公共人物表。
- `category` 是公共分类 / 标签表，可带模块和子模块作用域。
- `books`、`book_person`、`book_category` 已用于书籍草稿阶段的数据组织。

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

- `tools/db/export-generated.mjs` 从 SQLite 导出 Astro 可读取的静态 JSON，并导出当前记录引用到的静态资源。
- `generated/` 是前台站点的数据中转层。
- `.local/assets/` 是本地私有资源源目录。
- `site/public/assets/` 是 Astro 构建和 GitHub Pages 可发布的资源目录，由导出脚本按当前 generated 记录重建。

`.local/` 的目标职责应保持克制：保存已经进入主链路的本地主数据库、主资源和备份。采集过程中的 raw、staging、字段来源、冲突记录、批次摘要和临时下载缓存，应优先放在对应的 `temp-script/*-ingest/` 目录中。

```text
.local/treasure.db
.local/assets/
.local/backup/
```

当前 `.local/` 中若仍存在 `batches`、`field-sources`、`source-snapshots`、`new-flow` 等目录，应视为历史采集过程产物或迁移阶段产物，后续逐批审视后再决定迁移、归档或删除。

### 采集工坊职责契约

`temp-script/movie-ingest` 与 `temp-script/book-ingest` 的职责边界是“爬取作品信息 -> 下载到本地 -> 录入 `.local/treasure.db`”。它们不负责 generated 导出、Astro 页面、站点构建或发布校验；这些后续流程由 `tools/`、`generated/` 与 `site/` 承担。

采集工坊内部的标准层次：

```text
source task / curated input
  -> raw source snapshots
  -> normalized staging record
  -> field source / conflict notes
  -> SQLite import
```

各层职责：

- `source task / curated input`：记录馆长想录入什么，以及必要的外部 ID 或人工选择结果。
- `raw source snapshots`：保存原始抓取结果，便于回溯，不直接作为站点数据。
- `normalized staging record`：保存准备入库的结构化对象；原则上保持对象 / 数组结构，不要在 staging 阶段提前把复杂字段序列化成 JSON 字符串。
- `field source / conflict notes`：记录字段来源、自动推断依据、多源冲突和人工确认结果。
- `SQLite import`：把 staging 数据投影到 Prisma / SQLite 表结构，包括主表、人物关系、分类关系和展示型 JSON 字段。
- SQLite 入库完成后，采集工坊职责结束；从 SQLite 到 generated / site 的流程属于下一层系统。

过程约束：

- 正式进入导入流程前，至少应同时保留“候选作品数据”与“字段来源记录”，便于后续复核。
- 若同一字段存在多源冲突，不应静默覆盖；应保留足够的来源或冲突信息，供人工判断。
- 每次批量导入都应形成摘要性记录，至少能回看本批处理对象、导入数量、关键缺口、资源覆盖与后续回补提示。
- 如果脚本存在数量限制、数据源跳过、降级策略或只取前 N 条，必须在代码注释、运行前说明和批次摘要中同时可见。
- 模块局部 README 可以记录实验细节，但不得覆盖本文件中的主线契约。

主链路：

```text
.local/treasure.db
  -> tools/db/export-generated.mjs
  -> generated/
  -> site/src/lib/archive.ts
  -> Astro pages
```

DB 到 Astro 的当前真实链路：

1. `.local/treasure.db` 是本地结构化事实源。
2. `tools/db/export-generated.mjs` 使用本机 SQLite CLI 读取 `.local/treasure.db`。
3. 当前导出范围是 `works` 中的 `video/movie`，并联表读取 `work_person`、`person`、`work_category`、`category`。
4. 导出脚本生成：

```text
generated/entries/video/movie/{id}.json
generated/indexes/video-movie.json
generated/indexes/video.json
generated/indexes/all.json
generated/persons.json
generated/recent.json
generated/tags.json
```

5. `tools/db/export-generated.mjs` 同时导出当前记录引用的静态资源：作品图片复制到 `site/public/assets/video/movie/{id}/`，人物头像复制到对应作品自己的 `people/` 子目录。
6. `site/src/lib/archive.ts` 读取 `generated/indexes/video-movie.json` 与 `generated/entries/video/movie/{id}.json`，并补齐前台需要的路径、评分、海报 URL、演员预览等派生字段。
7. 当前 Astro 页面消费路径：

```text
site/src/pages/index.astro
site/src/pages/video/index.astro
site/src/pages/video/movie/[id].astro
```

8. `site/src/pages/video/movie/[id].astro` 通过 `loadAllMovieIds()` 生成静态详情页路径。

因此，当前站点构建不读取 SQLite、不读取 `temp-script/`，只读取 `generated/` 与 `site/public/assets/`。

资源链路：

```text
.local/assets/
  -> tools/db/export-generated.mjs
  -> site/public/assets/video/movie/{id}/
  -> /assets/*
```

发布侧不再导出共享 `site/public/assets/people/`。人物头像会复制到每个作品自己的资源目录，例如：

```text
site/public/assets/video/movie/0101000001/people/tmdb-504-avatar.jpg
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
npm.cmd run build
```

日常维护必须在仓库根目录直接运行 `node tools/db/export-generated.mjs`。旧的 `site/scripts/sync-assets.mjs` 与 `npm.cmd run sync` 兼容入口已删除，避免 DB 到 Astro 链路存在两个入口。

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

人物头像资源约定：

- 数据库中的 `person.avatar_path` 当前形如 `people/tmdb-{id}-avatar.jpg`。
- 导出到作品详情 JSON 时，`avatarPath` 会改写为作品私有资源路径，例如 `video/movie/0101000001/people/tmdb-504-avatar.jpg`。
- 前台 URL 拼接仍为 `/assets/${avatarPath}`。
- 实体文件最终必须位于对应作品目录的 `site/public/assets/video/movie/{id}/people/` 下，否则前台需要显式回退策略。
- `generated/persons.json` 不导出共享 `avatarPath`，避免前台误依赖共享人物资源池。
- 若头像缺失，前台应能回退到 `/assets/avatar-placeholder.svg`。

## 电影字段映射

当前电影导出逻辑位于 `tools/db/export-generated.mjs`。它不是旧 `content/.../data.json` 链路，而是直接从 SQLite 表组装 generated JSON。

主要映射关系：

| SQLite 来源 | generated 字段 |
|---|---|
| `works.id` | `id` |
| `works.module` / `works.submodule` | `module` / `submodule` |
| `works.schema_type` | `schemaType` |
| `works.title` / `works.title_original` | `title` / `originalTitle` |
| `works.year` / `works.country` / `works.language` | `year` / `country` / `language` |
| `works.studio` / `works.total_time` | `publishCompany` / `runtime` |
| `works.introduction` | `synopsis.text` |
| `works.story` | `story.text` |
| `works.other_titles` | `aka` |
| `works.release_dates` | `releaseDate` |
| `works.external_source` | `links`、`doubanId`、`imdbId`、`tmdbId` |
| `works.scores` | `doubanRating`、`imdbRating`、`tmdbRating`、`rottenTomatoes`、`metascore` |
| `works.images` / `works.videos` | `images` / `videos` |
| `works.comments` | `reviews` |
| `works.soundtrack` | `soundtrack` |
| `works.related` | `series` / `similar` |
| `works.quotes` | `quotes` |
| `works.created_at` / `works.updated_at` / `works.status` | `createdAt` / `updatedAt` / `status` |

关系表映射：

- `work_person + person` 生成 `director`、`writer`、`cast`、`otherCast`、`producer`。
- `department = direction` 进入 `director`。
- `department = writing` 或 `original_work` 进入 `writer`。
- `department = cast` 且 `is_primary = true` 进入 `cast`，否则进入 `otherCast`。
- `department = production` 进入 `producer`。
- `work_category + category` 中 `group = type` 进入 `genre`。
- `work_category + category` 中 `group = tag` 进入 `tags`。

前台派生字段：

- `path` 由 `module/submodule/id` 生成。
- `posterUrl` 由 `images.poster` 生成；缺失时回退到 `/assets/poster-placeholder.svg`。
- `aggregateRating` 由豆瓣、IMDb、TMDB、烂番茄计算。
- `directorNames`、`writerNames`、`castPreview` 等由人员数组派生。
- 列表页和首页应消费轻量索引字段，不直接读取全量详情 JSON。

类型与标签分工：

- `genre` / 类型来自相对标准化的分类，例如剧情、动作、科幻。
- `tags` / 标签可以包含外部平台标签，也可以包含站内手动维护标签。
- 前台筛选 UI 可以混合展示标签，不必向访问者暴露标签来源。

数据分层原则：

- 作品级数据只描述单个作品自身的结构化资料。
- 页面聚合数据服务首页、列表页、搜索页，通常是轻量索引或摘要。
- 站点级数据包括导航、模块顺序、主题、搜索规则等，不应塞进单个作品记录。

页面与数据源关系：

| 页面 | 当前数据源 |
|---|---|
| `/` | 聚合后的列表数据 / 模块入口 |
| `/video` | 电影列表索引与聚合读取 |
| `/video/movie/{id}` | 单条电影详情读取 |
| `/about` | 静态 Astro 页面 |
| `/search` | 预留入口，当前不代表完整搜索已完成 |

关键字段语义：

- `title` 是中文展示标题。
- `originalTitle` 是原名或源语言标题。
- `synopsis` 用于首页、列表和详情顶部的短简介。
- `story` 用于详情页的长内容介绍。
- `genre` 是相对标准化类型。
- `tags` 是标签集合，可承载外部标签和站内维护标签。
- `scores` 在数据库中保存多平台评分，导出后转为前台常用评分字段。
- `director`、`writer`、`cast`、`otherCast` 来源于人物关系导出。

关联作品规则：

- `series` / `similar` 若匹配到站内作品 ID，则可生成可跳转项。
- 未匹配到站内 ID 的关联项，可以保留为不可点击占位或摘要信息。
- `series` / `similar` 的原始关联数据，优先保留 `source` 与 `sourceId`，例如 `douban + subjectId`。
- 导出层应优先基于外部来源 ID 匹配站内作品，而不是依赖标题文本匹配。
- 若外部 ID 尚未匹配到站内作品，则保持摘要态，不伪造跳转。

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

页面层级原则：

```text
首页 -> 模块列表页 -> 详情页
```

- 首页是全站入口，负责呈现收藏馆气质、模块入口和适度内容预览。
- 模块列表页负责浏览、搜索、筛选、分页和进入详情页。
- 详情页负责展示单条作品的完整结构化资料。

计划但尚未正式落地：

```text
/book
/book/{id}
/music
/game
```

`content/` 当前仍存在，但应视为历史内容目录、人工审阅材料或迁移残留，不是正式前台数据源。

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

构建产物：

```text
site/dist/
```

线上不应依赖：

- SQLite 数据库。
- `.local/`。
- `temp-script/`。
- Playwright 或爬虫运行时。

## 前台 UI 方向

当前前台不是传统资源站，也不是博客，而是“资料馆气质 + 现代浏览体验”的静态收藏站。

原则：

- 深色 / 浅色主题都应作为完整体验成立，而不是简单反色。
- 海报、封面、剧照是关键视觉资产，但不能牺牲资料可读性。
- 全站统一导航、主题、基础交互和视觉气质。
- 各模块可以根据内容特征独立设计列表字段、详情结构、筛选项和页面节奏。
- 首页负责说明收藏馆气质和模块入口，不做长篇博客式叙述。
- 首页可采用“首屏 + 模块预览区”的结构，模块预览区使用作品卡片进入列表页或详情页。
- 列表页优先支持浏览、筛选、分页和卡片 / 列表视图切换。
- 影视列表页当前结构是搜索筛选区、内容区和分页区。
- 详情页偏资料型，不是文章页；优先展示基础信息、分区内容和关联内容。
- 搜索页当前主要是入口和后续扩展位置，不代表完整搜索功能已经完成。
- 避免把页面做成全量资源站、营销落地页或纯文章站。
- 避免夸张圆角、厚重阴影和通用后台组件感。

电影详情页分区可参考：

```text
基础信息
详情介绍
演职员
精选影评
视频
图片
音乐
外部来源
关联作品
评论区
```

Giscus 评论区保留在详情页，不出现在首页和列表页。

列表卡片原则：

- 网格模式适合快速扫视和封面浏览。
- 列表模式适合更高信息密度。
- 必要字段：海报、标题、年份、类型、综合评分。
- 高优先级字段：原名、地区、导演、摘要。
- 点击卡片进入详情页，悬停态不应造成布局不稳定。
- 影视列表页当前正式支持“卡片 / 列表”双视图切换。
- 默认优先进入卡片视图；列表视图承担更高信息密度浏览。
- 视图切换只改变呈现方式，不改变当前筛选结果与浏览上下文。

评分展示规则：

- 前台主评分使用多平台评分聚合后的综合评分。
- 当前聚合来源以豆瓣、IMDb、TMDB、烂番茄为主。
- 缺失的平台评分直接跳过，不为缺失来源制造占位值。
- 烂番茄在参与综合评分时，需要先从百分制换算到 10 分制。
- 综合评分最终以 1 位小数展示。
- 馆长主观评分不作为当前主评分体系的一部分。

## 标准工作流

新增或更新作品数据时：

采集工坊阶段：

1. 准备 source task 或馆长确认过的输入清单。
2. 抓取或整理 raw source snapshots，保留原始来源。
3. 下载作品图片、人物头像等本地资源。
4. 生成 normalized staging record，并同步生成字段来源 / 冲突记录。
5. 检查 staging 是否符合当前模块契约；发现字段冲突或脚本限制时先确认再继续。
6. 确认数据后写入 `.local/treasure.db`。
7. 如涉及结构变化，更新 `prisma/schema.prisma`。

站点中转阶段：

1. 运行 `node tools/db/export-generated.mjs` 导出静态 JSON 和当前记录引用的静态资源。
2. 运行 `cd site && npm.cmd run build` 验证 Astro 静态构建。
3. 更新 `docs/STATUS.md` 中的数据量、校验结果和已知风险。

书籍模块接入建议顺序：

1. 先让 `book-ingest` 的 staging 契约对齐采集工坊标准，尤其是字段来源、冲突记录和复杂字段 JSON 化时机。
2. 确认 `books`、`book_person`、`book_category` 的结构与导出需求。
3. 扩展导出脚本，生成：

```text
generated/entries/book/{id}.json
generated/indexes/book.json
```

4. 将书籍条目接入 `generated/indexes/all.json`。
5. 增加 `site/src/lib/book.ts`。
6. 增加 `/book` 与 `/book/{id}` 页面。

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

未来的完整性校验脚本应尽量输出：

- 数据记录总量。
- generated 完成量。
- 资源引用总量。
- 资源存在量。
- 覆盖率。
- 缺失样本。
- 是否阻断发布。

契约变更联动检查：

- 如果修改 generated 结构或字段语义，至少同步检查：
  - `tools/db/export-generated.mjs`
  - `site/src/lib/archive.ts`
  - `site/src/lib/site.ts`
  - `site/src/pages/video/index.astro`
  - `site/src/pages/video/movie/[id].astro`
  - `docs/STATUS.md`
- 如果修改资源路径策略，至少同步检查：
  - `.local/assets/`
  - `site/public/assets/`
  - 前台图片 URL 拼接逻辑

## 主链路文件分级

完成一次 DB -> generated -> Astro 闭环后，当前文件可以按职责分为四类。后续清理时优先按这个分级判断，不要只看文件是否还存在。

### A. 当前主链路文件

这些文件或目录属于当前规范，应该保留并保持文档同步：

```text
.local/README.md
.local/treasure.db
.local/assets/
.local/backup/
prisma/schema.prisma
prisma/migrations/
prisma.config.ts
tools/db/export-generated.mjs
tools/db/check-counts.mjs
tools/db/check-assets.mjs
tools/db/view-schema.mjs
tools/db/list-tables.mjs
tools/db/update-backup.mjs
generated/
site/src/
site/public/assets/avatar-placeholder.svg
site/public/assets/poster-placeholder.svg
```

说明：

- `.local/treasure.db` 与 `.local/assets/` 是本地主源，不提交 Git。
- `generated/` 是导出产物，前台依赖它，但不应人工编辑。
- `site/public/assets/video/` 等作品资源目录由导出脚本重建，不应手工维护。
- `site/public/assets/avatar-placeholder.svg` 与 `poster-placeholder.svg` 是前台回退资源，应提交 Git。

### B. 历史兼容或参考文件

这些内容可能仍有参考价值，但不属于当前运行链路：

```text
tools/archive/
docs/archive/
design-archive/
```

处理原则：

- `tools/archive/` 与 `docs/archive/` 只在追溯历史决策时读取。
- `design-archive/` 作为 UI 参考材料保留，不参与构建。

### C. 清理候选

这些内容已经不在当前主链路上，清理前需要用户确认：

| 路径 / 文件 | 当前判断 |
|---|---|
| `content/` | 旧 Markdown / 内容文件链路，当前 Astro 不读取；已跟踪约 195 个文件 |
| `.opencode/` | 本地 AI 技能和缓存文件，已跟踪约 46 个文件；需确认是否仍作为项目资产 |
| `data/.book_counter` | 书籍采集脚本仍在引用的计数状态文件，不属于 DB -> Astro 主链路；后续应随 `book-ingest` 一起整理 |
| `IMAGE-DESIGN-PROMPTS.md` | 设计提示词草稿，若仍有价值应进入 `design-archive/` 或 `docs/archive/` |

清理规则：

- 删除或取消跟踪前必须逐项确认，尤其是 `content/`、`.opencode/` 和顶层调试数据。
- 若某个候选文件仍被脚本引用，应先判断它属于采集工坊、DB 工具、站点构建还是历史归档，再移动到正确位置。
- 清理 generated 产物时，只能删除可由 `tools/db/export-generated.mjs` 稳定再生成的文件。

### D. 暂不处理范围

```text
temp-script/
.local/treasure.db
.local/assets/
```

`temp-script/` 的具体整理由用户处理；除非用户明确要求，否则只记录职责边界和问题，不主动移动或删除。`.local/` 中的数据库和资产是本地主源，清理时必须比普通生成物更谨慎。

## 架构原则

- SQLite 是本地事实源，generated 是前台事实源。
- Astro 不直接读取数据库。
- `temp-script/` 不能成为发布链路的隐式依赖。
- 新模块先稳定数据库和 generated 契约，再接入页面。
- 可重复的校验应脚本化，避免靠人工记忆判断是否可发布。
