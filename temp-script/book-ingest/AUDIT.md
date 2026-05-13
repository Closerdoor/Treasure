# book-ingest 目录审视记录

最后审视时间：2026-05-13

## 职责边界

`temp-script/book-ingest` 应被视为书籍数据的本地采集工坊，职责到写入本地数据库为止：

```text
爬取书籍信息
  -> 保存 raw / staging
  -> 下载封面、人物头像等本地资源
  -> 录入 .local/treasure.db
```

它不应负责 generated 导出、Astro 页面、站点构建、资源发布校验或 GitHub Pages 部署。后续链路应由仓库根部的 `tools/`、`generated/`、`site/` 负责。

## 当前功能分层

核心采集脚本：

- `main.py`：命令入口，调度 basic / reviews。
- `crawl_basic.py`：抓取豆瓣读书、OpenLibrary、百度百科、Wikipedia、当当、起点等基础信息。
- `crawl_reviews.py`：抓取豆瓣短评和长评。
- `sources/`：各外部数据源客户端。
- `merger.py`：合并多源数据，输出 raw / staging。
- `downloaders/`：下载封面和人物头像。
- `database.py`：把 staging 数据导入 `.local/treasure.db`，写入 `books`、`person`、`book_person`、`category`、`book_category`。
- `db_tools/import_to_db.py`：单本导入 DB。
- `db_tools/import_batch.py`：批量导入 DB。
- `progress.py`：记录批次进度。
- `tools/login_helper.py`：辅助处理需要登录的数据源。

## 已确认符合职责的部分

- 目录整体围绕书籍采集、封面下载、raw / staging、DB 导入展开。
- `db_tools/` 当前只有导入脚本，没有明显越过职责边界。
- `database.py` 与当前书籍相关表结构基本对应。
- `data/raw`、`data/staging`、`data/assets` 作为本地过程产物是合理的。

## 待处理 / 不合理内容

目前没有发现像 movie-ingest 那样大量越界的工具脚本，但存在几类需要整理的问题。

文档边界需要收窄：

- `README.md`
  - 当前包含 generated / Astro / GitHub Pages 后续链路描述。
  - 这些可以作为上下游背景，但不应让人误解 book-ingest 负责站点导出和发布。
- `DATA.md`
  - 当前提到“导出到 generated 或发布时复制到 `.local/assets/book/`”。
  - 建议改成：book-ingest 只负责把封面下载到本地过程目录，后续资源同步由项目级工具处理。

实现细节需要后续确认：

- `crawl_basic.py`
  - 下载封面后把 `cover_local` 写回内存，但保存 staging 发生在下载前。
  - 需要确认最终 staging 文件是否应记录本地封面路径。
- `merger.py`
  - 在 staging 阶段已经把 `externalSource`、`scores`、`images`、`related`、`quotes`、`otherTitles`、`reviews` 等字段序列化为 JSON 字符串。
  - 如果未来要统一采集工坊契约，建议 staging 保持对象 / 数组结构，在 DB 导入阶段再序列化。
- `merger.py`
  - `summary` 等字段的来源优先级与 `RULES.md` 中描述不完全一致。
  - 例如规则强调豆瓣优先，但实现中百度百科摘要可能覆盖已有摘要。
- 字段来源追踪
  - `RULES.md` 要求字段级来源标注，但当前实现主要是保存各来源 raw 数据和 progress 状态，没有形成稳定的字段级 source 文件或 source 字段落盘。
- `cookies.json`
  - 位于根目录，可能包含登录状态。
  - 建议确认是否应移动到 `data/cookies/` 或 `.local/`，并确保不会进入公开仓库。
- `docs/research-notes.md`
  - 位于 book-ingest 内部，偏研究记录。
  - 建议确认是否仍在使用；如果只是阶段性记录，可归档。

## 主要风险

- staging 契约和 movie-ingest 不一致，未来做统一校验、统一导入、统一预览时会增加成本。
- 字段级来源没有落地，后续人工复核和冲突判断会变难。
- README / DATA 中混入后续站点链路，可能让 AI 误以为 book-ingest 负责 generated 或 Astro。
- `cookies.json` 的位置和版本管理策略需要谨慎。

## 建议处理顺序

1. 先收窄 `README.md` 和 `DATA.md`，明确 book-ingest 只负责采集、下载、staging、入库。
2. 统一 staging 契约：复杂字段先保留对象 / 数组结构，DB 导入阶段再序列化。
3. 补齐字段来源记录，至少为关键字段记录来源和覆盖逻辑。
4. 修正封面下载后 staging 不持久化本地路径的问题。
5. 重新核对 `RULES.md` 中的数据源优先级和 `merger.py` 实际逻辑。
6. 清理或移动 `cookies.json` 与 `docs/research-notes.md`。
