# Treasure 文档入口

本目录只保留少量“当前有效文档”。旧方案、阶段记录、验收报告和细节草稿统一放入 `docs/archive/`，只作为历史参考。

AI / Codex / Claude 进入项目时，优先按下面顺序阅读：

1. `docs/README.md`
   - 全局目录和阅读路线。
2. `docs/PROJECT.md`
   - 当前项目架构、目录职责、数据流和标准工作流。
3. `docs/STATUS.md`
   - 当前真实进度、数据量、已知问题和下一步。

## 当前主线

Treasure 是一个“精选型个人收藏馆”。当前目标不是做全量资料库，而是把馆长筛选后的影视、书籍、音乐、游戏等作品，整理成可部署到 GitHub Pages 的静态站点。

主链路：

```text
temp-script/ 爬取与实验脚本
  -> .local/treasure.db
  -> tools/db/export-generated.mjs
  -> generated/ + site/public/assets/
  -> site/
  -> GitHub Pages
```

Astro 站点不直接读取 SQLite，也不直接依赖 `temp-script/`。线上发布只依赖仓库内静态文件和 `site/public/assets/`。

## 文档分工

| 文档 | 作用 |
|---|---|
| `README.md` | 入口、全局目录、AI 阅读路线 |
| `PROJECT.md` | 项目架构与工作流，按四个核心部分组织 |
| `STATUS.md` | 当前事实快照、校验结果、已知风险、下一步 |
| `archive/` | 历史文档，仅在追溯旧决策时阅读 |

## 四个核心部分

1. `temp-script/`
   - 爬虫、解析、实验和临时数据处理脚本。
   - 目标是把作品数据整理后写入 `.local/treasure.db`。
2. `prisma/` 与 `.local/treasure.db`
   - 定义和承载结构化主数据。
   - Prisma schema 位于 `prisma/schema.prisma`。
3. `tools/db/`、`generated/` 与资源同步
   - 把数据库导出为 Astro 可读取的静态 JSON。
   - 把当前导出记录引用的本地资源导出到 `site/public/assets/`。
   - 发布资源按作品目录隔离，不再导出共享人物资源目录。
4. `site/`
   - Astro 静态站项目。
   - 最终构建产物部署到 GitHub Pages。

## 常用命令

```bash
# 查看数据统计
node tools/db/check-counts.mjs

# 导出数据库到 generated/，并导出当前记录引用的静态资源
node tools/db/export-generated.mjs

# 构建 Astro 静态站
cd site
npm.cmd run build
```

Windows PowerShell 下优先使用 `npm.cmd`，避免执行策略拦截 `npm.ps1`。

## 维护原则

- 先更新这 3 份核心文档，不轻易新增长期文档。
- 新增文档前先判断能否并入 `PROJECT.md` 或 `STATUS.md`。
- 阶段记录、验收报告、旧设计稿放入 `docs/archive/`。
- 如果当前事实和旧文档冲突，以 `STATUS.md` 为准。

## 文档治理规则

这些规则用于约束今后的文档维护，默认视为当前项目的有效规范：

- 文档优先记录“当前事实”，不要把历史愿望、一次性讨论稿或阶段性设想写成现行规范。
- 能量化的内容必须量化，尤其是数据总量、实际完成量、覆盖率、缺口数量与校验结果。
- `temp-script/` 中的实验性说明、局部 README 或阶段草稿，不得覆盖 `docs/` 中的主文档结论。
- 当数据库 schema、数据库记录量、generated 目录结构、前端路由、构建命令、资源目录策略、发布前校验结果、模块优先级或 V1 范围发生变化时，必须检查是否同步更新当前文档。
- 其中与“当前状态”直接相关的变化，必须同步更新 `STATUS.md`。
- 当历史文档不再代表当前状态时，只能三选一：更新为当前事实、迁入 `docs/archive/`、或在文档顶部明确标注“历史参考，不作为当前规范”。
- 同一事项不得同时存在两份都自称“当前规范”的文档。
- 禁止只写“已完成”而不写数量；禁止把脚本中的限制条件隐去不报；禁止把一次性调试结论沉淀成长期规范。
