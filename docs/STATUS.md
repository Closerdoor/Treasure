# Treasure 当前状态

最近校验时间：2026-05-12

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
| 主海报 | 250 | 249 | 1 | 99.6% |
| 人物头像引用 | 12999 | 9072 | 3927 | 约 69.8% |

已知缺口：

- `0101000178`《绿里奇迹》缺少 `poster-main.webp`。
- `0101000001`《肖申克的救赎》的部分 `images.posters/stills` 项是 TMDB 外链对象，而不是本地文件名字符串。
- 3927 次人物头像引用在 `.local/assets/people/` 和 `site/public/assets/people/` 中找不到实体文件。

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

## 未完成

- 尚未建立稳定的 generated 完整性校验脚本。
- 电影资源仍有已知缺口。
- `generated.images` 中本地文件名和外链对象的边界需要统一。
- 书籍模块已有数据库草稿，但尚未进入 generated 和 Astro 页面链路。
- 电影批处理主流程仍需收口：`tools/db/run-movie-batch-workflow.mjs` 当前引用 `tools/db/import-movies.mjs`，但仓库中没有这个入口文件。
- 书籍录入脚本尚未完全对齐采集工坊契约：字段级来源追踪未落地，部分字段优先级与局部规则文档不一致，staging 阶段存在提前 JSON 字符串化，封面本地路径写回 staging 的流程仍需确认。
- `temp-script/movie-ingest/db_tools/` 中仍有部分脚本涉及 generated、site 构建、发布校验或迁移验收语境，职责上更像历史过渡工具或应迁入 `tools/` 的工具，尚未逐一确认去留。
- `tools/db/README.md` 仍包含旧 generated 文件名和 `tools/db/import-movies.mjs` 入口说明，需要按当前真实链路更新。
- `tools/db/export-generated.mjs` 与 `site/scripts/sync-assets.mjs` 都包含资源同步逻辑，当前可运行但存在职责重复，需要后续决定保留哪一个作为唯一同步入口。
- `temp-script/` 中仍有大量实验脚本、日志和调试产物，需要后续分类归档。

## 下一步建议

优先级从高到低：

1. 新增 `tools/db/check-generated-integrity.mjs`，把当前手动校验固化为脚本。
2. 明确 `images.posters/stills` 是否只允许本地文件名字符串。
3. 决定人物头像缺失策略：下载补齐、导出时只引用存在文件，或前台统一回退占位图。
4. 修正电影资源缺口后重新导出和构建。
5. 先收口电影批处理导入入口，明确 `tools/db/import-movies.mjs` 是需要恢复、重建，还是由现有导入脚本替代。
6. 更新 `tools/db/README.md`，移除旧 generated 文件名和不存在入口，确保工具文档与当前主链路一致。
7. 审视 `temp-script/movie-ingest/db_tools/` 中的历史过渡脚本，决定迁移、归档或删除。
8. 将书籍录入 staging 契约对齐采集工坊标准，再设计书籍模块的 generated 契约与 `/book`、`/book/{id}` 页面。
