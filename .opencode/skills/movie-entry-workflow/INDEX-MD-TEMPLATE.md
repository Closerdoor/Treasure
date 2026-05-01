# index.md 必须展示字段模板

本文档定义 index.md 必须展示的字段和章节结构，确保 data.json 中的所有数据都能正确展示。

## 章节结构

```markdown
# {title} {originalTitle} ({year})

[海报 + 基本信息区]

---

[剧情简介内容，无标题]

---

## 演职员信息

### 导演
[导演卡片]

### 编剧
[编剧表格]

### 主演
[主演卡片]

### 其他演员
[其他演员表格]

---

## 视频

[视频列表或表格]

---

## 图片

### 海报
[海报画廊]

### 剧照
[剧照画廊]

---

## 音乐

[原声带信息]

---

## 相似作品（豆瓣推荐）

[相似作品列表]

---

## 精彩影评

[影评列表]

---

## 关联链接

[链接列表]

---

## 数据来源说明

[数据源统计]

---

## 系统信息

[系统元数据]
```

## 基本信息区（必须展示）

| 字段 | data.json 路径 | 展示格式 | 必须性 |
|------|----------------|----------|--------|
| 标题 | `title` | `# {title}` | 必须 |
| 原标题 | `originalTitle` | `{originalTitle}` | 必须 |
| 年份 | `year` | `({year})` | 必须 |
| 导演 | `director[].name` | `**导演**：{names}` | 必须 |
| 编剧 | `writer[].name` | `**编剧**：{names}` | 必须 |
| 主演 | `cast[].name` | `**主演**：{前5位 names}` | 必须 |
| 类型 | `genre` | `**类型**：{items}` | 必须 |
| 制片国家 | `country` | `**制片国家/地区**：{value}` | 必须 |
| 语言 | `language` | `**语言**：{value}` | 必须 |
| 上映日期 | `releaseDate` | `**上映日期**：{formatted}` | 必须 |
| 片长 | `runtime` | `**片长**：{runtime}分钟` | 必须 |
| IMDb片长 | `runtimeEn` | `（IMDb: {runtimeEn}分钟）` | 可选（如有数据则展示） |
| 又名 | `aka` | `**又名**：{items}` | 必须 |
| IMDb ID | `imdbId` | `**IMDb**：{id}` | 必须 |
| 豆瓣评分 | `doubanRating` | `**豆瓣评分**：**{rating}** / {votes}人评价` | 必须 |
| MPAA评级 | `rated` | `**MPAA评级**：{value}` | **必须（如有数据）** |
| 获奖信息 | `awards` | `**获奖**：{value}` | **必须（如有数据）** |

## 演职员信息区（必须展示）

### 导演

| 字段 | data.json 路径 | 展示格式 |
|------|----------------|----------|
| 头像 | `director[].avatar` | `<img src="images/{avatar}">` |
| 中文名 | `director[].name` | `<strong>{name}</strong>` |
| 英文名 | `director[].nameEn` | `<small>{nameEn}</small>` |
| 代表作 | `director[].works` | `**代表作**：{works}` |

### 编剧

| 字段 | data.json 路径 | 展示格式 |
|------|----------------|----------|
| 中文名 | `writer[].name` | 表格列 |
| 英文名 | `writer[].nameEn` | 表格列 |
| 角色 | `writer[].role` | 表格列 |

### 主演

| 字段 | data.json 路径 | 展示格式 |
|------|----------------|----------|
| 头像 | `cast[].avatar` | `<img src="images/{avatar}">`（如无头像，显示"待补充"） |
| 中文名 | `cast[].name` | `<strong>{name}</strong>` |
| 英文名 | `cast[].nameEn` | `<small>{nameEn}</small>` |
| 饰演角色 | `cast[].role` | `<small>饰 {role}</small>` |

### 其他演员

| 字段 | data.json 路径 | 展示格式 |
|------|----------------|----------|
| 中文名 | `otherCast[].name` | 表格列 |
| 英文名 | `otherCast[].nameEn` | 表格列 |
| 饰演角色 | `otherCast[].role` | 表格列 |

## 视频区（必须展示）

| 字段 | data.json 路径 | 展示格式 |
|------|----------------|----------|
| 标题 | `videos[].title` | 表格列或卡片标题 |
| 时长 | `videos[].duration` | 表格列或卡片副标题 |
| 缩略图 | `videos[].thumbnail` | `<img src="images/{thumbnail}">` 或表格省略 |
| 链接 | `videos[].url` | `[观看]({url})` |

**降级方案**：如果缩略图下载失败，使用表格链接形式：

```markdown
| 标题 | 时长 | 链接 |
|------|------|------|
| 预告片1 | 01:00 | [观看](URL) |
```

## 图片区（必须展示）

### 海报

| 字段 | data.json 路径 | 展示格式 |
|------|----------------|----------|
| 主海报 | `images.poster` | 顶部展示（200px宽） |
| 海报列表 | `images.posters` | 补充海报画廊（160px宽，不重复主海报） |
| 海报总数 | `images.postersTotal` | 补充海报数量说明（不含主海报） |

### 剧照

| 字段 | data.json 路径 | 展示格式 |
|------|----------------|----------|
| 剧照列表 | `images.stills` | 画廊（200px宽） |
| 剧照总数 | `images.stillsTotal` | 源站剧照总量说明（不等于本地下载数量） |

### 壁纸

| 字段 | data.json 路径 | 展示格式 |
|------|----------------|----------|
| 壁纸列表 | `images.wallpapers` | 画廊展示（如有数据则展示） |

## 音乐区（如有数据则必须展示）

| 字段 | data.json 路径 | 展示格式 |
|------|----------------|----------|
| 专辑名称 | `soundtrack.name` | `**专辑名称**：{name}` |
| 作曲 | `soundtrack.composer` | `**作曲**：{composer}` |
| 发行年份 | `soundtrack.year` | `**发行日期**：{year}` |
| 曲目列表 | `soundtrack.tracks` | 表格形式 |

**曲目表格格式**：

```markdown
| 序号 | 曲名 | 演唱者 | 时长 |
|------|------|--------|------|
| 1 | I'll Be There | Jackson 5 | 3:00 |
```

## 相似作品区（必须展示）

| 字段 | data.json 路径 | 展示格式 |
|------|----------------|----------|
| 站内ID | `similar[].id` | 如存在则优先用于站内跳转 |
| 标题 | `similar[].title` | 列表项 |
| 年份 | `similar[].year` | `({year})` |
| 评分 | `similar[].rating` | `{rating}分` |

## 精彩影评区（必须展示）

| 字段 | data.json 路径 | 展示格式 |
|------|----------------|----------|
| 作者 | `reviews[].author` | `**{author}**` |
| 日期 | `reviews[].date` | `{date}` |
| 评分 | `reviews[].rating` | `[{rating}]` |
| 内容 | `reviews[].content` | 引用块 |

## 关联链接区（必须展示）

| 字段 | data.json 路径 | 展示格式 |
|------|----------------|----------|
| 豆瓣 | `links.douban` | `[豆瓣电影]({url})` |
| IMDb | `links.imdb` | `[IMDb]({url})` |
| TMDB | `links.tmdb` | `[TMDB]({url})`（值不为 `null` 时展示） |

## 数据来源说明区（必须展示）

展示各数据源贡献统计：

```markdown
**数据来源**：豆瓣、OMDb、百度百科、Wikipedia

**字段溯源**：见 source.json

**缺失字段**：见 raw/final-summary.md
```

## 系统信息区（必须展示）

| 字段 | data.json 路径 | 展示格式 |
|------|----------------|----------|
| 录入时间 | `createdAt` | `录入时间：{date}` |
| 更新时间 | `updatedAt` | `最后更新：{date}` |
| 系统ID | `id` | `系统ID：{id}` |

## 条件展示规则

### 必须展示（无条件）

- 基本信息（title, year, director, cast, genre 等）
- 剧情简介（无标题，直接显示内容）
- 演职员信息
- 图片（至少主海报）
- 数据来源说明
- 系统信息

### 有数据则展示

- **MPAA评级**（`rated`）：如有数据，在基本信息区展示
- **获奖信息**（`awards`）：如有数据，在基本信息区展示
- **IMDb片长**（`runtimeEn`）：如有数据，在片长后括号内展示
- **音乐原声带**（`soundtrack`）：如有数据，展示完整章节
- **视频**（`videos`）：如有数据，展示视频区
- **相似作品**（`similar`）：如有数据，展示相似作品区
- **精彩影评**（`reviews`）：如有数据，展示影评区

### 无数据则标注

- 演员头像缺失：显示"（头像待补充）"
- 字段缺失：在数据来源说明区标注

## 验证检查清单

生成 index.md 后，必须检查以下项目：

- [ ] 基本信息区包含所有必须字段
- [ ] `rated` 字段如有数据已展示
- [ ] `awards` 字段如有数据已展示
- [ ] `runtimeEn` 字段如有数据已展示
- [ ] `soundtrack` 字段如有数据已展示完整章节
- [ ] 演员头像缺失已标注"待补充"
- [ ] 数据来源说明区已包含溯源信息
- [ ] 系统信息区已包含录入时间

## 更新记录

| 日期 | 变更 |
|------|------|
| 2026-05-01 | 初始版本，定义必须展示字段和章节结构 |
