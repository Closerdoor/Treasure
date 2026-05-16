# movie-ingest 目录审视记录

最后审视时间：2026-05-14

## 职责边界

`temp-script/movie-ingest` 应被视为电影数据的本地采集工坊，职责到写入本地数据库为止：

```text
爬取电影信息
  -> 保存 raw / staging
  -> 下载海报、剧照、人物头像等本地资源
  -> 录入 .local/treasure.db
```

它不应负责 generated 导出、Astro 页面、站点构建、资源发布校验或 GitHub Pages 部署。后续链路应由仓库根部的 `tools/`、`generated/`、`site/` 负责。

## 2026-05-14 职责收口决定

当前正式主链路收口为：

```text
main.py / crawl.py
  -> sources/*.py
  -> downloader.py
  -> merger.py
  -> data/raw/
  -> data/staging/
  -> database.py
  -> .local/treasure.db
```

已确认的职责判断：

- `main.py`：保留为命令行入口。
- `crawl.py`：保留为统一采集编排入口。
- `sources/`：保留为外部数据源适配层。
- `downloader.py`：保留为采集阶段资源下载器，只写 `data/assets/`。
- `merger.py`：保留为 raw 到 staging 的合并层。
- `database.py`：保留为本目录正式 DB 入库层。
- `progress.py`：保留为采集进度状态。
- `name_matcher.py`：保留为人物匹配工具。
- `db_tools/import-movie.mjs`：降级为 legacy 入口；因会触碰 `site/public/assets`，默认不得直接运行。
- `db_tools/paths.mjs`：仅作为 legacy JS 入口配套路径常量保留。

当前目录实际不存在旧文档中提到的 `crawl_basic.py`、`crawl_reviews.py`、`crawl_images.py` 和若干头像维护脚本。后续文档与修复均以实际存在的文件为准。

## 当前功能分层

核心采集脚本：

- `main.py`：命令入口，调度 `MovieCrawler`。
- `crawl.py`：统一采集编排，负责豆瓣、TMDB、OMDb、百度百科、Wikipedia、烂番茄、Metacritic、资源下载、staging 输出。
- `sources/`：各外部数据源客户端；豆瓣单源由 `sources/douban.py` 在一次浏览器会话中采集详情、演职员、视频、图片、短评和影评。
- `merger.py`：合并多源数据，输出 raw / staging。
- `downloader.py`：下载作品图片与人物图片。
- `database.py`：把 staging 数据导入 `.local/treasure.db`，写入 `works`、`person`、`work_person`、`category`、`work_category`。
- `progress.py`：记录批次进度。
- `name_matcher.py`：用于人物姓名匹配。

旧文档中提及的 `crawl_basic.py`、`crawl_reviews.py`、`crawl_images.py`、`full_match.py`、`download_missing_avatars.py`、`fix_person_avatars.py`、`update_avatar_paths.py` 当前不存在，不作为当前工作流入口。

## 2026-05-14 豆瓣单源完备性判断

豆瓣单源当前可视为电影作品信息采集的完整实现：

- 基本信息来自 `/subject/{douban_id}/`，包含标题、原名、年份、评分、类型、国家/地区、语言、片长、上映日期、别名、IMDb ID、简介、主海报 URL、标签和推荐。
- 演职员来自 `/subject/{douban_id}/celebrities`，包含导演、编剧、全部演员、角色、中英文名、豆瓣人物 ID 和头像 URL。
- 视频来自 `/subject/{douban_id}/trailer`，包含视频名称、链接、封面图片和时长。
- 图片先访问 `/subject/{douban_id}/all_photos`，再按 `type=S/R/W` 全量采集剧照、海报、壁纸 URL 和总数。
- 短评来自 `/comments?percent_type=h&limit=20&status=P&sort=new_score`，即好评筛选下按热门/有用排序的前 20 条。
- 影评来自 `/reviews?start={start}&sort=hot`，先按热度排序确定前 20 条影评，再进入影评详情页读取完整正文。
- 图片和头像下载只使用本轮采集到的 URL，不重新访问豆瓣页面补抓。

## 2026-05-15 豆瓣反爬记录

调试《社交网络》时确认：豆瓣图片页在连续访问后可能跳转到 `https://www.douban.com/misc/sorry?...`，提示访问方式像机器人程序。进入该状态后，继续自动访问会持续返回禁止访问页，不能把空结果当作正常采集结果写入 raw。

处理规范已写入 `RULES.md`：遇到该页面立即暂停，不密集重试，不覆盖已有有效 raw；等待一段时间后重新执行，或由用户在浏览器里完成验证后继续。

## 2026-05-15 OMDb 单源增强记录

OMDb 单源职责定位为英文侧补充源，主要补充 IMDb / Rotten Tomatoes / Metacritic 评分、分级、奖项、票房、完整英文剧情和英文演职员文本。

本轮增强：

- API 请求增加重试与超时处理。
- 保留 `raw` 原始返回，便于字段追溯。
- 清洗 `N/A`，避免无效字符串进入合并层。
- 新增解析 `released`、`runtime_minutes`、`metascore`、`imdb_rating`、`imdb_votes`、`type`、`dvd`、`box_office`、`production`、`website`、`tomatoes` 等字段。
- 评分解析对 IMDb、Rotten Tomatoes、Metacritic 分别结构化保存。

## 2026-05-15 Wikipedia 单源增强记录

Wikipedia 单源职责定位为剧情、信息框、获奖/发行资料的补充源。

本轮增强：

- 重写搜索和电影页判断逻辑，支持中文电影、繁体电影、英文 `(film)` 等候选词条。
- 采集 `summary`、`plot`、`infobox`、`awards`、`quotes`、`categories`。
- 信息框原始字段完整保留到 `infobox`。
- 标准化导演、制片人、编剧、主演、配乐、摄影、剪辑、制片商、片长、产地、语言、上映日期、发行商、预算、票房、续作等字段，便于后续合并。

## 2026-05-16 Rotten Tomatoes 单源增强记录

Rotten Tomatoes 单源职责定位为英文评分、影评摘要、媒体共识和媒体评论补充源。本轮已重写 `sources/rotten_tomatoes.py`，并用《The Social Network》(2010) 实测通过。

当前采集契约：
- 搜索页 `search?search={title}`：保留搜索候选、候选年份、候选演员、候选番茄评分、认证状态和选中候选。
- 影片页 `/m/{slug}`：采集影片标题、Tomatometer、媒体评论总数、Audience Score、观众评分文本、海报主图 URL、简介、媒体共识、分级/年份/片长/类型，以及 JSON-LD 中的影片元数据。
- 评论页 `/m/{slug}/reviews?type=top`：按 Rotten Tomatoes Top reviews 页面顺序采集前 `REVIEWS_PER_SOURCE` 条评论，当前配置为 20 条；这是该源唯一保留的评论数量限制。
- 评论字段包含作者、作者页、媒体、日期、原始评分、正负倾向、Top critic 标记、评论正文和原文链接。

《The Social Network》实测结果：
- 命中 URL：`https://www.rottentomatoes.com/m/the-social-network`
- Tomatometer：96%，媒体评论总数 335。
- Audience Score：87%，观众评分文本 `100,000+ Ratings`。
- 采集到海报主图、简介、媒体共识。
- Top reviews 评论采集 20 条。

## 已确认符合职责的部分

- 主流程围绕电影数据采集、资源下载、staging、数据库录入展开。
- `database.py` 与当前数据库的电影主表、人物表、分类表和关联表结构基本同构。
- 图片和头像补全脚本仍服务于本地资源入库与资源覆盖率提升。
- `data/raw`、`data/staging`、`data/assets` 作为本地过程产物是合理的。

## 2026-05-15 新增与更新入口规范

后续入口设计必须区分新增作品和已有作品更新：

- 新增作品：先按外部 ID 只读查询 `.local/treasure.db`；已存在则默认停止，不重复采集和入库。
- 已有作品更新：必须指定 `work_id`、`source` 和字段白名单，只更新授权字段。
- 刷新单源 raw 与写入数据库应分成两个动作；`refresh-source` 不直接写库。
- 默认流程不得自动覆盖已有主数据。

## 2026-05-15 TMDB 单源采集核对

TMDB 单源当前覆盖详情、演职员、图片、视频、评论、外部 ID、上映/分级、关键词、推荐作品和相似作品。

已确认的默认数量限制：

- 评论默认取 `REVIEWS_PER_SOURCE` 条。
- 推荐作品和相似作品默认全量分页获取，不设置人工数量上限。

## 过程产物归属

电影采集过程中的任务清单、原始抓取结果、字段来源记录、冲突记录、批次摘要和临时资源下载缓存，应该优先归属本目录，而不是归属 `.local/` 主目录。

推荐边界：

```text
temp-script/movie-ingest/data/raw/       原始来源响应、网页快照或 API 结果
temp-script/movie-ingest/data/staging/   清洗后、准备入库的结构化候选记录
temp-script/movie-ingest/data/assets/    采集阶段下载的临时资源或待整理资源
temp-script/movie-ingest/data/reports/   批次摘要、失败项、字段来源与冲突记录
```

`.local/` 只接收已经被项目主链路承认的结果：`.local/treasure.db` 和 `.local/assets/`。也就是说，本目录负责解释“数据怎么来的、为什么这样入库”，`.local/` 负责保存“已经进入主数据链路的数据库和资源”。

如果未来继续保留字段来源或来源快照，建议放在 movie-ingest 的过程目录中，或由入库脚本写入数据库相关表；不建议长期散落在 `.local/field-sources/`、`.local/source-snapshots/` 这类全局目录中。

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
