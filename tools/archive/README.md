# Tools Archive

`tools/archive/` 保存已经从当前主链路中移出的历史工具。这里的脚本不应被 AI 或人工默认当作当前入口使用。

## 目录

```text
tools/archive/db-legacy-migrations/
tools/archive/movie-ingest-workflow/
```

### `db-legacy-migrations/`

旧数据库结构迁移、修表、恢复和测试脚本。多数脚本引用旧表名，例如 `people`、`terms`、`work_credits`、`work_types`。

当前数据库结构已经由 `prisma/schema.prisma` 和 `prisma/migrations/` 承担，这些脚本只作为历史参考保留。

### `movie-ingest-workflow/`

电影采集过程相关工具，例如候选搜索、批次任务、字段来源、staging 校验和旧 intake 流程。

这些能力更接近 `temp-script/movie-ingest` 的职责，而不是 DB -> generated -> Astro 主链路。后续如果继续使用，应迁回 movie-ingest 或重新设计为正式采集入口。

其中也包含一次性样板、验收文档、旧资源迁移和跨链路实验脚本。它们和旧 movie intake 工具有相对 import 关系，因此集中放置，便于后续复查。
