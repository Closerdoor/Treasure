# 字段与数据源映射规则

本文档定义每个字段的数据源优先级，确保数据来源清晰、可追溯。

## 数据源说明

| 数据源 | 代码 | 优势 | 劣势 |
|--------|------|------|------|
| 豆瓣电影 | `douban` | 中文数据完整、评分准确、演职员中文 | 需要登录、图片有防盗链 |
| IMDb | `imdb` | 英文数据权威、技术数据准确 | 中文缺失、直接访问受限 |
| 百度百科 | `baike` | 中文补充、背景资料丰富 | 数据结构不统一 |
| OMDb | `omdb` | 海报、基础数据、MPAA评级 | 数据有限、需要 API Key |
| Wikipedia | `wikipedia` | 背景资料、获奖信息、制作细节 | 中文数据可能不全 |
| TMDB | `tmdb` | 海报质量高、API友好 | 部分电影无数据 |
| 系统 | `system` | 自动生成字段 | - |
| 手动 | `manual` | 用户编辑 | - |

## 字段优先级表

### 基本信息

| 字段 | 优先级 | 说明 |
|------|--------|------|
| `title` | 豆瓣 > 百度百科 | 中文名称 |
| `originalTitle` | IMDb > 豆瓣 | 原始名称（通常为英文） |
| `year` | 豆瓣 > IMDb > 百度百科 | 上映年份 |
| `genre` | 豆瓣 > IMDb | 类型标签（中文优先） |
| `country` | 豆瓣 > IMDb > 百度百科 | 制片国家/地区 |
| `language` | 豆瓣 > IMDb | 语言 |
| `runtime` | 豆瓣 > IMDb | 片长（分钟） |
| `releaseDate` | 豆瓣 > IMDb | 上映日期列表 |
| `aka` | 豆瓣 > IMDb > 百度百科 | 又名/别名 |

### 标识符

| 字段 | 优先级 | 说明 |
|------|--------|------|
| `imdbId` | 豆瓣 > IMDb | IMDb ID（ttXXXXXXX） |
| `doubanId` | 豆瓣 | 豆瓣电影 ID |
| `tmdbId` | TMDB > OMDb | TMDB ID |
| `id` | 系统 | 系统内部 ID（自动生成） |

### 评分

| 字段 | 优先级 | 说明 |
|------|--------|------|
| `doubanRating` | 豆瓣 | 豆瓣评分（0-10） |
| `doubanVotes` | 豆瓣 | 豆瓣评价人数 |
| `imdbRating` | OMDb > IMDb | IMDb 评分（0-10） |
| `imdbVotes` | OMDb > IMDb | IMDb 评价人数 |
| `rated` | OMDb > IMDb | MPAA评级（PG-13, R等） |
| `awards` | OMDb > Wikipedia | 获奖信息 |

### 演职员

| 字段 | 优先级 | 说明 |
|------|--------|------|
| `director.name` | 豆瓣 > IMDb | 导演中文名 |
| `director.nameEn` | IMDb > 豆瓣 | 导演英文名 |
| `director.avatar` | IMDb > 豆瓣 | 导演头像 |
| `director.works` | 豆瓣 > IMDb | 导演代表作 |
| `writer.name` | 豆瓣 > IMDb | 编剧中文名 |
| `writer.nameEn` | IMDb > 豆瓣 | 编剧英文名 |
| `writer.role` | 豆瓣 > IMDb | 编剧角色（编剧/原著） |
| `cast.name` | 豆瓣 > IMDb | 演员中文名 |
| `cast.nameEn` | IMDb > 豆瓣 | 演员英文名 |
| `cast.role` | 豆瓣 > IMDb | 饰演角色 |
| `cast.avatar` | IMDb > 豆瓣 | 演员头像 |
| `otherCast` | 豆瓣 > IMDb | 其他演员列表 |
| `producer` | 豆瓣 > IMDb > 百度百科 | 制片人 |

**合并策略**：
- 演职员数据需要合并豆瓣和 IMDb
- 豆瓣提供：中文名、饰演角色
- IMDb 提供：英文名、头像
- 合并时以中文名匹配，补充英文名和头像

### 内容

| 字段 | 优先级 | 说明 |
|------|--------|------|
| `synopsis.text` | 豆瓣 > 百度百科 | 短简介，用于列表页与详情顶部 |
| `synopsis.note` | 豆瓣 > 百度百科 | 简介备注（获奖信息等） |
| `story.text` | 百度百科 > 维基百科 > 豆瓣 | 完整剧情，用于详情介绍；未上映作品只允许整理公开剧情物料 |
| `story.note` | 手动 > 百度百科 > 维基百科 | 完整剧情备注；未上映作品必须写明“非完整剧情/非完整人生全程” |
| `reviews` | 豆瓣长评页 > 手动整理 | 精选长评 / 高质量评语，不用短评凑数 |
| `similar` | 豆瓣 > IMDb | 相似推荐 |

`story` 选源补充规则：

- 已上映作品：优先使用百科 / 维基可交叉验证的完整剧情段落，再按站内文风整理。
- 未上映作品：优先使用豆瓣、百科、片方公开物料中的梗概信息，只能整理已公开阶段。
- 若来源本身只覆盖角色关系、成长阶段或前半段事件，禁止补写未公开结局或完整人生后续。
- `source.json.story.note` 必须说明是“完整剧情整理”还是“基于公开剧情物料整理”。

### 媒体

| 字段 | 优先级 | 说明 |
|------|--------|------|
| `images.poster` | 豆瓣 > OMDb | 主海报（豆瓣优先，禁止使用OMDb小图） |
| `images.posters` | 豆瓣 > IMDb | 补充海报列表，不包含 `images.poster` |
| `images.stills` | 豆瓣 > IMDb | 剧照列表 |
| `images.wallpapers` | 豆瓣 > IMDb | 壁纸列表，允许为空 |
| `videos` | 豆瓣 > IMDb | 预告片列表 |
| `soundtrack` | 百度百科 > 豆瓣 | 原声带信息（百度百科最完整） |

### 链接

| 字段 | 优先级 | 说明 |
|------|--------|------|
| `links.douban` | 豆瓣 | 豆瓣电影链接 |
| `links.imdb` | 豆瓣 > IMDb | IMDb 链接 |
| `links.tmdb` | IMDb > OMDb | TMDB 链接；缺失时统一写 `null` |

### 系统字段

| 字段 | 优先级 | 说明 |
|------|--------|------|
| `module` | 系统 | 模块（video） |
| `submodule` | 系统 | 子模块（movie） |
| `createdAt` | 系统 | 录入时间 |
| `updatedAt` | 系统 | 更新时间 |

## 合并规则

### 单一来源字段

直接取优先级最高的数据源值，记录来源。

示例：
```json
{
  "title": {
    "value": "肖申克的救赎",
    "source": "douban"
  }
}
```

### 多来源合并字段

需要从多个数据源合并的字段，记录所有来源。

示例：
```json
{
  "cast": {
    "value": [...],
    "source": "merged",
    "sources": [
      {
        "source": "douban",
        "fields": ["name", "role"]
      },
      {
        "source": "imdb",
        "fields": ["nameEn", "avatar"]
      }
    ]
  }
}
```

### 冲突解决

当多个数据源提供相同字段但值不同时：

1. **按优先级表选择**：使用优先级最高的数据源
2. **记录冲突**：在 source.json 中记录其他数据源的值
3. **用户确认**：如果差异较大，询问用户选择

示例：
```json
{
  "runtime": {
    "value": 142,
    "source": "douban",
    "conflicts": [
      {
        "source": "imdb",
        "value": 144,
        "note": "IMDb 显示 144 分钟，可能为不同版本"
      }
    ]
  }
}
```

## 图片来源规则

| 图片类型 | 来源 | 说明 |
|----------|------|------|
| 主海报 | 豆瓣 > Wikipedia > TMDB | **禁止使用 OMDb 海报作为主海报**（质量不稳定，通常 < 100KB） |
| 海报列表 | **TMDB** > 豆瓣 | TMDB 无防盗链，自动化爬取优先 |
| 剧照 | **TMDB** > 豆瓣 | TMDB backdrops 无防盗链，自动化爬取优先 |
| 壁纸 | 豆瓣 | 官方壁纸 |
| 演员头像 | Wikipedia > IMDb > 豆瓣 | Wikipedia 头像最标准且无防盗链 |
| 导演头像 | Wikipedia > IMDb > 豆瓣 | Wikipedia 头像最标准且无防盗链 |
| 视频封面 | 豆瓣 | 预告片截图 |

**TMDB 图片爬取优势**：
- 无防盗链，可直接下载
- 图片质量高（original 尺寸）
- 可通过正则提取 URL
- 自动化程度高

**TMDB ID 查询**：
- 手动查询：访问 themoviedb.org 搜索电影名
- API 查询：需要 API key
- 常见电影 TMDB ID：
  - 肖申克的救赎：278
  - 阿甘正传：13
  - 这个杀手不太冷：1104

## 更新记录

| 日期 | 变更 |
|------|------|
| 2026-05-02 | 收紧 `story` 选源规则，新增未上映作品不得补写未公开剧情的约束 |
| 2026-05-01 | 添加 TMDB 图片来源优先级（海报列表、剧照） |
| 2026-05-01 | 添加 Wikipedia、TMDB 数据源；添加 rated、awards、tmdbId 字段 |
| 2026-05-01 | 初始版本 |
