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
- 同步 `.local/assets/video/movie/` 到 `site/public/assets/video/movie/`
- 同步 `.local/assets/people/` 到 `site/public/assets/people/`

```powershell
node tools/db/export-generated.mjs
```

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
