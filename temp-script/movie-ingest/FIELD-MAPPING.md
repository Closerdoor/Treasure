# 电影数据字段映射文档

本文档记录电影数据字段与数据库表结构的对应关系，用于数据导入时参考。

---

## 一、数据库表结构概览

| 表名 | 职责 |
|------|------|
| `works` | 作品主表（电影基本信息） |
| `people` | 人物主表（导演、演员、编剧等） |
| `work_credits` | 作品与人物关系表（演职人员） |
| `terms` | 词项表（类型、标签） |
| `work_terms` | 作品与词项关联表 |

---

## 二、`works` 表字段映射

### 2.1 普通字段

| 业务字段 | 数据库字段 | 类型 | 来源优先级 | 示例值 |
|----------|-----------|------|-----------|--------|
| 电影名称(中文) | `title` | TEXT | 豆瓣 > TMDB | `星际穿越` |
| 原名 | `original_title` | TEXT | TMDB > 豆瓣 | `Interstellar` |
| 年份 | `year` | INTEGER | 豆瓣 > TMDB | `2014` |
| 制片国家/地区 | `country` | TEXT | 豆瓣 > TMDB | `美国` |
| 语言 | `language` | TEXT | 豆瓣 > TMDB | `英语` |
| 片长 | `runtime_minutes` | INTEGER | 豆瓣 > TMDB | `169` |
| 电影简介 | `synopsis_text` | TEXT | 豆瓣 > 百度百科 | `短简介文本` |
| 剧情详解 | `story_text` | TEXT | 豆瓣 > 百度百科 | `完整剧情文本` |
| 作品 ID | `id` | TEXT | 系统生成 | `0101000006` |
| 一级模块 | `module` | TEXT | 固定值 | `video` |
| 二级分类 | `submodule` | TEXT | 固定值 | `movie` |
| 结构类型 | `schema_type` | TEXT | TMDB > 豆瓣 | `live_action_movie` |
| 数据状态 | `status` | TEXT | 固定值 | `published` |

---

### 2.2 JSON 字段

#### `aliases_json`（别名）

| 业务字段 | JSON 字段 | 类型 | 来源 |
|----------|----------|------|------|
| 更多片名 | 整个数组 | JSON Array | 豆瓣 + TMDB（去重合并） |

**结构示例**：
```json
["星际启示录", "星际效应", "月黑高飞(港)", "刺激1995(台)"]
```

---

#### `release_dates_json`（上映日期）

| 业务字段 | JSON 字段 | 类型 | 来源 |
|----------|----------|------|------|
| 上映日期 | 整个数组 | JSON Array | 豆瓣 + TMDB（去重合并） |

**结构示例**：
```json
[
  {"date": "2014-10-26", "location": "洛杉矶首映"},
  {"date": "2014-11-07", "location": "中国大陆"},
  {"date": "2014-11-12", "location": "美国"}
]
```

---

#### `identifiers_json`（外部 ID）

| 业务字段 | JSON 字段 | 类型 | 来源 |
|----------|----------|------|------|
| 豆瓣 ID | `douban` | STRING | 豆瓣 |
| IMDB ID | `imdb` | STRING | OMDb / TMDB |
| TMDB ID | `tmdb` | STRING | TMDB |
| 百度百科词条名 | `baike` | STRING | 百度百科 |
| 中文 Wikipedia 词条名 | `wikipedia_zh` | STRING | Wikipedia |

**结构示例**：
```json
{
  "douban": "1889243",
  "imdb": "tt0816692",
  "tmdb": "157336",
  "baike": "星际穿越",
  "wikipedia_zh": "星际穿越_(电影)"
}
```

---

#### `ratings_json`（评分）

| 业务字段 | JSON 字段 | 类型 | 来源 | 说明 |
|----------|----------|------|------|------|
| 综合评分 | `aggregate.value` | NUMBER | 计算生成 | 10 分制 |
| 豆瓣评分 | `douban.value` | NUMBER | 豆瓣 | 10 分制 |
| IMDB 评分 | `imdb.value` | NUMBER | OMDb | 10 分制 |
| TMDB 评分 | `tmdb.value` | NUMBER | TMDB | 10 分制 |
| 烂番茄评分 | `rottenTomatoes.value` | NUMBER | OMDb | 10 分制（换算） |
| 烂番茄原始评分 | `rottenTomatoes.tomatometer` | NUMBER | OMDb | 原始百分比（73） |
| Metacritic 评分 | `metascore.value` | NUMBER | OMDb | 10 分制（换算） |
| Metacritic 原始评分 | `metascore.raw` | NUMBER | OMDb | 原始分数（74） |
| 分级 | `certification.value` | STRING | OMDb | `PG-13` |
| 获奖 | `awards.value` | STRING | OMDb / Wikipedia | `Won 1 Oscar...` |

**结构示例**：
```json
{
  "aggregate": {"value": 8.0, "scale": 10},
  "douban": {"value": 9.4, "scale": 10},
  "imdb": {"value": 8.7, "scale": 10},
  "tmdb": {"value": 8.3, "scale": 10},
  "rottenTomatoes": {"value": 7.3, "scale": 10, "tomatometer": 73},
  "metascore": {"value": 7.4, "scale": 10, "raw": 74},
  "certification": {"value": "PG-13"},
  "awards": {"value": "Won 1 Oscar. 45 wins & 148 nominations total"}
}
```

**处理规则**：
- 所有评分统一转换为 10 分制
- 无评分时 `value` 为 `null`
- 保留原始分数在 `tomatometer` / `raw` 字段

---

#### `links_json`（外部链接）

| 业务字段 | JSON 字段 | 类型 | 来源 |
|----------|----------|------|------|
| 豆瓣链接 | `douban` | STRING | 豆瓣 |
| IMDB 链接 | `imdb` | STRING | OMDb / TMDB |
| TMDB 链接 | `tmdb` | STRING | TMDB |
| 百度百科链接 | `baike` | STRING | 百度百科 |
| 中文 Wikipedia 链接 | `wikipedia_zh` | STRING | Wikipedia |
| 烂番茄链接 | `rottenTomatoes` | STRING | 烂番茄 |
| Metacritic 链接 | `metacritic` | STRING | Metacritic |

**结构示例**：
```json
{
  "douban": "https://movie.douban.com/subject/1889243/",
  "imdb": "https://www.imdb.com/title/tt0816692/",
  "tmdb": "https://www.themoviedb.org/movie/157336",
  "baike": "https://baike.baidu.com/item/星际穿越",
  "wikipedia_zh": "https://zh.wikipedia.org/wiki/星际穿越_(电影)",
  "rottenTomatoes": "https://www.rottentomatoes.com/m/interstellar_2014",
  "metacritic": "https://www.metacritic.com/movie/interstellar"
}
```

---

#### `images_json`（图片）

| 业务字段 | JSON 字段 | 类型 | 来源优先级 | 说明 |
|----------|----------|------|-----------|------|
| 电影封面海报图 | `poster` | STRING | 豆瓣 > TMDB | 主海报文件名 |
| 补充海报 | `posters` | ARRAY | TMDB > 豆瓣 | 海报列表 |
| 剧照 | `stills` | ARRAY | TMDB > 豆瓣 | 剧照列表 |
| 壁纸 | `wallpapers` | ARRAY | TMDB | 壁纸列表 |
| 海报总数 | `postersTotal` | NUMBER | 豆瓣 | 源站总量元数据 |
| 剧照总数 | `stillsTotal` | NUMBER | 豆瓣 | 源站总量元数据 |
| 资源目录 | `assetDir` | STRING | 系统生成 | `video/movie/0101000006` |

**结构示例**：
```json
{
  "poster": "poster-main.jpg",
  "posters": ["poster-01.jpg", "poster-02.jpg"],
  "stills": ["still-01.jpg", "still-02.jpg"],
  "wallpapers": [],
  "postersTotal": 250,
  "stillsTotal": 169,
  "assetDir": "video/movie/0101000006"
}
```

**图片去重规则**：
1. URL 去重（相同 URL 跳过）
2. 文件名去重（相同文件名跳过）
3. 内容哈希去重（下载后计算 MD5，相同跳过）
4. 跨来源去重（豆瓣和 TMDB 同一张图片只保留一份）

---

#### `videos_json`（视频）

| 业务字段 | JSON 字段 | 类型 | 来源 | 说明 |
|----------|----------|------|------|------|
| 视频封面图 | `thumbnail` | STRING | TMDB | 封面图 URL |
| 视频名称 | `name` | STRING | TMDB | `Official Trailer` |
| 视频时间 | `duration` | STRING | TMDB | `2:30` |
| 视频类型 | `type` | STRING | TMDB | `trailer` / `clip` |
| 视频来源 | `source` | STRING | TMDB | `youtube` |
| 视频标识 | `key` | STRING | TMDB | YouTube 视频 ID |
| 点击跳转链接 | `url` | STRING | TMDB | 完整 URL |

**结构示例**：
```json
[
  {
    "type": "trailer",
    "name": "Official Trailer",
    "thumbnail": "https://img.youtube.com/vi/zSWdZVtXT7E/maxresdefault.jpg",
    "duration": "2:30",
    "source": "youtube",
    "key": "zSWdZVtXT7E",
    "url": "https://www.youtube.com/watch?v=zSWdZVtXT7E"
  }
]
```

---

#### `reviews_json`（影评）

| 业务字段 | JSON 字段 | 类型 | 来源 | 说明 |
|----------|----------|------|------|------|
| 影评人 | `author` | STRING | 各来源 | |
| 影评来源 | `source` | STRING | 各来源 | 见下方标识规则 |
| 影评时间 | `date` | STRING | 各来源 | `2014-11-07` |
| 影评内容 | `content` | STRING | 各来源 | |
| 影评标题 | `title` | STRING | 各来源 | 短评为 `null` |
| 影评来源跳转链接 | `url` | STRING | 各来源 | 短评为 `null` |

**来源标识规则**：
| 来源 | `source` 格式 |
|------|---------------|
| 豆瓣短评 | `豆瓣短评` |
| 豆瓣长评 | `豆瓣长评` |
| TMDB | `TMDB` |
| 烂番茄 | `Rotten Tomatoes · {媒体名}` |
| Metacritic | `Metacritic · {媒体名}` |

**结构示例**：
```json
[
  {
    "author": "QuiteThrilling",
    "source": "豆瓣长评",
    "date": "2014-11-07",
    "content": "评论内容...",
    "url": "https://movie.douban.com/review/7181757/",
    "title": "当你想描写一个触手可及的未来，然而却……"
  },
  {
    "author": "比岁月含蓄",
    "source": "豆瓣短评",
    "date": "2014-11-06",
    "content": "时间可以伸缩和折叠...",
    "url": null,
    "title": null
  },
  {
    "author": "Matt Brunson",
    "source": "Rotten Tomatoes · Film Frenzy",
    "date": "Nov 3",
    "content": "Deeply flawed but also wholly absorbing...",
    "url": "https://www.rottentomatoes.com/m/interstellar_2014/reviews",
    "title": null
  }
]
```

**数量要求**：每源严格 20 条

---

#### `soundtrack_json`（音乐原声）

| 业务字段 | JSON 字段 | 类型 | 来源 |
|----------|----------|------|------|
| 专辑名 | `albums[].name` | STRING | TMDB / Wikipedia |
| 专辑备注 | `albums[].note` | STRING | TMDB / Wikipedia |
| 专辑封面图片 | `albums[].coverImage` | STRING | TMDB / Wikipedia |
| 专辑发行日期 | `albums[].releaseDate` | STRING | TMDB / Wikipedia |
| 专辑类型 | `albums[].type` | STRING | TMDB / Wikipedia |
| 歌名 | `albums[].tracks[].name` | STRING | TMDB / Wikipedia |
| 歌手 | `albums[].tracks[].artist` | STRING | TMDB / Wikipedia |
| 时长 | `albums[].tracks[].duration` | STRING | TMDB / Wikipedia |

**结构示例**：
```json
{
  "albums": [
    {
      "name": "Interstellar (Original Motion Picture Soundtrack)",
      "note": "Hans Zimmer",
      "coverImage": "soundtrack-cover-01.jpg",
      "releaseDate": "2014-11-18",
      "type": "soundtrack",
      "tracks": [
        {"name": "Dreaming of the Crash", "artist": "Hans Zimmer", "duration": "2:26"},
        {"name": "Cornfield Chase", "artist": "Hans Zimmer", "duration": "2:07"}
      ]
    }
  ]
}
```

---

#### `relations_json`（系列/相似作品）

| 业务字段 | JSON 字段 | 类型 | 来源 |
|----------|----------|------|------|
| 系列作品 | `series` | ARRAY | 豆瓣 |
| 相似作品 | `similar` | ARRAY | 豆瓣 |
| 作品名 | `title` | STRING | 豆瓣 |
| 年份 | `year` | NUMBER | 豆瓣 |
| 评分 | `rating` | NUMBER | 豆瓣 |
| 作品图片 | `image` | STRING | 豆瓣（下载后文件名） |
| 来源 | `source` | STRING | 固定 `豆瓣` |

**结构示例**：
```json
{
  "series": [],
  "similar": [
    {
      "title": "2001太空漫游",
      "year": 1968,
      "rating": 8.9,
      "image": "similar-01.jpg",
      "source": "豆瓣"
    },
    {
      "title": "地心引力",
      "year": 2013,
      "rating": 7.9,
      "image": "similar-02.jpg",
      "source": "豆瓣"
    }
  ]
}
```

---

#### `quotes_json`（名言名句）

| 业务字段 | JSON 字段 | 类型 | 来源 |
|----------|----------|------|------|
| 名言名句 | 整个数组 | JSON Array | Wikipedia |

**结构示例**：
```json
[
  {
    "text": "Love is the one thing we're capable of perceiving that transcends dimensions of time and space.",
    "character": "Brand",
    "source": "wikipedia"
  },
  {
    "text": "We used to look up at the sky and wonder at our place in the stars, now we just look down and worry about our place in the dirt.",
    "character": "Cooper",
    "source": "wikipedia"
  }
]
```

---

#### `production_companies_json`（出品公司）【新增】

| 业务字段 | JSON 字段 | 类型 | 来源 |
|----------|----------|------|------|
| 出品公司 | 整个数组 | JSON Array | 豆瓣 > TMDB |

**结构示例**：
```json
[
  {"name": "Warner Bros.", "country": "美国"},
  {"name": "Legendary Entertainment", "country": "美国"},
  {"name": "Syncopy", "country": "美国"}
]
```

---

## 三、`people` 表字段映射

| 业务字段 | 数据库字段 | 类型 | 来源优先级 | 说明 |
|----------|-----------|------|-----------|------|
| 人物名(中文) | `name` | TEXT | 豆瓣 > TMDB | |
| 人物名(英文) | `name_en` | TEXT | TMDB > 豆瓣 | |
| 人物图片 | `avatar_path` | TEXT | TMDB（优先） | 头像文件路径 |
| 人物编码 | `person_code` | TEXT | 系统生成 | `p000098` |
| 人物详情页链接 | `detail_url` | TEXT | TMDB > 豆瓣 | 【新增字段】 |
| 备注 | `notes` | TEXT | - | 可选 |
| 扩展信息 | `extra_json` | JSON | - | 来源标识等 |

**`extra_json` 结构示例**：
```json
{
  "avatarSource": "tmdb",
  "doubanId": "123456",
  "tmdbId": "525"
}
```

---

## 四、`work_credits` 表字段映射

| 业务字段 | 数据库字段 | 类型 | 说明 |
|----------|-----------|------|------|
| 作品 ID | `work_id` | TEXT | 关联 `works.id` |
| 人物 ID | `person_id` | INTEGER | 关联 `people.id` |
| 部门 | `department` | STRING | 见下方映射表 |
| 类型 | `credit_type` | STRING | 见下方映射表 |
| 显示标签 | `display_label` | STRING | 中文职位名 |
| 角色名 | `character_name` | STRING | 演员饰演的角色名 |
| 排序 | `sort_order` | INTEGER | 显示顺序 |
| 是否主要 | `is_primary` | INTEGER | 主演标记 |

### TMDB 部门映射表

| TMDB Department | `department` | `credit_type` | `display_label` |
|------------------|--------------|---------------|-----------------|
| Directing | `direction` | `director` | 导演 |
| Writing | `writing` | `writer` | 编剧 |
| Production | `production` | `producer` | 制片人 |
| Crew | `crew` | 按 job 映射 | 按具体职位 |
| Sound | `sound` | 按 job 映射 | 按具体职位 |
| Camera | `camera` | `cinematographer` | 摄影 |
| Art | `art` | 按 job 映射 | 按具体职位 |
| Costume & Make-Up | `costume` | `costume_designer` | 服装设计 |
| Visual Effects | `vfx` | 按 job 映射 | 按具体职位 |
| Editing | `editing` | `editor` | 剪辑 |
| Actors | `acting` | `actor` | 演员 |

---

## 五、`terms` 表字段映射

| 业务字段 | 数据库字段 | 类型 | 说明 |
|----------|-----------|------|------|
| 词项名 | `name` | TEXT | 类型名或标签名 |
| 词项类型 | `type` | TEXT | `genre` 或 `tag` |
| 词项编码 | `term_code` | TEXT | 系统生成 |

---

## 六、`work_terms` 表字段映射

| 业务字段 | 数据库字段 | 类型 | 说明 |
|----------|-----------|------|------|
| 作品 ID | `work_id` | TEXT | 关联 `works.id` |
| 词项 ID | `term_id` | INTEGER | 关联 `terms.id` |

---

## 七、数据来源汇总

| 来源 | 提供数据 |
|------|----------|
| 豆瓣 | 基本信息、评分、短评、长评、图片、标签、相关推荐 |
| TMDB | 基本信息、演职人员、图片、视频、原声、评分 |
| OMDb (IMDb) | 评分、分级、获奖信息 |
| 百度百科 | 基本信息补充、词条链接 |
| Wikipedia | 基本信息补充、获奖补充、名言名句、词条链接 |
| 烂番茄 | 评分、评论 |
| Metacritic | 评分、评论 |

---

## 八、字段冲突处理规则

| 字段 | 冲突处理 |
|------|----------|
| `title` | 豆瓣优先 |
| `original_title` | TMDB 优先 |
| `year` | 豆瓣优先 |
| `runtime_minutes` | 豆瓣优先 |
| `synopsis_text` | 豆瓣优先，百度百科补充 |
| `story_text` | 豆瓣优先，百度百科补充 |
| 演职人员 | TMDB 优先（数据更完整） |
| 人物头像 | TMDB 优先 |
| 图片 | 豆瓣主海报优先，TMDB 补充海报/剧照优先 |
| 评分 | 各来源独立存储，不合并 |

---

## 九、数据库字段变更记录

### 新增字段

| 表 | 字段 | 类型 | 说明 |
|----|------|------|------|
| `works` | `production_companies_json` | JSON | 出品公司列表 |
| `people` | `detail_url` | TEXT | 人物详情页链接 |

### 扩展 JSON 字段

| JSON 字段 | 新增子字段 | 说明 |
|-----------|-----------|------|
| `videos_json` | `thumbnail` | 视频封面图 |
| `videos_json` | `duration` | 视频时长 |
| `relations_json` | `image` | 作品图片 |
| `relations_json` | `source` | 数据来源 |
| `identifiers_json` | `baike` | 百度百科词条名 |
| `identifiers_json` | `wikipedia_zh` | 中文 Wikipedia 词条名 |
| `links_json` | `baike` | 百度百科链接 |
| `links_json` | `wikipedia_zh` | 中文 Wikipedia 链接 |

---

## 十、数据导入注意事项

1. **ID 生成规则**：`MMSSNNNNNN`（模块+子模块+序号）
2. **人物编码生成规则**：`p{NNNNNN}`（6位序号）
3. **词项编码生成规则**：`g{NNNNNN}`（类型）或 `t{NNNNNN}`（标签）
4. **图片存储路径**：`public/assets/{module}/{submodule}/{id}/`
5. **人物头像存储路径**：`public/assets/people/{person_code}/`
6. **JSON 字段解析**：使用 SQLite JSON 函数或应用层解析
7. **演职人员去重**：按 `person_id` + `department` + `credit_type` 去重
8. **词项去重**：按 `name` + `type` 去重

---

文档版本：v1.0
创建日期：2026-05-05