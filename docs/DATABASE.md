# Database

> Purpose: 记录当前已经确认的 SQLite 第一版精简设计方向，作为后续数据库建模与字段对齐的唯一最新版本。
> Status: active
> Scope: 数据库主源方向、精简表结构、跨类型公共信息、各模块字段映射、静态资源路径策略
> Out of scope: 完整迁移脚本、所有模块最终字段全集、前台视觉细节
> Update triggers: 新模块字段设计补充、核心表结构调整、静态资源策略变化
> Priority: 2

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

当前第一版只保留 5 张核心表：

1. `works`
2. `people`
3. `work_credits`
4. `terms`
5. `work_terms`

## 表职责摘要

### `works`

作品主表，承载：

- 作品主键与分类信息
- 一对一基础字段
- 强绑定但不必先拆表的一对多展示数据（以 JSON 保存）

### `people`

公共人物主表，承载：

- 人物名
- 英文名 / 原名
- 共享头像路径
- 人物默认外链
- 备注信息

### `work_credits`

作品与人物关系表，承载：

- 导演
- 编剧
- 主演
- 制片人
- 作者
- 译者
- 原著
- 配音
- 其它后续可扩展的人物关系

### `terms`

公共词项定义表，承载：

- `genre`
- `tag`

### `work_terms`

作品与词项的关联表，承载：

- 某部作品属于哪些类型
- 某部作品带有哪些标签

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
