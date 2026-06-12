# Treasure 项目结构与工作流

Treasure 是一个精选型个人收藏馆项目，用来收录影视、书籍、音乐、游戏等作品。当前核心目标是：在本地完成数据采集、人工校正和结构化入库，再导出为可部署到 GitHub Pages 的 Astro 静态站。

## 总体架构

```text
temp-script/ 数据采集与实验
  -> .local/treasure.db + .local/assets/
  -> tools/db/export-generated.mjs
  -> generated/ + site/public/assets/
  -> site/
  -> GitHub Pages
```

边界原则：

- SQLite 是本地结构化事实源。
- generated 是前台事实源。
- Astro 不直接读取 SQLite。
- Astro 不直接读取 `temp-script/`。
- `temp-script/` 不参与线上构建。
- 发布侧只依赖仓库内静态文件和 `site/public/assets/`。

## 快速定位

| 目标 | 位置 |
|---|---|
| 本地 SQLite 数据库 | `.local/treasure.db` |
| 本地资源主源 | `.local/assets/` |
| Prisma schema | `prisma/schema.prisma` |
| 数据库统计 | `tools/db/check-counts.mjs` |
| generated 与资源导出 | `tools/db/export-generated.mjs` |
| 前台 generated 数据 | `generated/` |
| 前台静态资源 | `site/public/assets/` |
| Astro 站点 | `site/` |
| 本地后台管理 | `admin/` |
| 电影采集工作流 | `temp-script/movie-ingest/` |
| 书籍采集工作流 | `temp-script/book-ingest/` |
| 当前状态快照 | `docs/STATUS.md` |

## 目录职责

### `temp-script/`

职责：

- 放置采集、解析、合并、调试和临时数据处理脚本。
- 产出 raw source snapshots、normalized staging record 和本地下载资源。
- 最终把确认后的作品写入 `.local/treasure.db`。

约束：

- 不直接改写 `generated/`。
- 不直接改写 `site/public/assets/`。
- 不参与 Astro 构建。
- 其中的中间产物、cookie、本地 HTML、raw、staging、assets 多数是本地工作材料，不应被前台直接依赖。

### `.local/`

职责：

- `.local/treasure.db` 是本地结构化主数据库。
- `.local/assets/` 是已入库作品引用的本地资源主源。
- `.local/backup/` 保存入库前备份。

约束：

- `.local/` 不提交 Git。
- 删除或批量改写前必须明确确认。

### `tools/db/`

职责：

- 承担当前 DB 主链路工具。
- `export-generated.mjs` 是唯一正式 DB -> generated / assets 导出入口。
- `check-counts.mjs` 用于快速查看数据库数量。
- 其他 DB 检查脚本可用于结构或资源核验。

约束：

- 不放采集脚本。
- 不放一次性实验脚本。
- 历史工具应进入 `tools/archive/`。

### `generated/`

职责：

- Astro 前台读取的静态 JSON 数据。
- 由 `tools/db/export-generated.mjs` 生成。

约束：

- 不手工编辑。
- 结构变化必须同步更新 `site/src/lib/` 与文档。

当前主要结构：

```text
generated/
  entries/
    video/movie/{id}.json
    book/{id}.json
  indexes/
    video-movie.json
    book.json
    all.json
  persons.json
```

### `site/`

职责：

- Astro 静态站。
- 消费 `generated/` 和 `site/public/assets/`。
- 构建产物部署到 GitHub Pages。

当前路由：

```text
/
/about
/search
/video
/video/movie/{id}
/book
/book/{id}
```

### `admin/`

职责：

- 本地后台管理系统，旁路人工校正工具。
- 直接读写 `.local/treasure.db`。
- 提供比纯字段表更适合人工校正的作品维护界面。

当前方案：

- 使用原生 Node 服务和定制前端。
- 不使用 Directus。
- 默认通过 `npm.cmd run admin` 启动。
- 默认运行在 `http://127.0.0.1:4317`。

边界：

- 不替代采集脚本。
- 不替代 generated 导出。
- 不参与 Astro 构建或 GitHub Pages 发布。
- 当前暂不提供字段级审计日志；如需追溯 before / after，后续应新增本地审计表。

## 数据库与 Prisma

核心表：

```text
works
person
category
work_person
work_category
books
book_series
book_person
book_category
```

策略：

- 关系型表承载人物、分类、系列等可查询关系。
- 展示型复杂字段以 JSON 形式保留，例如评分、外部来源、图片集合、评论、摘录、关联作品。
- Prisma schema 位于 `prisma/schema.prisma`，结构变更必须同步迁移和文档。

ID 规则：

```text
MMSSNNNNNN
```

示例：

```text
0101000001 = 影视 / 电影 / 第 1 条
0200000001 = 书籍 / 当前无子模块 / 第 1 条
```

## 标准工作流

### 采集工作坊阶段

```text
确认作品输入
  -> 多源采集 raw
  -> 合并 normalized staging
  -> 下载并本地化图片、封面、头像等资源
  -> 生成字段核对 HTML
  -> import_staging.py 只读预检
  -> 人工确认
  -> import_staging.py --apply 正式入库
```

要求：

- 预检默认只读，不写主库。
- 正式写库必须显式传入 `--apply`。
- 刷新已有记录必须显式传入 `--update-existing`。
- 入库前必须检查本地资源存在性。
- 不得用验证码页、空壳页、截断页覆盖有效 raw。
- 如果限制数据范围，例如只取前 20 条评论，必须在运行前说明。

### 站点中转阶段

```text
node tools/db/export-generated.mjs
cd site
npm.cmd run build
```

导出脚本负责：

- 从 `.local/treasure.db` 导出 generated JSON。
- 将当前记录引用的 `.local/assets/` 资源复制到 `site/public/assets/`。
- 按作品目录隔离资源；不再导出共享 `site/public/assets/people/`。

## 电影工作流

位置：

```text
temp-script/movie-ingest/
```

当前状态：

- 已稳定跑通单部电影新增与已有电影刷新。
- 正式入口以当前目录内 Python 工作流为准。
- `import_staging.py` 是正式入库 CLI。
- 已清理旧 JS 入库入口和明显过时产物。

已验证样本：

- 《社交网络》：新增电影完整流程。
- 《绿里奇迹》：已有电影完整刷新流程。

关键规则：

- 数据库和 Astro 只保留 `series`、`similar` 两类关联。
- `similar` 当前只使用豆瓣推荐。
- TMDB recommendations / similar 当前不采集、不合并、不入库。
- 多源海报封面主图需要下载并保留为独立封面资源。
- 普通图库、视频封面、人物头像也需要本地化。

## 书籍工作流

位置：

```text
temp-script/book-ingest/
```

当前状态：

- 已跑通普通书、系列书、网络小说的单本和小批量样本。
- 已完成网络小说 fast 批次与 blockedQueue manual fallback 补录验证，当前书籍库为 54 本。
- 当前正式入口是 `main.py` 与 `import_staging.py`。
- `import_staging.py` 默认只预检；`--apply` 才写 `.local/treasure.db`。
- `crawl_basic.py`、`crawl_reviews.py`、`db_tools/`、`sources/` 中不带 `_crawl.py` 的旧爬虫均视为 legacy / 参考入口，不得用于正式入库。

数据源：

```text
douban
openlibrary
baike
wikipedia
goodreads
dangdang
qidian
```

通用规则：

- 豆瓣读书是中文基础资料主源。
- 不得静默跳过豆瓣继续正式入库。
- `summary` 是内容简介。
- `story` 是完整剧情 / 内容情节。
- `year` 是作品首版年；具体版本日期进入 `publishDate`。
- `excerpts` 为原文摘录，内容字段只保留原文，不保留昵称、回复数、点赞数、日期等互动信息。
- 书评、短评、摘录当前限制为每类最多 20 条；这不是全量采集。

普通书规则：

- `summary` 优先取 Wikipedia 的“故事大纲”分节。
- `story` 优先取百度百科“内容情节”等正文分节。

网络小说规则：

- `summary` 不使用 Wikipedia，优先起点或豆瓣。
- `story` 使用百度百科词条顶部正文。
- 除原文名、外文别名、评论原文外，正式前台展示字段不得录入英文候选值。
- 类型标签必须是中文。
- 起点用于补充标题、作者、字数、连载状态、分类、标签、简介、封面。

百度百科规则：

- 同名词条先自动消歧，拒绝电视剧、电影、动画、游戏、有声书等非书籍词条。
- 可显式传入 `baike_id` / `baike_url` 锚定词条，但脚本仍需做标题和书籍类型校验。
- 触发验证时可使用用户保存的 `data/manual/baike/*.html` 或 `data/cookies/baike.json`。
- 不得用验证码页、空壳页、SEO 截断页覆盖有效 raw。

豆瓣 Cookie 规则：

- 用户可从浏览器 Network 面板复制 Cookie 到 `data/cookies/douban-cookie.txt`。
- 脚本成功访问后会自动续存 `data/cookies/douban.json`。
- 两者同时存在时按更新时间合并，较新值覆盖旧值。
- 只有重新登录、验证码、账号风控确认等必须在用户浏览器中完成的动作，才需要用户再次协助。

资源规则：

```text
采集阶段：
temp-script/book-ingest/data/assets/{book_id}/cover-main.jpg
temp-script/book-ingest/data/assets/{book_id}/covers/{source}.jpg
temp-script/book-ingest/data/assets/{book_id}/people/{person_id}-avatar.jpg

入库后：
.local/assets/book/{book_id}/cover-main.jpg
.local/assets/book/{book_id}/covers/{source}.jpg
.local/assets/book/{book_id}/people/{person_id}-avatar.jpg

发布侧：
site/public/assets/book/{book_id}/...
```

书籍批量状态：

- 当前已具备受控 fast 批次能力：manifest、批量质量报告、blockedQueue、approval apply、generated 导出和 Astro 构建均已跑通。
- 尚不适合无人值守的大批量正式录入；错配、无 raw、反爬、简介截断等仍必须进入 blockedQueue 或 manual fallback。
- manual fallback 只能作为 staging 级补录方式，不等于新增正式自动数据源。

## 前台 UI 方向

整体：

- Treasure 是资料馆气质 + 现代浏览体验，不是全量资源站、博客或营销页。
- 首页负责全站气质、模块入口和适度内容预览。
- 模块列表页负责浏览、筛选、搜索、分页和进入详情。
- 详情页负责展示单条作品的完整结构化资料。

电影：

- 列表页支持卡片 / 列表视图。
- 详情页突出海报、评分、演职员、剧情、图片、视频、评论和关联作品。

书籍：

- 视觉方向参考微信读书的纯白阅读感。
- 列表页使用清爽信息流，展示封面、书名、作者、年份、国家、简介、类型和评分。
- 详情页采用阅读型结构，展示封面、评分、基础信息、内容简介、内容情节、摘录、评论、多源封面、外部来源、系列作品等。
- 长评论和摘录必须避免横向溢出，右侧信息区不得覆盖正文内容。

## 发布前校验

至少确认：

- `node tools/db/check-counts.mjs` 数量符合预期。
- `node tools/db/export-generated.mjs` 成功。
- generated 详情数量与索引数量一致。
- 详情 JSON 能被对应索引覆盖。
- 关键字段如 `id`、`title`、`year`、`module` 与数据库一致。
- 当前记录引用的资源能在 `site/public/assets/` 找到，或前台有明确占位图兜底。
- `cd site && npm.cmd run build` 成功。

## 当前下一步

下一阶段回到电影作品录入。电影模块仍使用既有稳定单部工作流，新增或刷新作品时继续保持：

```text
确认电影输入
  -> 多源采集 raw
  -> 合并 normalized staging
  -> 图片 / 视频封面 / 人物头像本地化
  -> 字段 HTML 核对
  -> import_staging.py 只读预检
  -> 人工确认
  -> import_staging.py --apply 正式入库
  -> 导出 generated
  -> 构建 Astro
```

书籍模块暂时进入维护状态；如继续扩大书籍批量，必须保留 manifest、approval、apply-result 和 blockedQueue。
