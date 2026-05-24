# 书籍采集规则

最后更新：2026-05-22

本文件记录 `temp-script/book-ingest` 当前有效规则。旧入口、阶段性文档或历史脚本与本文件冲突时，以本文件和仓库根目录 `docs/STATUS.md` 为准。

## 职责边界

`book-ingest` 只负责：

```text
多源采集 -> raw -> staging -> 本地资源下载 -> 入库预检 -> 写入 .local/treasure.db
```

不负责：

```text
generated 导出
Astro 页面
站点构建
GitHub Pages 发布
```

## 数据源规则

当前正式采集入口使用 7 个数据源：

```text
douban
openlibrary
baike
wikipedia
goodreads
dangdang
qidian
```

豆瓣是书籍中文基础资料主源。豆瓣失败时不允许直接跳过后继续完成“正式入库”；应记录失败原因并等待用户确认下一步。

其他数据源如果触发登录、验证码、地区限制或反爬，不应静默降级。需要跳过某个数据源、降低质量或改用替代来源时，先向用户确认。

## 当前采集限制

当前配置存在一个明确数量限制：

```python
REVIEWS_PER_SOURCE = 20
```

含义：

- 豆瓣短评：最多 20 条。
- 豆瓣长评：最多 20 条。
- Goodreads 书评：最多 20 条。
- 豆瓣摘录：列表页按热度排序取前 20 条，进入摘录详情页获取原文内容。

这不是“全量采集”规则。后续如果用户要求全量书评、全量摘录或其他无限列表，必须先确认范围、排序、页数和反爬风险。

内容字段来源规则：

- `year` 表示作品首版年份，优先使用百度百科首版年；豆瓣具体版本年份保留在 `publishDate` / 版本信息中。
- `summary` 优先取 Wikipedia 的“故事大纲”分节。
- `story` 优先取百度百科的“内容情节”等正文分节，对齐电影作品的完整剧情字段；如果同一页面只能访问到验证码页，可使用本地手动保存 HTML 或 Cookie 辅助访问。
- `excerpts[].content` 只保留原文摘录，不保留用户昵称、回复数、点赞数、日期等互动信息；页码 / 章节备注写入 `excerpts[].note`。

百度百科反爬处理规则：

- 脚本优先解析 `data/manual/baike/*.html`，用作用户已确认页面的本地快照。
- 没有本地 HTML 时，脚本可加载 `data/cookies/baike.json` 提高线上访问成功率。
- 如果线上页面仍返回安全验证页，必须停止保存本次稀疏结果，不得覆盖已有有效 raw。
- `data/manual/` 和 `data/cookies/*.json` 不进入 Git。

当任一公开网页数据源出现类似反爬、验证码、端侧内容差异或自动化浏览器看不到用户浏览器内容时，应优先按这个协作流程处理：

1. 先用脚本记录实际访问地址、最终跳转地址、页面标题、页面长度和关键文本命中情况，确认是“地址错误”还是“页面内容不同”。
2. 如果用户浏览器能正常看到内容，请用户保存页面 HTML 到对应采集目录下的 `data/manual/{source}/`，脚本优先从本地 HTML 解析并保留来源标记。
3. 如果该站点 Cookie 能改善访问状态，请用户导出该站点 Cookie 到 `data/cookies/{source}.json`，脚本负责转换为 Playwright Cookie 格式并加载。
4. 本地 HTML 与 Cookie 都属于本地辅助材料，不提交 Git；最终 raw / staging 仍需记录字段来源，避免把人工辅助误写成未验证来源。

## Staging 规则

`data/staging/{book_id}.json` 是准备入库的候选数据，必须保持可审阅的对象结构。

不得在 staging 阶段提前序列化为 JSON 字符串的字段：

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

字段来源与冲突写入 `_meta`：

```text
_meta.fieldSources
_meta.conflicts
```

作者、译者、标签、主题、类型等用于关系表的临时合并信息，也保留在 `_meta`，由入库阶段投影到关系表。

## 资源规则

封面下载阶段必须把远程图片下载到：

```text
data/assets/{book_id}/
```

下载完成后必须把实际成功下载的文件名回写到：

```text
images.cover
images.covers
images.assetDir
```

入库阶段再把这些文件复制到：

```text
.local/assets/book/{book_id}/
```

staging 中的图片字段不应残留远程 URL 或未本地化对象。入库预检会阻断这种情况。

多源封面必须保留为映射：

```json
{
  "cover": "cover-main.jpg",
  "covers": {
    "openlibrary": "covers/openlibrary.jpg",
    "goodreads": "covers/goodreads.jpg"
  }
}
```

作者头像下载到 `data/assets/{book_id}/people/`，并回写 `_meta.personDetails[].avatarPath`。正式入库时头像随书籍资源递归复制到 `.local/assets/book/{book_id}/people/`。

## 系列规则

采集到的系列信息先放在 `_meta.series` 和 `_meta.seriesCandidates`。正式入库时：

- 如果 `_meta.series.name` 存在，复用或创建 `book_series`。
- 当前书籍写入 `books.series_id`。
- `books.series_order` 只在来源明确给出顺序时填写。
- `related.series` 仅作为来源候选，不替代数据库关系。

## 入库规则

正式入口是：

```bash
python import_staging.py --book-id 0200000002
```

默认只做预检和临时库演练，不写主库。

写入主库必须显式传：

```bash
--apply
```

刷新已有书籍必须显式传：

```bash
--update-existing
```

预检必须覆盖：

- ID 与文件名一致。
- 新书 ID 为数据库下一条 `0200NNNNNN`。
- 已有书刷新时数据库存在同 ID 记录。
- 外部 ID / ISBN 查重。
- 本地资源存在。
- staging 复杂字段未提前 JSON 字符串化。
- 临时数据库导入与外键检查通过。

## 合并规则

通用原则：

- 中文基础字段优先豆瓣。
- 豆瓣缺失时再使用中文补充源，如百度百科、当当。
- 原文标题、海外评分、英文主题等使用 OpenLibrary / Goodreads / Wikipedia 补充。
- 相同作者/译者需要清洗国籍前缀并去重。
- 多源冲突不应静默丢失，应记录到 `_meta.conflicts`。

当前优先级的具体实现以 `merger.py` 为准，字段能力说明见 `DATA.md`。

## 反爬规则

豆瓣：

- 需要登录时通知用户处理。
- 触发反爬或无法访问时停止等待，不反复高频重试。
- 不要为了完成流程而绕过豆瓣主源。

Goodreads / 当当 / 起点：

- 需要登录、验证码或请求失败时，记录失败原因。
- 除非用户确认，否则不把缺失数据视为已完成。

通用：

- 使用配置中的延迟、重试和代理。
- 不要新增隐藏的 `slice(0, N)`、固定跳页或跳过缺字段记录；确需限制时先确认，并在代码注释和运行说明中写明。

## Legacy 入口

以下内容当前保留为历史兼容或参考，不作为正式单本工作流入口：

```text
crawl_basic.py
crawl_reviews.py
db_tools/
sources/ 中不带 _crawl.py 的旧爬虫
```

删除、归档或改写 legacy 入口前，需要单独确认。
