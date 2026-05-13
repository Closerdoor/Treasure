# movie-ingest 目录审视记录

最后审视时间：2026-05-13

## 职责边界

`temp-script/movie-ingest` 应被视为电影数据的本地采集工坊，职责到写入本地数据库为止：

```text
爬取电影信息
  -> 保存 raw / staging
  -> 下载海报、剧照、人物头像等本地资源
  -> 录入 .local/treasure.db
```

它不应负责 generated 导出、Astro 页面、站点构建、资源发布校验或 GitHub Pages 部署。后续链路应由仓库根部的 `tools/`、`generated/`、`site/` 负责。

## 当前功能分层

核心采集脚本：

- `main.py`：命令入口，调度 basic / reviews / images。
- `crawl_basic.py`：抓取豆瓣、TMDB、OMDb、百度百科、Wikipedia 等基础信息。
- `crawl_reviews.py`：补充短评、长评、TMDB、烂番茄、Metacritic 等评论信息。
- `crawl_images.py`：补充图片资源。
- `sources/`：各外部数据源客户端。
- `merger.py`：合并多源数据，输出 raw / staging。
- `downloader.py`：下载作品图片与人物图片。
- `database.py`：把 staging 数据导入 `.local/treasure.db`，写入 `works`、`person`、`work_person`、`category`、`work_category`。
- `progress.py`：记录批次进度。
- `name_matcher.py`：用于人物姓名匹配。

补充维护脚本：

- `full_match.py`：批量补齐人物 TMDB ID。
- `download_missing_avatars.py`：下载缺失人物头像。
- `fix_person_avatars.py`：修正人物头像映射。
- `update_avatar_paths.py`：更新头像路径。

这些维护脚本仍属于“采集 / 补全 / 入库后修正”语境，可以暂时保留在本目录。

## 已确认符合职责的部分

- 主流程围绕电影数据采集、资源下载、staging、数据库录入展开。
- `database.py` 与当前数据库的电影主表、人物表、分类表和关联表结构基本同构。
- 图片和头像补全脚本仍服务于本地资源入库与资源覆盖率提升。
- `data/raw`、`data/staging`、`data/assets` 作为本地过程产物是合理的。

## 待处理 / 不合理文件

`db_tools/` 中存在较多历史过渡脚本。它们有些仍服务采集工坊，有些已经越过当前目录职责边界。

建议优先审视这些越界或疑似越界文件：

- `run-movie-batch-workflow.mjs`
  - 涉及 export-generated、check-assets、site build。
  - 已超出 movie-ingest 目录职责。
  - 建议迁入 `tools/db/`、改造为根部工作流，或归档。
- `generate-movie-acceptance-doc.mjs`
  - 生成验收文档，属于项目级验收或文档工具。
  - 建议迁入 `tools/db/` 或归档。
- `migrate-legacy-movie-files.mjs`
  - 迁移历史数据、复制资源到站点 public assets。
  - 属于一次性迁移工具，不宜长期作为 movie-ingest 主流程。
  - 建议确认是否仍有用；若无用，归档。
- `fetch-interstellar-assets.mjs`
  - 针对特定影片样本下载资源。
  - 明显是一次性样本脚本。
  - 建议归档或删除。
- `build-new-flow-movie-samples.mjs`
  - 生成新流程样本，偏阶段性迁移验证。
  - 建议确认是否还有复用价值；若无，归档。
- `report-movie-baseline.mjs`
  - 基线报告工具，偏验收 / 质量分析。
  - 如果继续使用，应迁入根部 `tools/db/`。
- `normalize-movie-field-sources.mjs`
  - 字段来源规范化工具。
  - 如长期使用，建议迁入根部 `tools/db/`；否则归档。
- `sync-movie-field-sources.mjs`
  - 字段来源同步工具。
  - 如长期使用，建议迁入根部 `tools/db/`；否则归档。
- `validate-movie-record.mjs`
  - 数据校验工具，职责可保留，但更适合根部 `tools/db/`。
- `check-movie-ingest-quality.mjs`
  - 质量校验工具，职责可保留，但更适合根部 `tools/db/`。

需要进一步确认的文件：

- `import-movie.mjs`
  - 功能是从 staging 导入 DB，符合采集工坊职责。
  - 但当前同类能力也存在于 Python `database.py`，需要确认是否保留双实现。
- `movie-db-projection.mjs`
  - 做 staging 到 DB 字段投影，理论上合理。
  - 但如果只被验收 / 新流程脚本使用，应考虑迁入 `tools/db/` 或合并。
- `movie-ingest-contract.mjs`
  - 记录 movie staging 契约，功能合理。
  - 建议未来成为根部通用 contract 的一部分。
- `movie-intake-registry.mjs`
  - 当前偏样本 / 特例配置。
  - 建议确认是否还需要长期维护。
- `generate-douban-top250-tasks.mjs`
- `search-movie-candidates.mjs`
- `prepare-movie-batch.mjs`
- `run-movie-intake-from-tasks.mjs`
  - 都属于任务生成、候选确认、批量 intake。
  - 如果这些是正式采集入口，可以保留，但建议统一位置和命名，避免与根部 `tools/db/` 重复。

## 主要风险

- `db_tools/` 与仓库根部 `tools/db/` 存在大量同名或近似功能脚本，容易让 AI 和人误判真实入口。
- 部分脚本已经引用 generated、site、build，和本目录“采集工坊”定位冲突。
- 部分脚本是一次性迁移或样本脚本，继续留在主目录会污染长期工作流。
- Python 导入路径和 JS 导入路径并存，需要确认最终保留哪条作为正式入库入口。

## 建议处理顺序

1. 先确认电影正式采集入口：Python 主流程还是 JS intake 流程。
2. 将涉及 generated、site build、发布校验的脚本迁出 `movie-ingest`，统一放到根部 `tools/db/` 或归档。
3. 对 `db_tools/` 中一次性样本 / 迁移脚本做归档或删除。
4. 保留真正服务采集工坊的脚本：候选、抓取、staging、字段来源、质量校验、DB 导入。
5. 最后更新 `README.md`、`RULES.md`、`DATA.md`，让它们只描述 movie-ingest 的采集和入库职责。
