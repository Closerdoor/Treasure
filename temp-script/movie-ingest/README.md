# movie-ingest：媒体作品采集与入库工作流

`movie-ingest` 是 Treasure 的媒体作品数据采集工坊，当前覆盖电影、纪录片、动画电影、电视剧、番剧 / 多季动画。核心规范以仓库根目录 `docs/PROJECT.md` 和 `docs/STATUS.md` 为准；本文件只说明本目录入口和边界。

当前稳定职责是：

```text
作品输入 / 豆瓣 ID 验证 / agent-assisted preflight
  -> 多数据源采集
  -> data/raw/{work_id}/
  -> data/assets/
  -> data/staging/{work_id}.json
  -> 入库预检
  -> .local/treasure.db
```

本目录不负责 `generated/` 导出、`site/public/assets/` 发布资源、Astro 构建或 GitHub Pages 发布校验。入库后的前台链路由仓库根目录的 `tools/db/export-generated.mjs` 和 `site/` 负责。

## 当前入口

| 文件 | 职责 |
|---|---|
| `main.py` | 命令行入口，调度 `MovieCrawler` |
| `crawl.py` | 统一采集编排，生成 raw、staging 和采集阶段资源 |
| `sources/*.py` | 豆瓣、TMDB、OMDb、百度百科、Wikipedia、Rotten Tomatoes、Metacritic 单源采集 |
| `downloader.py` | 并行下载作品图片、封面主图、视频封面、人物头像到 `data/assets/` |
| `merger.py` | 多源 raw 合并为 staging JSON |
| `import_staging.py` | staging 入库预检与正式导入 CLI；默认只预检，`--apply` 才写库 |
| `database.py` | SQLite 写入层，供 `import_staging.py` 调用 |
| `field_map_report.py` | 生成字段核对 HTML，供人工审视 |
| `progress.py` | 采集进度记录 |
| `name_matcher.py` | 豆瓣中文人物与 TMDB 人物匹配 |
| `config.py` | 本目录路径、API、代理、浏览器、数量限制配置 |
| `media_profiles.py` | 媒体 profile、模块 / 子模块、ID 前缀和必填字段规则 |
| `batch_validate.py` | 混合媒体批量验证；只生成报告和 staging，不写主库 |
| `backfill_enhancements.py` | 剧集 / 番剧分集剧情和角色介绍增强回填 |
| `generate_audit_preview.mjs` | 根据批量报告生成审核预览页 |
| `prepare_media_batch_for_apply.mjs` | 审核后准备批量正式入库 |

旧 `db_tools/` JS 入库入口已删除。当前正式入库只能走 `import_staging.py`。

## 目录结构

```text
movie-ingest/
  config.py
  main.py
  crawl.py
  merger.py
  downloader.py
  import_staging.py
  database.py
  field_map_report.py
  progress.py
  name_matcher.py
  sources/
  utils/
  data/
    raw/{work_id}/
    staging/{work_id}.json
    assets/
      works/{work_id}/
        cover/
        images/
      people/
```

`data/`、`cookies.json`、`progress.json`、`docs/field-map.html` 都是运行产物，不提交 Git。

## 安装与配置

```bash
pip install playwright beautifulsoup4 aiohttp pillow
playwright install chromium
```

在 `config.py` 配置：

```python
TMDB_API_KEY = "your_tmdb_api_key"
OMDB_API_KEY = "your_omdb_api_key"
PROXY_ENABLED = True
PROXY_URL = "http://127.0.0.1:7890"
HEADLESS = False
USE_CHROME = True
```

Windows PowerShell 下命令仍建议使用 `python ...`，Node / Astro 后续命令在仓库根目录或 `site/` 中使用 `npm.cmd`。

## 媒体 profile

| schemaType | 中文类型 | module/submodule | ID 前缀 |
|---|---|---|---|
| `live_action_movie` | 真人电影 | `video/movie` | `0101` |
| `documentary_film` | 纪录片 | `video/documentary` | `0103` |
| `animated_movie` | 动画电影 | `anime/anime_movie` | `0301` |
| `live_action_series` | 电视剧 | `video/tv_series` | `0102` |
| `documentary_series` | 纪录片 | `video/documentary` | `0103` |
| `animated_series` | 番剧 / 多季动画 | `anime/anime_series` | `0302` |

动漫是一级模块，和影视同级；纪录片对外只展示为 `video/documentary`，内部用 `schemaType` 区分电影形态和剧集形态。

## 单部媒体新增流程

1. 采集媒体作品数据：

```bash
python main.py --movie-name "社交网络" --year 2010 --schema-type live_action_movie
```

或已确认豆瓣 ID 时：

```bash
python main.py --douban-id 3205624 --title "社交网络" --schema-type live_action_movie
```

新作品默认不要手写 `--work-id`。只有在修复明确的历史编号或人工确认编号时才传入。

2. 生成字段核对页：

```bash
python field_map_report.py --work-id {work_id}
```

默认输出 `docs/field-map.html`。这是临时核对产物，已被 `.gitignore` 忽略。

3. 入库预检：

```bash
python import_staging.py --work-id {work_id}
```

4. 预检通过后正式入库：

```bash
python import_staging.py --work-id {work_id} --apply
```

5. 回到仓库根目录导出和构建：

```bash
node tools/db/export-generated.mjs
cd site
npm.cmd run build
```

## 混合批量流程

批量录入必须先由 Codex 做 agent-assisted preflight。脚本只能提供机械报告，不能替代候选身份判断。

```text
manifest 记录用户原始输入
  -> Codex 联网搜索 / DB 查重 / 候选消歧 / schemaType 判断
  -> batch_validate.py 只读验证采集
  -> audit-preview.html 给用户审核
  -> prepare_media_batch_for_apply.mjs 准备通过项
  -> import_staging.py --apply 或批量 apply
  -> node tools/db/export-generated.mjs
  -> cd site && npm.cmd run build
```

批量报告必须区分：

- `existing`：已入库，不重复采集。
- `ready`：机械检查暂未发现问题，仍需 Codex 复核。
- `needs_source_hint`：缺少足够来源线索。
- `source_hint_invalid` / `source_validation_failed`：来源地址或 ID 不可信，阻断。
- `precheck_failed`：字段、资源或数据库演练未通过。

## 入库预检规则

`import_staging.py` 默认只读主库，并使用临时数据库副本演练导入。只有 `--apply` 才写入 `.local/treasure.db`。

已有电影的完整刷新必须显式传入 `--update-existing`，且只允许覆盖数据库中同一个 `work_id` 的作品。示例：

```bash
python import_staging.py --work-id 0101000178 --update-existing
python import_staging.py --work-id 0101000178 --update-existing --apply
```

预检会检查：

- `data/staging/{work_id}.json` 文件名与内部 `id` 一致。
- 新作品 ID 等于对应媒体 profile 当前最大 ID 的下一条。
- 使用豆瓣 ID、IMDb ID、TMDB ID、标题 + 年份、原名 + 年份查重；疑似存在时停止。
- 校验百度百科必须使用数字词条 ID 的精确 URL；泛化 `/item/标题` 不能作为正式 source hint。
- `images.poster`、`images.covers`、`images.posters/stills/wallpapers`、`videos.thumbnail` 全部指向本地文件。
- 图片字段不得残留外链 URL 或 `{url,width,height}` 对象。
- 临时数据库导入成功，外键检查为 0。
- 正式导入前自动备份 `.local/treasure.db` 到 `.local/backup/`。

## 数据源与采集内容

| 数据源 | 采集内容 |
|---|---|
| 豆瓣 | 基本信息、演职员、视频、海报 / 剧照 / 壁纸、热门好评短评 20 条、热门影评 20 条、系列作品、推荐作品 |
| TMDB | 详情、演职员、图片、视频、评论、外部 ID、上映日期、关键词 |
| OMDb | IMDb 关联信息、英文剧情、评分、票房、海报 |
| 百度百科 | 中文基础字段与信息框字段 |
| Wikipedia | 信息框、剧情、奖项 / 引用材料 |
| Rotten Tomatoes | 评分、共识、海报、Top reviews |
| Metacritic | 评分、用户 / 媒体评论摘要 |

当前数据库和 Astro 只使用 `series` 与 `similar` 两类关联作品：

- `series`：同一系列作品。
- `similar`：当前只使用豆瓣推荐。
- TMDB recommendations / TMDB similar 当前不采集、不合并、不入库。

`rated` 和 `awards` 可以保留在 raw / staging 审视材料中，但不写入数据库，不进入 generated，也不在 Astro 前台展示。

## 图片资源规则

采集阶段：

```text
data/assets/works/{work_id}/
  cover/
    douban-main.webp
    tmdb-main.jpg
    omdb-main.jpg
    rotten-tomatoes-main.jpg
  images/
    poster-001.webp
    still-001.webp
    wallpaper-001.webp
    video-001.jpg
```

staging 中：

```json
{
  "images": {
    "poster": "cover/douban-main.webp",
    "covers": {
      "douban": "cover/douban-main.webp",
      "tmdb": "cover/tmdb-main.jpg",
      "omdb": "cover/omdb-main.jpg",
      "rottenTomatoes": "cover/rotten-tomatoes-main.jpg"
    },
    "posters": ["poster-001.webp"],
    "stills": ["still-001.webp"],
    "wallpapers": ["wallpaper-001.webp"]
  }
}
```

入库成功后：

- `images/` 同步到 `.local/assets/{module}/{submodule}/{work_id}/`。
- `cover/` 同步到 `.local/assets/{module}/{submodule}/{work_id}/cover/`。
- 后续发布资源由 `tools/db/export-generated.mjs` 从 `.local/assets/` 导出。

## 豆瓣反爬暂停规则

如果豆瓣跳转到 `douban.com/misc/sorry` 或提示“证明你是人类”，必须暂停当前采集：

- 不继续刷新或密集重试。
- 不用空列表覆盖已有 raw。
- 记录触发 URL、时间和正在采集的数据类型。
- 等待一段时间后重新执行，或由用户在浏览器中完成验证。

## 已跑通样本

`0101000251`《社交网络》已完成端到端验证：

| 项目 | 数量 / 结果 |
|---|---:|
| 评论总数 | 84 |
| 视频 | 20 |
| 海报图库 | 177 |
| 剧照图库 | 742 |
| 壁纸图库 | 3 |
| 各来源封面主图 | 4 |
| 演职员关系 | 36 |
| 类型关系 | 2 |
| 同步到 `.local/assets` 的作品资源 | 947 |
| 外键问题 | 0 |

入库后已运行：

```bash
node tools/db/export-generated.mjs
cd site
npm.cmd run build
```

首批混合媒体样本已完成：输入 14 条，2 条已在库，12 条新作品正式入库；6 条增强队列已全部补齐并写库，完成率 100.0%。Astro 当前生成 323 个页面。

## 维护规则

- 本目录只维护媒体作品采集、合并、入库预检与 SQLite 写入。
- 不在本目录添加 generated 导出、站点构建、发布校验脚本。
- 新增限制性逻辑，例如只处理前 N 条、跳过某来源、降级使用低质量候选，必须运行前说明并写入代码注释。
- 新增字段或改变入库契约时，同时检查 `DATA.md`、`import_staging.py`、`database.py`、`tools/db/export-generated.mjs` 和 Astro 类型。
- 批量任务入口已纳入受控工作流，但不能无人值守写库；必须先完成 agent-assisted preflight、审核和预检。
