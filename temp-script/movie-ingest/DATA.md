# 数据字段设计

> 本文档描述 movie-ingest 的数据字段设计，包括数据库表结构、字段映射、各数据源字段说明。

---

## 1. 数据库表结构

### 1.1 核心表概览

| 表名 | 职责 | 关联 |
|------|------|------|
| `works` | 作品主表 | - |
| `person` | 人物主表 | - |
| `work_person` | 作品与人物关系 | works, person |
| `category` | 类型/标签表 | - |
| `work_category` | 作品与类型关系 | works, category |

### 1.2 works 表（作品主表）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              works 表结构                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 字段名              │ 类型      │ 说明                                       │
├──────────────────────┼───────────┼───────────────────────────────────────────┤
│ id                  │ String    │ 作品ID（格式：MMSSNNNNNN）                 │
│ module              │ Enum      │ 一级模块（video/book/music/game）          │
│ submodule           │ Enum      │ 二级模块（movie/tv_series等）              │
│ schema_type         │ Enum      │ 内容类型（live_action_movie等）            │
│ title               │ String    │ 中文标题                                   │
│ title_original      │ String    │ 原名（英文或源语言）                       │
│ other_titles        │ String    │ 别名（JSON数组）                           │
│ year                │ Int       │ 年份                                       │
│ country             │ String    │ 国家/地区                                  │
│ language            │ String    │ 语言                                       │
│ total_time          │ Int       │ 总时长（分钟）                             │
│ studio              │ String    │ 制片方                                     │
│ release_dates       │ String    │ 上映日期（JSON数组）                       │
│ quotes              │ String    │ 名言（JSON数组）                           │
│ scores              │ String    │ 评分（JSON对象）                           │
│ introduction        │ String    │ 简介（短文）                               │
│ story               │ String    │ 剧情（长文）                               │
│ external_source     │ String    │ 外部来源（JSON数组）                       │
│ images              │ String    │ 图片（JSON对象）                           │
│ videos              │ String    │ 视频（JSON数组）                           │
│ comments            │ String    │ 评论（JSON数组）                           │
│ soundtrack          │ String    │ 原声（JSON对象）                           │
│ related             │ String    │ 相关作品（JSON对象）                       │
│ status              │ Enum      │ 状态（draft/published/archived）           │
│ created_at          │ DateTime  │ 创建时间                                   │
│ updated_at          │ DateTime  │ 更新时间                                   │
└──────────────────────┴───────────┴───────────────────────────────────────────┘
```

### 1.3 person 表（人物主表）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              person 表结构                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 字段名              │ 类型      │ 说明                                       │
├──────────────────────┼───────────┼───────────────────────────────────────────┤
│ id                  │ Int       │ 自增主键                                   │
│ person_id           │ String    │ 人物代码（格式：p000001）                  │
│ name                │ String    │ 中文名                                     │
│ name_en             │ String    │ 英文名/原名                                │
│ source_ids          │ String    │ 外部来源ID（JSON对象）                     │
│ avatar_path         │ String    │ 主头像路径                                 │
│ tmdb_avatar_path    │ String    │ TMDB头像路径                               │
│ douban_avatar_path  │ String    │ 豆瓣头像路径                               │
│ profile_link        │ String    │ 默认外链                                   │
│ intro               │ String    │ 简介                                       │
└──────────────────────┴───────────┴───────────────────────────────────────────┘
```

**source_ids 结构**：

```json
{
  "tmdb": "4027",
  "douban": "p12345"
}
```

### 1.4 work_person 表（演职关系表）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           work_person 表结构                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ 字段名              │ 类型      │ 说明                                       │
├──────────────────────┼───────────┼───────────────────────────────────────────┤
│ id                  │ Int       │ 自增主键                                   │
│ work_id             │ String    │ 作品ID                                     │
│ person_id           │ Int       │ 人物ID（关联person.id）                    │
│ department          │ Enum      │ 部门（direction/writing/cast等）           │
│ role                │ String    │ 具体职位（导演/编剧/主演等）               │
│ character           │ String    │ 角色名（演员专用）                         │
│ character_en        │ String    │ 角色名英文                                 │
│ order               │ Int       │ 排序顺序                                   │
│ is_primary          │ Boolean   │ 是否主要人员                               │
└──────────────────────┴───────────┴───────────────────────────────────────────┘
```

**department 枚举值**：

| 值 | 说明 |
|---|---|
| direction | 导演 |
| writing | 编剧 |
| cast | 演员 |
| production | 制片 |
| music | 音乐 |
| book | 书籍作者 |
| translation | 译者 |
| original_work | 原著 |
| other | 其他 |

### 1.5 category 表（类型/标签表）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            category 表结构                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 字段名              │ 类型      │ 说明                                       │
├──────────────────────┼───────────┼───────────────────────────────────────────┤
│ id                  │ Int       │ 自增主键                                   │
│ group               │ Enum      │ 分组（type/tag）                           │
│ name                │ String    │ 名称（剧情/犯罪/科幻等）                   │
│ module              │ String    │ 模块作用域                                 │
│ submodule           │ String    │ 子模块作用域                               │
│ order               │ Int       │ 排序顺序                                   │
│ enabled             │ Boolean   │ 是否启用                                   │
└──────────────────────┴───────────┴───────────────────────────────────────────┘
```

---

## 2. 字段映射表

### 2.1 Staging JSON → Prisma Schema 映射

爬取脚本内部使用驼峰命名（camelCase），写入数据库时转换为下划线命名（snake_case）：

| Staging JSON | Prisma Schema | 类型 | 说明 |
|-------------|---------------|-----|------|
| id | id | String | 作品ID |
| title | title | String | 中文名 |
| originalTitle | title_original | String? | 英文名 |
| year | year | Int? | 年份 |
| country | country | String? | 地区 |
| language | language | String? | 语言 |
| runtime | total_time | Int? | 时长（分钟） |
| director | - | Json | 导演列表（写入work_person） |
| writer | - | Json | 编剧列表（写入work_person） |
| cast | - | Json | 主演列表（写入work_person） |
| otherCast | - | Json | 其他演员（写入work_person） |
| producer | - | Json | 制片人（写入work_person） |
| genre | - | Json | 类型列表（写入work_category） |
| tags | - | Json | 标签列表（写入work_category） |
| aka | other_titles | String? | 别名列表（JSON） |
| releaseDate | release_dates | String? | 上映日期（JSON） |
| doubanId | - | String? | 豆瓣ID（写入external_source） |
| imdbId | - | String? | IMDb ID（写入external_source） |
| tmdbId | - | String? | TMDB ID（写入external_source） |
| doubanRating | - | Float? | 豆瓣评分（写入scores） |
| imdbRating | - | Float? | IMDb评分（写入scores） |
| tmdbRating | - | Float? | TMDB评分（写入scores） |
| rottenTomatoes | - | Int? | 烂番茄评分（写入scores） |
| metascore | - | Int? | Metascore（写入scores） |
| synopsis | introduction | String? | 简介 |
| story | story | String? | 剧情 |
| images | images | String? | 图片（JSON） |
| videos | videos | String? | 视频（JSON） |
| reviews | comments | String? | 评论（JSON） |
| similar | related | String? | 相似推荐（JSON） |
| soundtrack | soundtrack | String? | 原声（JSON） |
| quotes | quotes | String? | 名言（JSON） |

### 2.2 演职员字段映射

**director/writer/cast 结构**：

```json
{
  "personCode": "p000001",
  "name": "弗兰克·德拉邦特",
  "nameEn": "Frank Darabont",
  "role": "导演",
  "avatarPath": "people/tmdb-4027-avatar.jpg"
}
```

| 字段 | 说明 | 来源 |
|------|------|------|
| personCode | 人物代码 | 系统生成 |
| name | 中文名 | 豆瓣 |
| nameEn | 英文名 | TMDB |
| role | 职位/角色名 | 豆瓣/TMDB |
| avatarPath | 头像路径 | TMDB |

---

## 3. 数据源字段说明

### 3.1 豆瓣 (douban.json)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           douban.json 结构                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 字段名              │ 类型           │ 说明                                  │
├──────────────────────┼────────────────┼──────────────────────────────────────┤
│ douban_id           │ String         │ 豆瓣ID                                │
│ url                 │ String         │ 豆瓣链接                              │
│ source              │ String         │ 来源标识（"douban"）                  │
│ title               │ String         │ 中文标题                              │
│ year                │ String         │ 年份                                  │
│ rating              │ String         │ 豆瓣评分                              │
│ rating_count        │ String         │ 评分人数                              │
│ main_poster_url     │ String         │ 主海报URL                             │
│ directors           │ Array<String>  │ 导演列表（中文名）                    │
│ writers             │ Array<String>  │ 编剧列表（中文名）                    │
│ casts               │ Array<String>  │ 演员列表（中文名）                    │
│ genres              │ Array<String>  │ 类型列表                              │
│ countries           │ String         │ 国家/地区                             │
│ languages           │ String         │ 语言                                  │
│ release_dates       │ Array<Object>  │ 上映日期                              │
│ runtime_minutes     │ Number         │ 时长（分钟）                          │
│ aliases             │ Array<String>  │ 别名列表                              │
│ imdb_id             │ String         │ IMDb ID                               │
│ production_companies│ Array<String>  │ 制片公司                              │
│ summary             │ String         │ 简介                                  │
│ story               │ String         │ 剧情                                  │
│ tags                │ Array<String>  │ 标签列表                              │
│ poster              │ String         │ 海报URL                               │
│ recommendations     │ Array<Object>  │ 豆瓣推荐；最终合并进 similar          │
│ comments            │ Array<Object>  │ 短评                                  │
│ reviews             │ Array<Object>  │ 影评                                  │
│ images              │ Object         │ 图片信息                              │
└──────────────────────┴────────────────┴──────────────────────────────────────┘
```

**release_dates 结构**：

```json
[
  { "date": "1994-09-10", "location": "多伦多电影节" },
  { "date": "1994-10-14", "location": "美国" }
]
```

**recommendations 结构**：

```json
[
  { "title": "阿甘正传", "douban_id": "1292720" }
]
```

**comments/reviews 结构**：

```json
{
  "author": "作者名",
  "source": "豆瓣短评",
  "date": "2024-01-01",
  "content": "评论内容...",
  "url": "原文链接"
}
```

### 3.2 TMDB (tmdb.json)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            tmdb.json 结构                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 字段名              │ 类型           │ 说明                                  │
├──────────────────────┼────────────────┼──────────────────────────────────────┤
│ imdb_id             │ String         │ IMDb ID                               │
│ source              │ String         │ 来源标识（"tmdb"）                    │
│ detail              │ Object         │ 电影详情                              │
│ credits             │ Object         │ 演职员信息                            │
│ images              │ Object         │ 图片信息                              │
│ videos              │ Array<Object>  │ 视频列表                              │
│ reviews             │ Array<Object>  │ 评论列表                              │
└──────────────────────┴────────────────┴──────────────────────────────────────┘
```

**detail 结构**：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           detail 子结构                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 字段名              │ 类型           │ 说明                                  │
├──────────────────────┼────────────────┼──────────────────────────────────────┤
│ tmdb_id             │ Number         │ TMDB ID                               │
│ source              │ String         │ 来源标识                              │
│ title               │ String         │ 中文标题                              │
│ original_title      │ String         │ 原标题                                │
│ year                │ String         │ 年份                                  │
│ overview            │ String         │ 简介                                  │
│ runtime_minutes     │ Number         │ 时长（分钟）                          │
│ genres              │ Array<String>  │ 类型列表                              │
│ countries           │ Array<String>  │ 国家列表                              │
│ languages           │ Array<String>  │ 语言列表                              │
│ production_companies│ Array<String>  │ 制片公司                              │
│ rating              │ Number         │ TMDB评分                              │
│ rating_count        │ Number         │ 评分人数                              │
│ imdb_id             │ String         │ IMDb ID                               │
│ poster              │ String         │ 海报URL                               │
│ backdrop            │ String         │ 背景图URL                             │
└──────────────────────┴────────────────┴──────────────────────────────────────┘
```

**credits 结构**：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           credits 子结构                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 字段名              │ 类型           │ 说明                                  │
├──────────────────────┼────────────────┼──────────────────────────────────────┤
│ tmdb_id             │ Number         │ TMDB ID                               │
│ source              │ String         │ 来源标识                              │
│ cast                │ Array<Object>  │ 演员列表                              │
│ crew                │ Array<Object>  │ 幕后人员列表                          │
└──────────────────────┴────────────────┴──────────────────────────────────────┘
```

**cast 结构**：

```json
{
  "id": 504,
  "name": "Tim Robbins",
  "character": "Andy Dufresne",
  "profile_path": "/abc123.jpg",
  "order": 0
}
```

**crew 结构**：

```json
{
  "id": 4027,
  "name": "Frank Darabont",
  "job": "Director",
  "department": "Directing",
  "profile_path": "/def456.jpg"
}
```

**images 结构**：

```json
{
  "posters": [
    { "url": "https://image.tmdb.org/t/p/original/xxx.jpg", "width": 2000, "height": 3000 }
  ],
  "backdrops": [
    { "url": "https://image.tmdb.org/t/p/original/yyy.jpg", "width": 3840, "height": 2160 }
  ]
}
```

### 3.3 OMDb (omdb.json)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            omdb.json 结构                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 字段名              │ 类型           │ 说明                                  │
├──────────────────────┼────────────────┼──────────────────────────────────────┤
│ imdb_id             │ String         │ IMDb ID                               │
│ source              │ String         │ 来源标识（"omdb"）                    │
│ title               │ String         │ 英文标题                              │
│ year                │ String         │ 年份                                  │
│ rated               │ String         │ 分级（R/PG-13等）                     │
│ runtime             │ String         │ 时长（"142 min"）                     │
│ genres              │ Array<String>  │ 类型列表                              │
│ directors           │ Array<String>  │ 导演列表                              │
│ writers             │ Array<String>  │ 编剧列表                              │
│ actors              │ Array<String>  │ 演员列表                              │
│ plot                │ String         │ 简介                                  │
│ languages           │ Array<String>  │ 语言列表                              │
│ countries           │ Array<String>  │ 国家列表                              │
│ awards              │ String         │ 获奖信息                              │
│ poster              │ String         │ 海报URL                               │
│ ratings             │ Object         │ 各平台评分                            │
└──────────────────────┴────────────────┴──────────────────────────────────────┘
```

**ratings 结构**：

```json
{
  "imdb": { "value": "9.3", "scale": "10" },
  "rottenTomatoes": { "value": "9.1", "scale": "10", "tomatometer": 91 },
  "metascore": { "value": "8.2", "scale": "10", "raw": 82 }
}
```

### 3.4 百度百科 (baike.json)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           baike.json 结构                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 字段名              │ 类型           │ 说明                                  │
├──────────────────────┼────────────────┼──────────────────────────────────────┤
│ url                 │ String         │ 百度百科链接                          │
│ source              │ String         │ 来源标识（"baike"）                   │
│ title               │ String         │ 词条标题                              │
│ baike_id            │ String         │ 百度百科ID                            │
│ summary             │ String         │ 摘要                                  │
└──────────────────────┴────────────────┴──────────────────────────────────────┘
```

### 3.5 Wikipedia (wikipedia.json)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          wikipedia.json 结构                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ 字段名              │ 类型           │ 说明                                  │
├──────────────────────┼────────────────┼──────────────────────────────────────┤
│ url                 │ String         │ Wikipedia链接                         │
│ source              │ String         │ 来源标识（"wikipedia"）               │
│ title               │ String         │ 词条标题                              │
│ wikipedia_id        │ String         │ Wikipedia ID                          │
│ summary             │ String         │ 摘要                                  │
│ awards              │ Array<Object>  │ 获奖信息                              │
│ quotes              │ Array<Object>  │ 名言名句                              │
└──────────────────────┴────────────────┴──────────────────────────────────────┘
```

**awards 结构**：

```json
[
  { "name": "奥斯卡最佳影片", "year": 1995, "result": "提名" }
]
```

**quotes 结构**：

```json
[
  { "text": "希望是美好的事物...", "speaker": "安迪" }
]
```

### 3.6 烂番茄 (rotten_tomatoes.json)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       rotten_tomatoes.json 结构                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 字段名              │ 类型           │ 说明                                  │
├──────────────────────┼────────────────┼──────────────────────────────────────┤
│ title               │ String         │ 电影标题                              │
│ source              │ String         │ 来源标识（"rotten_tomatoes"）         │
│ tomatometer         │ Number         │ 烂番茄指数（0-100）                   │
│ audience_score      │ Number         │ 观众评分（0-100）                     │
│ consensus           │ String         │ 评论共识                              │
└──────────────────────┴────────────────┴──────────────────────────────────────┘
```

### 3.7 Metacritic (metacritic.json)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          metacritic.json 结构                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 字段名              │ 类型           │ 说明                                  │
├──────────────────────┼────────────────┼──────────────────────────────────────┤
│ title               │ String         │ 电影标题                              │
│ source              │ String         │ 来源标识（"metacritic"）              │
│ metascore           │ Number         │ Metascore（0-100）                    │
│ user_score          │ Number         │ 用户评分（0-10）                      │
└──────────────────────┴────────────────┴──────────────────────────────────────┘
```

---

## 4. 数据来源对照表

### 4.1 基本信息字段来源

| 字段 | 主要来源 | 备用来源 | 说明 |
|-----|---------|---------|------|
| title（中文名） | 豆瓣 | 百度百科 | 优先豆瓣 |
| originalTitle（英文名） | TMDB | OMDb | 外文网站 |
| year（年份） | 豆瓣 | TMDB | - |
| country（地区） | 豆瓣 | - | 豆瓣最准确 |
| language（语言） | 豆瓣 | - | 豆瓣最准确 |
| runtime（时长） | 豆瓣 | TMDB | - |
| genre（类型） | 豆瓣 | TMDB | 中文类型名 |
| synopsis（简介） | 豆瓣 | 百度百科 | 优先豆瓣 |
| story（剧情） | Wikipedia | 百度百科 | 详细剧情 |
| aka（别名） | 豆瓣 | - | - |
| releaseDate（上映日期） | 豆瓣 | TMDB | - |

### 4.2 评分字段来源

| 字段 | 来源 | 说明 |
|-----|------|------|
| doubanRating | 豆瓣 | 10分制 |
| imdbRating | OMDb / TMDB | 10分制 |
| tmdbRating | TMDB | 10分制 |
| rottenTomatoes | OMDb / 烂番茄 | 百分制 |
| metascore | OMDb / Metacritic | 百分制 |

### 4.3 演职员字段来源

| 字段 | 中文名 | 英文名 | 角色名 | 头像 |
|-----|-------|-------|-------|-----|
| 导演 | 豆瓣 | TMDB | - | TMDB |
| 编剧 | 豆瓣 | TMDB | TMDB | TMDB |
| 演员 | 豆瓣 | TMDB | TMDB | TMDB |

**说明**：
- 中文名从国内网站获取（豆瓣、百度百科）
- 英文名、角色名、头像从外文网站获取（TMDB）
- 百度百科演职员数据不可靠，不作为主要来源

### 4.4 图片字段来源

| 字段 | 主要来源 | 备用来源 | 说明 |
|-----|---------|---------|------|
| poster（海报） | TMDB | 豆瓣 | TMDB 图片质量高 |
| stills（剧照） | TMDB | 豆瓣 | - |
| backdrops（背景图） | TMDB | - | - |
| 人物头像 | TMDB | 豆瓣 | TMDB 头像质量高 |

### 4.5 其他字段来源

| 字段 | 来源 | 说明 |
|-----|------|------|
| awards（奖项） | Wikipedia | 百度百科 |
| quotes（名言） | Wikipedia | - |
| soundtrack（原声） | TMDB | - |
| videos（视频） | TMDB | - |
| similar（相似推荐） | 豆瓣推荐 | TMDB recommendations / similar 不使用 |
| reviews（评论） | 豆瓣/TMDB/烂番茄/Metacritic | 各平台独立 |

---

## 5. 数据合并规则

### 5.1 合并优先级

```
豆瓣 > TMDB > OMDb > 百度百科 > Wikipedia > 烂番茄 > Metacritic
```

### 5.2 字段合并策略

| 情况 | 策略 |
|------|------|
| 字段只有一个来源 | 直接使用 |
| 字段有多个来源 | 按优先级选择 |
| 字段冲突 | 豆瓣优先，记录来源 |
| 字段缺失 | 使用备用来源 |

### 5.3 演职员合并策略

1. **导演/编剧**：
   - 中文名从豆瓣获取
   - 英文名从 TMDB 获取
   - 通过名字匹配合并

2. **演员**：
   - 中文名从豆瓣获取
   - 英文名、角色名从 TMDB 获取
   - 通过名字匹配合并
   - 按豆瓣顺序排序

3. **头像**：
   - 优先使用 TMDB 头像
   - TMDB 无头像时使用豆瓣头像

---

## 6. 数据验证规则

### 6.1 必填字段

| 字段 | 验证规则 |
|------|---------|
| title | 非空 |
| year | 1888-当前年份+1 |
| doubanId | 非空 |

### 6.2 字段格式

| 字段 | 格式 |
|------|------|
| id | MMSSNNNNNN（10位数字） |
| personCode | pNNNNNN（p+6位数字） |
| releaseDate.date | YYYY-MM-DD |
| avatarPath | people/tmdb-{id}-avatar.jpg |

### 6.3 数据完整性检查

```python
def validate_work_data(data: Dict) -> bool:
    """验证作品数据完整性"""
    required = ['id', 'title', 'year', 'doubanId']
    for field in required:
        if not data.get(field):
            Logger.warning(f"缺失必填字段: {field}")
            return False
    return True
```
