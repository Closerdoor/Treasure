# 书籍数据录入工具开发背景分析

本文档汇总了现有项目架构、数据库设计、以及电影爬虫实现，作为书籍数据录入工具开发的参考基础。

---

## 一、项目整体架构

### 1.1 两层系统设计

| 层级 | 说明 | 技术 |
|------|------|------|
| **展示站点** | 公开访问，静态生成 | Astro → GitHub Pages |
| **本地内容工坊** | 数据录入、爬取、整理 | Python 爬虫 + SQLite |

### 1.2 模块划分

| 模块 | 编号 | 子模块 |
|------|------|--------|
| 影视 | 01 | 电影、电视剧、动漫、纪录片、短片 |
| 书 | 02 | 网络小说、经典文学、名著、散文随笔、漫画 |
| 音乐 | 03 | 专辑、单曲、原声带、演唱会现场、音乐人专题 |
| 游戏 | 04 | 单机游戏、独立游戏、网游、手游、主机游戏 |

### 1.3 ID 系统

格式：`MMSSNNNNNN`

- `MM`：一级模块编号（01-04）
- `SS`：子模块编号（01-05）
- `NNNNNN`：该子模块下的递增序号

示例：
- `0101000001` = 影视/电影/第 1 条
- `0201000001` = 书/默认子模块/第 1 条

---

## 二、数据库设计（treasure.db）

### 2.1 表结构概览

| 表 | 记录数 | 说明 |
|------|--------|------|
| `works` | 250 | 作品主表（已导入豆瓣 Top250 电影） |
| `person` | 4600 | 人物主表（导演/编剧/演员） |
| `work_person` | 5691 | 作品与人物关系表 |
| `category` | 27 | 类型/标签表 |
| `work_category` | 700 | 作品与类型关联表 |

### 2.2 works 表字段

#### 标识信息

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String | 作品 ID，格式 `MMSSNNNNNN` |
| `module` | Enum | 一级模块：`video`/`anime`/`book`/`music`/`game` |
| `submodule` | Enum? | 二级模块（book 模块可为空） |
| `schemaType` | Enum | 内容类型，决定展示模板 |

#### 基本信息

| 字段 | 类型 | 说明 | 书籍对应 |
|------|------|------|----------|
| `title` | String | 中文标题 | 书名 |
| `titleOriginal` | String? | 原名 | 英文原名 |
| `otherTitles` | String? | 别名 JSON 数组 | 其他译名 |
| `year` | Int? | 年份 | 出版年份 |
| `country` | String? | 国家/地区 | 作者国家 |
| `language` | String? | 语言 | 语言 |
| `totalTime` | Int? | 总时长 | **页数** |
| `studio` | String? | 制片方 | **出版社** |
| `releaseDates` | String? | 上映日期 JSON 数组 | 出版日期 |

#### 内容文本

| 字段 | 类型 | 说明 |
|------|------|------|
| `introduction` | String? | 简介（短文，列表页） |
| `story` | String? | 剧情（长文，详情页） → 书籍可存作者简介 |

#### 外部来源

| 字段 | 类型 | 说明 |
|------|------|------|
| `externalSource` | String? | JSON 数组，示例见下方 |

```json
[
  { "name": "豆瓣", "id": "2567638", "link": "https://book.douban.com/subject/2567638/" },
  { "name": "OpenLibrary", "id": "OL123456M", "link": "https://openlibrary.org/works/OL123456M" },
  { "name": "ISBN", "id": "9787536692930", "link": null }
]
```

#### 评分

| 字段 | 类型 | 说明 |
|------|------|------|
| `scores` | String? | JSON 对象，示例见下方 |

```json
{
  "avg": 8.9,
  "douban": 9.3,
  "openlibrary": 8.5
}
```

#### 媒体资源

| 字段 | 类型 | 说明 |
|------|------|------|
| `images` | String? | JSON 对象（poster/posters） |
| `videos` | String? | JSON 数组（书籍可为空） |
| `comments` | String? | JSON 数组（书评） |

#### 其他

| 字段 | 类型 | 说明 |
|------|------|------|
| `quotes` | String? | 名言 JSON 数组 |
| `related` | String? | 相关作品 JSON 对象 |
| `soundtrack` | String? | 原声（书籍可为空） |
| `characters` | String? | 角色介绍（书籍可为空） |
| `status` | Enum | `draft`/`published`/`archived` |

### 2.3 person 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Int | 自增主键 |
| `personId` | String | 人物代码，格式 `p000001` |
| `name` | String | 中文名 |
| `nameEn` | String? | 英文名 |
| `avatarPath` | String? | 头像路径 |
| `profileLink` | String? | 外链（百度百科/Wikipedia） |
| `intro` | String? | 简介 |

### 2.4 work_person 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Int | 自增主键 |
| `workId` | String | 作品 ID |
| `personId` | Int | 人物 ID |
| `department` | Enum | 部门（见下方） |
| `role` | String? | 具体职位 |
| `character` | String? | 角色名（演员专用） |
| `order` | Int | 排序 |
| `isPrimary` | Boolean | 是否主要 |

**Department 枚举**：

| 值 | 电影 | 书籍 |
|------|------|------|
| `direction` | 导演 | — |
| `writing` | 编剧 | — |
| `cast` | 演员 | — |
| `production` | 制片 | — |
| `music` | 音乐 | — |
| `book` | — | **作者** |
| `translation` | — | **译者** |
| `original_work` | — | **原著** |
| `other` | 其他 | 其他 |

### 2.5 category 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Int | 自增主键 |
| `group` | Enum | `type`（类型）/`tag`（标签） |
| `name` | String | 名称 |
| `module` | String? | 模块作用域 |
| `submodule` | String? | 子模块作用域 |
| `order` | Int | 排序 |
| `enabled` | Boolean | 是否启用 |

---

## 三、电影爬虫实现（movie-ingest）

### 3.1 目录结构

```
temp-script/movie-ingest/
├── main.py              # 主入口
├── config.py            # 配置（API Keys、代理、延迟）
├── progress.py          # 断点续传
├── merger.py            # 数据合并
├── database.py          # 数据库操作
├── downloader.py        # 图片下载
├── crawl_basic.py       # 基本信息爬取
├── crawl_reviews.py     # 影评爬取
├── crawl_images.py      # 图片爬取
├── sources/
│   ├── douban.py        # 豆瓣（Playwright）
│   ├── tmdb.py          # TMDB API
│   ├── omdb.py          # OMDb API
│   ├── baike.py         # 百度百科
│   ├── wikipedia.py     # Wikipedia
│   ├── rotten_tomatoes.py
│   └── metacritic.py
├── utils/
│   ├── hash.py          # 哈希计算
│   ├── id_generator.py  # ID 生成
│   └── logger.py        # 日志
└── data/                # 爬取结果
```

### 3.2 数据来源优先级

| 来源 | 数据类型 | 爬取方式 | 优先级 |
|------|----------|----------|--------|
| 豆瓣 | 基本信息、评分、评论、封面 | Playwright | 最高 |
| TMDB | 演职人员、图片、视频 | REST API | 高 |
| OMDb | 评分、分级、获奖 | REST API | 中 |
| 百度百科 | 补充信息 | Playwright | 中 |
| Wikipedia | 剧情、获奖、名言 | Playwright | 中 |
| 烂番茄 | 评分、评论 | Playwright | 低 |
| Metacritic | 评分、评论 | Playwright | 低 |

### 3.3 核心流程

```
1. 爬取基本信息（豆瓣 + TMDB + OMDb + 百度百科 + Wikipedia）
   ↓
2. 爬取影评（豆瓣短评/长评 + TMDB + 烂番茄 + Metacritic）
   ↓
3. 爬取图片（豆瓣 + TMDB）
   ↓
4. 数据合并（merger.py）
   ↓
5. 图片下载（downloader.py）
   ↓
6. 数据库导入（database.py）
```

### 3.4 断点续传机制

`progress.json` 结构：

```json
{
  "lastUpdated": "2026-05-06T14:32:00",
  "total": 250,
  "completed_count": 250,
  "movies": {
    "1292052": {
      "title": "肖申克的救赎",
      "work_id": "0101000001",
      "status": "completed",
      "sources": {
        "douban": "done",
        "tmdb": "done",
        "omdb": "done",
        "baike": "done",
        "wikipedia": "done"
      },
      "basic_crawled": true,
      "reviews_crawled": true,
      "images_crawled": true,
      "images_downloaded": true,
      "data_merged": true
    }
  }
}
```

### 3.5 数据合并规则

| 字段 | 优先级 |
|------|--------|
| `title` | 豆瓣 > TMDB |
| `originalTitle` | TMDB > 豆瓣 |
| `year` | 豆瓣 > TMDB |
| `runtime` | 豆瓣 > TMDB |
| `synopsis` | 豆瓣 > Wikipedia |
| `story` | Wikipedia > 豆瓣 |
| 评分 | 各来源独立存储 |

### 3.6 图片去重策略

| 维度 | 检查时机 |
|------|----------|
| URL | 下载前 |
| 文件名 | 下载前 |
| 内容哈希（MD5） | 下载后 |
| 图片比例 | 下载后（区分海报/剧照） |

---

## 四、书籍数据源分析

### 4.1 主数据源对比

| 来源 | 数据类型 | 爬取方式 | 优势 |
|------|----------|----------|------|
| **豆瓣读书** | 基本信息、评分、书评、封面、标签 | Playwright | 中文最全 |
| **OpenLibrary** | 英文信息、作者、封面、ISBN | REST API | 完全开放 |
| **百度百科** | 作者简介、获奖 | Playwright | 中文补充 |
| **Wikipedia** | 获奖、经典语录 | Playwright | 权威补充 |

### 4.2 豆瓣读书字段

| 字段 | 获取方式 |
|------|----------|
| 书名 | 详情页 h1 |
| 原名 | info 区域"原名:" |
| 作者 | info 区域"作者:"链接 |
| 出版社 | info 区域"出版社:" |
| 出版年份 | info 区域"出版年:" |
| 页数 | info 区域"页数:" |
| ISBN | info 区域"ISBN:" |
| 评分 | strong.rating_num |
| 简介 | span[property='v:summary'] |
| 标签 | .tags-body a |
| 封面 | #mainpic img |
| 书评 | 短评页/长评页 |

### 4.3 OpenLibrary API

**搜索接口**：
```
https://openlibrary.org/search.json?isbn={ISBN}
```

**详情接口**：
```
https://openlibrary.org/works/{OLID}.json
```

**封面接口**：
```
https://covers.openlibrary.org/b/id/{COVER_ID}-L.jpg
```

**返回字段**：
- `title`：英文标题
- `first_publish_date`：首次出版日期
- `description`：简介
- `covers`：封面 ID 列表
- `authors`：作者 OLID 列表
- `subject_places`：地点标签
- `subject_times`：时间标签
- `subjects`：主题标签

---

## 五、书籍与电影的关键差异

### 5.1 字段映射差异

| 电影字段 | 书籍字段 | 说明 |
|----------|----------|------|
| `totalTime`（分钟） | 页数 | 同字段，含义不同 |
| `studio`（制片公司） | 出版社 | 同字段，含义不同 |
| `releaseDates`（上映） | 出版日期 | 同字段，含义不同 |
| `videos` | — | 书籍无视频 |
| `soundtrack` | — | 书籍无原声 |
| `characters` | — | 书籍无角色介绍 |
| `story`（剧情） | 作者简介 | 同字段，含义不同 |

### 5.2 人物关系差异

| 电影 | 书籍 |
|------|------|
| 导演（direction） | 作者（book） |
| 编剧（writing） | 译者（translation） |
| 演员（cast） | 原著（original_work） |
| 制片（production） | — |
| 音乐（music） | — |

### 5.3 ID 生成差异

| 模块 | ID 格式 | 示例 |
|------|---------|------|
| 电影 | `0101NNNNNN` | `0101000001` |
| 书籍 | `0201NNNNNN` | `0201000001` |

### 5.4 schemaType 差异

| 电影 | 书籍 |
|------|------|
| `live_action_movie` | `book` |
| `animated_movie` | — |
| `documentary_film` | — |

---

## 六、可复用组件清单

### 6.1 直接复用

| 文件 | 复用内容 |
|------|----------|
| `config.py` | 代理配置、延迟配置、浏览器配置 |
| `progress.py` | 断点续传机制、进度状态管理 |
| `downloader.py` | 图片下载、哈希去重、比例判断 |
| `sources/baike.py` | 百度百科爬虫 |
| `sources/wikipedia.py` | Wikipedia 爬虫 |
| `utils/hash.py` | MD5 哈希计算 |
| `utils/id_generator.py` | ID 生成逻辑（需修改起始编号） |
| `utils/logger.py` | 日志输出 |

### 6.2 需要适配

| 文件 | 适配内容 |
|------|----------|
| `database.py` | 书籍字段映射、department 枚举适配 |
| `merger.py` | 书籍数据合并逻辑、字段优先级 |
| `sources/douban.py` | 豆瓣读书页面结构（与电影不同） |

### 6.3 需要新建

| 文件 | 新建内容 |
|------|----------|
| `sources/douban_book.py` | 豆瓣读书爬虫 |
| `sources/openlibrary.py` | OpenLibrary API 调用 |
| `crawl_basic.py` | 书籍基本信息爬取流程 |
| `crawl_reviews.py` | 书评爬取流程 |
| `crawl_images.py` | 封面爬取流程 |

---

## 七、开发建议

### 7.1 推荐架构

```
temp-script/book-ingest/
├── main.py              # 主入口（复用 movie 结构）
├── config.py            # 配置（复用 + 书籍特定）
├── progress.py          # 断点续传（复用）
├── merger.py            # 数据合并（新建，适配书籍）
├── database.py          # 数据库操作（新建，适配书籍）
├── downloader.py        # 图片下载（复用）
├── crawl_basic.py       # 基本信息爬取（新建）
├── crawl_reviews.py     # 书评爬取（新建）
├── crawl_images.py      # 封面爬取（新建）
├── sources/
│   ├── douban_book.py   # 豆瓣读书（新建）
│   ├── openlibrary.py   # OpenLibrary（新建）
│   ├── baike.py         # 百度百科（复用 movie）
│   └── wikipedia.py     # Wikipedia（复用 movie）
├── utils/               # 工具函数（复用）
└── data/                # 爬取结果
```

### 7.2 开发优先级

1. **豆瓣读书爬虫** - 核心数据源
2. **OpenLibrary API** - 英文数据补充
3. **数据合并逻辑** - 字段优先级、冲突处理
4. **数据库导入** - 书籍字段映射
5. **书评爬取** - 按热度排序
6. **封面下载** - 去重、存储

### 7.3 测试验证

建议先爬取以下书籍验证流程：

| 书籍 | 类型 | 验证内容 |
|------|------|----------|
| 《三体》 | 中文原创 | 豆瓣数据、系列书籍 |
| 《百年孤独》 | 翻译作品 | 译者信息、OpenLibrary |
| 《1984》 | 经典名著 | 多版本、ISBN 匹配 |

---

---

## 八、书籍数据库表设计（已实现）

### 8.1 表结构

| 表 | 说明 |
|------|------|
| `books` | 书籍主表 |
| `book_series` | 书籍系列表 |
| `book_person` | 书籍-人物关系表（复用 person 表） |
| `book_category` | 书籍-类型关系表（复用 category 表） |

### 8.2 books 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | TEXT | 书籍 ID，格式 0200NNNNNN |
| `title` | TEXT | 中文书名 |
| `title_original` | TEXT | 原名（英文/源语言） |
| `other_titles` | TEXT | 别名 JSON 数组 |
| `isbn` | TEXT | ISBN（唯一） |
| `year` | INTEGER | 出版年份 |
| `country` | TEXT | 作者国家 |
| `language` | TEXT | 语言 |
| `word_count` | INTEGER | 字数 |
| `publisher` | TEXT | 出版社 |
| `summary` | TEXT | 内容简介 |
| `quotes` | TEXT | 名句摘录 JSON 数组 |
| `series_id` | TEXT | 所属系列 ID |
| `series_order` | INTEGER | 系列内序号 |
| `scores` | TEXT | 评分 JSON（10 分制） |
| `external_source` | TEXT | 外部来源 JSON |
| `images` | TEXT | 封面 JSON |
| `reviews` | TEXT | 书评 JSON（每源 20 条） |
| `related` | TEXT | 相关书籍 JSON |
| `status` | TEXT | 状态（draft/published/archived） |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

### 8.3 book_series 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | TEXT | 系列 ID，格式 0299NNNNNN |
| `name` | TEXT | 系列名 |
| `name_original` | TEXT | 原名 |
| `book_count` | INTEGER | 书籍数量 |
| `summary` | TEXT | 系列简介 |
| `images` | TEXT | 系列封面 JSON |
| `status` | TEXT | 状态 |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

### 8.4 book_person 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER | 自增主键 |
| `book_id` | TEXT | 书籍 ID |
| `person_id` | INTEGER | 人物 ID（关联 person 表） |
| `role` | TEXT | 角色（author/translator） |
| `order` | INTEGER | 排序 |
| `is_primary` | BOOLEAN | 是否主要 |

### 8.5 book_category 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER | 自增主键 |
| `book_id` | TEXT | 书籍 ID |
| `category_id` | INTEGER | 类型 ID（关联 category 表） |
| `order` | INTEGER | 排序 |

### 8.6 JSON 字段格式

#### scores（评分）
```json
{
  "avg": 8.9,
  "douban": 9.3,
  "openlibrary": 8.4,
  "goodreads": 8.2
}
```

#### external_source（外部来源）
```json
[
  { "name": "豆瓣", "id": "2567638", "link": "https://book.douban.com/subject/2567638/" },
  { "name": "OpenLibrary", "id": "OL123456M", "link": "https://openlibrary.org/works/OL123456M" },
  { "name": "ISBN", "id": "9787536692930", "link": null }
]
```

#### images（封面）
```json
{
  "cover": "cover-main.jpg",
  "covers": ["cover-002.jpg"],
  "assetDir": "book/0200000001"
}
```

#### reviews（书评）
```json
[
  {
    "author": "读者A",
    "source": "豆瓣短评",
    "date": "2024-01-01",
    "content": "书评内容...",
    "url": null,
    "title": null
  }
]
```

#### related（相关书籍）
```json
{
  "series": [{ "title": "三体Ⅱ", "year": 2008, "rating": 9.3, "bookId": "0200000002" }],
  "similar": [{ "title": "基地", "year": 1951, "rating": 9.0, "bookId": "0200000050" }],
  "sameAuthor": [{ "title": "球状闪电", "year": 2005, "rating": 8.6, "bookId": "0200000100" }]
}
```

#### quotes（名句）
```json
[
  { "text": "给岁月以文明，而不是给文明以岁月。", "source": "三体" }
]
```

---

文档版本：v1.1
更新日期：2026-05-10
基于：movie-ingest 实现 + Prisma Schema + 豆瓣读书页面分析 + 书籍表设计讨论