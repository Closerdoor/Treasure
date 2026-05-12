# 字段变更对照表

## Work 表字段变更

### 标识信息

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `id` | `id` | 不变 |
| `module` | `module` | 不变 |
| `submodule` | `submodule` | 不变 |
| `schemaType` | `schemaType` | 不变 |

### 基本信息

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `title` | `title` | 不变 |
| `originalTitle` | `titleOriginal` | 重命名，命名更一致 |
| `aliasesJson` | `otherTitles` | 去掉 `Json` 后缀，含义更清晰 |
| `year` | `year` | 不变 |
| `country` | `country` | 不变 |
| `language` | `language` | 不变 |

### 影视专用

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `runtimeMinutes` | `totalTime` | 重命名，更简洁 |
| `episodeCount` | `episodeCount` | 不变 |
| `episodeRuntimeMinutes` | `episodeTime` | 重命名，更简洁 |
| `publishCompany` | `studio` | 重命名，更准确 |

### 内容文本

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `synopsisText` | `introduction` | 重命名，去掉 `Text` 后缀 |
| `synopsisNote` | **删除** | 合并到 `introduction` |
| `storyText` | `story` | 重命名，去掉 `Text` 后缀 |

### 外部标识

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `identifiersJson` | `externalIds` | 重命名，去掉 `Json` 后缀 |
| `linksJson` | `externalLinks` | 重命名，去掉 `Json` 后缀 |

### 评分信息

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `ratingsJson` | `scores` | 重命名，去掉 `Json` 后缀 |
| `certification`（在 ratingsJson 中） | **删除** | 不再存储分级信息 |
| `awards`（在 ratingsJson 中） | **删除** | 不再存储获奖信息 |

### 媒体资源

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `imagesJson` | `images` | 重命名，去掉 `Json` 后缀 |
| `videosJson` | `videos` | 重命名，去掉 `Json` 后缀 |

### 评论内容

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `reviewsJson` | `comments` | 重命名，去掉 `Json` 后缀 |
| `quotesJson` | `quotes` | 重命名，去掉 `Json` 后缀 |

### 音乐相关

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `soundtrackJson` | `soundtrack` | 重命名，去掉 `Json` 后缀 |

### 上映信息

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `releaseDatesJson` | `releaseDates` | 重命名，去掉 `Json` 后缀 |

### 关联作品

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `relationsJson` | `related` | 重命名，去掉 `Json` 后缀 |

### 特殊内容

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `episodeStoriesJson` | `episodesStory` | 重命名，去掉 `Json` 后缀 |
| `charactersJson` | `characters` | 重命名，去掉 `Json` 后缀 |

### 系统字段

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `status` | `status` | 不变 |
| `createdAt` | `createdAt` | 不变 |
| `updatedAt` | `updatedAt` | 不变 |

---

## Person 表字段变更

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `id` | `id` | 不变 |
| `personCode` | `personCode` | 不变 |
| `name` | `name` | 不变 |
| `nameEn` | `nameEn` | 不变 |
| `avatarPath` | `avatarPath` | 不变 |
| `profileLink` | `profileLink` | 不变 |
| `notes` | `notes` | 不变 |
| `extraJson` | `extra` | 重命名，去掉 `Json` 后缀 |

---

## WorkCredit 表字段变更

| 旧字段 | 新字段 | 变化说明 |
|--------|--------|---------|
| `id` | `id` | 不变 |
| `workId` | `workId` | 不变 |
| `personId` | `personId` | 不变 |
| `department` | `department` | 不变 |
| `creditType` | `creditType` | 不变 |
| `displayLabel` | `displayLabel` | 不变 |
| `characterName` | `characterName` | 不变 |
| `sortOrder` | `sortOrder` | 不变 |
| `isPrimary` | `isPrimary` | 不变 |
| `linkOverride` | `linkOverride` | 不变 |
| `extraJson` | `extra` | 重命名，去掉 `Json` 后缀 |

---

## Term 表字段变更

无变化。

---

## WorkTerm 表字段变更

无变化。

---

## 总结

### 主要变化

1. **去掉所有 `Json` 后缀**
   - `ratingsJson` → `scores`
   - `imagesJson` → `images`
   - 等等...

2. **去掉 `Text` 后缀**
   - `synopsisText` → `introduction`
   - `storyText` → `story`

3. **更直观的命名**
   - `runtimeMinutes` → `totalTime`
   - `episodeRuntimeMinutes` → `episodeTime`
   - `publishCompany` → `studio`
   - `aliasesJson` → `otherTitles`
   - `relationsJson` → `related`

4. **删除冗余字段**
   - `synopsisNote` - 合并到 `introduction`
   - `certification` - 不再存储分级
   - `awards` - 不再存储获奖

### 字段数量变化

| 表 | 旧字段数 | 新字段数 | 变化 |
|----|---------|---------|------|
| Work | 34 | 31 | -3 |
| Person | 9 | 9 | 0 |
| WorkCredit | 13 | 13 | 0 |
| Term | 9 | 9 | 0 |
| WorkTerm | 7 | 7 | 0 |

---

## 数据迁移注意事项

由于字段名称变化，需要迁移现有数据：

1. 字段重命名需要 SQL `ALTER TABLE ... RENAME COLUMN`
2. 删除的字段需要 `ALTER TABLE ... DROP COLUMN`
3. JSON 字段内容不变，只是字段名变化

建议：
- 先备份数据库
- 使用 Prisma migrate 自动处理迁移
- 或手动编写迁移脚本
