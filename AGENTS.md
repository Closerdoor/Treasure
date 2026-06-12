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
  -> generated/ + site/public/assets/
  -> site/
  -> GitHub Pages
```

约定：

- `.local/treasure.db` 是本地结构化主数据源。
- `generated/` 是 Astro 前台的数据源。
- `site/public/assets/` 是前台可发布静态资源目录。
- `tools/db/export-generated.mjs` 同时负责导出 JSON 数据与当前记录引用的静态资源。
- 发布侧资源按作品目录隔离，不再导出共享 `site/public/assets/people/`。
- Astro 站点不直接读取 SQLite。
- Astro 站点不直接依赖 `temp-script/`。
- `temp-script/` 的具体整理由用户处理，未被要求时不要主动改动。

## Common Commands

```bash
# 查看数据库统计
node tools/db/check-counts.mjs

# 导出 generated 数据与当前记录引用的静态资源
node tools/db/export-generated.mjs

# 构建 Astro 静态站
cd site
npm.cmd run build
```

Windows PowerShell 下优先使用 `npm.cmd`，避免执行策略拦截 `npm.ps1`。

## Encoding Rules

本项目默认使用 UTF-8。写文件和输出中文时必须显式处理编码，避免 Windows PowerShell 控制台编码把中文替换成 `?` 或产生乱码。

- Markdown、JSON、脚本、报告等文本文件统一使用 UTF-8 编码写入。
- 生成或改写文件时优先使用明确指定 UTF-8 的工具链，例如 Node.js `fs.writeFileSync(path, text, { encoding: "utf8" })`，或 Python `Path.write_text(text, encoding="utf-8")`。
- PowerShell 读取中文文件时使用 `Get-Content -Encoding UTF8`；写中文文件时不要依赖默认编码，必须显式指定 UTF-8。
- 不要把 PowerShell 控制台里显示的乱码直接复制回文件；如果只是终端显示乱码，先用 UTF-8 读取或用脚本检查文件字节内容。
- 在 PowerShell 中执行包含中文字符串的内联脚本要特别小心；如需生成中文 Markdown/JSON，优先从已有 UTF-8 JSON 读取中文内容，或使用 UTF-8 脚本文件/Node.js 生成，避免中文常量经过控制台转码。
- 控制台输出中文时，脚本应使用 UTF-8 或对当前 stdout 编码做安全降级，只允许影响显示，不得把降级后的文本写入数据文件。

## Source Governance Rules

数据源必须分层管理，不能因为临时搜索到页面就把新站点直接并入正式录入流程。

- 书籍现有自动采集数据源以 `docs/PROJECT.md` 和 `temp-script/book-ingest` 当前实现为准：`douban`、`openlibrary`、`baike`、`wikipedia`、`goodreads`、`dangdang`、`qidian`。
- 网络小说 fast 批次默认只使用已实现的 `qidian` 自动采集；其他已有来源只能按当前规则补充，不得静默扩大。
- 新搜索到的 QQ阅读、微信读书、番茄、晋江、纵横、中国作家网、第三方全文站等页面，只能先标记为 `candidate`、`reference` 或 `manual_fallback`，用于人工审视、补强 source hints 或后续开发 adapter。
- 未实现 adapter、未验证反爬稳定性、未纳入字段映射和预检规则的新站点，不得进入 `batch_runner.py` 自动采集和 `batch_apply.py` 正式入库。
- 第三方全文站、论坛、博客、媒体文章只能作为低优先级参考或剧情补充候选；不得作为标题、作者、封面、主元数据的唯一事实来源。
- 如果确需新增正式数据源，必须先更新文档和配置，说明字段用途、可信度、失败模式、预检规则和人工确认边界。

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
