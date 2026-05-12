# Architecture

> Purpose: 记录当前项目系统边界、模块结构、数据层级和目录职责。
> Status: active
> Scope: 展示站点、本地内容工坊、数据库、导出产物、静态资源、路由
> Out of scope: 字段级 schema 全量说明、具体爬虫实现、视觉样式细节
> Update triggers: 数据主源变化、模块结构变化、路由变化、目录职责变化、前台读取方式变化
> Priority: 1

## 系统分层

Treasure 当前分为两层：

1. 公开展示站点
   - 面向访问者。
   - 使用 Astro 静态生成。
   - 部署目标是 GitHub Pages。
   - 消费 `generated/` 和 `site/public/assets/`。
   - 不直接读取 SQLite。
   - 不直接依赖 `temp-script/` 或旧 `content/` 目录。

2. 本地内容工坊
   - 面向馆长。
   - 负责抓取、清洗、补全、人工确认、导入、导出。
   - 使用 SQLite 保存结构化主数据。
   - 使用 `.local/assets/` 保存私有资源源文件。
   - 使用 `tools/` 和 `temp-script/` 承载脚本。

## 当前主链路

```text
外部数据源 / 手动录入
  -> 抓取与清洗脚本
  -> .local/treasure.db
  -> tools/db/export-generated.mjs
  -> generated/
  -> site/src/lib/*
  -> Astro pages
  -> site/dist/
```

静态资源链路：

```text
.local/assets/
  -> site/public/assets/
  -> /assets/*
```

## 目录职责

### `.local/`

私有本地工作区，不进入 Git。

当前承载：

- `treasure.db`：本地 SQLite 主数据库。
- `assets/`：本地私有图片资源。
- `backup/`：备份文件。
- `staging/`、`batches/`、`source-snapshots/` 等：导入/实验过程产物。

### `prisma/`

数据库 schema 和迁移目录。

当前主 schema：

```text
prisma/schema.prisma
```

### `tools/`

长期可复用脚本目录。

当前重点：

```text
tools/db/export-generated.mjs
tools/db/check-counts.mjs
tools/db/view-schema.mjs
```

后续稳定的导入、校验、备份脚本应优先沉淀到这里。

### `temp-script/`

实验脚本和临时产物目录。

当前包括：

- `movie-ingest/`
- `book-ingest/`
- `reference-archive/`

约定：

- 这里的脚本可以作为实验参考。
- 不作为前台正式构建依赖。
- 成熟流程应迁入 `tools/`。

### `generated/`

数据库导出的前台数据投影。

当前由 `tools/db/export-generated.mjs` 生成。

前台 Astro 读取 generated，而不是读取 SQLite。

### `site/`

Astro 前台站点。

关键目录：

```text
site/src/pages/
site/src/components/
site/src/layouts/
site/src/lib/
site/src/styles/
site/public/assets/
```

构建产物：

```text
site/dist/
```

### `content/`

历史内容目录，目前不作为前台正式数据源。

当前应视为历史样本、人工审阅材料或迁移残留。后续是否清理需要单独确认。

## 模块结构

当前产品规划模块：

| 模块 | 状态 | 说明 |
|---|---|---|
| 影视 | active | 当前电影模块已跑通主链路 |
| 书籍 | draft | 数据库已有 3 条草稿，尚未接入 generated 和页面 |
| 音乐 | planned | 仅保留方向 |
| 游戏 | planned | 仅保留方向 |

当前真实前台页面只落地了影视/电影主线。

## 当前数据库边界

SQLite 是本地结构化主源。当前核心表包括：

- `works`
- `person`
- `category`
- `work_person`
- `work_category`
- `books`
- `book_series`
- `book_person`
- `book_category`

电影仍使用 `works` 主表。书籍当前使用独立 `books` 表及书籍关联表。

## 当前前台路由

已落地：

```text
/
/about
/search
/video
/video/movie/{id}
```

当前 `/search` 仍主要是入口和占位，不代表完整搜索功能已经完成。

计划中但尚未正式落地：

```text
/book
/book/{id}
/music
/game
```

## GitHub Pages 约束

Astro 配置：

```text
site/astro.config.mjs
site: https://closerdoor.github.io/Treasure
output: static
```

发布站点必须是纯静态产物。线上不应依赖：

- SQLite 数据库
- Playwright
- 爬虫运行时
- `.local/`
- `temp-script/`

## 架构原则

- SQLite 是本地事实源，generated 是前台事实源。
- 站点页面只消费 generated 和 public assets。
- 资源路径必须能在 `site/public/assets/` 找到实体文件，或前台必须有明确回退策略。
- 列表页使用轻量索引，详情页使用单条详情 JSON。
- 新模块先接入 generated 契约，再接入页面。
- 临时实验脚本不能直接成为发布流程的一部分。
