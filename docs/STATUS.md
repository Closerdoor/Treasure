# Treasure 当前状态

最近校验时间：2026-05-22

当前项目处于 **DB-first 静态站闭环整理阶段**。电影模块已经跑通从 SQLite 到 generated，再到 Astro 静态构建的主链路；书籍模块已有数据库草稿，但还没有正式接入 generated 和前台页面。

## 数据库快照

| 表 | 数量 | 说明 |
|---|---:|---|
| `works` | 251 | 影视 / 电影，全部为 `published` |
| `person` | 11582 | 公共人物表 |
| `category` | 28 | 公共分类 / 标签 |
| `work_person` | 13027 | 电影演职员关系 |
| `work_category` | 700 | 电影分类关系 |
| `books` | 3 | 书籍草稿，全部为 `draft` |
| `book_series` | 0 | 书籍系列 |
| `book_person` | 0 | 书籍人物关系 |
| `book_category` | 1 | 书籍分类关系 |

## generated 快照

| 校验项 | 结果 |
|---|---:|
| 数据库电影数 | 251 |
| `generated/entries/video/movie/*.json` | 251 |
| `generated/indexes/video-movie.json` 记录数 | 251 |
| generated 中找不到数据库记录 | 0 |
| 数据库中缺少 generated 详情 | 0 |
| 关键字段不一致 | 0 |
| 索引缺详情 | 0 |
| 详情缺索引 | 0 |
| 人物引用总数 | 13027 |
| 人物编号找不到数据库记录 | 0 |

结论：数据库主数据与 generated 详情 / 索引已经对齐。

## 资源快照

| 资源项 | 总量 | 存在 | 缺失 | 覆盖率 |
|---|---:|---:|---:|---:|
| generated 资源引用 | 11706 | 11706 | 0 | 100% |
| 作品资源导出 | 2767 | 2767 | 0 | 100% |
| 人物头像导出尝试 | 13020 | 9069 | 3951 | 约 69.7% |

已知缺口：

- 导出脚本会把存在的人物头像复制到对应作品自己的 `site/public/assets/video/movie/{id}/people/` 目录。
- 3951 次人物头像源文件在 `.local/assets/people/` 中找不到；导出时已从对应作品 JSON 中移除这些缺失头像引用，前台回退到 `/assets/avatar-placeholder.svg`。

作品资源缺失已清零；人物头像历史缺口仍只记录，尚未批量回补。

## Astro 构建状态

最近校验命令：

```bash
cd site
npm.cmd run build
```

结果：

```text
构建成功
生成页面：255
```

页面包括：

- 首页 `/`
- 关于页 `/about`
- 搜索入口 `/search`
- 影视列表页 `/video`
- 电影详情页 `/video/movie/{id}`，共 251 个

## 已完成

- 明确项目定位为“精选型个人收藏馆”。
- 明确本地内容工坊与公开静态站的边界。
- 确认 SQLite 是本地结构化主数据源。
- 确认 Astro 只消费 `generated/` 和 `site/public/assets/`。
- 电影模块已导入 251 条作品记录。
- 电影模块已导出 251 个详情 JSON 和 251 条列表索引。
- Astro 静态站可成功构建 255 个页面。
- 文档已收敛为入口、项目结构与状态三类。
- 已完成一次 `movie-ingest` 与 `book-ingest` 的代码级流程审视，确认这两个目录的职责边界是爬取作品信息、下载到本地、录入 `.local/treasure.db`；generated / Astro / 发布校验不属于它们的职责。
- 已将 `tools/db/` 收口为当前 DB 主链路工具，历史修库脚本和旧电影 intake / 样板脚本已移入 `tools/archive/`。
- 已将 `tools/db/export-generated.mjs` 扩展为统一导出入口：同时导出 generated JSON 和当前记录引用的静态资源。
- 发布侧不再导出共享 `site/public/assets/people/`；人物头像改为按作品目录复制并写入作品 JSON。
- 已完成一次 DB -> generated -> Astro 的完整工作流校验：电影 250 条详情与索引对齐，Astro 构建成功生成 254 个页面。
- 已在 `docs/PROJECT.md` 增加主链路文件分级，区分当前主链路、历史兼容、清理候选和暂不处理范围。
- 已清理第一批低风险入库噪声：删除 172 个 `.playwright-mcp/` 调试快照，以及 5 个 `.opencode/**/__pycache__/` Python 字节码缓存文件。
- 已清理 DB -> Astro 链路中的历史兼容入口：删除 `site/scripts/sync-assets.mjs` 和 `site` 的 `sync` npm script，统一使用仓库根目录的 `node tools/db/export-generated.mjs`。
- 已将 `generated/recent.json` 与 `generated/tags.json` 从 Git 跟踪中移除；它们仍由 `tools/db/export-generated.mjs` 生成，但不再作为需要人工维护的仓库文件。
- 已清理顶层一次性抓取 / 调试文件：`interstellar-reviews.json`、`shawshank-reviews.json`、`rt-requests.txt`、`rt-review-body.json`、`tmdb-requests.txt`。
- 已移除旧 `content/` Markdown / 样例内容链路；设计稿引用的 6 张肖申克海报已复制到 `design-archive/references/`，并改写 `design-archive/drafts/` 中的图片引用。
- 已新增原生本地后台管理应用 `admin/`，默认通过 `npm.cmd run admin` 启动，运行在 `http://127.0.0.1:4317`。该工具作为旁路人工校正入口，直接维护 `.local/treasure.db`，不参与 Astro 构建或 GitHub Pages 发布；Directus 方案已放弃，不作为长期后台方案。
- 当前后台已覆盖：影视作品列表与搜索、作品新增/删除、基础字段编辑、JSON 字段编辑、演职员关系维护、分类/标签关系维护、人物检索添加，以及书籍基础字段与 JSON 字段维护。
- 影视作品编辑页已改为左侧表单、右侧前台预览；字段表单会展示数据库字段名、中文说明和前台用途。
- 影视作品保存基础信息、结构化 JSON、演职员关系或分类关系后，会自动执行 `node tools/db/export-generated.mjs`，本地 Astro 前台刷新后可读取最新 generated 数据。
- 当前后台暂不提供字段级审计日志；人工修改没有 before / after 历史记录。若后续需要追溯，应新增本地审计表记录后台 API 写入行为。
- 已以 `0101000251`《社交网络》跑通 movie-ingest 稳定单片流程：多源采集、图片本地化、staging 合并、入库预检、临时库演练、正式入库、generated 导出和 Astro 构建。
- `temp-script/movie-ingest/import_staging.py` 已成为电影 staging 的正式入库 CLI：默认只预检，`--apply` 才会备份并写入 `.local/treasure.db`。
- 已清理 `temp-script/movie-ingest` 旧内容：删除 legacy `db_tools/` JS 入库入口、过期 `AUDIT.md`、已跟踪的字段核对 HTML、旧进度 / 任务 / 报告产物和 Python 缓存；当前目录收口为单部电影稳定工作流。
- 已以 `0101000178`《绿里奇迹》跑通“已有电影完整刷新”流程：多源重新采集、图片本地化、staging 合并、`--update-existing` 预检、正式覆盖入库、generated 导出、资源完整性校验和 Astro 构建；作品资源缺失从 2 条降为 0。
- 已将 `temp-script/book-ingest` 的入库入口整理为 movie-ingest 同类模式：新增 / 使用 `import_staging.py` 做只读预检、临时库演练、查重、资源校验和显式 `--apply` 入库；`main.py --import` 也走同一预检入口。
- 已修正书籍封面资源链路：封面下载后回写 `data/staging/{book_id}.json` 的 `images` 字段，正式入库时把 `data/assets/{book_id}/` 复制到 `.local/assets/book/{book_id}/`。
- 已用《围城》草稿执行一次不写主库的书籍流程演练：合并、主封面下载、staging 回写、`--update-existing` 预检、临时库导入和外键检查均通过；预检问题数为 0，临时库生成 `book_person` 1 条、`book_category` 1 条。

## 未完成

- 尚未建立稳定的 generated 完整性校验脚本。
- 电影作品资源引用当前完整；人物头像仍有历史缺口，前台使用占位头像回退。
- 电影新增流程中的 `generated.images` 本地文件名和外链对象边界已在 movie-ingest 侧明确；历史存量记录仍可能需要逐步清理。
- 书籍模块已有数据库草稿，但尚未进入 generated 和 Astro 页面链路。
- 书籍录入脚本已开始对齐采集工坊契约：当前正式入口是 `temp-script/book-ingest/main.py` 与 `import_staging.py`，staging 保持对象 / 数组结构，入库预检默认只读，并已补齐封面下载后回写 staging 与正式入库时递归复制到 `.local/assets/book/{book_id}/` 的流程。
- 书籍数据库已补齐出版版本字段：`publish_date`、`pages`、`price`、`binding`、`format`、`edition`，并新增 `story` 用于对齐电影作品的完整剧情 / 内容情节字段。上述字段均为可空字段，现有草稿记录可逐步刷新。
- 书籍系列关系已接入入库流程：`_meta.series.name` 存在时会复用或创建 `book_series`，并写入当前书籍的 `series_id`。
- 书籍图片资源契约已升级为主封面 + 多源封面映射 + 作者头像：`images.cover`、`images.covers`、`_meta.personDetails[].avatarPath`。
- 书籍模块尚未完成端到端前台闭环：当前只验证了《围城》已有草稿的采集、合并、封面/头像下载、staging 回写、临时库导入和外键检查；尚未执行正式覆盖入库，也未接入 generated / Astro 页面。
- 《围城》当前书籍样板已刷新豆瓣、当当、Goodreads，并保留百度百科、Wikipedia、OpenLibrary raw；起点未找到该作品，符合网文源定位。当前 staging 覆盖：`year` 已按作品首版年使用百度百科 1947，`publishDate` 保留豆瓣版本日期 1991-2，`summary` 已切换为 Wikipedia “故事大纲”，`story` 已通过本地保存的百度百科 HTML 取自“内容情节”分节（1226 字），豆瓣短评 20、豆瓣长评 20、原文摘录 20、作者头像 1、主封面 1、多源补充封面 2、字段来源 18；版本年与首版年的差异作为已决冲突记录保留。
- 已将“用户协助处理反爬”的流程记录为书籍采集规则：当自动化浏览器遇到验证码、风控页或端侧差异时，先量化脚本拿到的页面，再使用用户保存的本地 HTML 或导出的 Cookie 辅助解析；辅助材料不提交 Git，脚本不得用验证码页 / 空壳页覆盖有效 raw。
- 已新增 `temp-script/book-ingest/tools/field_report.py`，可生成 `temp-script/book-ingest/docs/field-map.html`，用于对照 DB 字段、staging 当前值和各 raw 数据源实际内容。
- `tools/db/` 已收口为当前 DB 主链路工具；历史修库脚本和旧电影 intake / 样板脚本已移入 `tools/archive/`，后续完整跑工作流时再确认是否还有需要恢复的正式入口。
- `temp-script/` 中仍有大量实验脚本、日志和调试产物，需要后续分类归档。
- 当前仓库仍存在一批不在主链路上的历史或调试文件，尚未删除：
  - `.opencode/` 中除 `__pycache__` 之外的本地 AI 技能、数据和脚本仍被跟踪，需确认是否仍作为项目资产。
  - `data/.book_counter` 不属于 DB -> Astro 主链路，但仍被 `temp-script/book-ingest` 引用，后续应随书籍采集流程一起整理。

## 下一步建议

优先级从高到低：

1. 新增 `tools/db/check-generated-integrity.mjs`，把当前手动校验固化为脚本。
2. 按 `docs/PROJECT.md` 的“主链路文件分级”逐项确认清理候选，优先处理明显不该入库的调试日志、缓存和 generated 历史产物。
3. 使用《社交网络》和《绿里奇迹》页面做前台渲染抽查，确认新流程电影在 Astro 列表页和详情页展示正常。
4. 继续核对 book-ingest 各数据源采集质量，确认书评 20 条限制、legacy 入口去留和字段核对 HTML 入口后，再正式刷新已有书籍或新增书籍。
5. 书籍入库流程稳定后，再设计书籍模块的 generated 契约与 `/book`、`/book/{id}` 页面。
