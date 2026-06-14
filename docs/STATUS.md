# Treasure 当前状态

最近校验时间：2026-06-14

当前项目处于 **DB-first 静态站闭环整理阶段**。电影模块已经完成稳定单部工作流，并已扩展为通用媒体作品 profile 工作流；书籍模块已经完成普通书、系列书、网络小说样本的端到端验证，并已接入 Astro 前台页面。书籍批量编排层已经完成网络小说 fast 流程与 blockedQueue manual fallback 补录验证：manifest 记录、批量采集、质量分组、人工 fallback staging、approval apply、generated 导出和 Astro 构建均已跑通。2026-06-12 已完成豆瓣电影 250 存量分类迁移：动漫确认为一级模块，40 部动画电影迁移到 `anime/anime_movie`，1 部纪录片迁移到 `video/documentary`。2026-06-13 已为该 TOP250 存量批次补充自定义标签 `豆瓣TOP250`。2026-06-13 首批混合媒体样本已正式入库 12 条，并完成 generated 导出和 Astro 构建；2026-06-14 已完成 6 条增强队列实采回填，6 条全部补齐并正式写库，其中《西游记后传》通过百度百科精确词条 `/2833885` 的动态分集分页补齐 30/30 集分集剧情。

当前交接结论：

- 本批混合媒体作品录入已完成：用户输入 14 条，2 条已在库跳过，12 条新作品正式入库，增强字段缺口 0。
- 通用媒体录入工作流已完成到可用于下一批受控批量录入的状态，覆盖电影、纪录片、动画电影、电视剧、番剧 / 多季动画。
- 下一批正式入库前仍必须先做 agent-assisted preflight：Codex 结合网络搜索、数据源页面、现有 DB、用户输入语境和脚本报告综合判断候选身份；固定脚本的 `ready` 不能直接视为可入库。
- `.local/treasure.db` 和 `.local/assets/` 仍是本地事实源，不提交 Git；`generated/` 与 `site/public/assets/` 由导出脚本重建。

## 数据库快照

运行命令：

```bash
node tools/db/check-counts.mjs
```

结果：

| 表 | 数量 | 说明 |
|---|---:|---|
| `works` | 263 | 影视 218 条（电影 213、纪录片 3、电视剧 2）+ 动漫 45 条（动画电影 43、番剧 2） |
| `person` | 11943 | 公共人物表 |
| `category` | 149 | 公共分类 / 标签 |
| `work_person` | 13398 | 影视 / 动漫人物关系 |
| `work_category` | 992 | 影视 / 动漫分类关系 |
| `books` | 54 | 书籍记录，当前均为 `draft` |
| `book_series` | 2 | 书籍系列 |
| `book_person` | 64 | 书籍人物关系 |
| `book_category` | 206 | 书籍分类关系 |

## Generated 快照

最近导出命令：

```bash
node tools/db/export-generated.mjs
```

当前导出结果：

| 项目 | 数量 |
|---|---:|
| `generated/entries/video/movie/*.json` | 213 |
| `generated/indexes/video-movie.json` | 213 |
| `generated/entries/video/documentary/*.json` | 3 |
| `generated/indexes/video-documentary.json` | 3 |
| `generated/entries/video/tv_series/*.json` | 2 |
| `generated/indexes/video-tv_series.json` | 2 |
| `generated/indexes/video.json` | 218 |
| `generated/entries/anime/anime_movie/*.json` | 43 |
| `generated/indexes/anime-anime_movie.json` | 43 |
| `generated/entries/anime/anime_series/*.json` | 2 |
| `generated/indexes/anime-anime_series.json` | 2 |
| `generated/indexes/anime.json` | 45 |
| `generated/entries/book/*.json` | 54 |
| `generated/indexes/book.json` | 54 |
| `generated/indexes/all.json` | 317 |
| `generated/persons.json` | 11943 |

资源导出最近结果：

| 资源项 | 结果 |
|---|---|
| 作品资源 | copied=4598, missing=1 |
| 人物头像 | copied=9103, missing=4171 |
| 共享人物资源目录 | 不再导出 |

说明：

- 作品资源仍有 1 条历史缺口，后续按作品审视时清理。
- 人物头像缺口主要来自历史存量人物资源，不阻断当前前台渲染；前台使用头像占位图回退。
- 新增书籍流程中，封面和作者头像会在入库前通过 `import_staging.py` 预检本地文件存在性。

## Astro 构建状态

最近构建命令：

```bash
cd site
npm.cmd run build
```

结果：

```text
构建成功
生成页面：323
```

当前已落地路由：

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

当前可本地启动：

```bash
cd site
npm.cmd run dev -- --host 127.0.0.1
```

## 已完成任务项

### 项目主链路

- 已确立 DB-first 静态站流程：`.local/treasure.db -> generated/ + site/public/assets/ -> Astro`。
- 已确认 Astro 不直接读取 SQLite，也不直接依赖 `temp-script/`。
- 已统一 generated 与资源导出入口为 `tools/db/export-generated.mjs`。
- 已移除或弃用旧的站点侧资源同步入口，日常只使用根目录导出命令。
- 已建立本地后台管理应用 `admin/`，作为旁路人工校正工具；Directus 方案已放弃。

### 电影模块

- 已完成 `movie-ingest` 单部电影稳定工作流。
- 已完成豆瓣电影 250 存量分类迁移：
  - 40 部动画电影迁移到一级模块 `anime/anime_movie/animated_movie`，新 ID 为 `0301000001` 至 `0301000040`。
  - 《海豚湾》迁移到 `video/documentary/documentary_film`，新 ID 为 `0103000001`。
  - 迁移按旧 ID 升序分配新 ID；旧 ID 已废弃，不做兼容路由。
  - 资源目录已同步迁移到 `.local/assets/anime/anime_movie/` 和 `.local/assets/video/documentary/`。
- 已修正旧 ID 生成逻辑：动漫是一级模块，和影视同级，不再作为影视子模块。
- 已补充豆瓣 TOP250 自定义标签：
  - 新增 `tag: 豆瓣TOP250`，关联 250 条 TOP250 存量作品。
  - 分布为真人电影 209、纪录片 1、动画电影 40。
  - 后续单部样本《社交网络》（`0101000251`）未关联该标签。
  - generated 详情、列表索引和 `generated/tags.json` 已导出该标签。
- 已补齐混合媒体作品录入的 profile 层：
  - `live_action_movie` 写入 `video/movie`，ID 前缀 `0101`。
  - `documentary_film` 写入 `video/documentary`，ID 前缀 `0103`；对外仍展示为“纪录片”。
  - `animated_movie` 写入 `anime/anime_movie`，ID 前缀 `0301`。
  - `live_action_series` 写入 `video/tv_series`，ID 前缀 `0102`。
  - `documentary_series` 写入 `video/documentary`，ID 前缀 `0103`；对外仍展示为“纪录片”，但必须携带集数信息。
  - `animated_series` 写入 `anime/anime_series`，ID 前缀 `0302`。
  - 剧集字段 `episodeCount`、`episodeTime`、`episodesStory`、`characters` 已进入数据库写入、generated 导出和 Astro 详情展示。
- 已完成 2026-06-13 混合媒体样本批量验证、用户审核确认和正式入库：
  - 输入 14 条，预审发现 2 条已入库：《白日梦想家》《大鱼》。
  - 剩余 12 条进入采集验证；初次运行时 7 条通过、5 条因豆瓣详情页未返回有效标题 / 年份被预检拦下。
  - 验证码 / 反爬状态缓解后断点重试，12 条采集条目全部通过 staging 预检，0 条失败。
  - 正式入库项：3 部真人电影《钢铁侠》《钢铁侠2》《钢铁侠3》，2 部剧集形态纪录片《地球脉动 第一季》《河西走廊》，3 部动画电影《声之形》《颠倒的帕特玛》《星之梦~星之人》，2 部电视剧《神探狄仁杰》《西游记后传》，2 部番剧《食灵零》《反叛的鲁路修》。
  - 新增 ID：`0101000252`、`0101000253`、`0101000254`、`0103000002`、`0103000003`、`0301000041`、`0301000042`、`0301000043`、`0102000001`、`0102000002`、`0302000001`、`0302000002`。
  - 纪录片样本均归入 `video/documentary`，其中《地球脉动》解析出 `episodeCount=11`，《河西走廊》解析出 `episodeCount=10`。
  - 电视剧样本解析出《神探狄仁杰》`episodeCount=30`、`episodeTime=45`，《西游记后传》`episodeCount=30`、`episodeTime=40`。
  - 番剧样本解析出《食灵零》`episodeCount=12`、`episodeTime=24`，《反叛的鲁路修》`episodeCount=25`、`episodeTime=24`。
  - 验证覆盖率：剔除已入库项后通过 12/12 = 100.0%；全量输入中 12/14 采集通过、2/14 已入库跳过；14/14 均已形成报告，12/12 通过项已写入主库。
  - 已生成审核预览：`temp-script/movie-ingest/data/batch-runs/2026-06-13-media-validation/audit-preview.html`。
  - 已记录增强队列：`temp-script/movie-ingest/data/batch-runs/2026-06-13-media-validation/enhancement-queue.json`，共 6 条；剧集类缺 `episodesStory`，番剧额外缺 `characters`。
- 已补齐剧集 / 番剧增强字段首版逻辑：
  - 豆瓣采集新增 `/subject/{doubanId}/episode/{n}/` 分集剧情逐集抓取；无 `episodeCount` 时不猜测页数。
  - 合并层会把豆瓣 `episodes` 写入 staging `episodesStory`。
  - 合并层会从豆瓣 `/celebrities` 的“饰演角色”生成 `characters`，百度百科 `credits.cast` 和 TMDB credits 作为已有正式来源兜底。
  - 百度百科采集会从“分集剧情 / 每集剧情 / 剧集列表”等章节、`data-module-value` 内嵌 JSON 和角色模块解析 `episodes_story`、`characters`。
  - `episodesStory` 和 `characters` 不允许设置前 N 条采样上限，不裁剪正文长度；采不到则量化缺口并进入增强队列。
  - `import_staging.py` 默认把剧集 / 番剧缺 `episodesStory`、番剧缺 `characters` 列为预检问题；显式 `--allow-enhancement-missing` 才能作为例外通过。
  - `batch_validate.py` 报告新增 `episodesStoryCount`、`charactersCount` 和 `enhancementProblems`。
- 已完成 2026-06-13 增强队列实采回填：
  - 回填总量 6 条，正式写库 6 条，完成率 100.0%。
  - 已补齐并写库：《地球脉动 第一季》11/11 集分集剧情、1 个角色；《河西走廊》10/10 集分集剧情、11 个角色；《神探狄仁杰》30/30 集分集剧情、46 个角色；《西游记后传》30/30 集分集剧情、20 个角色；《食灵零》12/12 集分集剧情、8 个角色；《反叛的鲁路修》25/25 集分集剧情、58 个角色。
  - 《西游记后传》使用百度百科精确词条 `/2833885` 作为 source hint，采集逻辑会点击“分集剧情”动态分页并逐段解析，避免只读初始 DOM 时漏掉后续集数。
  - 百度百科增强采集会拒绝验证页、空壳页和泛化百科页；如果用户提供的精确词条 URL 失败，不再静默回退到标题搜索结果。
  - TMDB 已补充 TV 搜索、TV 详情、单季分集、TV 聚合演职员接口；回填 raw 快照保留完整采集结果。
  - 合并层按当前作品 `episodeCount` 过滤入库范围，越界分集只记录在报告中，不进入 staging；预检要求 `episodesStory` 正好覆盖 `1..episodeCount`。
  - 报告位置：`temp-script/movie-ingest/data/batch-runs/2026-06-13-media-validation/enhancement-backfill-report.json`、`temp-script/movie-ingest/data/batch-runs/2026-06-13-media-validation/enhancement-apply-report.json`、`temp-script/movie-ingest/data/batch-runs/2026-06-13-media-validation/xiyouji-houchuan-apply-report.json`。
- 已以《社交网络》跑通新增电影：多源采集、图片本地化、字段核对、合并、预检、正式入库、导出、Astro 渲染。
- 已以《绿里奇迹》跑通已有电影刷新：重新采集、`--update-existing` 预检、正式覆盖入库、导出、Astro 渲染。
- 已清理 `movie-ingest` 中旧 JS 入库入口、过期报告和明显冗余内容，使当前目录职责收敛到最新工作流。
- 电影关联作品规则已收口：数据库和 Astro 只保留 `series` 与 `similar`；`similar` 当前只使用豆瓣推荐；TMDB recommendations / similar 当前不使用。
- 电影图片规则已收口：普通图库、视频封面、人物头像、各数据源海报主图均需本地化；多源封面主图单独进入 `cover/` 类资源目录。

### 书籍模块

- 已将 `book-ingest` 重构为接近 `movie-ingest` 的单本工作流：
  `多源采集 -> raw -> staging -> 封面/头像下载 -> 字段 HTML 核对 -> import_staging 预检 -> --apply 入库`。
- 当前正式入库入口是 `temp-script/book-ingest/import_staging.py`；默认只预检，不写主库；刷新已有记录必须加 `--update-existing`。
- 已完成《围城》普通书样本：
  - `summary` 取 Wikipedia “故事大纲”。
  - `story` 取百度百科“内容情节”。
  - `year` 使用百度百科首版年 1947。
  - 豆瓣短评、长评、摘录、封面、作者头像均已纳入流程。
- 已完成系列书样本：
  - 三体三部曲：`0200000004` 至 `0200000006`，归入 `0299000001`。
  - 冰与火之歌正传五部：`0200000007` 至 `0200000011`，归入 `0299000002`。
- 已完成网络小说样本：
  - `0200000003`《凡人修仙传》
  - `0200000012`《诡秘之主》
  - `0200000013`《庆余年》
- 网络小说规则已落地：
  - `summary` 不使用 Wikipedia，优先起点或豆瓣。
  - `story` 使用百度百科词条顶部正文。
  - 除原文名、外文别名、评论原文外，前台中文展示字段不录入英文候选值。
  - 类型标签必须是中文。
- 百度百科反爬协作流程已记录并实践：
  - 优先解析 `data/manual/baike/*.html` 中用户保存的本地页面。
  - 可加载 `data/cookies/baike.json`。
  - 遇到验证码页、空壳页、SEO 截断页时不得覆盖有效 raw。
- 豆瓣读书 Cookie 规则已落地：
  - 用户可提供 `data/cookies/douban-cookie.txt`。
  - 脚本成功访问后自动续存 `data/cookies/douban.json`。
  - 只有登录、验证码、账号风控等脚本无法代表用户完成的动作才需要用户协助。
- 书籍前台已落地：
  - `/book`
  - `/book/{id}`
  - 纯白、偏微信读书的信息流和阅读型详情页。
  - 已修复详情页长评论横向溢出、右侧信息区叠压、列表页元信息展示等问题。
- 已完成从本地数据库到 Astro 的书籍端到端验证，54 本书均生成静态详情页。
- 已完成第一轮网络小说批量 fast 入库：
  - 用户一次性提供 44 行网络小说书单，已完整记录到 `temp-script/book-ingest/data/batch-manifests/2026-06-10-web-novel-bulk.json`。
  - 去重后 43 个唯一书名，其中 2 本已在库、1 行重复、41 本进入批量处理。
  - 第一轮起点优先只读采集完成 41 本分组；27 本通过标题/作者核对并重新编排为连续 ID `0200000014` 至 `0200000040`。
  - 27 本已通过 `batch_apply.py` 正式写入 `.local/treasure.db`，并完成 generated 导出和 Astro 构建。
  - 14 本曾因错配、无 raw、简介截断等进入 blockedQueue，已于 2026-06-11 通过 manual fallback staging 补录完成，ID 为 `0200000041` 至 `0200000054`。
  - manual fallback 批次没有新增正式自动数据源；额外页面仅作为候选锚点 / 参考来源，仍走 staging、字段报告、`import_staging.py` 预检、approval apply、generated 导出和 Astro 构建。

## 当前限制与风险

### 混合媒体批量录入需要 agent-assisted preflight

当前已经补齐电影 / 纪录片 / 动画电影 / 电视剧 / 番剧的基础分型层，并完成首批 12 条混合媒体样本正式入库。纪录片不拆公开子类；电影形态和剧集形态只通过 `schemaType` 区分字段要求。下一批混合录入不能无人值守写库，必须先完成 agent-assisted preflight；剧集 / 番剧必须补齐或明确记录增强字段缺口。

原因：

- 用户每次提供录入清单后，必须先运行 agent-assisted preflight：Codex 结合网络搜索、数据源页面、现有 DB、用户输入语境和脚本机械报告综合判断作品身份、类型、候选来源与 source hint 可信度。
- 固定脚本的 `ready` 只能表示机械检查暂未发现问题，不得直接等同于“可以入库”；必须经过 agent / LLM 复核后才能进入采集或写库。
- 预审必须覆盖查重、类型判断、候选数据源消歧、source hint 有效性校验。已入库条目不得重复采集；不确定候选必须先列给用户确认。
- 预审必须单独标记 `source_hint_invalid` 和 `source_validation_failed`；百度百科缺数字词条 ID、百科 URL 与 `baikeId` 不一致、豆瓣 / IMDb / TMDB ID 格式异常等问题会阻断入库。
- 用户提供作品类型时，可直接映射到对应 `schemaType`；未提供类型时，应先由脚本或 Codex 生成判断清单给用户核对。
- 真人电影、电影形态纪录片、动画电影可复用已验证的电影形态采集流程。
- 电视剧、剧集形态纪录片、番剧已经在首批样本中通过 staging 预检并正式入库；集数、单集时长、分集剧情和角色资料已有首版采集逻辑，并已通过 6 条增强队列完成 6 条实采回填。后续批量仍需把未补齐项留在增强队列，不得降级入库。
- 剧集类作品的 `episodesStory`、番剧 / 多季动画的 `characters` 从下一轮起视为必须采集或必须进入增强队列的字段；不得静默缺省后当作完整记录。预检默认会拦截缺失项，显式 `--allow-enhancement-missing` 是唯一例外通道。
- 同一作品可能存在电影版、剧集版、动画版、纪录片版等同名条目，必须通过年份、导演 / 主创、数据源 ID 辅助消歧。
- Rotten Tomatoes / Metacritic 对中文影视、番剧和动画电影容易错配，不能在未强校验标题、年份、媒介类型时作为封面、标题、评分或评论的正式来源。
- 批量验证已显式设置为非交互模式；遇到豆瓣登录 / 验证码 / 机器人验证时，不等待人工处理，只记录失败并继续后续条目。

### 书籍批量录入已可用于受控 fast 批次

当前已经跑通网络小说 fast 批次的端到端编排，但仍不能视为无人值守的全自动大批量录入。适合处理“来源明确、可按起点整体入库、允许后续补 story”的受控批次。

原因：

- 已新增 manifest-driven `batch_runner.py` 和 explicit approval `batch_apply.py`，可替代旧的 `config.TEST_BOOKS` 批量思路。
- `db_tools/import_batch.py` 仍是 legacy 入口，会绕过当前正式 `import_staging.py` 预检体系，不得用于正式入库。
- 豆瓣、百度百科、当当、起点、Goodreads 都可能触发反爬或返回异常页；fast 批次当前只使用起点作为主来源。
- 当前批量报告已经能分组“可入库 / 需人工确认 / 失败”，但错配标题、无 raw、简介截断仍必须进入 blockedQueue。
- 系列、译本、套装、多册版本、网络小说实体书版本等复杂场景还需要更多样本规则。

### 资源缺口

- 作品资源导出仍有 1 条历史缺失。
- 人物头像历史缺口仍较多，当前通过前台占位图兜底。
- 存量书籍和电影中的旧图片字段形态仍可能存在，后续按作品逐步清理。

### 文档与目录清理

- `temp-script/book-ingest` 仍保留 legacy 文件：`crawl_basic.py`、`crawl_reviews.py`、`db_tools/`、以及 `sources/` 中不带 `_crawl.py` 的旧爬虫。当前只作为参考或历史兼容，不是正式入口。
- `temp-script/` 仍包含采集产物、调试产物和本地辅助材料；未被明确要求时不要主动删除。
- `data/manual/`、`data/cookies/`、raw、staging、assets 是采集过程材料，是否提交或清理需要按具体任务判断。

## 下一步建议

优先级从高到低：

1. 继续媒体作品批量录入，电影形态作品沿用已验证的 `movie-ingest` 稳定工作流。
2. 用户提供下一批作品后，先生成 agent-assisted preflight 清单：已入库、候选明确、候选不确定、source hint 无效、需用户确认分组列出；核对完成后再采集和入库。
3. 继续修正混合媒体采集策略：批量模式下已阻止豆瓣详情缺标题时生成空标题 staging；后续应把失败点前移到豆瓣详情失败当场，并加强 Rotten Tomatoes / Metacritic 对中文影视、番剧、动画电影的错配拦截。
4. 电影新增或刷新时继续量化采集、预检、入库、导出、构建结果，并保留字段核对报告；普通电影写入 `video/movie/live_action_movie`，纪录片统一写入 `video/documentary`，动画电影和番剧必须进入动漫一级模块。
5. 将 `web-novel-fast` 的标题/作者错配校验前移到 runner，避免后续书籍批次中错误候选进入 approval 候选池。
6. 为 manual fallback 批次补充更高质量封面或正式 adapter 前的 HTML 快照，但不得把新站点静默升格为自动来源。
7. 归档或删除 `book-ingest` legacy 批量入口，避免误用绕过预检的旧脚本。
8. 新增 generated 完整性校验脚本，覆盖电影和书籍：
   DB 数量、generated 数量、索引一致性、资源存在性、关键字段完整性。
9. 再考虑扩大书籍录入规模；扩大前必须保留 manifest、approval、apply-result 和 blockedQueue。
