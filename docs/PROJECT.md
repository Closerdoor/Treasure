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
    video/documentary/{id}.json
    video/tv_series/{id}.json
    anime/anime_movie/{id}.json
    anime/anime_series/{id}.json
    book/{id}.json
  indexes/
    video.json
    video-movie.json
    video-documentary.json
    video-tv_series.json
    anime.json
    anime-anime_movie.json
    anime-anime_series.json
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
/video/documentary/{id}
/video/tv_series/{id}
/anime
/anime/anime_movie/{id}
/anime/anime_series/{id}
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

分类与标签：

- `category.group = type` 表示作品类型 / 题材，主要来自数据源，例如剧情、犯罪、动画、科幻。
- `category.group = tag` 表示馆内自定义标签，用于策展、批次、专题和人工归类，例如 `豆瓣TOP250`。
- `type` 可按 `module` / `submodule` 建立作用域；`tag` 默认可保持全局作用域，除非某个标签明确只服务于单一模块。
- 前台 generated 会把两者分别导出为 `genre` 与 `tags`，不得把自定义标签混入数据源类型。

ID 规则：

```text
MMSSNNNNNN
```

示例：

```text
0101000001 = 影视 / 电影 / 第 1 条
0103000001 = 影视 / 纪录片 / 第 1 条
0200000001 = 书籍 / 当前无子模块 / 第 1 条
0301000001 = 动漫 / 动画电影 / 第 1 条
```

当前一级模块编号：

```text
01 = 影视
02 = 书籍
03 = 动漫
04 = 音乐
05 = 游戏
```

注意：动漫是一级模块，和影视同级；`anime_movie`、`anime_series` 属于动漫模块下的子模块，不属于影视子模块。

纪录片是 `video` 下的一个统一子模块，不拆成纪录片电影和纪录片剧集两个公开分类。采集与入库时可用内部 `schemaType` 区分字段形态：

```text
documentary_film = 纪录片，电影形态，无集数字段要求
documentary_series = 纪录片，剧集形态，必须带 episodeCount，并把 episodesStory 作为正式采集字段
```

## 标准工作流

### 工作流总览

| 工作流 | 状态 | 入口 | 完成条件 |
|---|---|---|---|
| DB -> generated -> Astro | 已稳定 | `tools/db/export-generated.mjs` | 导出成功、索引数量匹配、Astro 构建成功 |
| 媒体单部新增 | 已稳定 | `temp-script/movie-ingest/main.py` + `import_staging.py` | staging 预检通过、用户确认、`--apply` 写库、导出和构建成功 |
| 媒体已有作品刷新 | 已稳定 | `import_staging.py --update-existing` | 同 ID 匹配、无其他疑似匹配、预检通过、备份后写库 |
| 媒体混合批量录入 | 已完成受控批量流程 | agent-assisted preflight + `batch_validate.py` | 预审分组明确、候选消歧完成、通过项 100% 有报告、审核后写库 |
| 剧集 / 番剧增强字段回填 | 已通过首批样本 | `backfill_enhancements.py` | `episodesStory` 覆盖 `1..episodeCount`，番剧 / 多季动画具备 `characters` |
| 书籍单本录入 | 已稳定 | `temp-script/book-ingest/main.py` + `import_staging.py` | raw、staging、资源、字段报告、预检和写库闭环完成 |
| 网络小说批量 fast / manual fallback | 已完成受控批次验证 | `batch_runner.py` + `batch_apply.py` | manifest、质量分组、blockedQueue、approval apply、导出和构建完成 |
| 本地人工校正 | 已建立旁路工具 | `npm.cmd run admin` | 仅用于人工维护 `.local/treasure.db`，不替代采集 / 导出 |

### 采集工作坊阶段

```text
确认作品输入
  -> manifest 记录原始输入
  -> 预审查重、类型判断、数据源候选消歧
  -> 需要时输出清单给用户二次确认
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
- 批量录入必须先生成预审报告，至少标出总量、已入库匹配、可采集条目、缺少数据源线索或候选不确定条目。
- 批量预审必须是 agent-assisted preflight：脚本只负责查重、格式校验、候选收集和报告结构；最终预审结论必须由 Codex 结合网络搜索结果、数据源页面内容、现有 DB、作品类型、年份、主创和用户输入语境综合判断。
- 不得把固定脚本的 `ready` 状态直接等同于“可以入库”；`ready` 只能表示机械校验暂未发现问题，还必须经过 agent / LLM 复核后才能进入采集或入库。
- 同名、多版本、多季、多媒介改编作品如果无法靠年份、主创、数据源 ID 明确消歧，必须先列出候选让用户确认。
- 预审必须校验数据源身份和地址稳定性；已搜索到的数据源候选必须能通过标题 / 年份 / 类型 / 主创 / 数据源 ID 的强校验后，才允许进入采集和入库。
- 百度百科正式 source hint 必须优先使用带数字词条 ID 的精确 URL，例如 `/item/词条名/123456`；只有 `/item/词条名` 的泛化链接不得作为已确认正式来源。
- 正式写库必须显式传入 `--apply`。
- 刷新已有记录必须显式传入 `--update-existing`。
- 入库前必须检查本地资源存在性。
- 不得用验证码页、空壳页、截断页覆盖有效 raw。
- 如果限制数据范围，例如只取前 20 条评论，必须在运行前说明。

### 交接与清理要求

- 新对话进入项目时只把 `docs/README.md`、`docs/PROJECT.md`、`docs/STATUS.md` 视为当前规范入口。
- `temp-script/*/data/` 下未写入数据库、未被当前报告引用、且 ID 超出当前数据快照范围的 raw / staging / assets 只能作为临时产物，不得当作当前事实源。
- 旧提示、临时讨论、过期批次报告不得放在仓库根目录；需要保留历史时归档到 `docs/archive/`，否则清理。
- legacy 脚本可以作为参考保留，但必须在文档中标明不得作为正式入口；新增正式入口必须同步写入本节工作流总览。

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

## 媒体作品工作流

位置：

```text
temp-script/movie-ingest/
```

当前状态：

- 已稳定跑通单部真人电影新增与已有电影刷新。
- 已接入媒体作品 profile 层，用同一套入口区分真人电影、纪录片、动画电影、电视剧、番剧 / 多季动画；纪录片公开分类不拆分，内部按电影 / 剧集采集形态区分字段要求。
- 正式入口以当前目录内 Python 工作流为准。
- `import_staging.py` 是正式入库 CLI。
- 已清理旧 JS 入库入口和明显过时产物。

已验证样本：

- 《社交网络》：新增电影完整流程。
- 《绿里奇迹》：已有电影完整刷新流程。

关键规则：

- 新增普通电影默认写入 `video/movie/live_action_movie`。
- 混合批量录入前必须先确定或推断 `schemaType`；用户未提供类型时，先输出待核对清单，确认后再正式入库。
- 混合批量录入的预审报告必须单独标出 `source_hint_invalid`、`source_validation_failed` 等来源问题；这些条目不得进入正式写库。
- 纪录片和动画电影必须显式指定目标分类：纪录片统一写入 `video/documentary`，动画电影写入 `anime/anime_movie/animated_movie`。
- 电视剧写入 `video/tv_series/live_action_series`。
- 纪录片如果是剧集形态，内部 `schemaType` 使用 `documentary_series`，并必须具备 `episodeCount`。
- 番剧 / 多季动画写入 `anime/anime_series/animated_series`。
- 动漫是一级模块，不得再按影视子模块写入。
- 剧集类作品必须具备 `episodeCount`，并把 `episodesStory` 作为正式采集字段；如果当前自动来源暂时无法取得，必须进入增强队列或在入库前明确记录例外，不能静默当作完整记录。
- 番剧 / 多季动画除 `episodeCount` 和 `episodesStory` 外，还必须把 `characters` 作为正式采集字段；缺失时同样进入增强队列或明确记录例外。
- `episodesStory` 当前优先由豆瓣 `/subject/{doubanId}/episode/{n}/` 按集采集；无 `episodeCount` 时不得猜测页数。豆瓣缺正文时，可使用已有正式 TMDB TV 分集接口和百度百科 fallback 补齐。
- `characters` 当前优先由豆瓣 `/celebrities` 的“演员饰演角色”结构生成，百度百科 `credits.cast` / 角色模块和 TMDB TV aggregate credits 只作为已有正式数据源内的兜底。
- 百度百科 fallback 已支持从“分集剧情 / 每集剧情 / 剧集列表”等章节、动态分集分页、`data-module-value` 内嵌 JSON 和角色模块解析 `episodesStory`、`characters`；这些字段不得设置前 N 条采样上限，也不得裁剪正文长度。
- 百度百科 fallback 如果使用用户提供的精确词条 URL / ID，采集失败时不得静默回退到标题搜索结果；验证页、空壳页和泛化百科页必须拒绝写入 raw，避免覆盖有效快照。
- `import_staging.py` 预检会阻断百科缺数字 ID、百科 URL 与 `baikeId` 不一致、豆瓣 / IMDb / TMDB ID 格式异常等来源问题；不得绕过该预检直接写库。
- 剧集增强回填按当前作品 `episodeCount` 控制入库范围；采集 raw 不截断，但越界集数不得进入 staging。`import_staging.py` 预检要求 `episodesStory` 正好覆盖 `1..episodeCount`。
- `import_staging.py` 默认会把剧集 / 番剧增强字段缺失列入预检问题；只有显式传入 `--allow-enhancement-missing` 才允许作为记录过的例外继续。
- 数据库和 Astro 只保留 `series`、`similar` 两类关联。
- `similar` 当前只使用豆瓣推荐。
- TMDB recommendations / similar 当前不采集、不合并、不入库。
- 多源海报封面主图需要下载并保留为独立封面资源。
- 普通图库、视频封面、人物头像也需要本地化。

媒体 profile：

| schemaType | 中文类型 | module/submodule | ID 前缀 | 采集形态 |
|---|---|---|---|---|
| `live_action_movie` | 真人电影 | `video/movie` | `0101` | 电影 |
| `documentary_film` | 纪录片 | `video/documentary` | `0103` | 电影 |
| `animated_movie` | 动画电影 | `anime/anime_movie` | `0301` | 电影 |
| `live_action_series` | 电视剧 | `video/tv_series` | `0102` | 剧集 |
| `documentary_series` | 纪录片 | `video/documentary` | `0103` | 剧集 |
| `animated_series` | 番剧 / 多季动画 | `anime/anime_series` | `0302` | 剧集 |

CLI 示例：

```bash
python temp-script/movie-ingest/main.py --movie-name "作品名" --schema-type animated_movie
python temp-script/movie-ingest/import_staging.py --work-id 0302000001 --schema-type animated_series
```

当前能力边界：

- 电影形态的真人电影、纪录片、动画电影可复用已验证的单部流程。
- 数据库、generated、Astro 前台已经支持剧集字段和 `tv_series` / `anime_series` 索引与详情路由。
- 剧集 / 番剧的数据源适配已通过首批样本验证基础入库链路，并已补充分集剧情 / 角色介绍的首版采集与预检逻辑；2026-06-14 增强队列实采回填完成 6/6，其中《西游记后传》通过百度百科精确词条 `/2833885` 的动态分集分页补齐 30/30 集分集剧情。后续批量可继续使用该工作流，但缺增强字段的条目必须阻断或进入队列。

### 存量分类迁移

2026-06-12 已完成豆瓣电影 250 存量分类迁移：

- 40 部动画电影从 `video/movie` 迁移到 `anime/anime_movie`，新 ID 为 `0301000001` 至 `0301000040`。
- 《海豚湾》从 `video/movie` 迁移到 `video/documentary`，新 ID 为 `0103000001`。
- 迁移按旧 ID 升序分配新 ID。
- 旧 ID 已废弃，不做兼容路由或冗余映射；后续新增电影继续使用电影子模块的新 ID。
- `.local/assets/` 与发布侧资源目录同步按新模块 / 子模块拆分。

2026-06-13 已为豆瓣 TOP250 存量批次补充自定义标签：

- 新增 / 复用 `category.group = tag`、`name = 豆瓣TOP250`。
- 关联 250 条 TOP250 存量作品，其中真人电影 209、纪录片 1、动画电影 40。
- 后续单部样本《社交网络》（`0101000251`）不属于该批次，未关联此标签。
- generated 详情、列表索引和 `generated/tags.json` 均会导出该标签。

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
- generated 详情数量与索引数量一致：当前影视电影、影视纪录片、动漫动画电影、书籍均分别有独立索引。
- 详情 JSON 能被对应索引覆盖。
- 关键字段如 `id`、`title`、`year`、`module` 与数据库一致。
- 当前记录引用的资源能在 `site/public/assets/` 找到，或前台有明确占位图兜底。
- `cd site && npm.cmd run build` 成功。

## 当前下一步

下一阶段继续完善媒体作品批量录入。电影形态作品继续使用既有稳定单部工作流，新增或刷新普通电影时保持：

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

混合批量录入前必须先做查重、分型、候选消歧和字段质量预检；剧集 / 番剧还必须补齐或记录 `episodesStory`、`characters` 等增强字段缺口。书籍模块暂时进入维护状态；如继续扩大书籍批量，必须保留 manifest、approval、apply-result 和 blockedQueue。
