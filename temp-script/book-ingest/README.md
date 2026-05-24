# 书籍作品采集工作流

`temp-script/book-ingest` 是 Treasure 书籍作品的本地采集工坊，职责边界到写入 `.local/treasure.db` 为止。它不负责 generated 导出、Astro 页面、站点构建或发布校验。

当前目标是对齐已经跑通的 `movie-ingest` 单作品流程：

```text
确认作品输入
  -> 多数据源采集 raw
  -> 合并 normalized staging
  -> 下载封面资源并回写 staging
  -> staging 入库预检与临时库演练
  -> 显式 --apply 后写入 .local/treasure.db
```

## 当前状态

更新时间：2026-05-22

| 环节 | 当前状态 |
|---|---|
| 数据源采集 | 已有 7 个当前入口：豆瓣、OpenLibrary、百度百科、Wikipedia、Goodreads、当当、起点 |
| raw 保存 | `data/raw/{book_id}/{source}.json` |
| staging 合并 | `data/staging/{book_id}.json`，复杂字段保持对象 / 数组 |
| 封面下载 | `data/assets/{book_id}/`，下载成功后回写 `images.cover` / `images.covers` |
| 作者头像 | `data/assets/{book_id}/people/`，下载成功后回写 `_meta.personDetails[].avatarPath` |
| 入库入口 | `import_staging.py`；默认只预检，`--apply` 才写主库 |
| 资源提升 | 正式入库时递归复制到 `.local/assets/book/{book_id}/` |
| generated / Astro | 尚未接入，属于仓库根目录后续主链路 |

现有数据库中有 3 条书籍草稿；这些记录仍是早期数据，后续需要按新流程逐本刷新。

## 目录职责

```text
book-ingest/
├── main.py                 # 当前主入口，调度采集/合并/下载/预检/入库
├── import_staging.py       # 正式 staging 预检与入库 CLI
├── merger.py               # 多源合并，生成 normalized staging
├── database.py             # 写入 books/person/book_person/category/book_category
├── progress.py             # 豆瓣 ID 与内部 book_id 的进度映射
├── config.py               # 数据源、延迟、数量限制和 ID 前缀配置
├── sources/*_crawl.py      # 当前被 main.py 使用的数据源爬虫
├── downloaders/            # 封面/头像下载器
├── data/raw/               # 原始来源快照
├── data/staging/           # 准备入库的结构化候选记录
└── data/assets/            # 采集阶段下载的本地资源
```

`sources/` 中不带 `_crawl.py` 的旧文件、`crawl_basic.py`、`crawl_reviews.py`、`db_tools/` 目前视为 legacy / 参考入口；当前正式单本流程以 `main.py` 和 `import_staging.py` 为准。删除或归档这些旧入口前需要单独确认。

## 标准命令

在 `temp-script/book-ingest` 目录下执行：

```bash
# 采集全部当前数据源；--book 使用豆瓣读书 subject id
python main.py --crawl all --book 1008145 --title "围城"

# 合并 raw 为 staging；--book 使用内部 book_id
python main.py --merge --book 0200000002

# 下载封面和作者头像，并把实际文件名回写到 staging
python main.py --download --book 0200000002

# 只读预检：检查查重、资源、本地化、staging 形态，并在临时 DB 演练导入
python import_staging.py --book-id 0200000002 --update-existing

# 生成字段核对 HTML，展示 DB / staging / 各 raw 数据源的实际内容
python tools/field_report.py --book-id 0200000002

# 预检通过后，显式写入主数据库
python import_staging.py --book-id 0200000002 --update-existing --apply
```

`main.py --import` 也会调用同一套预检逻辑。没有 `--apply` 时不会写入 `.local/treasure.db`。

## 当前数据源

| 数据源 | 当前用途 |
|---|---|
| 豆瓣读书 | 中文标题、ISBN、出版年、出版社、简介、评分、标签、作者/译者、短评/长评、摘录、推荐、封面 |
| OpenLibrary | 英文标题/原名、ISBN、作者、首版年份、简介、主题、评分、封面 |
| 百度百科 | 中文补充信息、出版信息、字数、语言、简介、别名、作者、页数/定价 |
| Wikipedia | 原名、国家、语言、简介、名句、译者、出版信息、封面 |
| Goodreads | 英文标题、ISBN、评分、作者/译者、系列、类型、页数、出版社、简介、书评、相似作品、封面 |
| 当当 | ISBN、出版社、字数、页数、价格、出版年、简介、译者、丛书、封面 |
| 起点 | 网络小说标题、作者、字数、连载状态、分类、标签、简介、封面 |

当前配置中书评类采集存在明确限制：`config.REVIEWS_PER_SOURCE = 20`。如果后续要改成全量采集，需要先确认数量、排序和反爬策略。

当前内容字段规则：

- `year`：作品首版年份，优先取百度百科首版年；具体录入版本的出版日期保留在 `publishDate` 等版本字段中。
- `summary`：书籍内容简介，优先取 Wikipedia 的“故事大纲”分节。
- `story`：完整剧情 / 内容情节，优先取百度百科的“内容情节”等正文分节。
- `excerpts`：原文摘录，豆瓣列表页按热度排序取前 20 条，并尽量进入每条摘录详情页，只保留原文内容；用户昵称、回复数、点赞数、日期等互动信息不得进入 `content`。

百度百科存在安全验证时，`sources/baike_crawl.py` 支持两种人工辅助方式：

- 优先读取 `data/manual/baike/*.html` 中手动保存的百科页面；文件标题或 `h1` 命中书名时直接从本地 HTML 解析，不再访问百度。
- 没有本地 HTML 时，自动加载 `data/cookies/baike.json` 中由 Cookie-Editor 导出的百度 Cookie，再访问线上页面。

`data/manual/` 和 `data/cookies/*.json` 是本地辅助材料，包含外部页面快照或 Cookie，不提交 Git。

这套人工辅助流程适用于其他数据源：当脚本被验证码、风控页、端侧差异或动态加载挡住，而用户浏览器能看到目标内容时，先让用户保存 HTML 或导出 Cookie，再让采集脚本解析本地快照 / 加载 Cookie。脚本仍必须避免把验证码页、空壳页或稀疏结果覆盖进 raw。

## 字段核对

`tools/field_report.py` 会从当前 raw 与 staging 自动生成字段核对 HTML：

```text
docs/field-map.html
```

它用于人工检查“数据库字段、staging 当前值、各数据源实际抓取内容”的对应关系。图片字段只展示文件名和数量，不直接嵌入图片。

## Staging 契约

`data/staging/{book_id}.json` 是入库候选记录，不应提前把复杂字段 JSON 字符串化。

复杂字段在 staging 中保持对象 / 数组：

```text
scores
externalSource
images
reviews
related
quotes
excerpts
otherTitles
```

字段来源、冲突和临时合并信息放入 `_meta`：

```text
_meta.fieldSources
_meta.conflicts
_meta.authors
_meta.translators
_meta.tags
_meta.subjects
_meta.genres
_meta.personDetails
_meta.coverUrls
```

入库阶段由 `database.py` 负责把复杂字段序列化为 DB 需要的 JSON 字符串，并把 `_meta` 中的作者、译者、标签投影到关系表。

## 入库预检

`import_staging.py` 默认只读，预检内容包括：

- staging 文件名与内部 `id` 一致。
- 新书 ID 必须等于数据库当前最大书籍 ID 的下一条 `0200NNNNNN`。
- 刷新已有书籍时必须传 `--update-existing`，并要求数据库存在同 ID 记录。
- 使用 ISBN、豆瓣、OpenLibrary、Goodreads、百度百科、Wikipedia、当当、起点等外部 ID 查重。
- `images.cover` 与 `images.covers` 必须是本地文件名，且能在 `data/assets/{book_id}/` 找到。
- `_meta.personDetails[].avatarPath` 必须是本地文件名，且能在 `data/assets/{book_id}/people/` 找到。
- staging 复杂字段不能提前序列化成 JSON 字符串。
- 临时复制数据库并演练导入，最后执行 SQLite 外键检查。

正式写库前会备份 `.local/treasure.db` 到 `.local/backup/`。

## 资源约定

采集阶段资源：

```text
data/assets/{book_id}/cover-main.jpg
data/assets/{book_id}/covers/{source}.jpg
data/assets/{book_id}/people/{person_id}-avatar.jpg
...
```

入库后主资源：

```text
.local/assets/book/{book_id}/cover-main.jpg
.local/assets/book/{book_id}/covers/{source}.jpg
.local/assets/book/{book_id}/people/{person_id}-avatar.jpg
```

`images.cover` 是主封面文件名；`images.covers` 是各数据源封面映射；`images.assetDir` 当前记录内部书籍 ID。后续书籍接入 generated / Astro 时，再由项目级导出脚本决定发布侧 URL。

## 系列约定

采集阶段的系列候选保存在 `_meta.series` 和 `_meta.seriesCandidates`。正式入库时，如果 `_meta.series.name` 存在，`database.py` 会复用或创建 `book_series`，并把当前书籍的 `seriesId` 指向该系列。`related.series` 只作为来源候选和后续人工核对材料，不替代数据库关系。

## 重要边界

- 不要在 book-ingest 内直接改写 `generated/` 或 `site/public/assets/`。
- 不要跳过豆瓣主源；豆瓣触发反爬时应停止等待，不应静默降级。
- 不要隐式限制采集范围；已有的每源 20 条书评限制必须在运行前说明。
- 不要直接使用 legacy `db_tools/` 作为正式入库入口，除非后续确认保留。
