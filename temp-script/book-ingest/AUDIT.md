# book-ingest 审视记录

最后审视时间：2026-05-22

## 当前结论

`temp-script/book-ingest` 已按 movie-ingest 的模式收口为单作品采集工坊：

```text
raw source snapshots
  -> normalized staging
  -> local assets
  -> import precheck
  -> .local/treasure.db
```

当前正式入口：

- `main.py`：调度采集、合并、下载、预检。
- `import_staging.py`：只读预检、临时库演练和显式入库。
- `merger.py`：输出对象 / 数组结构的 staging，并记录 `_meta.fieldSources`、`_meta.conflicts`。
- `database.py`：写入 SQLite，并把封面资源提升到 `.local/assets/book/{book_id}/`。

## 已完成的结构修正

- staging 复杂字段保持对象 / 数组，不在合并阶段提前 JSON 字符串化。
- 入库预检默认只读；只有 `--apply` 才写 `.local/treasure.db`。
- 已新增 `--update-existing`，用于明确刷新数据库中同 ID 的已有书籍。
- 入库前会查重、检查本地资源、检查 staging 形态，并在临时数据库里演练导入。
- 封面下载完成后会把实际成功下载的文件名回写到 staging，避免合并阶段猜测文件名。
- 多源封面已调整为 `images.covers` 映射，补充封面保存到 `covers/{source}.jpg`。
- 作者头像已纳入采集阶段资源目录：`data/assets/{book_id}/people/`，并回写 `_meta.personDetails[].avatarPath`。
- 正式入库后会递归复制 `data/assets/{book_id}/` 到 `.local/assets/book/{book_id}/`。
- `book_series` 已接入入库流程：`_meta.series.name` 存在时复用或创建系列，并写入 `books.series_id`。
- `books` 已补齐出版版本字段：`publish_date`、`pages`、`price`、`binding`、`format`、`edition`。
- 已新增 `tools/field_report.py`，可从 raw/staging 自动生成 `docs/field-map.html` 字段核对页。
- 已用《围城》刷新豆瓣、当当、Goodreads；当前样板 staging 包含豆瓣短评 20、豆瓣长评 20、摘录 20、作者头像 1、主封面 1、多源补充封面 2。
- `database.py` 的书籍导入改为事务内统一提交，避免人物 / 分类关系半写入。

## 当前保留的 legacy 内容

以下内容仍存在，但不作为正式单本工作流入口：

```text
crawl_basic.py
crawl_reviews.py
db_tools/
sources/ 中不带 _crawl.py 的旧爬虫
```

这些文件可能仍有参考价值。删除、归档或迁移前需要单独确认。

## 仍需后续讨论

- 是否保留每源 20 条书评 / 摘录限制，或改为全量采集。
- 是否把 legacy 入口归档或删除。
- 是否为书籍生成类似电影的字段核对 HTML 固定入口。
- 书籍进入 generated / Astro 后，`.local/assets/book/{book_id}/` 到 `site/public/assets/book/{book_id}/` 的导出契约需要单独设计。
