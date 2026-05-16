# Treasure 当前状态

最近校验时间：2026-05-13

当前项目处于 **DB-first 静态站闭环整理阶段**。电影模块已经跑通从 SQLite 到 generated，再到 Astro 静态构建的主链路；书籍模块已有数据库草稿，但还没有正式接入 generated 和前台页面。

## 数据库快照

| 表 | 数量 | 说明 |
|---|---:|---|
| `works` | 250 | 影视 / 电影，全部为 `published` |
| `person` | 11546 | 公共人物表 |
| `category` | 28 | 公共分类 / 标签 |
| `work_person` | 12999 | 电影演职员关系 |
| `work_category` | 698 | 电影分类关系 |
| `books` | 3 | 书籍草稿，全部为 `draft` |
| `book_series` | 0 | 书籍系列 |
| `book_person` | 5 | 书籍人物关系 |
| `book_category` | 1 | 书籍分类关系 |

## generated 快照

| 校验项 | 结果 |
|---|---:|
| 数据库电影数 | 250 |
| `generated/entries/video/movie/*.json` | 250 |
| `generated/indexes/video-movie.json` 记录数 | 250 |
| generated 中找不到数据库记录 | 0 |
| 数据库中缺少 generated 详情 | 0 |
| 关键字段不一致 | 0 |
| 索引缺详情 | 0 |
| 详情缺索引 | 0 |
| 人物引用总数 | 12999 |
| 人物编号找不到数据库记录 | 0 |

结论：数据库主数据与 generated 详情 / 索引已经对齐。

## 资源快照

| 资源项 | 总量 | 存在 | 缺失 | 覆盖率 |
|---|---:|---:|---:|---:|
| generated 资源引用 | 9199 | 9197 | 2 | 约 99.98% |
| 作品主资源导出 | 250 | 249 | 1 | 99.6% |
| 人物头像导出尝试 | 12999 | 9072 | 3927 | 约 69.8% |

已知缺口：

- `0101000178`《绿里奇迹》缺少 `poster-main.webp`；该文件同时作为主海报和海报图库项被引用，因此资源校验显示 2 条缺失。
- 导出脚本会把存在的人物头像复制到对应作品自己的 `site/public/assets/video/movie/{id}/people/` 目录。
- 3927 次人物头像源文件在 `.local/assets/people/` 中找不到；导出时已从对应作品 JSON 中移除这些缺失头像引用，前台回退到 `/assets/avatar-placeholder.svg`。

这些问题目前只记录，尚未修复。

## Astro 构建状态

最近校验命令：

```bash
cd site
npm.cmd run build
```

结果：

```text
构建成功
生成页面：254
```

页面包括：

- 首页 `/`
- 关于页 `/about`
- 搜索入口 `/search`
- 影视列表页 `/video`
- 电影详情页 `/video/movie/{id}`，共 250 个

## 已完成

- 明确项目定位为“精选型个人收藏馆”。
- 明确本地内容工坊与公开静态站的边界。
- 确认 SQLite 是本地结构化主数据源。
- 确认 Astro 只消费 `generated/` 和 `site/public/assets/`。
- 电影模块已导入 250 条作品记录。
- 电影模块已导出 250 个详情 JSON 和 250 条列表索引。
- Astro 静态站可成功构建 254 个页面。
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
- 已新增本地后台管理工具 `tools/admin/`，默认通过 `npm.cmd run admin` 启动，运行在 `http://127.0.0.1:4317`。该工具作为旁路人工校正入口，直接维护 `.local/treasure.db`，不参与 generated 导出、Astro 构建或 GitHub Pages 发布。
- 当前后台已覆盖：影视作品列表与搜索、作品新增/删除、基础字段编辑、JSON 字段编辑、演职员关系维护、分类/标签关系维护、人物检索添加，以及书籍基础字段与 JSON 字段维护。

## 未完成

- 尚未建立稳定的 generated 完整性校验脚本。
- 电影资源仍有已知缺口。
- `generated.images` 中本地文件名和外链对象的边界需要统一。
- 书籍模块已有数据库草稿，但尚未进入 generated 和 Astro 页面链路。
- 书籍录入脚本尚未完全对齐采集工坊契约：字段级来源追踪未落地，部分字段优先级与局部规则文档不一致，staging 阶段存在提前 JSON 字符串化，封面本地路径写回 staging 的流程仍需确认。
- `temp-script/movie-ingest/db_tools/` 中仍有部分脚本涉及 generated、site 构建、发布校验或迁移验收语境，职责上更像历史过渡工具或应迁入 `tools/` 的工具，尚未逐一确认去留。
- `tools/db/` 已收口为当前 DB 主链路工具；历史修库脚本和旧电影 intake / 样板脚本已移入 `tools/archive/`，后续完整跑工作流时再确认是否还有需要恢复的正式入口。
- `temp-script/` 中仍有大量实验脚本、日志和调试产物，需要后续分类归档。
- 当前仓库仍存在一批不在主链路上的历史或调试文件，尚未删除：
  - `.opencode/` 中除 `__pycache__` 之外的本地 AI 技能、数据和脚本仍被跟踪，需确认是否仍作为项目资产。
  - `data/.book_counter` 不属于 DB -> Astro 主链路，但仍被 `temp-script/book-ingest` 引用，后续应随书籍采集流程一起整理。

## 下一步建议

优先级从高到低：

1. 新增 `tools/db/check-generated-integrity.mjs`，把当前手动校验固化为脚本。
2. 按 `docs/PROJECT.md` 的“主链路文件分级”逐项确认清理候选，优先处理明显不该入库的调试日志、缓存和 generated 历史产物。
3. 修正 `0101000178`《绿里奇迹》的 `poster-main.webp` 缺口后重新导出和构建。
4. 明确 `images.posters/stills` 是否只允许本地文件名字符串。
5. 审视 `temp-script/movie-ingest/db_tools/` 中的历史过渡脚本，决定迁移、归档或删除。
6. 将书籍录入 staging 契约对齐采集工坊标准，再设计书籍模块的 generated 契约与 `/book`、`/book/{id}` 页面。
