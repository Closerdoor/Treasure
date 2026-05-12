# Workflow

> Purpose: 记录当前项目从本地内容工坊到 Astro 静态站发布的标准流程。
> Status: active
> Scope: 数据录入、数据库、导出、资源同步、构建、发布前校验
> Out of scope: 单个爬虫的具体解析逻辑、UI 视觉细节、字段级 schema 全量说明
> Update triggers: 主流程变化、导出产物结构变化、发布前校验规则变化
> Priority: 2

## 总体流程

```text
外部数据源 / 手动录入
  -> 抓取与清洗脚本
  -> SQLite 本地数据库
  -> generated JSON 导出
  -> 静态资源同步
  -> Astro 静态构建
  -> GitHub Pages
```

## 1. 数据获取与录入

当前项目存在两类录入脚本：

- 稳定脚本：`tools/db/`
- 实验脚本：`temp-script/movie-ingest/`、`temp-script/book-ingest/`

当前约定：

- 能反复运行并作为长期流程依赖的脚本，应逐步沉淀到 `tools/`。
- `temp-script/` 保留调试脚本、网页样本、日志、中间实验结果。
- 不应让 Astro 直接依赖 `temp-script/` 产物。

涉及数据完整性的限制必须显式标注，例如只取前 N 条、跳过某些源、使用低质量候选数据等。

## 2. 数据库主源

当前结构化主源是：

```text
.local/treasure.db
```

Prisma schema 位于：

```text
prisma/schema.prisma
```

SQLite 只用于本地内容工坊，不作为线上数据库。线上站点只消费导出的 JSON 与静态资源。

## 3. 导出 generated

当前导出入口：

```bash
node tools/db/export-generated.mjs
```

导出产物位于：

```text
generated/
  entries/
  indexes/
  recent.json
  tags.json
```

当前电影模块已接入导出流程。书籍模块已有数据库表和少量草稿数据，但尚未正式接入前台 generated 契约。

## 4. 静态资源同步

私有资源源目录：

```text
.local/assets/
```

前台发布资源目录：

```text
site/public/assets/
```

站点构建时只会发布 `site/public/` 下的资源。因此凡是前台 JSON 引用的本地资源，最终都必须存在于 `site/public/assets/`。

当前同步入口：

```bash
cd site
npm.cmd run sync
```

该命令会运行数据库导出，并复制 `.local/assets/video/movie` 与 `.local/assets/people` 到 `site/public/assets/`。

## 5. Astro 构建

当前站点位于：

```text
site/
```

构建命令：

```bash
cd site
npm.cmd run build
```

当前 Astro 配置：

```text
site/astro.config.mjs
site: https://closerdoor.github.io/Treasure
output: static
```

构建产物：

```text
site/dist/
```

## 6. 发布前校验

发布前至少确认：

- 数据库电影数与 `generated/entries/video/movie/*.json` 数量一致。
- `generated/indexes/video-movie.json` 记录数与详情 JSON 数一致。
- 每个 generated 电影 ID 都能在数据库中找到。
- 每个索引记录都能找到详情 JSON。
- 关键字段如 `title`、`year`、`module`、`submodule` 与数据库一致。
- 主海报引用存在。
- 详情页使用的本地图片资源存在。
- 人物头像引用要么存在，要么前台能优雅回退到占位头像。
- Astro 构建成功。

当前校验结果详见 `STATUS.md`。

## 7. 书籍模块接入原则

书籍模块应先接入导出契约，再做页面。

推荐顺序：

1. 确认 `books`、`book_person`、`book_category` 数据结构。
2. 扩展导出脚本，生成：

```text
generated/entries/book/{id}.json
generated/indexes/book.json
```

3. 将书籍条目加入 `generated/indexes/all.json`。
4. 增加 `site/src/lib/book.ts`。
5. 增加 `/book` 列表页和 `/book/{id}` 详情页。

书籍仍处于 draft 阶段时，可以只做内部验证，不急于暴露到首页主入口。
