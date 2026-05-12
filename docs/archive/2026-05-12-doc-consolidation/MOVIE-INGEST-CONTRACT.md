# Movie Ingest Contract

> Purpose: 定义当前电影批量录入 workflow 必须满足的 staging 结构与字段来源要求。
> Status: active
> Scope: `.local/staging/video/movie/{id}.json` 与 `.local/field-sources/video/movie/{id}.json`
> Out of scope: 最终数据库列设计、前台渲染细节、具体爬虫实现

## 目标

新的电影批量录入 workflow 在真正批量执行前，必须先保证：

1. 生成的电影 staging JSON 与当前 6 条样板处于同一结构层级
2. 每个 staging 字段都必须有对应的字段来源记录
3. 存在冲突的数据必须能展示多个来源，供人工决策

## 当前基线

基线来源：

- `.local/staging/video/movie/*.json`
- `.local/field-sources/video/movie/*.json`
- `.local/movie-baseline-report.json`

## 顶层字段要求

### 必需字段

- `id`
- `title`
- `originalTitle`
- `year`
- `director`
- `writer`
- `cast`
- `otherCast`
- `producer`
- `genre`
- `country`
- `language`
- `runtime`
- `releaseDate`
- `aka`
- `imdbId`
- `doubanId`
- `doubanRating`
- `synopsis`
- `story`
- `videos`
- `images`
- `similar`
- `reviews`
- `links`
- `module`
- `submodule`
- `createdAt`
- `updatedAt`

### 可选字段

- `rated`
- `awards`
- `imdbRating`
- `runtimeEn`
- `soundtrack`

## `images` 子字段要求

### 必需子字段

- `poster`
- `posters`
- `stills`
- `wallpapers`

### 可选子字段

- `postersTotal`
- `stillsTotal`

## 字段来源文件要求

每部电影必须有对应来源文件：

- `.local/field-sources/video/movie/{id}.json`

要求：

1. staging 中出现的每个顶层字段，都必须在 field-sources 里有同名条目
2. `images.*` 中出现的每个子字段，都必须在 `field-sources.images.*` 中有来源条目
3. 每个来源条目至少具备：
   - `value`
   - `source`
4. 如果字段来自多源合并，应写：
   - `source: "merged"`
   - `sources: []`
5. 如果字段存在争议但尚未拍板，应额外保留：
   - `conflicts: []`

## 冲突字段处理要求

对于有潜在争议的字段，不允许静默覆盖，至少要能展示候选值。

优先包括：

- `title`
- `originalTitle`
- `year`
- `runtime`
- `releaseDate`
- `story`
- `images.poster`
- `images.posters`
- `images.stills`
- `director`
- `writer`
- `cast`

推荐冲突结构：

```json
{
  "value": 142,
  "source": "douban",
  "conflicts": [
    {
      "source": "omdb",
      "value": 144,
      "note": "OMDb / IMDb runtime"
    }
  ]
}
```

## 校验命令

同步旧样板来源文件：

```powershell
node "tools/db/sync-movie-field-sources.mjs"
```

补齐旧样板来源占位：

```powershell
node "tools/db/normalize-movie-field-sources.mjs"
```

输出当前基线报告：

```powershell
node "tools/db/report-movie-baseline.mjs"
```

校验单部电影：

```powershell
node "tools/db/validate-movie-record.mjs" --movie ".local/staging/video/movie/0101000004.json" --sources ".local/field-sources/video/movie/0101000004.json" --baseline-id "0101000004"
```

## 当前结论

从现在起，新 workflow 不能只生成“任务文件”。

它至少必须同时生成：

1. `staging movie json`
2. `field sources json`

并且两者都先通过 contract 校验，才允许继续导入 SQLite。

## 当前补充约束

- `story.note` 不再进入数据库主字段；如需保留，只能作为抓取阶段边界说明或来源备注
- 评分仅保留评分值，不保留 `votes`
- `reviews_json` 必须使用：`author / source / date / content / url / title`
- 已上映电影的高标准评论覆盖基线为：`豆瓣长评 10 + 豆瓣短评 10 + TMDB 10 + 烂番茄 10`
- `soundtrack_json` 必须使用多专辑结构：`albums[]`
- `cast` 与 `otherCast` 在可获取范围内都应完整收录，不能只保留前几位
- 主海报优先使用 `TMDB` 高清图；如果未拿到合格 TMDB 主海报，必须在来源说明中明确原因
- `country` 仅保留单值，按最早真实公映地区推断；电影节、影展、首映场次不作为首发地区依据
