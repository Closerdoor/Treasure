# Schema 变更记录

## 版本：v6.0

**变更日期**：2026-05-09

---

## 一、related 字段结构调整

### 背景

当前 `related` 字段中的 `similar`/`series` 数据只有 `title`，缺少作品 ID，导致前端无法跳转到相似作品。

### 问题分析

- 爬取豆瓣"推荐电影"时，只获取了标题，没有获取豆瓣 subject ID
- 导入时直接存储原始数据，没有做标题匹配
- 导出时也没有补充作品 ID
- 标题匹配不可靠（重名、原名差异等问题）

### 新设计

**数据结构**：

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

**新增字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `source` | string | 是 | 数据来源平台标识 |
| `sourceId` | string | 是 | 来源平台的作品 ID |

**source 枚举值**：

| 值 | 说明 | sourceId 示例 |
|------|------|------|
| `douban` | 豆瓣 | `1292052`（subject ID） |
| `tmdb` | TMDB | `8392`（movie ID） |
| `imdb` | IMDb | `tt0107204`（title ID） |

### 实现步骤

1. **爬取阶段**：获取推荐作品的外部 ID
   - 豆瓣推荐 → 获取豆瓣 subject ID
   - TMDB 推荐 → 获取 TMDB movie ID
   - IMDb 推荐 → 获取 IMDb title ID

2. **导入阶段**：直接存储 `source` + `sourceId`，不做匹配

3. **导出阶段**：根据外部 ID 匹配数据库，补充作品 ID
   - 匹配逻辑：用 `sourceId` 匹配 `externalSource` 中对应平台的 `id`
   - 匹配成功 → 补充作品 `id`
   - 匹配失败 → 仅保留标题（不可跳转）

### 代码变更

1. **douban.py**：从推荐链接 URL 提取豆瓣 subject ID
   ```python
   # URL 格式: https://movie.douban.com/subject/1292052/
   match = re.search(r'/subject/(\d+)/', url)
   if match:
       source_id = match.group(1)
   ```

2. **merger.py**：转换数据结构，添加 `source` 和 `sourceId`
   ```python
   similar.append({
       "title": rec.get("title"),
       "source": rec.get("source", "douban"),
       "sourceId": rec.get("sourceId", ""),
       "year": None,
       "rating": float(rec.get("rating")) if rec.get("rating") else None
   })
   ```

3. **update_related.py**：更新已有数据
   - 为 250 条已有记录添加 `source` 和 `sourceId` 字段
   - `source` 固定为 `"douban"`
   - `sourceId` 暂时为空字符串（需重新爬取获取）

### 数据迁移

已执行 `update_related.py` 更新 250 条记录：

```bash
python update_related.py --dry-run  # 预览
python update_related.py            # 执行更新
```

### 优势

- 明确数据来源，可追溯
- 支持多平台匹配，覆盖率高
- 避免标题匹配的不可靠性
- 导出时自动匹配，无需重新导入历史数据

---

## 版本：v5.0

**变更日期**：2026-05-07

---

## 一、数据导入

### 豆瓣 Top 250 电影数据导入

从 `temp-script/movie-ingest/data/` 导入豆瓣 Top 250 电影数据到数据库。

**数据来源**：
- 豆瓣（主数据源）：基本信息、演职人员、评分、评论
- TMDB：补充评分、制片公司
- OMDb：补充 IMDb/烂番茄/Metacritic 评分
- 百度百科：补充词条链接
- 维基百科：补充剧情简介

**导入结果**：

| 表 | 记录数 | 说明 |
|------|--------|------|
| `works` | 249 | 豆瓣 Top 250（跳过 0101000001） |
| `person` | 4527 | 去重后的导演/编剧/演员 |
| `category` | 27 | 电影类型 |
| `work_person` | 5660 | 演职关系 |
| `work_category` | 698 | 类型关联 |

**数据完整性**：
- 所有作品都有豆瓣评分、IMDb 评分
- 所有作品都有外部来源（豆瓣 + IMDb + TMDB + 百度百科 + 维基百科）
- 所有作品都有简介、评论
- 9 部作品无剧情（维基百科无数据）
- 10 部作品无 TMDB 评分

---

## 二、字段映射规则

### works 表字段映射

| Prisma 字段 | 数据来源 | 提取规则 |
|-------------|---------|---------|
| `id` | 目录名 | 直接使用（0101000002 - 0101000250） |
| `title` | 豆瓣.title | 中文标题 |
| `titleOriginal` | 豆瓣.original_title | 原名 |
| `otherTitles` | 豆瓣.aliases | JSON.stringify |
| `year` | 豆瓣.year | parseInt |
| `country` | 豆瓣.countries | 取第一个（按 ` / ` 分割） |
| `language` | 豆瓣.languages | 取第一个（按 ` / ` 分割） |
| `totalTime` | 豆瓣.runtime_minutes | 片长（分钟） |
| `studio` | TMDB.detail.production_companies[0] | 制片公司 |
| `releaseDates` | 豆瓣.release_dates | JSON.stringify |
| `scores` | 多源合并 | 豆瓣/IMDb/TMDB/烂番茄/Metacritic |
| `introduction` | 豆瓣.summary | 完整内容，不截取 |
| `story` | 维基百科.summary > 豆瓣.story | 完整内容，不截取 |
| `externalSource` | 多源合并 | 豆瓣 + IMDb + TMDB + 百度百科 + 维基百科 |
| `images` | 本地文件 | poster-main.webp |
| `comments` | 豆瓣.comments + 豆瓣.reviews + TMDB.reviews | 不限制数量 |
| `related` | 豆瓣.recommendations | 相关作品 |

### person 表字段映射

| Prisma 字段 | 数据来源 | 提取规则 |
|-------------|---------|---------|
| `personId` | 系统生成 | p000001, p000002... |
| `name` | 豆瓣.directors/writers/casts | 人物名 |

### work_person 表字段映射

| Prisma 字段 | 数据来源 | 提取规则 |
|-------------|---------|---------|
| `department` | 角色类型 | direction/writing/cast |
| `role` | 固定值 | 导演/编剧/演员 |
| `order` | 数组索引 | 0, 1, 2... |
| `isPrimary` | 判断 | 导演/前 5 名演员为 true |

### category 表字段映射

| Prisma 字段 | 数据来源 | 提取规则 |
|-------------|---------|---------|
| `group` | 固定值 | type |
| `name` | 豆瓣.genres | 类型名 |
| `module` | 固定值 | video |
| `submodule` | 固定值 | movie |

---

## 三、数据质量问题

### 已修复问题

| 问题 | 影响 | 修复方式 |
|------|------|---------|
| work_person.role 中文乱码 | 5660 条 | 重新导入，使用 UTF-8 编码 |
| works.external_source 中文乱码 | 249 条 | 更新字段，使用 UTF-8 编码 |
| 重复作品（3部） | 阿甘正传、霸王别姬、星际穿越 | 合并数据，补充 story/soundtrack |

### 已知限制

| 问题 | 影响 | 说明 |
|------|------|------|
| 演员角色名缺失 | 所有演员 | 豆瓣数据无角色名字段 |
| 人物英文名缺失 | 所有人物 | 豆瓣数据无英文名字段 |
| 人物头像缺失 | 所有人物 | 豆瓣数据无头像字段 |
| TMDB credits 为空 | 大多数电影 | TMDB API 返回空数组 |

---

## 四、图片资源

### 目录结构

```
.local/assets/video/movie/
├── 0101000002/
│   └── poster-main.webp
├── 0101000003/
│   └── poster-main.webp
└── ...
```

### 图片格式

- 格式：WebP
- 来源：豆瓣主海报
- 数量：249 张

---

## 五、备份文件

### 位置

`.local/backup/`

### 文件列表

| 文件 | 说明 |
|------|------|
| `works-backup.json` | 剩余 2 条旧数据（肖申克的救赎、肖申克的救赎1） |
| `person-backup.json` | 旧人物数据（116 条） |
| `category-backup.json` | 旧类型数据（8 条） |

---

## 六、版本历史

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v1.0 | 2026-05-06 | 初始 Prisma Schema |
| v2.0 | 2026-05-06 | 重新设计 Work 表字段命名和分组 |
| v3.0 | 2026-05-07 | 重新设计 Person/WorkCredit/WorkType/WorkCategory 表字段命名 |
| v4.0 | 2026-05-07 | 表名改为单数形式，图片迁移到 .local/assets/ |
| v5.0 | 2026-05-07 | 导入豆瓣 Top 250 电影数据（249 部） |

---

## 版本：v4.0

**变更日期**：2026-05-07

---

## 一、表名变更

| 旧表名 | 新表名 | 说明 |
|--------|--------|------|
| `people` | `person` | 人物表改为单数形式 |
| `work_credits` | `work_person` | 作品人物关系表 |
| `work_types` | `category` | 类型/标签表 |
| `work_categories` | `work_category` | 作品分类关联表 |

---

## 二、字段变更

### WorkCategory 表

| 旧字段 | 新字段 | 说明 |
|--------|--------|------|
| `type_id` | `category_id` | 关联字段重命名 |

---

## 三、索引变更

| 旧索引名 | 新索引名 |
|----------|----------|
| `idx_people_name` | `idx_person_name` |
| `idx_work_credits_work_id` | `idx_work_person_work_id` |
| `idx_work_credits_person_id` | `idx_work_person_person_id` |
| `idx_work_types_scope` | `idx_category_scope` |
| `idx_work_types_identity` | `idx_category_identity` |
| `idx_work_categories_work_id` | `idx_work_category_work_id` |
| `idx_work_categories_type_id` | `idx_work_category_category_id` |

---

## 四、系统表说明

### sqlite_sequence

SQLite 内部系统表，用于跟踪 `AUTOINCREMENT` 列的最大值。

- 自动维护，不要手动修改
- 确保自增 ID 即使删除数据后也不会重置

### schema_migrations

Prisma 内部迁移记录表，跟踪已应用的数据库迁移。

- 由 Prisma Migrate 自动维护
- 防止重复执行迁移

---

## 五、最终表结构

| 表名 | 数据量 | 说明 |
|------|--------|------|
| `works` | 6 | 作品主表 |
| `person` | 116 | 人物表 |
| `work_person` | 0 | 作品人物关系表 |
| `category` | 8 | 类型/标签表 |
| `work_category` | 0 | 作品分类关联表 |
| `sqlite_sequence` | - | SQLite 系统表 |
| `schema_migrations` | - | Prisma 迁移记录 |

---

## 六、版本历史

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v1.0 | 2026-05-06 | 初始 Prisma Schema |
| v2.0 | 2026-05-06 | 重新设计 Work 表字段命名和分组 |
| v3.0 | 2026-05-07 | 重新设计 Person/WorkCredit/WorkType/WorkCategory 表字段命名 |
| v4.0 | 2026-05-07 | 表名改为单数形式，图片迁移到 .local/assets/ |

---

## 版本：v3.0

**变更日期**：2026-05-07

---

## 一、表名变更

| 旧表名 | 新表名 | 说明 |
|--------|--------|------|
| `Term` | `WorkType` | 词项表改名为类型表 |
| `WorkTerm` | `WorkCategory` | 作品词项关联表改名为作品分类关联表 |

---

## 二、Person 表字段变更

| 旧字段 | 新字段 | 变化类型 | 说明 |
|--------|--------|----------|------|
| `personCode` | `personId` | 重命名 | 人物代码 |
| `nameEn` | `nameEn` | 不变 | 英文名/原名 |
| `avatarPath` | `avatarPath` | 不变 | 头像路径 |
| `profileLink` | `profileLink` | 不变 | 外部链接 |
| `notes` | `intro` | 重命名 | 简介 |
| `extra` | **删除** | 删除 | 不需要 |

---

## 三、WorkCredit 表字段变更

| 旧字段 | 新字段 | 变化类型 | 说明 |
|--------|--------|----------|------|
| `department` | `department` | 不变 | 部门 |
| `creditType` | `role` | 重命名 | 具体职位 |
| `displayLabel` | **删除** | 删除 | 不需要 |
| `characterName` | `character` | 重命名 | 角色名 |
| `sortOrder` | `order` | 重命名 | 排序 |
| `isPrimary` | `isPrimary` | 不变 | 是否主要人员 |
| `linkOverride` | **删除** | 删除 | 不需要 |
| `extra` | **删除** | 删除 | 不需要 |

---

## 四、WorkType 表字段变更（原 Term 表）

| 旧字段 | 新字段 | 变化类型 | 说明 |
|--------|--------|----------|------|
| `termType` | `group` | 重命名 | 分组（type/tag） |
| `name` | `name` | 不变 | 名称 |
| `moduleScope` | `module` | 重命名 | 模块作用域 |
| `submoduleScope` | `submodule` | 重命名 | 子模块作用域 |
| `description` | **删除** | 删除 | 不需要 |
| `sortOrder` | `order` | 重命名 | 排序 |
| `isActive` | `enabled` | 重命名 | 是否启用 |

### 枚举值变更

| 旧值 | 新值 | 说明 |
|------|------|------|
| `genre` | `type` | 类型 |
| `tag` | `tag` | 标签（不变） |

---

## 五、WorkCategory 表字段变更（原 WorkTerm 表）

| 旧字段 | 新字段 | 变化类型 | 说明 |
|--------|--------|----------|------|
| `termId` | `typeId` | 重命名 | 类型/标签ID |
| `sortOrder` | `order` | 重命名 | 排序 |
| `note` | **删除** | 删除 | 不需要 |

---

## 六、字段数量变化

| 表 | 旧字段数 | 新字段数 | 变化 |
|----|---------|---------|------|
| Work | 29 | 29 | 0 |
| Person | 8 | 7 | -1 |
| WorkCredit | 11 | 8 | -3 |
| WorkType | 8 | 7 | -1 |
| WorkCategory | 5 | 4 | -1 |

---

## 七、数据迁移

### Person 迁移

```sql
INSERT INTO people (id, person_id, name, name_en, avatar_path, profile_link, intro)
SELECT id, person_code, name, name_en, avatar_path, profile_link, notes
FROM people_backup;
```

### WorkType 迁移

```sql
INSERT INTO work_types (id, "group", name, module, submodule, "order", enabled)
SELECT 
  id, 
  CASE WHEN term_type = 'genre' THEN 'type' ELSE 'tag' END,
  name, 
  module_scope, 
  submodule_scope, 
  sort_order, 
  is_active
FROM terms_backup;
```

---

## 八、版本历史

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v1.0 | 2026-05-06 | 初始 Prisma Schema |
| v2.0 | 2026-05-06 | 重新设计 Work 表字段命名和分组 |
| v3.0 | 2026-05-07 | 重新设计 Person/WorkCredit/WorkType/WorkCategory 表字段命名 |

---

## 版本：v2.0

**变更日期**：2026-05-06

---

## 一、字段分组调整

### 新的字段分组

```
标识信息（4个）
├── id              作品ID
├── module          一级模块
├── submodule       二级模块
└── schemaType      内容类型

基本信息（11个）
├── title           中文标题
├── titleOriginal   原名
├── otherTitles     别名
├── year            年份
├── country         国家/地区
├── language        语言
├── totalTime       总时长
├── studio          制片方
├── releaseDates    上映日期
├── quotes          名言
└── scores          评分

剧集专用（3个）
├── episodeCount    集数
├── episodeTime     单集时长
└── episodesStory   分集剧情

内容文本（2个）
├── introduction    简介
└── story           剧情

外部来源（1个）
└── externalSource  外部来源

媒体资源（2个）
├── images          图片
└── videos          视频

评论内容（1个）
└── comments        影评

音乐相关（1个）
└── soundtrack      原声

关联作品（1个）
└── related         相关作品

特殊内容（1个）
└── characters      角色介绍

系统字段（3个）
├── status          状态
├── createdAt       创建时间
└── updatedAt       更新时间
```

---

## 二、字段变更对照表

### Work 表

| 旧字段 | 新字段 | 变化类型 | 说明 |
|--------|--------|----------|------|
| `id` | `id` | 不变 | |
| `module` | `module` | 不变 | |
| `submodule` | `submodule` | 不变 | |
| `schemaType` | `schemaType` | 不变 | |
| `title` | `title` | 不变 | |
| `originalTitle` | `titleOriginal` | 重命名 | |
| `aliasesJson` | `otherTitles` | 重命名 | 去掉 `Json` 后缀 |
| `year` | `year` | 不变 | |
| `country` | `country` | 不变 | |
| `language` | `language` | 不变 | |
| `runtimeMinutes` | `totalTime` | 重命名 | |
| `publishCompany` | `studio` | 重命名 | |
| `releaseDatesJson` | `releaseDates` | 重命名 | 去掉 `Json` 后缀 |
| `quotesJson` | `quotes` | 重命名+结构调整 | 结构从对象数组改为字符串数组 |
| `ratingsJson` | `scores` | 重命名+移动 | 移动到"基本信息"分组 |
| `synopsisText` | `introduction` | 重命名 | |
| `synopsisNote` | **删除** | 删除 | |
| `storyText` | `story` | 重命名 | |
| `identifiersJson` | **删除** | 删除 | 合并到 `externalSource` |
| `linksJson` | **删除** | 删除 | 合并到 `externalSource` |
| - | `externalSource` | 新增 | 合并 `externalIds` 和 `externalLinks` |
| `imagesJson` | `images` | 重命名 | 去掉 `Json` 后缀 |
| `videosJson` | `videos` | 重命名 | 去掉 `Json` 后缀 |
| `reviewsJson` | `comments` | 重命名 | |
| `soundtrackJson` | `soundtrack` | 重命名+结构调整 | 增加 `cover` 和 `duration` 字段 |
| `relationsJson` | `related` | 重命名 | |
| `episodeStoriesJson` | `episodesStory` | 重命名+移动 | 移动到"剧集专用"分组 |
| `charactersJson` | `characters` | 重命名 | |
| `status` | `status` | 不变 | |
| `createdAt` | `createdAt` | 不变 | |
| `updatedAt` | `updatedAt` | 不变 | |

---

## 三、JSON 结构变更

### 1. quotes（名言）

**旧结构**：
```json
[
  { "text": "内容", "speaker": "说话人" }
]
```

**新结构**：
```json
["名言1", "名言2"]
```

**变化**：从对象数组改为字符串数组，删除 `speaker` 字段

---

### 2. externalSource（外部来源）

**旧结构**（两个字段）：
```json
// externalIds
{ "douban": "1889243", "imdb": "tt0816692", "tmdb": "157336" }

// externalLinks
{ "douban": "https://...", "imdb": "https://..." }
```

**新结构**（合并为一个字段）：
```json
[
  { "name": "豆瓣", "id": "1889243", "link": "https://movie.douban.com/subject/1889243/" },
  { "name": "IMDb", "id": "tt0816692", "link": "https://www.imdb.com/title/tt0816692/" },
  { "name": "TMDB", "id": "157336", "link": "https://www.themoviedb.org/movie/157336" }
]
```

**变化**：合并 `externalIds` 和 `externalLinks` 为 `externalSource`，结构改为数组

---

### 3. soundtrack（原声）

**旧结构**：
```json
{
  "albums": [
    {
      "name": "专辑名",
      "tracks": [
        { "name": "歌名", "artist": "歌手" }
      ]
    }
  ]
}
```

**新结构**：
```json
{
  "albums": [
    {
      "name": "专辑名",
      "cover": "封面图片.jpg",
      "tracks": [
        { "name": "歌名", "artist": "歌手", "duration": "03:45" }
      ]
    }
  ]
}
```

**变化**：
- 专辑增加 `cover` 字段（封面图片）
- 歌曲增加 `duration` 字段（时长）

---

## 四、分组变更

### 评分信息 → 基本信息

`scores` 字段从"评分信息"分组移动到"基本信息"分组。

### 影视专用 → 剧集专用

原"影视专用"分组改名为"剧集专用"，包含：
- `episodeCount` - 集数
- `episodeTime` - 单集时长
- `episodesStory` - 分集剧情（从"特殊内容"移入）

---

## 五、删除的字段

| 字段 | 原因 |
|------|------|
| `synopsisNote` | 用途不明确，合并到 `introduction` |
| `externalIds` | 合并到 `externalSource` |
| `externalLinks` | 合并到 `externalSource` |

---

## 六、字段数量变化

| 表 | 旧字段数 | 新字段数 | 变化 |
|----|---------|---------|------|
| Work | 34 | 29 | -5 |
| Person | 9 | 9 | 0 |
| WorkCredit | 13 | 13 | 0 |
| Term | 9 | 9 | 0 |
| WorkTerm | 7 | 7 | 0 |

---

## 七、数据迁移要点

### 需要迁移的数据

1. **字段重命名**
   - `original_title` → `title_original`
   - `aliases_json` → `other_titles`
   - `runtime_minutes` → `total_time`
   - `publish_company` → `studio`
   - `release_dates_json` → `release_dates`
   - `quotes_json` → `quotes`
   - `ratings_json` → `scores`
   - `synopsis_text` → `introduction`
   - `story_text` → `story`
   - `images_json` → `images`
   - `videos_json` → `videos`
   - `reviews_json` → `comments`
   - `soundtrack_json` → `soundtrack`
   - `relations_json` → `related`
   - `episode_stories_json` → `episodes_story`
   - `characters_json` → `characters`

2. **JSON 结构转换**
   - `quotes`：从对象数组转为字符串数组
   - `externalSource`：合并 `identifiersJson` 和 `linksJson`
   - `soundtrack`：增加 `cover` 和 `duration` 字段

3. **删除字段**
   - `synopsis_note`
   - `identifiers_json`
   - `links_json`

### 迁移脚本示例

```javascript
// quotes 结构转换
const oldQuotes = JSON.parse(work.quotes_json || '[]');
const newQuotes = oldQuotes.map(q => q.text);
work.quotes = JSON.stringify(newQuotes);

// externalSource 合并
const ids = JSON.parse(work.identifiers_json || '{}');
const links = JSON.parse(work.links_json || '{}');
const sourceMap = {
  douban: '豆瓣',
  imdb: 'IMDb',
  tmdb: 'TMDB'
};
const externalSource = [];
for (const [key, name] of Object.entries(sourceMap)) {
  if (ids[key] || links[key]) {
    externalSource.push({
      name: name,
      id: ids[key] || '',
      link: links[key] || ''
    });
  }
}
work.externalSource = JSON.stringify(externalSource);
```

---

## 八、版本历史

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v1.0 | 2026-05-06 | 初始 Prisma Schema |
| v2.0 | 2026-05-06 | 重新设计字段命名和分组 |
