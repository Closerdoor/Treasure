# AGENTS.md

This file provides guidance to Codex and other AI agents when working in this repository.

## Language

请使用中文与用户对话。

## Read First

进入项目后先读：

```text
docs/README.md
docs/PROJECT.md
docs/STATUS.md
```

项目事实、数据量、目录职责和当前下一步以 `docs/` 下的当前文档为准。不要把归档文档、旧设计稿或临时脚本产物当作当前规范。

## Project Shape

Treasure 是一个精选型个人收藏馆，最终目标是部署为 GitHub Pages 静态站。

当前主链路：

```text
temp-script/ 数据获取与实验
  -> .local/treasure.db
  -> tools/db/export-generated.mjs
  -> generated/
  -> site/
  -> GitHub Pages
```

约定：

- `.local/treasure.db` 是本地结构化主数据源。
- `generated/` 是 Astro 前台的数据源。
- `site/public/assets/` 是前台可发布静态资源目录。
- Astro 站点不直接读取 SQLite。
- Astro 站点不直接依赖 `temp-script/`。
- `temp-script/` 的具体整理由用户处理，未被要求时不要主动改动。

## Common Commands

```bash
# 查看数据库统计
node tools/db/check-counts.mjs

# 导出 generated 数据
node tools/db/export-generated.mjs

# 同步资源并导出数据
cd site
npm.cmd run sync

# 构建 Astro 静态站
cd site
npm.cmd run build
```

Windows PowerShell 下优先使用 `npm.cmd`，避免执行策略拦截 `npm.ps1`。

## Data Integrity Rules

涉及以下情况时，必须先向用户确认：

- 限制数据范围，例如只处理前 N 条。
- 跳过某些数据源。
- 降级处理，例如先使用低质量候选数据。
- 删除、覆盖或批量改写可能影响数据完整性的内容。
- 改变数据库到 generated 的字段契约。

汇报进度时必须量化：

- 数据总量。
- 实际完成量。
- 覆盖率或完成率。
- 未完成原因。

如果脚本中存在限制性逻辑，例如 `slice(0, 10)`、只取前 N 条、跳过缺字段记录等，必须在代码注释中说明，并在运行前向用户汇报。

## Documentation Rules

- 优先更新 `docs/README.md`、`docs/PROJECT.md`、`docs/STATUS.md`。
- 不轻易新增长期文档；能并入现有 3 份核心文档的就并入。
- 阶段记录、验收报告、旧设计稿放入 `docs/archive/`。
- 当前事实和归档文档冲突时，以 `docs/STATUS.md` 为准。
