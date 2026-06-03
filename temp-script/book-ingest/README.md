# 书籍作品采集工作流

`temp-script/book-ingest` 是 Treasure 书籍作品的本地采集工作坊。它的职责边界止于写入 `.local/treasure.db`；入库后的 generated 导出、Astro 页面、站点构建和发布校验属于仓库根目录主链路。

当前书籍模块已经完成普通书、系列书、网络小说样本的端到端验证，并已接入 Astro 前台 `/book` 与 `/book/{id}`。当前仍未完成的是“稳定的大批量无人值守录入”；现在适合每批 5-10 本的小批量试运行。

## 当前标准流程

```text
确认作品输入
  -> 多数据源采集 raw
  -> 合并 normalized staging
  -> 下载封面和作者头像并回写 staging
  -> 生成字段核对 HTML
  -> import_staging.py 只读预检和临时库演练
  -> 人工确认
  -> 显式 --apply 后写入 .local/treasure.db
  -> 回到仓库根目录导出 generated 并构建 Astro
```

## 当前数据源

正式采集入口使用 7 个数据源：

```text
douban
openlibrary
baike
wikipedia
goodreads
dangdang
qidian
```

用途概览：

| 数据源 | 当前用途 |
|---|---|
| 豆瓣读书 | 中文标题、ISBN、出版信息、简介、评分、作者/译者、短评、长评、摘录、推荐、封面 |
| OpenLibrary | 英文原名、ISBN、作者、首版年、主题、评分、封面 |
| 百度百科 | 中文补充信息、首版年、字数、语言、国家、作者、顶部正文或内容情节 |
| Wikipedia | 普通书的故事大纲、原名、国家、语言、出版信息、封面 |
| Goodreads | 海外评分、英文标题、作者、系列、书评、相似作品、封面 |
| 当当 | ISBN、出版社、字数、页数、价格、出版日期、简介、封面 |
| 起点 | 网络小说标题、作者、字数、连载状态、分类、标签、简介、封面 |

限制：

- `REVIEWS_PER_SOURCE = 20`，当前短评、长评、Goodreads 书评、豆瓣摘录均按最多 20 条处理。
- 这不是全量评论采集规则；如需全量采集，必须先确认范围、排序、页数和反爬风险。

## 目录职责

```text
book-ingest/
├── main.py                 # 当前主入口：采集、合并、下载、预检调度
├── import_staging.py       # 正式 staging 预检与入库 CLI
├── merger.py               # 多源合并，生成 normalized staging
├── database.py             # 写入 books/person/book_person/category/book_category/book_series
├── progress.py             # 豆瓣 ID 与内部 book_id 的进度映射
├── config.py               # 数据源、延迟、数量限制、ID 前缀配置
├── sources/*_crawl.py      # 当前 main.py 使用的数据源爬虫
├── downloaders/            # 封面和头像下载器
├── tools/field_report.py   # 字段核对 HTML 生成器
├── data/raw/               # 原始来源快照
├── data/staging/           # 准备入库的结构化候选记录
└── data/assets/            # 采集阶段下载的本地资源
```

Legacy / 参考入口：

```text
crawl_basic.py
crawl_reviews.py
db_tools/
sources/ 中不带 _crawl.py 的旧爬虫
```

这些旧入口不得作为正式入库路径使用，尤其是 `db_tools/import_batch.py` 会绕过当前 `import_staging.py` 预检体系。

## 常用命令

在 `temp-script/book-ingest` 目录下执行。

```bash
# 采集全部当前数据源；--book 使用豆瓣读书 subject id
python main.py --crawl all --book 1008145 --title "围城"

# 百度百科同名多义词可显式锚定词条；脚本仍会二次校验
python main.py --crawl baike --book 0200000013 --title "庆余年" --baike-id 9592679
python main.py --crawl baike --book 0200000013 --title "庆余年" --baike-url "https://baike.baidu.com/item/庆余年/9592679"

# 合并 raw 为 staging；--book 使用内部 book_id
python main.py --merge --book 0200000013

# 下载封面和作者头像，并把实际文件名回写 staging
python main.py --download --book 0200000013

# 只读预检：查重、资源、本地化、staging 形态、临时 DB 演练和外键检查
python import_staging.py --book-id 0200000013 --update-existing

# 生成字段核对 HTML
python tools/field_report.py --book-id 0200000013

# 预检通过后正式写入主数据库
python import_staging.py --book-id 0200000013 --update-existing --apply
```

回到仓库根目录后：

```bash
node tools/db/export-generated.mjs
cd site
npm.cmd run build
```

## 字段规则

核心字段：

- `year`：作品首版年份，优先百度百科首版年；具体录入版本日期放入 `publishDate`。
- `summary`：内容简介。
- `story`：完整剧情 / 内容情节。
- `genre` / `_meta.genres`：书籍类型，必须是中文。
- `excerpts`：原文摘录，只保留原文内容；章节、页码可进 `note`；互动信息不得进入 `content`。

普通书：

- `summary` 优先取 Wikipedia 的“故事大纲”分节。
- `story` 优先取百度百科“内容情节”等正文分节。

网络小说：

- `summary` 不使用 Wikipedia，优先起点或豆瓣。
- `story` 使用百度百科词条顶部正文。
- 除原文名、外文别名、评论原文外，正式前台展示字段不得录入英文候选值。
- 起点是网络小说的重要补充源。

## 资源规则

采集阶段：

```text
data/assets/{book_id}/cover-main.jpg
data/assets/{book_id}/covers/{source}.jpg
data/assets/{book_id}/people/{person_id}-avatar.jpg
```

入库后：

```text
.local/assets/book/{book_id}/cover-main.jpg
.local/assets/book/{book_id}/covers/{source}.jpg
.local/assets/book/{book_id}/people/{person_id}-avatar.jpg
```

发布侧：

```text
site/public/assets/book/{book_id}/...
```

约定：

- `images.cover` 是主封面文件名。
- `images.covers` 是各数据源封面映射。
- `_meta.personDetails[].avatarPath` 是作者头像本地路径。
- 入库预检会阻止远程 URL、缺失本地文件或提前 JSON 字符串化的复杂字段进入主库。

## 反爬协作规则

百度百科：

- 脚本优先解析 `data/manual/baike/*.html` 中用户保存的页面。
- 没有本地 HTML 时，可加载 `data/cookies/baike.json`。
- 遇到验证码页、空壳页、SEO 截断页时不得覆盖有效 raw。

豆瓣读书：

- 用户可从浏览器 Network 面板复制 Cookie 请求头到 `data/cookies/douban-cookie.txt`。
- 脚本成功访问后自动续存 Playwright Cookie 到 `data/cookies/douban.json`。
- 两个 Cookie 文件同时存在时按更新时间合并，较新值覆盖旧值。
- 只有重新登录、验证码、账号风控确认等必须由用户在浏览器中完成的动作，才需要用户再次协助。

通用：

- 先记录脚本实际访问地址、最终跳转地址、页面标题、页面长度和关键文本命中情况。
- 如果用户浏览器能正常看到内容，可让用户保存 HTML 或导出 Cookie，再由脚本解析本地快照或加载 Cookie。
- 本地 HTML 和 Cookie 是辅助材料，不提交 Git。

## 系列规则

- 采集阶段的系列候选保存在 `_meta.series` 和 `_meta.seriesCandidates`。
- 正式入库时，`database.py` 会复用或创建 `book_series`，并写入 `books.series_id`。
- `books.series_order` 只在来源明确给出顺序时填写。
- `related.series` 只作为来源候选和人工核对材料，不替代数据库关系。

已验证样本：

- 三体三部曲：3 本，顺序 1/2/3。
- 冰与火之歌正传：5 本，顺序 1/2/3/4/5。

## 批量能力状态

当前结论：

- 单本完整链路稳定。
- 5-10 本小批量试运行可行。
- 尚不适合无人值守的大批量正式录入。

原因：

- 缺少正式 `batch manifest`。
- 旧 `db_tools/import_batch.py` 仍是 legacy，不能用于正式入库。
- 豆瓣、百度百科、当当、起点、Goodreads 都可能触发反爬。
- 缺少批量质量报告和“可入库 / 需人工确认 / 失败”分组。

下一步应新增正式批量编排层：

```text
batch manifest
  -> 逐本运行单本链路
  -> 每本字段 HTML
  -> 批量质量摘要
  -> 人工确认
  -> 只对确认通过项执行 --apply
```

