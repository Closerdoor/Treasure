# 书籍采集规则

最后更新：2026-06-03

本文记录 `temp-script/book-ingest` 当前有效规则。旧入口、阶段性文档或历史脚本与本文冲突时，以本文、仓库根目录 `docs/PROJECT.md` 和 `docs/STATUS.md` 为准。

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

入库后的主链路在仓库根目录执行：

```bash
node tools/db/export-generated.mjs
cd site
npm.cmd run build
```

## 正式入口

正式入口：

```text
main.py
import_staging.py
merger.py
database.py
tools/field_report.py
sources/*_crawl.py
downloaders/
```

Legacy / 参考入口：

```text
crawl_basic.py
crawl_reviews.py
db_tools/
sources/ 中不带 _crawl.py 的旧爬虫
```

legacy 入口不得用于正式入库。尤其是 `db_tools/import_batch.py` 会绕过当前正式预检链路。

## 数据源规则

当前正式数据源：

```text
douban
openlibrary
baike
wikipedia
goodreads
dangdang
qidian
```

豆瓣读书是中文基础资料主源。豆瓣失败时不得静默跳过后继续正式入库；必须记录原因并等待人工确认。

其他数据源如果触发登录、验证码、地区限制或反爬，不得静默降级。需要跳过某个数据源、降低质量或使用替代来源时，必须先向用户确认。

## 数量限制

当前配置存在明确数量限制：

```python
REVIEWS_PER_SOURCE = 20
```

含义：

- 豆瓣短评：最多 20 条。
- 豆瓣长评：最多 20 条。
- Goodreads 书评：最多 20 条。
- 豆瓣摘录：列表页按热度排序取前 20 条，并尽量进入详情页获取纯原文。

这不是全量采集规则。如需全量评论、全量摘录或其他无限列表，必须先确认范围、排序、页数和反爬风险。

## 中文字段规则

正式前台展示字段必须优先保证中文质量。

不得录入英文候选值的字段包括：

```text
summary
story
language
country
publisher
genre
tags
_meta.genres
_meta.tags
```

允许外文的字段：

```text
titleOriginal
外文别名
评论原文
海外来源 raw / 审视字段
```

如果多个来源只提供英文简介或英文分类，应保留在 raw 或 `_meta` 审视字段，不得降级写入正式 staging 字段。

## 内容字段规则

- `summary` 对齐电影作品的“简介”。
- `story` 对齐电影作品的“完整剧情 / 内容情节”。
- 没有可靠中文 `story` 时保持为空，不得复制 `summary` 充数。
- 百度百科如果只取得带 `...` 或省略号的 SEO 短描述，不得写入 `summary` 或 `story`。

普通书：

- `summary` 优先取 Wikipedia 的“故事大纲”分节。
- `story` 优先取百度百科“内容情节”等正文分节。

网络小说：

- `summary` 不使用 Wikipedia。
- `summary` 优先使用起点或豆瓣介绍。
- `story` 使用百度百科词条顶部正文，即词条开头完整介绍块。

## 年份与版本规则

- `year` 表示作品首版年份，优先使用百度百科首版年。
- 当前录入版本的出版日期保留在 `publishDate`。
- 页数、定价、装帧、版式、版本说明等属于版本信息字段。

## 类型规则

- 书籍类型必须是中文。
- `genre` / `_meta.genres` 可来自豆瓣、起点、百度百科等中文来源。
- OpenLibrary / Goodreads 的英文 subjects、genres 只能用于 raw 或审视，不进入 `book_category` 和前台类型展示。

## 摘录规则

- 豆瓣摘录列表按热度排序取前 20 条。
- 尽量进入每条摘录详情页获取完整内容。
- `excerpts[].content` 只保留原文。
- 用户昵称、回复数、点赞数、日期等互动信息不得进入 `content`。
- 页码、章节等可写入 `excerpts[].note`。
- 摘录必须去重；重复内容不得批量进入 staging。

## 百度百科规则

反爬处理：

- 脚本优先解析 `data/manual/baike/*.html`。
- 没有本地 HTML 时，可加载 `data/cookies/baike.json`。
- 线上页面如果返回安全验证页，必须停止保存本次稀疏结果，不得覆盖已有有效 raw。
- `data/manual/` 与 `data/cookies/*.json` 不提交 Git。

同名多义词：

- 自动采集时必须结合书名、作者名、`小说`、`网络小说`、`长篇小说` 等正向信号评分。
- 必须拒绝电视剧、电影、动画、游戏、有声书等非书籍词条。
- 自动消歧不稳定时，允许在 CLI 或批量清单中显式指定 `baike_id` / `baike_url`。
- 显式锚定仍要做标题相关性、书籍 / 网络小说类型和正文有效性校验。

示例：

```bash
python main.py --crawl baike --book 0200000013 --title "庆余年" --baike-id 9592679
```

## 豆瓣 Cookie 规则

- `data/cookies/douban-cookie.txt` 保存用户从浏览器 Network 面板复制的 Cookie 请求头。
- `data/cookies/douban.json` 保存脚本运行中自动续存的 Playwright Cookie。
- 两个文件同时存在时按更新时间合并加载，较新值覆盖旧值。
- 脚本成功访问详情页、短评页、长评页、摘录页或作者页后，应自动续存 Cookie。
- 不得要求用户为每次采集都手动刷新 Cookie。
- 只有重新登录、验证码、账号风控确认或安全挑战这类脚本无法代表用户完成的动作，才需要用户重新协助。

## Staging 规则

`data/staging/{book_id}.json` 是准备入库的候选数据，必须保持可审阅的对象结构。

不得提前序列化为 JSON 字符串的字段：

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

字段来源与冲突写入：

```text
_meta.fieldSources
_meta.conflicts
```

作者、译者、标签、主题、类型等用于关系表的临时合并信息保存在 `_meta`，由入库阶段投影到 `person`、`book_person`、`category`、`book_category`。

## 资源规则

封面下载阶段必须把远程图片下载到：

```text
data/assets/{book_id}/
```

下载完成后必须回写：

```text
images.cover
images.covers
images.assetDir
```

作者头像下载到：

```text
data/assets/{book_id}/people/
```

并回写：

```text
_meta.personDetails[].avatarPath
```

正式入库后资源复制到：

```text
.local/assets/book/{book_id}/
```

staging 中的图片字段不得残留远程 URL 或未本地化对象。入库预检会阻断这种情况。

## 系列规则

采集到的系列信息先放在：

```text
_meta.series
_meta.seriesCandidates
```

正式入库时：

- `_meta.series.name` 存在时，复用或创建 `book_series`。
- 当前书籍写入 `books.series_id`。
- 来源明确给出顺序时写入 `books.series_order`。
- `related.series` 仅作为来源候选和人工核对材料，不替代数据库关系。

已验证：

- 三体三部曲，3 本。
- 冰与火之歌正传，5 本。

## 入库规则

正式入口：

```bash
python import_staging.py --book-id 0200000013
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
- 新书 ID 是数据库下一条 `0200NNNNNN`。
- 已有书刷新时数据库存在同 ID 记录。
- 外部 ID / ISBN 查重。
- 本地资源存在。
- staging 复杂字段未提前 JSON 字符串化。
- 临时数据库导入与外键检查通过。
- `summary` / `story` 不得出现截断省略号污染。
- 摘录不得大量重复。

## 批量规则

当前状态：

- 单本链路稳定。
- 小批量试运行可行。
- 尚不支持无人值守的大批量正式录入。

正式批量能力完成前，不得使用 legacy `db_tools/import_batch.py` 直接批量入库。

未来批量入口必须具备：

```text
manifest
  -> 逐本采集
  -> 单本字段 HTML
  -> 批量质量报告
  -> 分组：可入库 / 需人工确认 / 失败
  -> 只对确认通过项执行 --apply
```

批量 manifest 至少应支持：

```text
title
douban_id
book_id
isbn
book_type
baike_id
baike_url
qidian_title
update_existing
notes
```

## 反爬通用协作流程

当任何公开网页数据源出现验证码、风控页、端侧差异或自动化浏览器看不到用户浏览器内容时：

1. 先记录脚本实际访问地址、最终跳转地址、页面标题、页面长度和关键文本命中情况。
2. 如果用户浏览器能正常看到内容，请用户保存页面 HTML 到 `data/manual/{source}/`。
3. 如果 Cookie 能改善访问状态，请用户导出 Cookie 到 `data/cookies/{source}.json` 或对应 txt。
4. 脚本优先解析本地 HTML 或加载 Cookie。
5. 本地 HTML 和 Cookie 不提交 Git。
6. raw / staging 仍需记录字段来源，避免把人工辅助误写成未经验证来源。

