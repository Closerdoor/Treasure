# 数据源对比矩阵

本文档汇总各数据源可获取的字段，帮助选择最佳组合策略。

## 数据源可用性

| 数据源 | 状态 | 访问方式 | 覆盖率 |
|--------|------|----------|--------|
| 豆瓣 | ✅ 可用 | Playwright + Cookie | 78% |
| OMDb | ✅ 可用 | REST API | 47% |
| 百度百科 | ✅ 可用 | WebFetch | 72% |
| Wikipedia | ✅ 可用 | REST API | 28% |
| TMDB | ⚠️ 可能未收录 | REST API | 0-80% |
| IMDb | ❌ 访问受限 | OMDb代理 | 9% |

## 字段覆盖矩阵

### 基本信息

| 字段 | 豆瓣 | OMDb | 百度百科 | Wikipedia | TMDB | IMDb |
|------|:----:|:----:|:--------:|:---------:|:----:|:----:|
| title (中文) | ✅ | ❌ | ✅ | ❌ | ⚠️ | ❌ |
| originalTitle | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| year | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| genre | ✅中文 | ✅英文 | ✅中文 | ⚠️ | ✅ | ✅ |
| country | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| language | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| runtime | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| releaseDate | ✅完整 | ⚠️美国 | ⚠️部分 | ❌ | ✅完整 | ✅完整 |
| aka | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |

### 标识符

| 字段 | 豆瓣 | OMDb | 百度百科 | Wikipedia | TMDB | IMDb |
|------|:----:|:----:|:--------:|:---------:|:----:|:----:|
| imdbId | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| doubanId | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| tmdbId | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| wikibaseId | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |

### 评分

| 字段 | 豆瓣 | OMDb | 百度百科 | Wikipedia | TMDB | IMDb |
|------|:----:|:----:|:--------:|:---------:|:----:|:----:|
| doubanRating | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| doubanVotes | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| imdbRating | ❌ | ⚠️ | ❌ | ❌ | ❌ | ⚠️ |
| imdbVotes | ❌ | ⚠️ | ❌ | ❌ | ❌ | ⚠️ |
| rated | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| tomatoMeter | ❌ | ⚠️ | ✅ | ❌ | ❌ | ❌ |
| metascore | ❌ | ⚠️ | ✅ | ❌ | ❌ | ❌ |

### 演职员

| 字段 | 豆瓣 | OMDb | 百度百科 | Wikipedia | TMDB | IMDb |
|------|:----:|:----:|:--------:|:---------:|:----:|:----:|
| director.name | ✅中文 | ✅英文 | ✅中文 | ✅英文 | ✅ | ✅ |
| director.nameEn | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| director.avatar | ⚠️需下载 | ❌ | ❌ | ✅ | ✅ | ✅ |
| director.works | ⚠️需访问 | ❌ | ❌ | ❌ | ❌ | ✅ |
| writer | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ✅ |
| cast.name | ✅中文 | ❌ | ✅中文 | ❌ | ✅ | ✅ |
| cast.nameEn | ✅ | ⚠️3位 | ❌ | ✅ | ✅ | ✅ |
| cast.role | ✅ | ❌ | ✅详细 | ❌ | ✅ | ✅ |
| cast.avatar | ⚠️需下载 | ❌ | ❌ | ✅部分 | ✅ | ✅ |
| otherCast | ✅ | ❌ | ✅合并 | ❌ | ✅ | ✅ |
| producer | ✅ | ❌ | ⚠️ | ❌ | ✅ | ✅ |

### 内容

| 字段 | 豆瓣 | OMDb | 百度百科 | Wikipedia | TMDB | IMDb |
|------|:----:|:----:|:--------:|:---------:|:----:|:----:|
| synopsis.text | ✅中文 | ✅英文 | ✅详细 | ✅英文 | ✅ | ✅ |
| synopsis.note | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| reviews | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| similar | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |

### 媒体

| 字段 | 豆瓣 | OMDb | 百度百科 | Wikipedia | TMDB | IMDb |
|------|:----:|:----:|:--------:|:---------:|:----:|:----:|
| images.poster | ✅ | ⚠️小图 | ✅ | ✅ | ✅高清 | ✅ |
| images.posters | ✅多张 | ❌ | ⚠️ | ❌ | ✅高清 | ✅ |
| images.stills | ✅多张 | ❌ | ⚠️ | ❌ | ✅ | ✅ |
| images.wallpapers | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| videos | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| soundtrack | ❌ | ❌ | ✅完整 | ❌ | ❌ | ✅ |

### 其他

| 字段 | 豆瓣 | OMDb | 百度百科 | Wikipedia | TMDB | IMDb |
|------|:----:|:----:|:--------:|:---------:|:----:|:----:|
| awards | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| boxOffice | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| filmingDates | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| productionCompany | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| technicalSpecs | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

## 图例说明

- ✅ 可获取
- ⚠️ 部分可获取或质量不稳定
- ❌ 无法获取

## 各数据源独有字段

### 豆瓣独有
- doubanId, doubanRating, doubanVotes
- 中文演职员名、饰演角色
- 相似推荐、用户评论
- 海报/剧照数量统计

### OMDb 独有
- rated（MPAA评级）
- awards（获奖信息）

### 百度百科独有
- soundtrack（原声带曲目列表）
- boxOffice（票房数据）
- filmingDates（拍摄日期）
- tomatoMeter, metascore, cinemaScore
- 详细剧情介绍（含剧透）

### Wikipedia 独有
- wikibaseId（Wikidata ID）
- 演职员头像（无防盗链）

### TMDB 独有
- 高清海报/剧照
- 技术规格

### IMDb 独有
- 完整演职员表
- 详细获奖记录
- 技术规格

## 推荐组合策略

### 主数据源：豆瓣
- 基本信息、演职员、评分、图片、视频、评论

### 补充数据源

| 字段 | 来源 | 原因 |
|------|------|------|
| rated | OMDb | MPAA评级 |
| awards | OMDb | 获奖信息 |
| soundtrack | 百度百科 | 原声带曲目 |
| boxOffice | 百度百科 | 票房数据 |
| tomatoMeter | 百度百科 | 烂番茄评分 |
| metascore | 百度百科 | Metacritic评分 |
| 演职员头像 | Wikipedia | 无防盗链 |
| wikibaseId | Wikipedia | 数据关联 |

## 数据冲突处理

### 片长 (runtime)
- 优先使用豆瓣值
- 记录 IMDb/百度百科差异
- 差异 > 5 分钟时标注

### 制片国家
- 优先使用豆瓣值
- 记录 OMDb 差异

### 上映日期
- 优先使用豆瓣完整列表
- 补充其他地区日期

## 更新记录

| 日期 | 变更 |
|------|------|
| 2026-05-01 | 初始版本 |
