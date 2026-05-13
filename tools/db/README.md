# DB Tools

`tools/db/` 只保留当前 DB 主链路工具。电影或书籍采集过程、历史迁移、一次性样板实验不再放在这里。

当前主链路：

```text
.local/treasure.db
  -> tools/db/export-generated.mjs
  -> generated/
  -> site/public/assets/
  -> site/
```

`tools/db/export-generated.mjs` 是 DB 到前台静态输入的唯一正式导出入口。它不仅导出 JSON，也负责把当前导出记录引用到的本地静态资源复制到 `site/public/assets/`。

## 当前工具

### `check-counts.mjs`

读取 `.local/treasure.db`，输出当前核心表数量。

```powershell
node tools/db/check-counts.mjs
```

### `list-tables.mjs`

读取 SQLite 实际表列表，用来确认本地数据库当前有哪些表。

```powershell
node tools/db/list-tables.mjs
```

### `view-schema.mjs`

读取 `prisma/schema.prisma`，查看 Prisma model 和字段说明。

```powershell
node tools/db/view-schema.mjs
node tools/db/view-schema.mjs Work
node tools/db/view-schema.mjs Book
```

### `export-generated.mjs`

当前 DB 到 Astro 的主要导出入口。

它会：

- 读取 `.local/treasure.db`
- 导出 `generated/entries/video/movie/{id}.json`
- 导出 `generated/indexes/*.json`
- 导出 `generated/persons.json`、`generated/recent.json`、`generated/tags.json`
- 只导出当前 generated 记录引用到的作品资源到 `site/public/assets/video/movie/{id}/`
- 将人物头像复制到对应作品自己的 `site/public/assets/video/movie/{id}/people/` 目录，并改写该作品 JSON 内的人物 `avatarPath`
- 删除旧的公开共享人物资源目录 `site/public/assets/people/`，避免前台继续依赖共享静态资源池

```powershell
node tools/db/export-generated.mjs
```

资源约定：

- `.local/assets/` 是本地私有资源源头。
- `site/public/assets/` 是发布副本，由导出脚本重建。
- 前台详情页中的人物头像路径应指向作品自己的资源目录，例如 `/assets/video/movie/0101000001/people/tmdb-504-avatar.jpg`。
- `generated/persons.json` 是人物索引数据，不导出共享 `avatarPath`。

### `check-assets.mjs`

扫描 `generated/entries/**/*.json` 中引用的本地资源，并检查它们是否存在于 `site/public/assets/`。

输出：

```text
.local/asset-check-report.json
```

```powershell
node tools/db/check-assets.mjs
```

如果存在缺失资源，脚本会以非 0 状态码退出。

### `update-backup.mjs`

把当前数据库核心表导出到 `.local/backup/`。这是本地备份工具，不参与站点构建。

```powershell
node tools/db/update-backup.mjs
```

## 不在这里的内容

以下脚本已经移入 `tools/archive/`，不是当前主链路入口：

- 历史修库 / 迁移脚本：`tools/archive/db-legacy-migrations/`
- 电影采集过程脚本：`tools/archive/movie-ingest-workflow/`

如果后续确认某个归档脚本仍是正式工作流的一部分，应先明确职责边界，再移动回对应目录。
