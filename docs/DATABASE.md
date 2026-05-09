# Database

> Purpose: 记录当前已经确认的 SQLite 第一版精简设计方向，作为后续数据库建模与字段对齐的唯一最新版本。
> Status: active
> Scope: 数据库主源方向、精简表结构、跨类型公共信息、各模块字段映射、静态资源路径策略
> Out of scope: 完整迁移脚本、所有模块最终字段全集、前台视觉细节
> Update triggers: 新模块字段设计补充、核心表结构调整、静态资源策略变化
> Priority: 2

## 当前状态（2026-05-07 更新）

### 数据库已投入使用

数据库已完成设计并导入豆瓣 Top 250 电影数据：

| 表 | 记录数 | 说明 |
|------|--------|------|
| `works` | 249 | 豆瓣 Top 250 电影（跳过 0101000001） |
| `person` | 4527 | 去重后的导演/编剧/演员 |
| `category` | 27 | 电影类型 |
| `work_person` | 5660 | 演职关系 |
| `work_category` | 698 | 类型关联 |

### 数据库文件位置

```
.local/treasure.db
```

### 静态资源位置

```
.local/assets/video/movie/{id}/
```

### Prisma Schema

```
prisma/schema.prisma
```

---

## 目标

当前项目下一阶段采用：

- 本地 SQLite 作为唯一结构化数据主源
- Astro 前台不直接读取数据库
- 前台继续消费导出产物与静态资源目录
- 数据库第一版先走精简方案，不做过度拆表

对应链路：

```text
SQLite -> export script -> JSON / generated data -> Astro build -> GitHub Pages
```

## 当前已确认的设计原则

### 1. 先按“是否一对一 / 一对多”判断是否拆表

- 一对一字段：优先直接放在主表中
- 强绑定的一对多展示数据：第一阶段优先使用 JSON 字段承载
- 需要跨作品复用、单独维护或形成关系网络的数据：独立成表

### 2. SQLite 第一版先避免过度拆分

- 不追求一开始就完全范式化
- 优先保证可理解、可迁移、可扩展
- 等作品规模显著增长后，再讨论继续拆表

### 3. `people` 第一阶段就独立

- 人物是明确要做成公共资源的实体
- 共享头像、人物跳转链接、后续跨作品复用都依赖 `people` 主表

### 4. 分类体系使用公共词项模型

- `genre` 与 `tag` 不直接塞进 `works` 的单列字段中
- 使用公共词项表 + 作品关联表承载
- `genre` 允许按模块或子模块建立作用域
- `tag` 作为跨模块公共标签体系

### 5. 机构类信息暂不独立，但应按“未来公共实体”思维设计

当前已明确会出现：

- 电影 / 电视剧的出品公司
- 动漫的制作公司（未来高概率出现）
- 书籍的出版社（未来高概率出现）
- 音乐厂牌、游戏开发商 / 发行商（未来高概率出现）

当前结论：

- 第一版暂不单独建立 `organizations` 表
- 先在 `works` 中使用一对一字段或 JSON 承载机构类信息
- 但后续如果机构复用、检索或聚合需求显著增加，应优先升级为公共实体表

## 当前确认的分类体系

### module

- `video`
- `anime`
- `book`
- `music`
- `game`

### submodule

#### `video`

- `movie`
- `tv_series`
- `documentary`
- `short_drama`

#### `anime`

- `anime_movie`
- `anime_series`

#### `book` / `music` / `game`

- 当前允许为 `NULL`

### schema_type

- `live_action_movie`
- `animated_movie`
- `live_action_series`
- `animated_series`
- `documentary_film`
- `documentary_series`
- `book`
- `music`
- `game`

## 第一版精简表结构（当前基线）

当前第一版保留 5 张核心表：

1. `works` - 作品主表（249 条）
2. `person` - 人物表（4527 条）
3. `work_person` - 作品人物关系表（5660 条）
4. `category` - 类型/标签表（27 条）
5. `work_category` - 作品分类关联表（698 条）

> 注意：表名已改为单数形式（person 而非 people，category 而非 categories）

---

## 表职责摘要

### `works`

作品主表，承载：

- 作品主键与分类信息
- 一对一基础字段
- 强绑定但不必先拆表的一对多展示数据（以 JSON 保存）

**当前数据**：249 部豆瓣 Top 250 电影

**字段分组**：

```
标识信息（4个）
├── id              作品ID（0101000002 - 0101000250）
├── module          一级模块（video）
├── submodule       二级模块（movie）
└── schemaType      内容类型（live_action_movie）

基本信息（11个）
├── title           中文标题
├── titleOriginal   原名
├── otherTitles     别名（JSON）
├── year            年份
├── country         国家/地区
├── language        语言
├── totalTime       总时长（分钟）
├── studio          制片方
├── releaseDates    上映日期（JSON）
├── quotes          名言（JSON）
└── scores          评分（JSON）

内容文本（2个）
├── introduction    简介（豆瓣 summary）
└── story           剧情（维基百科 summary）

外部来源（1个）
└── externalSource  外部来源（JSON）
    - 豆瓣、IMDb、TMDB、百度百科、维基百科

媒体资源（2个）
├── images          图片（JSON）
└── videos          视频（JSON）

评论内容（1个）
└── comments        影评（JSON，不限制数量）

音乐相关（1个）
└── soundtrack      原声（JSON）

关联作品（1个）
└── related         相关作品（JSON）
    ├── series      系列作品
    └── similar     相似作品

系统字段（3个）
├── status          状态（published）
├── createdAt       创建时间
└── updatedAt       更新时间
```

### `person`

公共人物主表，承载：

- 人物代码（personId：p000001 - p004527）
- 中文名（name）
- 英文名/原名（nameEn）
- 共享头像路径（avatarPath）
- 人物默认外链（profileLink）
- 简介（intro）

**当前数据**：4527 条人物（从豆瓣数据提取，按姓名去重）

**已知限制**：
- 演员角色名缺失（豆瓣数据无角色名字段）
- 人物英文名缺失（豆瓣数据无英文名）
- 人物头像缺失（豆瓣数据无头像）

### `work_person`

作品与人物关系表，承载：

- 作品ID（workId）
- 人物ID（personId）
- 部门（department）：direction / writing / cast
- 具体职位（role）：导演 / 编剧 / 演员
- 排序（order）
- 是否主要人员（isPrimary）

**当前数据**：5660 条关系

**统计**：
- 导演：284 条
- 编剧：569 条
- 演员：4807 条

### `category`

公共词项定义表，承载：

- 分组（group）：type / tag
- 名称（name）
- 模块作用域（module）：video
- 子模块作用域（submodule）：movie
- 排序（order）
- 是否启用（enabled）

**当前数据**：27 条电影类型

**类型列表**：
传记、儿童、冒险、剧情、动作、动画、历史、古装、同性、喜剧、奇幻、家庭、恐怖、悬疑、情色、惊悚、战争、歌舞、武侠、灾难、爱情、犯罪、科幻、纪录片、西部、运动、音乐

### `work_category`

作品与词项的关联表，承载：

- 作品ID（workId）
- 词项ID（categoryId）
- 排序（order）

**当前数据**：698 条关联（平均每部约 3 个类型）

---

## 数据导入说明

### 数据来源

| 来源 | 提供数据 |
|------|----------|
| 豆瓣 | 基本信息、演职人员、评分、评论、类型 |
| TMDB | 补充评分、制片公司 |
| OMDb | IMDb/烂番茄/Metacritic 评分 |
| 百度百科 | 词条链接 |
| 维基百科 | 剧情简介 |

### 字段映射规则

| Prisma 字段 | 数据来源 | 提取规则 |
|-------------|---------|---------|
| `title` | 豆瓣.title | 中文标题 |
| `titleOriginal` | 豆瓣.original_title | 原名 |
| `year` | 豆瓣.year | parseInt |
| `country` | 豆瓣.countries | 取第一个 |
| `language` | 豆瓣.languages | 取第一个 |
| `totalTime` | 豆瓣.runtime_minutes | 片长 |
| `introduction` | 豆瓣.summary | 完整内容 |
| `story` | 维基百科.summary | 完整内容 |
| `scores` | 多源合并 | 豆瓣/IMDb/TMDB/烂番茄/Metacritic |
| `externalSource` | 多源合并 | 所有来源 |

### JSON 字段结构

#### scores（评分）

```json
{
  "avg": 9.6,
  "douban": 9.6,
  "imdb": 8.1,
  "tmdb": 7.889,
  "rottenTomatoes": 90,
  "metacritic": 84
}
```

#### externalSource（外部来源）

```json
[
  { "name": "豆瓣", "id": "1291546", "link": "https://movie.douban.com/subject/1291546/" },
  { "name": "IMDb", "id": "tt0106332", "link": "https://www.imdb.com/title/tt0106332/" },
  { "name": "TMDB", "id": "10997", "link": "https://www.themoviedb.org/movie/10997" },
  { "name": "百度百科", "id": "霸王别姬", "link": "https://baike.baidu.com/item/霸王别姬" },
  { "name": "维基百科", "id": "霸王别姬", "link": "https://zh.wikipedia.org/wiki/霸王别姬" }
]
```

#### images（图片）

```json
{
  "poster": "poster-main.webp",
  "posters": ["poster-main.webp"],
  "stills": [],
  "wallpapers": [],
  "assetDir": ".local/assets/video/movie/0101000002"
}
```

#### related（关联作品）

```json
{
  "series": [
    {
      "title": "教父2",
      "source": "douban",
      "sourceId": "1291842",
      "year": 1974,
      "rating": 9.2
    }
  ],
  "similar": [
    {
      "title": "活着",
      "source": "douban",
      "sourceId": "1292052",
      "year": 1994,
      "rating": 9.3
    }
  ]
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | 作品标题（用于展示） |
| `source` | string | 是 | 数据来源平台标识 |
| `sourceId` | string | 是 | 来源平台的作品 ID |
| `year` | number | 否 | 年份 |
| `rating` | number | 否 | 评分 |

**source 枚举值**：

| 值 | 说明 | sourceId 示例 |
|------|------|------|
| `douban` | 豆瓣 | `1292052`（subject ID） |
| `tmdb` | TMDB | `8392`（movie ID） |
| `imdb` | IMDb | `tt0107204`（title ID） |

**匹配逻辑**（导出时执行）：

1. 根据 `source` 和 `sourceId` 匹配数据库中已存在的作品
2. 如果 `source = "douban"` → 用 `sourceId` 匹配 `externalSource` 中豆瓣的 `id`
3. 如果 `source = "tmdb"` → 用 `sourceId` 匹配 `externalSource` 中 TMDB 的 `id`
4. 如果 `source = "imdb"` → 用 `sourceId` 匹配 `externalSource` 中 IMDb 的 `id`
5. 匹配成功 → 补充作品 `id`，前端可跳转
6. 匹配失败 → 保留原始数据，前端仅展示标题（不可跳转）

**设计原则**：

- 爬取阶段：获取推荐作品的外部 ID（豆瓣 subject ID / TMDB movie ID / IMDb title ID）
- 导入阶段：直接存储 `source` + `sourceId`，不做匹配
- 导出阶段：根据外部 ID 匹配数据库，补充作品 ID
- 优势：明确数据来源，支持多平台匹配，避免标题匹配的不可靠性

---

## 静态资源路径策略

### 作品私有资源

- 路径：`.local/assets/{module}/{submodule}/{id}/`
- 例如：`.local/assets/video/movie/0101000002/poster-main.webp`

### 共享人物资源

- 路径：`.local/assets/people/`
- 命名：`{personId}-avatar.jpg`（如 `p000001-avatar.jpg`）

### 图片格式

- 当前：WebP（豆瓣主海报）
- 未来：支持 JPG/PNG

---

## 备份文件

### 位置

`.local/backup/`

### 文件列表

| 文件 | 说明 |
|------|------|
| `works-backup.json` | 剩余 2 条旧数据 |
| `person-backup.json` | 旧人物数据（116 条） |
| `category-backup.json` | 旧类型数据（8 条） |

---

## 变更记录

详见 `docs/SCHEMA-CHANGELOG.md`

---

## 原始设计文档（历史参考）

以下为原始设计文档，保留作为历史参考：

---

## 目标（原始）

## `works` 第一版字段方向

### 基础字段

- `id`
- `module`
- `submodule`
- `schema_type`
- `title`
- `original_title`
- `year`
- `country`
- `language`
- `publish_company`
- `runtime_minutes`
- `episode_count`
- `episode_runtime_minutes`
- `synopsis_text`
- `synopsis_note`
- `story_text`
- `status`
- `created_at`
- `updated_at`

### JSON 字段

- `aliases_json`
- `release_dates_json`
- `identifiers_json`
- `ratings_json`
- `links_json`
- `images_json`
- `videos_json`
- `reviews_json`
- `soundtrack_json`
- `relations_json`
- `quotes_json`
- `episode_stories_json`
- `characters_json`

说明：

- `quotes_json` 用于存储“名言名句”数组
- `episode_stories_json` 用于存储电视剧 / 番剧的分集剧情与分集剧情图片
- `characters_json` 用于存储动漫模块的角色介绍数组

## 电影作品字段映射（当前确认版）

### 放在 `works` 的一对一字段

- 电影名称（中文） -> `title`
- 原名（英文或源语言） -> `original_title`
- 年份 -> `year`
- 制片国家/地区 -> `country`
- 语言 -> `language`
- 出品公司 -> `publish_company`
- 片长 -> `runtime_minutes`
- 电影简介 -> `synopsis_text`
- 剧情详解 -> `story_text`

### 放在 `work_credits` 的人物关系字段

- 导演
- 编剧
- 主演
- 演职员表中的职位或饰演角色

### 放在 `terms + work_terms` 的分类字段

- 类型（如剧情 / 犯罪）
- 未来的全站通用标签

### 放在 `works` 的 JSON 字段

- 更多片名 -> `aliases_json`
- 上映日期 -> `release_dates_json`
- 豆瓣 ID / IMDb ID / 未来 TMDB -> `identifiers_json`
- 综合评分 / 豆瓣评分 / IMDb 评分 / TMDB 评分 / 烂番茄评分 / Metascore / 分级 / 获奖信息 -> `ratings_json`
- 系列作品 / 相似作品 -> `relations_json`
- 图片 -> `images_json`
- 精彩影评 -> `reviews_json`
- 音乐原声（按专辑记录，可含多张专辑） -> `soundtrack_json`
- 视频 -> `videos_json`
- 外部来源 -> `links_json`
- 名言名句 -> `quotes_json`

## 电影图片字段的特别说明

### `poster` 与 `images` 分开

当前已确认：

- 海报图片不是“普通图片集合”的一部分语义
- 它承担列表页、详情页顶部等核心展示职责

因此建议：

- `poster` 作为 `images_json` 内的独立主字段
- 其它图片继续放在 `images_json` 的图片集合中

推荐结构示意：

```json
{
  "poster": "poster-main.jpg",
  "posters": ["poster-01.jpg", "poster-02.jpg"],
  "stills": ["still-01.jpg", "still-02.jpg"],
  "wallpapers": ["wallpaper-01.jpg"],
  "postersTotal": 149,
  "stillsTotal": 918
}
```

## 电影名言名句字段的特别说明

当前新增确认：

- 电影作品需要增加“名言名句”字段
- 该字段采用数组形式
- 用于记录多条与作品相关的经典句子内容

第一版建议直接放在：

- `quotes_json`

推荐结构示意：

```json
[
  {
    "text": "Hope is a good thing, maybe the best of things, and no good thing ever dies.",
    "speaker": "Andy Dufresne",
    "note": "可选，记录语境或出处"
  },
  {
    "text": "Get busy living, or get busy dying.",
    "speaker": "Andy Dufresne"
  }
]
```

## 电影评分字段的特别说明

当前确认：

- `ratings_json` 中不再保留 `votes`
- 所有评分统一折算为 10 分制
- 评分对象统一使用：`value` + `scale`

推荐结构示意：

```json
{
  "aggregate": { "value": 9.1, "scale": 10 },
  "douban": { "value": 9.6, "scale": 10 },
  "imdb": { "value": 8.1, "scale": 10 },
  "rottenTomatoes": { "value": 9.0, "scale": 10 },
  "metascore": { "value": 8.4, "scale": 10 },
  "certification": { "value": "R" },
  "awards": { "value": "Nominated for 2 Oscars. 24 wins & 12 nominations total" }
}
```

说明：

- `certification`：内容分级信息，例如 `PG-13`、`R`
- `awards`：获奖与提名摘要

## 电影影评字段的特别说明

当前确认 `reviews_json` 结构为：

```json
[
  {
    "author": "kino",
    "source": "豆瓣",
    "date": "2008-07-12",
    "content": "影评摘录内容",
    "url": "https://movie.douban.com/review/1436379/",
    "title": "阿甘的爱情"
  }
]
```

说明：

- 不再保留 `rating`
- `url` 用于跳转到影评原文
- `title` 若无可写 `null`

## 电影原声字段的特别说明

当前确认 `soundtrack_json` 以“专辑列表”承载：

```json
{
  "albums": [
    {
      "name": "Forrest Gump: The Soundtrack",
      "note": "专辑备注",
      "coverImage": null,
      "releaseDate": "1994",
      "type": "soundtrack",
      "tracks": [
        {
          "name": "Hound Dog",
          "artist": "Elvis Presley",
          "duration": null
        }
      ]
    }
  ]
}
```

说明：

- 一部作品允许存在多张专辑
- 每张专辑记录：专辑名 / 备注 / 封面图 / 发行日期 / 类型 / 曲目
- 每首歌记录：歌名 / 歌手 / 时长

## 电视剧字段设计（当前确认版）

电视剧的界面结构与电影基本一致，但有以下差异：

- 没有片长字段
- 上映日期改为首播日期
- 增加集数
- 增加单集时长
- 除了简介和剧情详解外，增加分集剧情 / 分集剧情图片
- 增加出品公司字段

### 放在 `works` 的一对一字段

- 作品名 -> `title`
- 原名 -> `original_title`
- 年份 -> `year`
- 国家 / 地区 -> `country`
- 语言 -> `language`
- 出品公司 -> `publish_company`
- 集数 -> `episode_count`
- 单集时长 -> `episode_runtime_minutes`
- 简介 -> `synopsis_text`
- 剧情详解 -> `story_text`

### 放在 `works` 的 JSON 字段

- 首播日期 -> `release_dates_json`
- 分集剧情 / 分集剧情图片 -> `episode_stories_json`
- 图片 -> `images_json`
- 视频 -> `videos_json`
- 影评 -> `reviews_json`
- 系列作品 / 相似作品 -> `relations_json`
- 外部来源 -> `links_json`

## 动漫字段设计（当前确认版）

当前结论：

- 动漫是独立一级模块
- 子模块只有：`anime_movie` 与 `anime_series`
- 动画电影与电影基本一致
- 番剧与电视剧基本一致
- 但整个动漫模块都必须额外增加“角色介绍”字段

### 动画电影

- 一级模块：`anime`
- 子模块：`anime_movie`
- `schema_type`：`animated_movie`
- 基础字段大体沿用电影字段
- 同样支持：出品公司、海报、图片、视频、影评、原声、名言名句等
- 必须额外增加：角色介绍

### 番剧

- 一级模块：`anime`
- 子模块：`anime_series`
- `schema_type`：`animated_series`
- 基础字段大体沿用电视剧字段
- 必须额外增加：角色介绍

### `characters_json` 建议结构

```json
[
  {
    "name": "炭治郎",
    "image": "character-01.jpg",
    "actor": null,
    "voice_actor": "花江夏树",
    "bio": "角色简介或演员 / 配音介绍"
  }
]
```

## 书籍字段设计（当前确认版）

当前已确认书籍展示字段包括：

- 书籍封面
- 作品名（中文）
- 作品名（源语言）
- 作者
- 作者国家
- 首次出版年份
- 作品类型
- 翻译者
- 评分
- 内容简介
- 作者简介
- 创作者和翻译信息（类似电影演职员表）
- 读书笔记
- 精彩书评
- 系列作品
- 相似作品

### 放在 `works` 的一对一字段

- 作品名（中文） -> `title`
- 作品名（源语言） -> `original_title`
- 首次出版年份 -> `year`
- 作者国家 -> `country`
- 内容简介 -> `synopsis_text`
- 作者简介 -> `story_text` 或后续独立讨论项

### 放在 `work_credits` 的人物关系字段

- 作者
- 翻译者
- 创作者和翻译信息中的人物条目

### 放在 `terms + work_terms` 的分类字段

- 作品类型

### 放在 `works` 的 JSON 字段

- 评分 -> `ratings_json`
- 封面与其它图片 -> `images_json`
- 读书笔记 -> 后续建议进入 JSON 字段
- 精彩书评 -> `reviews_json`
- 系列作品 / 相似作品 -> `relations_json`
- 外部来源 -> `links_json`

## 哪些字段当前可视为跨类型公共字段

### 基础信息公共字段

- `title`
- `original_title`
- `year`
- `country`
- `language`
- `synopsis_text`
- `ratings_json`
- `relations_json`
- `reviews_json`
- `links_json`

### 人物关系公共设计

- `people`
- `work_credits`

### 分类公共设计

- `terms`
- `work_terms`

### 未来可能升级为公共实体的信息

- 出品公司
- 制作公司
- 出版社
- 厂牌
- 开发商 / 发行商

## 静态资源路径策略

### 作品私有资源

- 路径：`site/public/assets/{module}/{submodule}/{id}/`
- 例如：`site/public/assets/video/movie/0101000001/poster-main.jpg`

### 共享人物资源

- 路径：`site/public/assets/people/`
- 命名：内部人物 ID，例如 `p000001-avatar.jpg`

### 当前结论

- 不额外建立第二份镜像资源目录
- `site/public/assets/` 同时作为前台发布目录与静态资源主目录
- 数据库只记录路径与引用关系

## 当前阶段结论

到目前为止，数据库第一版精简设计应继续围绕：

- `works`
- `people`
- `work_credits`
- `terms`
- `work_terms`

推进。

而新增的电视剧 / 动漫 / 书籍字段，当前优先通过：

- 一对一字段直接入 `works`
- 作品人物关系进入 `work_credits`
- 分类进入 `terms + work_terms`
- 其余强绑定展示型信息先使用 JSON 字段承载
