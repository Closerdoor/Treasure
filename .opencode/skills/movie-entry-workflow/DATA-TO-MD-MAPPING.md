# data.json 到 index.md 字段映射规则

本文档定义 data.json 每个字段如何映射到 index.md 的展示格式，确保数据与展示完全同步。

## 映射原则

1. **所有 data.json 字段都必须在 index.md 中展示**
2. **有数据则展示，无数据则标注**
3. **格式统一，便于阅读**

## 标题区映射

### 标题行

```markdown
# {title} {originalTitle} ({year})
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `title` | 直接展示 |
| `originalTitle` | 直接展示（空格分隔） |
| `year` | 括号包裹 |

**示例**：
```json
{
  "title": "肖申克的救赎",
  "originalTitle": "The Shawshank Redemption",
  "year": 1994
}
```

```markdown
# 肖申克的救赎 The Shawshank Redemption (1994)
```

## 基本信息区映射

### 海报展示

```markdown
<div style="flex-shrink: 0;">
<img src="images/{poster}" width="200" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
</div>
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `images.poster` | `images/{poster}` |

### 信息列表

#### 导演

```markdown
**导演**：{directorNames}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `director[].name` | 逗号分隔：`name1 / name2` |

**示例**：
```json
{
  "director": [
    { "name": "弗兰克·德拉邦特" }
  ]
}
```

```markdown
**导演**：弗兰克·德拉邦特
```

#### 编剧

```markdown
**编剧**：{writerNames}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `writer[].name` | 逗号分隔：`name1 / name2` |

#### 主演

```markdown
**主演**：{castNames}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `cast[].name` | 前5位，逗号分隔：`name1 / name2 / name3 / name4 / name5` |

#### 类型

```markdown
**类型**：{genreItems}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `genre` | ` / ` 分隔：`剧情 / 犯罪` |

#### 制片国家

```markdown
**制片国家/地区**：{country}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `country` | 直接展示 |

#### 语言

```markdown
**语言**：{language}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `language` | 直接展示 |

#### 上映日期

```markdown
**上映日期**：{releaseDates}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `releaseDate[].date` | ISO格式转中文：`2026-04-24` → `2026年4月24日` |
| `releaseDate[].location` | 括号包裹：`(美国/中国大陆)` |

**组合规则**：`{date}({location}) / {date2}({location2})`

**示例**：
```json
{
  "releaseDate": [
    { "date": "2026-04-24", "location": "美国/中国大陆" },
    { "date": "2026-04-22", "location": "中国香港" }
  ]
}
```

```markdown
**上映日期**：2026年4月24日(美国/中国大陆) / 2026年4月22日(中国香港)
```

#### 片长

```markdown
**片长**：{runtime}分钟
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `runtime` | 直接展示 + "分钟" |
| `runtimeEn` | **如有数据，追加**：`（IMDb: {runtimeEn}分钟）` |

**示例**：
```json
{
  "runtime": 128,
  "runtimeEn": 127
}
```

```markdown
**片长**：128分钟（IMDb: 127分钟）
```

#### 又名

```markdown
**又名**：{akaItems}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `aka` | ` / ` 分隔 |

#### IMDb ID

```markdown
**IMDb**：{imdbId}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `imdbId` | 直接展示 |

#### 豆瓣评分

```markdown
**豆瓣评分**：**{doubanRating}** / {doubanVotes}人评价
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `doubanRating` | 加粗展示 |
| `doubanVotes` | 数字格式化：`34594` → `34,594` |

#### MPAA评级（新增）

```markdown
**MPAA评级**：{rated}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `rated` | **如有数据，必须展示** |

**示例**：
```json
{
  "rated": "PG-13"
}
```

```markdown
**MPAA评级**：PG-13
```

#### 获奖信息（新增）

```markdown
**获奖**：{awards}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `awards` | **如有数据，必须展示** |

**示例**：
```json
{
  "awards": "2 wins & 1 nomination"
}
```

```markdown
**获奖**：2 wins & 1 nomination
```

## 剧情简介区映射

```markdown
## 剧情简介

{synopsisText}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `synopsis.text` | 直接展示（保留换行） |
| `synopsis.note` | 如有数据，追加在末尾 |

## 演职员信息区映射

### 导演卡片

```markdown
### 导演

<div style="display: flex; flex-wrap: wrap; gap: 16px; margin: 16px 0;">

<div style="width: 120px; text-align: center;">
<img src="images/{avatar}" width="100" height="100" style="border-radius: 4px; object-fit: cover;"><br>
<strong>{name}</strong><br>
<small>{nameEn}</small>
</div>

</div>

**代表作**：{works}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `director[].avatar` | `images/{avatar}` |
| `director[].name` | 加粗展示 |
| `director[].nameEn` | 小字展示 |
| `director[].works` | 逗号分隔 |

### 编剧表格

```markdown
### 编剧

| 姓名 | 外文名 | 角色 |
|------|--------|------|
| {name} | {nameEn} | {role} |
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `writer[].name` | 表格列 |
| `writer[].nameEn` | 表格列 |
| `writer[].role` | 表格列 |

### 主演卡片

```markdown
### 主演

<div style="display: flex; flex-wrap: wrap; gap: 16px; margin: 16px 0;">

<div style="width: 120px; text-align: center;">
<img src="images/{avatar}" width="100" height="100" style="border-radius: 4px; object-fit: cover;"><br>
<strong>{name}</strong><br>
<small>{nameEn}</small><br>
<small>饰 {role}</small>
</div>

</div>
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `cast[].avatar` | `images/{avatar}`（**如为空，显示"（头像待补充）"**） |
| `cast[].name` | 加粗展示 |
| `cast[].nameEn` | 小字展示 |
| `cast[].role` | `饰 {role}` |

**头像缺失处理**：

```markdown
<div style="width: 120px; text-align: center;">
<strong>{name}</strong><br>
<small>{nameEn}</small><br>
<small>饰 {role}</small><br>
<small style="color: #888;">（头像待补充）</small>
</div>
```

### 其他演员表格

```markdown
### 其他演员

| 姓名 | 外文名 | 饰演角色 |
|------|--------|----------|
| {name} | {nameEn} | {role} |
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `otherCast[].name` | 表格列 |
| `otherCast[].nameEn` | 表格列 |
| `otherCast[].role` | 表格列 |

## 视频区映射

### 有缩略图

```markdown
## 视频

<div style="display: flex; flex-wrap: wrap; gap: 16px; margin: 16px 0;">

<div style="width: 280px;">
<a href="{url}">
<img src="images/{thumbnail}" width="280" style="border-radius: 8px;"><br>
<strong>{title}</strong><br>
<small>{duration}</small>
</a>
</div>

</div>
```

### 无缩略图（降级方案）

```markdown
## 视频

| 标题 | 时长 | 链接 |
|------|------|------|
| {title} | {duration} | [观看]({url}) |
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `videos[].title` | 表格列或卡片标题 |
| `videos[].duration` | 表格列或卡片副标题 |
| `videos[].thumbnail` | 卡片图片（如有） |
| `videos[].url` | 链接 |

## 图片区映射

### 海报画廊

```markdown
## 图片

### 海报（共 {postersTotal} 张）

<div style="display: flex; flex-wrap: wrap; gap: 16px; margin: 16px 0;">

<img src="images/{poster}" width="160" style="border-radius: 8px;">
<img src="images/{poster1}" width="160" style="border-radius: 8px;">
...

</div>
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `images.poster` | 主海报单独展示 |
| `images.posters[]` | 补充海报画廊展示（160px宽，不重复主海报） |
| `images.postersTotal` | 补充海报数量说明（不含主海报） |

### 剧照画廊

```markdown
### 剧照（共 {stillsTotal} 张）

<div style="display: flex; flex-wrap: wrap; gap: 16px; margin: 16px 0;">

<img src="images/{still}" width="200" style="border-radius: 8px;">
...

</div>
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `images.stills[]` | 画廊展示（200px宽） |
| `images.stillsTotal` | 源站剧照总量说明（不等于本地下载数量） |

### 壁纸画廊

| data.json 字段 | 映射规则 |
|----------------|----------|
| `images.wallpapers[]` | 画廊展示（如有数据则展示） |

## 音乐区映射（新增）

```markdown
## 音乐

### 原声带

**专辑名称**：{soundtrackTitle}

**作曲**：{soundtrackComposer}

**发行日期**：{soundtrackYear}

**曲目列表**：

| 序号 | 曲名 | 演唱者 | 时长 |
|------|------|--------|------|
| 1 | {trackName} | {trackArtist} | {trackDuration} |
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `soundtrack.name` | 专辑名称 |
| `soundtrack.composer` | 作曲 |
| `soundtrack.year` | 发行日期 |
| `soundtrack.tracks[].name` | 曲名 |
| `soundtrack.tracks[].artist` | 演唱者 |
| `soundtrack.tracks[].duration` | 时长 |

**示例**：
```json
{
  "soundtrack": {
    "name": "Michael: Songs From The Motion Picture",
    "composer": "迈克尔·杰克逊",
    "year": 2026,
    "tracks": [
      { "name": "I'll Be There", "artist": "Jackson 5", "duration": "3:00" }
    ]
  }
}
```

```markdown
## 音乐

### 原声带

**专辑名称**：Michael: Songs From The Motion Picture

**作曲**：迈克尔·杰克逊

**发行日期**：2026

**曲目列表**：

| 序号 | 曲名 | 演唱者 | 时长 |
|------|------|--------|------|
| 1 | I'll Be There | Jackson 5 | 3:00 |
```

## 相似作品区映射

```markdown
## 相似作品（豆瓣推荐）

| 片名 | 年份 | 豆瓣评分 |
|------|------|----------|
| {title} | {year} | {rating} |
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `similar[].id` | 如存在则作为站内详情页链接目标 |
| `similar[].title` | 表格列 |
| `similar[].year` | 表格列 |
| `similar[].rating` | 表格列 |

## 精彩影评区映射

```markdown
## 精彩影评

### {author}（{date}）

> [{rating}]
>
> {content}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `reviews[].author` | 标题 |
| `reviews[].date` | 括号内 |
| `reviews[].rating` | 方括号内 |
| `reviews[].content` | 引用块 |

## 关联链接区映射

```markdown
## 关联链接

- [豆瓣电影]({doubanUrl})
- [IMDb]({imdbUrl})
- [TMDB]({tmdbUrl})（如有）
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `links.douban` | 链接 |
| `links.imdb` | 链接 |
| `links.tmdb` | 链接（如有数据则展示） |

## 数据来源说明区映射

```markdown
## 数据来源说明

**数据来源**：豆瓣、OMDb、百度百科、Wikipedia

**字段溯源**：见 source.json

**缺失字段**：见 raw/final-summary.md

| 数据源 | 贡献字段数 | 主要贡献 |
|--------|------------|----------|
| 豆瓣 | {count} | title, year, genre, cast... |
| OMDb | {count} | rated, awards, runtimeEn... |
| 百度百科 | {count} | soundtrack, boxOffice... |
| Wikipedia | {count} | wikibaseId, 演员头像... |
```

## 系统信息区映射

```markdown
## 系统信息

- 录入时间：{createdAt}
- 最后更新：{updatedAt}
- 系统ID：{id}
- 模块：{module}/{submodule}
```

| data.json 字段 | 映射规则 |
|----------------|----------|
| `createdAt` | 直接展示 |
| `updatedAt` | 直接展示 |
| `id` | 直接展示 |
| `module` | 直接展示 |
| `submodule` | 直接展示 |

## 特殊字段处理

### runtimeEn（IMDb片长）

**条件展示**：
- 如果 `runtimeEn` 有值，在片长后追加：`（IMDb: {runtimeEn}分钟）`
- 如果无值，只展示豆瓣片长

### rated（MPAA评级）

**条件展示**：
- 如果 `rated` 有值，在基本信息区新增一行：`**MPAA评级**：{rated}`
- 如果无值，不展示

### awards（获奖信息）

**条件展示**：
- 如果 `awards` 有值，在基本信息区新增一行：`**获奖**：{awards}`
- 如果无值，不展示

### soundtrack（原声带）

**条件展示**：
- 如果 `soundtrack.tracks` 有数据，展示完整音乐章节
- 如果无数据，不展示该章节

### cast[].avatar（演员头像）

**条件展示**：
- 如果有头像，展示图片
- 如果无头像，显示文字：`（头像待补充）`

## 更新记录

| 日期 | 变更 |
|------|------|
| 2026-05-01 | 初始版本，定义所有字段映射规则 |
