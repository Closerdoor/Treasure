# Import Summary

> Purpose: 定义当前 DB-first 录入流程中的导入摘要与溯源中间对象规范。
> Status: active
> Scope: 电影导入摘要、缺失字段记录、资源统计、回补提示
> Out of scope: 最终数据库 schema、前台页面 JSON 结构、完整抓取原始数据格式

## 目标

在当前 SQLite 主源方案下，不再要求必须生成 `source.json` 才能完成录入。

但每次导入仍需要一份稳定的中间摘要，用来承载：

- 本次导入了哪些作品
- 每部作品用了哪些外部来源
- 资源下载情况如何
- 哪些字段缺失
- 哪些问题需要后续回补

当前摘要文件路径：

- `.local/import-movies-summary.json`

## 当前摘要顶层结构

```json
{
  "version": 1,
  "generatedAt": "2026-05-04T10:00:00.000Z",
  "dbPath": ".local/treasure.db",
  "summaryType": "movie_import",
  "importedWorks": 6,
  "counts": {
    "works_count": 6,
    "people_count": 116,
    "credits_count": 149,
    "terms_count": 8,
    "work_terms_count": 15
  },
  "works": []
}
```

## 单部作品摘要结构

```json
{
  "id": "0101000001",
  "title": "肖申克的救赎",
  "module": "video",
  "submodule": "movie",
  "schemaType": "live_action_movie",
  "status": "published",
  "sourceFiles": {
    "stagingData": ".local/staging/video/movie/0101000001.json",
    "workAssetDir": "site/public/assets/video/movie/0101000001/"
  },
  "sources": [
    {
      "name": "douban",
      "url": "https://movie.douban.com/subject/1292052/"
    }
  ],
  "assets": {
    "poster": "poster-main.jpg",
    "posters": 10,
    "stills": 13,
    "wallpapers": 4,
    "peopleWithAvatar": 9,
    "peopleMissingAvatar": 17
  },
  "missingFields": ["rated", "awards"],
  "warnings": ["reviews 为空"],
  "retryHints": ["rated 可在 OMDb / IMDb 补齐"]
}
```

## 字段说明

### 顶层字段

- `version`: 摘要格式版本号
- `generatedAt`: 生成时间
- `dbPath`: 当前导入目标数据库文件
- `summaryType`: 当前固定为 `movie_import`
- `importedWorks`: 本次处理作品数量
- `counts`: 导入后核心表计数
- `works`: 单部作品摘要数组

### 单部作品字段

- `id` / `title`: 作品基本标识
- `module` / `submodule` / `schemaType`: 落库分类结果
- `status`: 当前导入状态
- `sourceFiles`: 当前内容文件与资源目录定位
- `sources`: 本次实际引用到的外部来源链接
- `assets`: 资源覆盖统计
- `missingFields`: 当前仍缺失的重要字段
- `warnings`: 需要注意但不阻断导入的问题
- `retryHints`: 建议后续回补动作

## 与旧 `source.json` 的关系

旧 `source.json` 的目标，是给每个字段逐一保存来源。

当前摘要并不试图 1:1 复刻它，而是先承载当前最需要的最小能力：

- 作品级来源概览
- 资源覆盖概览
- 缺失字段与回补建议

后续如果要继续细化字段级溯源，可在此基础上增加：

- `fieldSources`
- `conflicts`
- `sourceSnapshots`

而不必回到旧的 file-first 目录结构。

## 当前补充约定

- 导入摘要应能区分“已成功入库”与“仍需高标准补录”的电影条目
- 对评论覆盖不足的作品，建议在 `warnings` 中直接记录缺口，例如：`reviews 未达到高标准基线`
- 当前高标准基线指已上映电影达到：`豆瓣长评 10 + 豆瓣短评 10 + TMDB 10 + 烂番茄 10`
