# 电影数据字段映射文档

本文档记录电影数据字段与数据库表结构的对应关系。

---

## 一、数据库表结构概览

| 表名 | 职责 |
|------|------|
| `works` | 作品主表（电影基本信息） |
| `person` | 人物主表（导演、演员、编剧等） |
| `work_person` | 作品与人物关系表 |
| `category` | 类型/标签表 |
| `work_category` | 作品与类型/标签关联表 |

---

## 二、数据流程

```
爬虫脚本 (crawl_basic.py)
    ↓
staging JSON 文件 (.local/staging/video/movie/{id}.json)
    ↓
导入脚本 (import_to_db.py)
    ↓
treasure.db (Prisma Schema 定义的表)
```

---

## 三、Staging JSON 字段结构

### 3.1 基本字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | String | 作品 ID | `0101000001` |
| `title` | String | 中文标题 | `肖申克的救赎` |
| `originalTitle` | String | 原名 | `The Shawshank Redemption` |
| `year` | Int | 年份 | `1994` |
| `country` | String | 国家/地区 | `美国` |
| `language` | String | 语言 | `英语` |
| `runtime` | Int | 片长（分钟） | `142` |
| `doubanId` | String | 豆瓣 ID | `1292052` |
| `imdbId` | String | IMDb ID | `tt0111161` |
| `tmdbId` | String | TMDB ID | `278` |

### 3.2 评分字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `doubanRating` | Float | 豆瓣评分 | `9.7` |
| `imdbRating` | Float | IMDb 评分 | `9.3` |
| `tmdbRating` | Float | TMDB 评分 | `8.7` |
| `rottenTomatoes` | Float | 烂番茄评分 | `9.1` |
| `metascore` | Float | Metacritic 评分 | `8.2` |
| `rated` | String | 分级 | `R` |
| `awards` | String | 获奖信息 | `Won 1 Oscar...` |

### 3.3 内容字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `synopsis` | Object | 简介 `{text, note}` |
| `story` | Object | 剧情 `{text, note}` |
| `quotes` | Array | 名言名句 |

### 3.4 数组字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `director` | Array | 导演列表 |
| `writer` | Array | 编剧列表 |
| `cast` | Array | 主演列表 |
| `otherCast` | Array | 其他演员列表 |
| `producer` | Array | 制片人列表 |
| `genre` | Array | 类型列表 |
| `tags` | Array | 标签列表 |
| `aka` | Array | 别名列表 |
| `releaseDate` | Array | 上映日期列表 |
| `videos` | Array | 视频列表 |
| `reviews` | Array | 评论列表 |
| `similar` | Array | 相似作品列表 |

### 3.5 对象字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `images` | Object | 图片信息 |
| `soundtrack` | Object | 原声信息 |

---

## 四、字段映射（Staging JSON → Prisma Schema）

### 4.1 Work 表

| Staging JSON | Prisma Schema | 转换规则 |
|--------------|---------------|----------|
| `id` | `id` | 直接使用 |
| `title` | `title` | 直接使用 |
| `originalTitle` | `titleOriginal` | 直接使用 |
| `year` | `year` | 直接使用 |
| `country` | `country` | 直接使用 |
| `language` | `language` | 直接使用 |
| `runtime` | `totalTime` | 直接使用 |
| `synopsis.text` | `introduction` | 取 text 字段 |
| `story.text` | `story` | 取 text 字段 |
| `aka` | `otherTitles` | JSON 字符串化 |
| `releaseDate` | `releaseDates` | JSON 字符串化 |
| `doubanId/imdbId/tmdbId` | `externalSource` | 合并为 `[{name, id, link}]` |
| `doubanRating/imdbRating/...` | `scores` | 合并为 `{douban, imdb, ...}` |
| `images` | `images` | JSON 字符串化 |
| `videos` | `videos` | JSON 字符串化 |
| `reviews` | `comments` | JSON 字符串化 |
| `soundtrack` | `soundtrack` | JSON 字符串化 |
| `similar` | `related` | 合并为 `{similar: [...]}` |
| `quotes` | `quotes` | JSON 字符串化 |
| - | `module` | 固定 `video` |
| - | `submodule` | 固定 `movie` |
| - | `schemaType` | 固定 `live_action_movie` |
| - | `status` | 固定 `published` |

### 4.2 Person 表

| Staging JSON | Prisma Schema | 转换规则 |
|--------------|---------------|----------|
| `name` | `name` | 直接使用 |
| `nameEn` | `nameEn` | 直接使用 |
| `avatar` | `avatarPath` | 转换为 `people/{personId}-avatar.{ext}` |
| `baike` | `profileLink` | 直接使用 |
| - | `personId` | 生成 `p000001` 格式 |

### 4.3 WorkPerson 表

| Staging JSON | Prisma Schema | 转换规则 |
|--------------|---------------|----------|
| - | `workId` | 作品 ID |
| - | `personId` | 关联 Person.id |
| `director` | `department: direction` | `role: "导演"` |
| `writer` | `department: writing/original_work` | 根据 `role` 判断 |
| `cast` | `department: cast` | `isPrimary: true` |
| `otherCast` | `department: cast` | `isPrimary: false` |
| `producer` | `department: production` | 根据 `role` 判断 |
| `role`（演员） | `character` | 角色名 |
| 顺序 | `order` | 按数组顺序 |

### 4.4 Category 表

| Staging JSON | Prisma Schema | 转换规则 |
|--------------|---------------|----------|
| `genre[]` | `name` | 类型名 |
| - | `group` | 固定 `type` |
| - | `module` | 固定 `video` |
| - | `submodule` | 固定 `movie` |
| `tags[]` | `name` | 标签名 |
| - | `group` | 固定 `tag` |

---

## 五、数据来源汇总

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

## 六、使用说明

### 6.1 运行脚本（Windows UTF-8 兼容）

**重要**：在 Windows 上运行脚本时，必须使用 `run.ps1` 启动脚本来确保 UTF-8 编码：

```powershell
# 使用启动脚本（推荐）
.\run.ps1 import_to_db.py --work-id 0101000001
.\run.ps1 crawl_basic.py --test

# 或者手动设置环境变量
$env:PYTHONUTF8 = '1'; python import_to_db.py --work-id 0101000001
```

### 6.2 爬取数据

```bash
# 爬取单部电影
python crawl_basic.py --douban-id 1292052 --title "肖申克的救赎" --work-id 0101000001

# 测试模式
python crawl_basic.py --test
```

### 6.2 导入数据库

```bash
# 导入单部作品
python import_to_db.py --work-id 0101000001

# 导入所有 staging 文件
python import_to_db.py --all

# 只导入数据库中不存在的作品
python import_to_db.py --missing

# 检查模式（不实际导入）
python import_to_db.py --all --dry-run
```

### 6.3 补充评论和图片

```bash
# 爬取评论
python crawl_reviews.py --work-id 0101000001

# 爬取图片
python crawl_images.py --work-id 0101000001
```

---

## 七、注意事项

1. **ID 生成规则**：`MMSSNNNNNN`（模块+子模块+序号）
2. **人物 ID 生成规则**：`p{NNNNNN}`（6位序号）
3. **图片存储路径**：`.local/assets/video/movie/{work_id}/`
4. **人物头像存储路径**：`.local/assets/people/{person_id}-avatar.{ext}`
5. **演职人员去重**：按 `name + nameEn` 组合去重
6. **类型/标签去重**：按 `group + name + module + submodule` 组合去重

---

文档版本：v2.0
更新日期：2026-05-09
