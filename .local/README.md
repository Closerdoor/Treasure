# .local 本地主数据工作区

最后更新：2026-05-13

## 职责定位

`.local/` 是 Treasure 项目的本地主数据交付区，用来保存已经进入项目主链路、但不应提交到公开仓库或部署到 GitHub Pages 的本地资产。

它不是爬虫过程工作台，也不是站点构建产物目录。

主链路位置：

```text
temp-script/*-ingest
  -> .local/treasure.db + .local/assets/
  -> generated/ + site/public/assets/
  -> site/
```

## 核心内容

```text
.local/treasure.db   唯一本地 SQLite 主数据库
.local/assets/       本地静态资源主源
.local/backup/       数据库或关键数据的本地备份
```

### .local/treasure.db

结构化主数据源。movie/book ingest 的最终入库目标，也是 `tools/db/export-generated.mjs` 的读取来源。

约定：

- 不部署到线上。
- 不提交到 Git。
- 不由 Astro 站点直接读取。
- 表结构以 `prisma/schema.prisma` 和已执行迁移为准。

### .local/assets/

本地静态资源主源，例如电影海报、剧照、人物头像等。站点发布前由项目级脚本同步到 `site/public/assets/`。

约定：

- `.local/assets/` 是本地资源源头。
- `site/public/assets/` 是发布副本，不是源头。
- 数据库或 generated 中引用的本地资源，应最终能从 `.local/assets/` 同步得到。

### .local/backup/

本地备份区，用于保存数据库备份或关键数据快照。备份文件不应参与站点构建。

## 不推荐长期放在这里的内容

以下内容更适合放在对应 ingest 目录中：

```text
批次任务清单
原始抓取结果
网页/API 来源快照
字段来源记录
多源冲突记录
采集阶段临时下载缓存
单次实验脚本产物
```

推荐归属：

```text
temp-script/movie-ingest/data/raw/
temp-script/movie-ingest/data/staging/
temp-script/movie-ingest/data/assets/
temp-script/movie-ingest/data/reports/

temp-script/book-ingest/data/raw/
temp-script/book-ingest/data/staging/
temp-script/book-ingest/data/assets/
temp-script/book-ingest/data/reports/
```

如果字段来源或来源快照需要成为长期事实，优先考虑写入数据库结构或纳入 ingest 目录的稳定过程记录，而不是散落在 `.local/field-sources/`、`.local/source-snapshots/` 这类全局目录中。

## 当前历史残留

当前 `.local/` 中可能仍存在历史目录，例如：

```text
.local/batches/
.local/field-sources/
.local/source-snapshots/
.local/new-flow/
.local/new-flow-field-sources/
.local/temp-docs/
```

这些目录应视为历史采集过程产物或迁移阶段产物。清理前需要逐批确认其内容是否已经迁移到对应 ingest 目录、数据库、正式文档或已经过期。

## Prisma 与数据库文件的关系

`prisma/schema.prisma` 不是本地数据库文件本身，而是数据库结构契约。它应该提交到 Git，并作为 `.local/treasure.db` 表结构、字段关系和类型约束的主要说明来源。

简化理解：

```text
prisma/schema.prisma  定义数据库长什么样
.local/treasure.db    保存本地真实数据
```

因此，讨论“本地数据库资产”时需要同时关注两类文件：

- 数据文件：`.local/treasure.db`
- 结构契约：`prisma/schema.prisma` 与 `prisma/migrations/`

但只有 `.local/treasure.db` 属于本地私有数据；Prisma 文件属于项目源码和结构文档。
