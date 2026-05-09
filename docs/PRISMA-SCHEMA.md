# Prisma Schema 可视化文档

> 此文档由 Prisma Schema 自动生成，展示所有表和字段的详细注释。
> 
> **唯一真相来源**：`prisma/schema.prisma`
> 
> **可视化工具**：运行 `npx prisma studio` 打开浏览器界面

---

## 数据库概览

| 表名 | 中文名 | 说明 |
|------|--------|------|
| `works` | 作品主表 | 承载所有模块的作品基础信息 |
| `people` | 公共人物主表 | 人物公共资源，支持跨作品复用 |
| `work_credits` | 作品与人物关系表 | 导演/编剧/主演等关系 |
| `terms` | 公共词项定义表 | genre（类型）和 tag（标签） |
| `work_terms` | 作品与词项关联表 | 作品属于哪些类型/标签 |
| `schema_migrations` | 迁移记录表 | 记录已应用的数据库迁移版本 |

---

## 表结构详解

### 1. Work（作品主表）

**说明**：承载所有模块（影视/动漫/书籍/音乐/游戏）的作品基础信息。一对一字段直接存储，一对多展示数据以 JSON 字段存储。

#### 基础字段

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `id` | String | ✓ | - | 作品ID。格式：MMSSNNNNNN（MM:模块, SS:子模块, NNNNNN:序号）。示例：0101000001 = 影视/电影/第1条 |
| `module` | Module | ✓ | - | 一级模块。枚举：video/anime/book/music/game |
| `submodule` | Submodule | - | null | 二级模块。枚举：movie/tv_series/documentary/short_drama/anime_movie/anime_series |
| `schemaType` | SchemaType | ✓ | - | Schema类型，决定字段验证规则和前台展示模板 |
| `title` | String | ✓ | - | 中文标题（必填） |
| `originalTitle` | String | - | null | 原始标题（英文或源语言） |
| `year` | Int | - | null | 上映/出版年份 |
| `country` | String | - | null | 首发国家/地区。规则：单值，按最早真实公映地区推断 |
| `language` | String | - | null | 语言（主要对白语言） |
| `publishCompany` | String | - | null | 出品公司/出版社/制作公司 |
| `runtimeMinutes` | Int | - | null | 时长（分钟），电影专用 |
| `episodeCount` | Int | - | null | 集数，电视剧/番剧专用 |
| `episodeRuntimeMinutes` | Int | - | null | 单集时长（分钟），电视剧/番剧专用 |
| `synopsisText` | String | - | null | 简介短文 |
| `synopsisNote` | String | - | null | 简介备注（如来源说明） |
| `storyText` | String | - | null | 剧情长文。规则：仅已上映作品使用 |
| `status` | WorkStatus | ✓ | draft | 状态。枚举：draft/published/archived |
| `createdAt` | DateTime | ✓ | now() | 创建时间 |
| `updatedAt` | DateTime | ✓ | auto | 更新时间 |

#### JSON 字段

| 字段名 | 类型 | 说明 | 示例结构 |
|--------|------|------|----------|
| `aliasesJson` | String | 更多片名 | `["星际启示录", "星际效应"]` |
| `releaseDatesJson` | String | 上映日期 | `[{ date: "2014-11-05", location: "美国" }]` |
| `identifiersJson` | String | 外部标识符 | `{ doubanId: "1889243", imdbId: "tt0816692", tmdbId: "157336" }` |
| `ratingsJson` | String | 评分信息 | `{ aggregate: { value: 9.1, scale: 10 }, douban: { value: 9.6, scale: 10 } }` |
| `linksJson` | String | 外部来源链接 | `{ douban: "https://...", imdb: "https://..." }` |
| `imagesJson` | String | 图片资源 | `{ poster: "poster-main.jpg", posters: [...], stills: [...] }` |
| `videosJson` | String | 视频资源 | `[{ title: "预告片", duration: "01:00", url: "..." }]` |
| `reviewsJson` | String | 影评 | `[{ author: "kino", source: "豆瓣", date: "2008-07-12", content: "..." }]` |
| `soundtrackJson` | String | 音乐原声 | `{ albums: [{ name: "...", tracks: [...] }] }` |
| `relationsJson` | String | 系列作品/相似作品 | `[{ title: "波西米亚狂想曲", year: 2018, rating: 8.6 }]` |
| `quotesJson` | String | 名言名句 | `[{ text: "...", speaker: "Andy Dufresne" }]` |
| `episodeStoriesJson` | String | 分集剧情 | 电视剧/番剧专用 |
| `charactersJson` | String | 角色介绍 | 动漫模块专用 |

#### 索引

| 索引名 | 字段 |
|--------|------|
| `idx_works_module_submodule` | module, submodule |
| `idx_works_schema_type` | schemaType |
| `idx_works_status` | status |
| `idx_works_year` | year |

---

### 2. Person（公共人物主表）

**说明**：人物是明确要做成公共资源的实体。支持共享头像、人物跳转链接、跨作品复用。

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `id` | Int | ✓ | auto | 自增主键 |
| `personCode` | String | ✓ | - | 人物代码。格式：p000001。用于生成头像路径等 |
| `name` | String | ✓ | - | 中文名 |
| `nameEn` | String | - | null | 英文名/原名 |
| `avatarPath` | String | - | null | 共享头像路径。相对于 site/public/assets/people/。示例：p000001-avatar.jpg |
| `profileLink` | String | - | null | 默认外链。如 Wikipedia、百度百科等 |
| `notes` | String | - | null | 备注 |
| `extraJson` | String | - | null | 扩展信息（JSON） |

#### 索引

| 索引名 | 字段 |
|--------|------|
| `idx_people_name` | name, nameEn |

---

### 3. WorkCredit（作品与人物关系表）

**说明**：承载导演/编剧/主演/制片人/作者/译者/原著/配音等关系。

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `id` | Int | ✓ | auto | 自增主键 |
| `workId` | String | ✓ | - | 作品 ID |
| `personId` | Int | ✓ | - | 人物 ID |
| `department` | Department | ✓ | - | 部门。枚举：direction/writing/cast/production/music/book/translation/original_work/other |
| `creditType` | String | ✓ | - | 职位类型。如：导演、编剧、主演、制片人 |
| `displayLabel` | String | - | null | 显示标签。如角色名："库珀 Cooper" |
| `characterName` | String | - | null | 角色名。演员专用 |
| `sortOrder` | Int | ✓ | 0 | 排序顺序 |
| `isPrimary` | Boolean | ✓ | false | 是否主要人员。用于前台优先展示 |
| `linkOverride` | String | - | null | 链接覆盖。如需为该人物在该作品中指定特殊外链 |
| `extraJson` | String | - | null | 扩展信息（JSON） |

#### 索引

| 索引名 | 字段 |
|--------|------|
| `idx_work_credits_work_id` | workId, sortOrder |
| `idx_work_credits_person_id` | personId |

---

### 4. Term（公共词项定义表）

**说明**：承载 genre（类型）和 tag（标签）。

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `id` | Int | ✓ | auto | 自增主键 |
| `termType` | TermType | ✓ | - | 词项类型。枚举：genre/tag |
| `name` | String | ✓ | - | 名称。如：剧情、犯罪、科幻、经典 |
| `moduleScope` | String | - | null | 模块作用域。genre 可按模块建立作用域 |
| `submoduleScope` | String | - | null | 子模块作用域 |
| `description` | String | - | null | 描述 |
| `sortOrder` | Int | ✓ | 0 | 排序顺序 |
| `isActive` | Boolean | ✓ | true | 是否启用 |

#### 索引

| 索引名 | 字段 |
|--------|------|
| `idx_terms_scope` | termType, moduleScope, submoduleScope, sortOrder |
| `idx_terms_identity` | termType, name, moduleScope, submoduleScope |

---

### 5. WorkTerm（作品与词项关联表）

**说明**：承载作品属于哪些类型、带有哪些标签。

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `id` | Int | ✓ | auto | 自增主键 |
| `workId` | String | ✓ | - | 作品 ID |
| `termId` | Int | ✓ | - | 词项 ID |
| `sortOrder` | Int | ✓ | 0 | 排序顺序 |
| `note` | String | - | null | 备注 |

#### 索引

| 索引名 | 字段 |
|--------|------|
| `idx_work_terms_work_id` | workId, sortOrder |
| `idx_work_terms_term_id` | termId |
| UNIQUE | workId, termId |

---

### 6. SchemaMigration（迁移记录表）

**说明**：记录已应用的数据库迁移版本。

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `version` | String | ✓ | - | 迁移版本号（主键） |
| `appliedAt` | DateTime | ✓ | now() | 应用时间 |

---

## 枚举定义

### Module（一级模块）

| 值 | 中文 |
|----|------|
| `video` | 影视 |
| `anime` | 动漫 |
| `book` | 书 |
| `music` | 音乐 |
| `game` | 游戏 |

### Submodule（二级模块）

| 值 | 中文 |
|----|------|
| `movie` | 电影 |
| `tv_series` | 电视剧 |
| `documentary` | 纪录片 |
| `short_drama` | 短剧 |
| `anime_movie` | 动画电影 |
| `anime_series` | 番剧 |

### SchemaType（Schema 类型）

| 值 | 中文 |
|----|------|
| `live_action_movie` | 真人电影 |
| `animated_movie` | 动画电影 |
| `live_action_series` | 真人剧集 |
| `animated_series` | 动画剧集 |
| `documentary_film` | 纪录片电影 |
| `documentary_series` | 纪录片剧集 |
| `book` | 书籍 |
| `music` | 音乐 |
| `game` | 游戏 |

### WorkStatus（作品状态）

| 值 | 中文 |
|----|------|
| `draft` | 草稿 |
| `published` | 已发布 |
| `archived` | 已归档 |

### Department（部门）

| 值 | 中文 |
|----|------|
| `direction` | 导演 |
| `writing` | 编剧 |
| `cast` | 演员 |
| `production` | 制片 |
| `music` | 音乐 |
| `book` | 书籍作者 |
| `translation` | 译者 |
| `original_work` | 原著 |
| `other` | 其他 |

### TermType（词项类型）

| 值 | 中文 |
|----|------|
| `genre` | 类型 |
| `tag` | 标签 |

---

## 使用方式

### 1. 启动可视化界面

```bash
npx prisma studio
```

浏览器会自动打开 `http://localhost:51212`，显示：
- 所有表的数据
- 字段注释（鼠标悬停查看）
- 可编辑数据

### 2. 修改 Schema

```bash
# 修改 prisma/schema.prisma 后
npx prisma migrate dev --name <迁移名称>

# 这会自动：
# 1. 创建迁移文件
# 2. 应用迁移到数据库
# 3. 重新生成 Prisma Client
```

### 3. 在代码中使用

```typescript
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

// 查询所有电影
const movies = await prisma.work.findMany({
  where: {
    module: 'video',
    submodule: 'movie',
    status: 'published',
  },
  include: {
    credits: {
      include: { person: true },
    },
    terms: {
      include: { term: true },
    },
  },
});
```

---

## 关系图

```
┌─────────────────────────────────────────────────────────────┐
│                         Work                                 │
│  作品主表                                                    │
│  - id (PK)                                                  │
│  - module, submodule, schemaType                            │
│  - title, originalTitle, year, country...                   │
│  - JSON fields: ratings, images, reviews...                 │
└─────────────────────────────────────────────────────────────┘
        │                           │
        │ 1:N                       │ N:M
        ▼                           ▼
┌───────────────────────┐   ┌───────────────────────┐
│    WorkCredit         │   │      WorkTerm         │
│  作品与人物关系        │   │  作品与词项关联        │
│  - workId (FK)        │   │  - workId (FK)        │
│  - personId (FK)      │   │  - termId (FK)        │
│  - department         │   │  - sortOrder          │
│  - creditType         │   └───────────────────────┘
│  - sortOrder          │           │
└───────────────────────┘           │ N:1
        │                           ▼
        │ N:1               ┌───────────────────────┐
        ▼                   │        Term           │
┌───────────────────────┐   │  公共词项定义表        │
│       Person          │   │  - termType           │
│  公共人物主表          │   │  - name               │
│  - personCode (UK)    │   │  - moduleScope        │
│  - name, nameEn       │   │  - submoduleScope     │
│  - avatarPath         │   └───────────────────────┘
│  - profileLink        │
└───────────────────────┘

图例：
PK = Primary Key (主键)
FK = Foreign Key (外键)
UK = Unique Key (唯一键)
N:1 = Many-to-One (多对一)
N:M = Many-to-Many (多对多)
```
