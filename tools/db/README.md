# DB Tools

## 初始化数据库

使用本机 SQLite CLI 初始化数据库：

```powershell
Get-Content "tools/db/init.sql" | & "D:\ArtSoftware\sqlite3.exe" ".local\treasure.db"
```

## 导入现有电影数据

如需把旧 `content/video/movie/*` 的数据、原始抓取快照、资源文件迁入当前 DB-first 路径，先执行：

```powershell
node "tools/db/migrate-legacy-movie-files.mjs"
```

当前会：

- 复制 `data.json` 到 `.local/staging/video/movie/{id}.json`
- 复制旧 `raw/` 到 `.local/source-snapshots/video/movie/{id}/`
- 复制作品资源到 `site/public/assets/video/movie/{id}/`
- 复制可映射的人物头像到 `site/public/assets/people/`
- 清除 staging 中引用但实际上缺失的视频缩略图路径

## 导入当前 staging 电影数据

当前电影导入脚本读取 `.local/staging/video/movie/*.json`：

```powershell
node "tools/db/import-movies.mjs"
```

当前脚本会：

- 读取 `.local/staging/video/movie/*.json`
- 将电影主数据导入 `works`
- 将人物导入 `people`
- 将导演 / 编剧 / 演员 / 制片相关关系导入 `work_credits`
- 将电影类型导入 `terms` 与 `work_terms`
- 输出导入摘要到 `.local/import-movies-summary.json`

## 批量片名搜索候选

当你只有一批作品名称时，先生成豆瓣候选文件：

```powershell
node "tools/db/search-movie-candidates.mjs" --input ".local/batches/movies.txt"
```

支持输入格式：

- `.txt`：每行一个作品名
- `.json`：`["片名1", "片名2"]` 或 `{ "titles": ["片名1", "片名2"] }`

默认输出：

- `.local/batches/{inputName}.candidates.json`

输出内容包含：

- 每个查询词的豆瓣候选列表
- 自动高置信命中结果（如有）
- 仍需人工复核的条目

人工复核方式：

- 打开生成的 `.candidates.json`
- 对需要手工指定的条目，填写 `selectedDoubanId`
- 如果你认可脚本自动命中的结果，也可以直接在下一步使用 `--accept-auto`

## 从候选文件生成批处理任务

当候选文件里的 `selectedDoubanId` 已经填好后，生成可继续执行的任务文件：

```powershell
node "tools/db/prepare-movie-batch.mjs" --input ".local/batches/movies.candidates.json"
```

如果你接受脚本给出的自动高置信命中，也可以直接：

```powershell
node "tools/db/prepare-movie-batch.mjs" --input ".local/batches/movies.candidates.json" --accept-auto
```

默认输出：

- `.local/batches/{inputName}.tasks.json`

该任务文件当前承载：

- `query`
- `doubanId`
- `title`
- `originalTitle`
- `year`
- `subjectUrl`

后续新的多源抓取与归一化脚本可以直接消费这份任务文件。

## 同步字段来源文件

当前样板电影的字段来源仍保存在旧目录中的 `source.json`。为了让新 workflow 有统一承载位置，可以同步到：

- `.local/field-sources/video/movie/{id}.json`

执行：

```powershell
node "tools/db/sync-movie-field-sources.mjs"
```

## 生成当前电影录入基线报告

这个报告会扫描当前 `.local/staging/video/movie/*.json` 与旧 `source.json`，产出现在真实在用的字段基线：

```powershell
node "tools/db/report-movie-baseline.mjs"
```

输出：

- `.local/movie-baseline-report.json`

用途：

- 明确当前电影样板实际有哪些字段
- 明确哪些字段是必需键，哪些是扩展键
- 明确是否存在 staging 字段无来源说明的问题

## 规范化字段来源文件

历史样板里的 `source.json` 不一定对每个空字段都写了来源占位。为了让它们成为严格基线，可以先补齐：

```powershell
node "tools/db/normalize-movie-field-sources.mjs"
```

当前会：

- 为存在于 staging 里的顶层字段补齐缺失来源项
- 为 `images.poster/posters/stills/wallpapers` 等子字段补齐缺失来源项
- 对空数组或空值使用 `system` 占位说明，明确这是“当前为空，等待后续补录”

## 校验新电影记录是否符合当前样板基线

在新抓取流程真正入库前，先用这条命令校验候选产物：

```powershell
node "tools/db/validate-movie-record.mjs" --movie ".local/staging/video/movie/0101000003.json" --sources ".local/field-sources/video/movie/0101000003.json" --baseline-id "0101000003"
```

当前校验会检查：

- 顶层字段是否落在当前样板允许范围内
- 必需字段是否齐全
- 每个已存在字段是否都有来源说明
- `images.*` 是否逐项具备来源说明
- 如果传了 `--baseline-id`，还会输出与指定样板的字段差异

## 生成新流程样板数据

基于当前样板电影，生成一套“新流程标准输入样板”：

```powershell
node "tools/db/build-new-flow-movie-samples.mjs"
```

输出：

- `.local/new-flow/video/movie/{id}.json`
- `.local/new-flow-field-sources/video/movie/{id}.json`

当前会在保持旧样板核心字段一致的前提下，补上新流程新增字段，例如：

- `schemaType`
- `status`
- `publishCompany`
- `tags`
- `series`
- `tmdbId`
- `quotes`

同时会按当前规则做结构整理：

- `story.note` 不再作为数据库主字段承载
- `reviews` 改成 `author / source / date / content / url / title`
- `soundtrack` 改成 `albums[]` 多专辑结构
- `ratings_json` 不再保留 `votes`，并统一为 10 分制

## 当前样板状态

当前已完成闭环验证的电影样板共 6 部：

- `0101000001` 肖申克的救赎
- `0101000002` 迈克尔·杰克逊：巨星之路
- `0101000003` 阿甘正传
- `0101000004` 霸王别姬
- `0101000005` 肖申克的救赎1
- `0101000006` 星际穿越

其中当前高标准录入样板为：

- `0101000005` 肖申克的救赎1
- `0101000006` 星际穿越

这两条样板目前额外确认了：

- 评论使用统一结构 `author / source / date / content / url / title`
- 已上映电影的高标准评论覆盖基线为：`豆瓣长评 10 + 豆瓣短评 10 + TMDB 10 + 烂番茄 10`
- 主海报优先使用 `TMDB` 高清图
- 评分不再保留票数
- `country` 采用最早真实公映地区的单值推断规则

## 当前批量 workflow 边界

现有工具已经支持：

- 批量搜索豆瓣候选
- 批量生成任务文件
- 从 staging 导入 SQLite
- 从 SQLite 导出前台 JSON

但在真正进入豆瓣电影 TOP250 全量录入前，还需要继续完善：

- intake 的通用化，减少样板特判
- 清库后从头重跑的稳定性
- 去重、续跑和批量质量报告

## 生成电影录入验收文档

自动输出“数据库字段 / 旧的当前数据内容 / 新流程数据内容 / 数据来源或处理逻辑”的完整比对文档：

```powershell
node "tools/db/generate-movie-acceptance-doc.mjs"
```

输出：

- `docs/MOVIE-INGEST-ACCEPTANCE.md`

推荐流程：

```powershell
# 1. 准备片名列表
Copy-Item ".local/batches/movies.template.txt" ".local/batches/my-movies.txt"

# 2. 搜索豆瓣候选
node "tools/db/search-movie-candidates.mjs" --input ".local/batches/my-movies.txt"

# 3a. 如果全部自动命中可接受，直接生成任务文件
node "tools/db/prepare-movie-batch.mjs" --input ".local/batches/my-movies.candidates.json" --accept-auto

# 3b. 如果有歧义，手工填写 selectedDoubanId 后再生成任务文件
node "tools/db/prepare-movie-batch.mjs" --input ".local/batches/my-movies.candidates.json"
```

## 导出前台 JSON 产物

将 SQLite 中的电影条目导出到 `generated/`：

```powershell
node "tools/db/export-generated.mjs"
```

当前会生成：

- `generated/entries.json`
- `generated/modules/video.json`
- `generated/modules/video-movie.json`
- `generated/tags.json`
- `generated/search-index.json`
- `generated/recent.json`

## 检查静态资源文件是否存在

校验 `generated/entries.json` 中引用的作品图片、视频缩略图、共享人物头像是否真实存在于 `site/public/assets/`：

```powershell
node "tools/db/check-assets.mjs"
```

当前会输出：

- 控制台统计
- `.local/asset-check-report.json`

如果存在缺失文件，脚本会以非 0 状态码退出。

## 当前限制

- 当前只处理 `video/movie`
- 当前只导入电影样本，不处理电视剧 / 动漫 / 书籍
- 当前 `publish_company`、`quotes_json` 等新字段如果源数据尚未存在，会导入为 `NULL` 或空数组
