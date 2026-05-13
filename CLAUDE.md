# CLAUDE.md

本文件只保留 Claude Code 的入口说明，当前项目事实以 `AGENTS.md` 和 `docs/` 下的核心文档为准。

进入项目后请先阅读：

```text
AGENTS.md
docs/README.md
docs/PROJECT.md
docs/STATUS.md
```

关键约定：

- 请使用中文与用户对话。
- 不要把旧 `content/` 链路、归档文档、临时脚本产物或历史设计稿当作当前规范。
- 当前主链路是 `.local/treasure.db -> tools/db/export-generated.mjs -> generated/ + site/public/assets/ -> site/`。
- Astro 站点不直接读取 SQLite，也不直接依赖 `temp-script/`。
- 任何数据范围限制、跳过数据源、降级处理、删除覆盖或字段契约变更，都必须先向用户确认。
- 汇报进度必须量化：数据总量、实际完成量、覆盖率或缺口数量。
