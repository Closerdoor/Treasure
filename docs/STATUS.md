# Treasure 当前状态

最近校验时间：2026-06-03

当前项目处于 **DB-first 静态站闭环整理阶段**。电影模块已经完成稳定单部工作流；书籍模块已经完成普通书、系列书、网络小说样本的端到端验证，并已接入 Astro 前台页面。下一阶段重点不是继续扩大数据量，而是把书籍批量录入编排层补齐，使“多本采集 -> 质量报告 -> 人工确认 -> 批量入库”变成稳定流程。

## 数据库快照

运行命令：

```bash
node tools/db/check-counts.mjs
```

结果：

| 表 | 数量 | 说明 |
|---|---:|---|
| `works` | 251 | 影视 / 电影 |
| `person` | 11599 | 公共人物表 |
| `category` | 53 | 公共分类 / 标签 |
| `work_person` | 13027 | 电影人物关系 |
| `work_category` | 700 | 电影分类关系 |
| `books` | 13 | 书籍记录，当前均为 `draft` |
| `book_series` | 2 | 书籍系列 |
| `book_person` | 23 | 书籍人物关系 |
| `book_category` | 36 | 书籍分类关系 |

## Generated 快照

最近导出命令：

```bash
node tools/db/export-generated.mjs
```

当前导出结果：

| 项目 | 数量 |
|---|---:|
| `generated/entries/video/movie/*.json` | 251 |
| `generated/indexes/video-movie.json` | 251 |
| `generated/entries/book/*.json` | 13 |
| `generated/indexes/book.json` | 13 |
| `generated/indexes/all.json` | 264 |
| `generated/persons.json` | 11599 |

资源导出最近结果：

| 资源项 | 结果 |
|---|---|
| 作品资源 | copied=2795, missing=1 |
| 人物头像 | copied=9076, missing=3955 |
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
生成页面：269
```

当前已落地路由：

```text
/
/about
/search
/video
/video/movie/{id}
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
- 已完成从本地数据库到 Astro 的书籍端到端验证，13 本书均生成静态详情页。

## 当前限制与风险

### 大批量书籍录入尚未稳定

当前可以进行“小批量试运行”，例如每批 5-10 本；还不能视为无人值守的大批量正式录入。

原因：

- `book-ingest --batch` 目前仍依赖 `config.TEST_BOOKS`，不是长期可维护的正式批量清单。
- `db_tools/import_batch.py` 仍是 legacy 入口，会绕过当前正式 `import_staging.py` 预检体系，不得用于正式入库。
- 豆瓣、百度百科、当当、起点、Goodreads 都可能触发反爬或返回异常页，无法保证几十本连续无人值守。
- 当前字段 HTML 核对仍以单本为主，缺少批量质量报告和“可入库 / 需人工确认 / 失败”分组。
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

1. 为 `book-ingest` 设计正式批量清单和批量 runner：
   `manifest -> 逐本采集 -> 字段 HTML -> 批量质量报告 -> 人工确认 -> apply 入库`。
2. 归档或删除 `book-ingest` legacy 批量入口，避免误用绕过预检的旧脚本。
3. 新增 generated 完整性校验脚本，覆盖电影和书籍：
   DB 数量、generated 数量、索引一致性、资源存在性、关键字段完整性。
4. 用 5-10 本新书执行第一轮正式小批量试运行，验证批量报告和人工确认流程。
5. 再考虑扩大书籍录入规模。
