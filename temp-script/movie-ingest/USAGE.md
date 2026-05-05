# 电影数据多源爬取工具 - 使用说明

## 一、工具概述

本工具用于从多个来源爬取电影数据，输出符合数据库设计的 JSON 数据，用于个人收藏馆网站数据录入。

### 数据来源

| 来源 | 数据类型 | 爬取方式 | 优先级 |
|------|----------|----------|--------|
| 豆瓣 | 基本信息、评分、短评、长评、图片、标签、相关推荐 | Playwright | 最高 |
| TMDB | 基本信息、演职人员、图片、视频、评分 | REST API | 高 |
| OMDb | 评分、分级、获奖 | REST API | 高 |
| 百度百科 | 基本信息补充 | Playwright | 中 |
| Wikipedia | 剧情详解、名言名句 | Playwright | 中 |
| 烂番茄 | 评分、评论 | Playwright | 低 |
| Metacritic | 评分、评论 | Playwright | 低 |

---

## 二、环境要求

### 依赖安装

```bash
pip install playwright beautifulsoup4 aiohttp pillow
playwright install chromium
```

### 代理配置

如果需要代理访问，修改 `config.py`：

```python
PROXY_ENABLED = True
PROXY_URL = "http://127.0.0.1:7890"  # 修改为你的代理地址
```

---

## 三、使用方法

### 1. 测试模式（单部电影）

```bash
python main.py
```

默认测试电影为《星际穿越》，可在 `config.py` 中修改：

```python
TEST_MOVIE = {
    "douban_id": "1889243",
    "title": "星际穿越",
    "imdb_id": "tt0816692"
}
```

### 2. 批量模式

修改 `main.py` 中的代码：

```python
# 加载电影列表
movie_list = [
    {"douban_id": "1292052", "title": "肖申克的救赎"},
    {"douban_id": "1291546", "title": "霸王别姬"},
    # ...
]

# 运行批量
await pipeline.run_batch(movie_list)
```

### 3. 豆瓣登录

首次运行会打开浏览器，需要手动登录豆瓣：
1. 在浏览器中登录豆瓣账号
2. 回到终端按回车继续
3. Cookie 会自动保存，下次运行无需重新登录

---

## 四、输出结构

每部电影生成一个独立目录：

```
data/
└── 0101000001/                    # 作品 ID
    ├── data.json                  # 合并后的完整数据
    ├── raw/                       # 原始数据
    │   ├── douban.json
    │   ├── tmdb.json
    │   ├── omdb.json
    │   ├── baike.json
    │   ├── wikipedia.json
    │   ├── rotten_tomatoes.json
    │   └── metacritic.json
    └── images/                    # 图片
        ├── poster-001.webp        # 海报
        ├── poster-002.webp
        ├── still-001.webp         # 剧照
        └── ...
```

---

## 五、数据结构说明

### 5.1 `data.json` 字段说明

#### 基础字段

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| `id` | string | 作品 ID（格式：MMSSNNNNNN） | 系统生成 |
| `title` | string | 中文标题 | 豆瓣 |
| `original_title` | string | 原名（英文或源语言） | 豆瓣 |
| `year` | number | 上映年份 | 豆瓣 |
| `country` | string | 制片国家/地区（单个） | 豆瓣上映日期 |
| `language` | string | 语言 | 豆瓣 |
| `runtime_minutes` | number | 片长（分钟） | 豆瓣 |
| `synopsis_text` | string | 短简介 | 豆瓣 |
| `story_text` | string | 剧情详解 | Wikipedia |
| `module` | string | 一级模块 | 固定 `video` |
| `submodule` | string | 二级分类 | 固定 `movie` |
| `schema_type` | string | 结构类型 | 固定 `live_action_movie` |
| `status` | string | 数据状态 | 固定 `published` |
| `created_at` | string | 创建时间 | 系统生成 |
| `updated_at` | string | 更新时间 | 系统生成 |
| `assetDir` | string | 资源目录路径 | 系统生成 |

#### `identifiers_json`（标识符）

```json
{
  "douban": "1889243",           // 豆瓣 ID
  "imdb": "tt0816692",           // IMDb ID
  "tmdb": "157336",              // TMDB ID
  "baike": "星际穿越",           // 百度百科词条名
  "wikipedia_zh": "星际穿越"     // Wikipedia 词条名
}
```

#### `links_json`（外部链接）

```json
{
  "douban": "https://movie.douban.com/subject/1889243/",
  "tmdb": "https://www.themoviedb.org/movie/157336",
  "baike": "https://baike.baidu.com/item/星际穿越",
  "wikipedia_zh": "https://zh.wikipedia.org/wiki/星际穿越",
  "rottenTomatoes": "https://www.rottentomatoes.com/m/interstellar_2014"
}
```

#### `ratings_json`（评分）

```json
{
  "douban": {"value": 9.4, "scale": 10},
  "tmdb": {"value": 8.471, "scale": 10},
  "imdb": {"value": 8.7, "scale": 10},
  "rottenTomatoes": {"value": 7.3, "scale": 10, "tomatometer": 73},
  "metascore": {"value": 7.4, "scale": 10, "raw": 74},
  "certification": {"value": "PG-13"},
  "awards": {"value": "Won 1 Oscar. 45 wins & 148 nominations total"}
}
```

**字段说明**：
- `value`: 10 分制评分
- `scale`: 评分制式（固定 10）
- `tomatometer`: 烂番茄原始百分比
- `raw`: Metascore 原始分数（0-100）

#### `aliases_json`（别名）

```json
["星际启示录(港)", "星际效应(台)", "星际空间", "星际之间", "星际远航", "星际", "Flora's Letter"]
```

#### `release_dates_json`（上映日期）

```json
[
  {"date": "2014-11-12", "location": "中国大陆"},
  {"date": "2020-08-02", "location": "中国大陆重映"},
  {"date": "2014-11-07", "location": "美国"}
]
```

#### `genres`（类型）

```json
["剧情", "科幻", "冒险"]
```

#### `reviews_json`（评论）

```json
[
  {
    "author": "比岁月含蓄",
    "source": "豆瓣短评",
    "date": "2014-11-06 23:27:12",
    "content": "时间可以伸缩和折叠...",
    "rating": "50",
    "votes": 43514,
    "url": null,
    "title": null
  },
  {
    "author": "QuiteThrilling",
    "source": "豆瓣长评",
    "date": "2014-11-07",
    "content": "评论内容...",
    "url": "https://movie.douban.com/review/7181757/",
    "title": "当你想描写一个触手可及的未来，然而却……"
  }
]
```

**来源标识**：
- `豆瓣短评`: 豆瓣短评
- `豆瓣长评`: 豆瓣长评
- `Rotten Tomatoes · {媒体名}`: 烂番茄评论
- `Metacritic · {媒体名}`: Metacritic 评论

#### `images_json`（图片）

```json
{
  "poster": "poster-main.jpg",     // 主海报文件名
  "posters": [],                   // 海报列表（下载后填充）
  "stills": [],                    // 剧照列表（下载后填充）
  "postersTotal": 1753,            // 海报总数
  "stillsTotal": 1753,             // 剧照总数
  "assetDir": "video/movie/0101000001"
}
```

#### `credits`（演职人员）

```json
{
  "cast": [
    {
      "id": 525,
      "name": "Matthew McConaughey",
      "character": "Cooper",
      "order": 0,
      "profile_path": "https://image.tmdb.org/t/p/original/..."
    }
  ],
  "crew": [
    {
      "id": 525,
      "name": "Christopher Nolan",
      "job": "Director",
      "department": "Directing",
      "profile_path": "https://image.tmdb.org/t/p/original/..."
    }
  ]
}
```

#### `videos_json`（视频）

```json
[
  {
    "type": "trailer",
    "name": "Official Trailer",
    "thumbnail": "https://img.youtube.com/vi/.../maxresdefault.jpg",
    "duration": "2:30",
    "source": "youtube",
    "key": "zSWdZVtXT7E",
    "url": "https://www.youtube.com/watch?v=zSWdZVtXT7E"
  }
]
```

---

## 六、字段处理规则

### 6.1 标题处理

- `title`: 只取中文部分（如"星际穿越 Interstellar" → "星际穿越"）
- `original_title`: 从豆瓣"原名"字段获取，或从标题中提取英文部分

### 6.2 国家/地区

- 从上映日期中提取最早上映的地区
- 忽略电影节、首映等特殊上映
- 只保留一个国家/地区

### 6.3 评分换算

| 来源 | 原始分数范围 | 换算公式 |
|------|-------------|----------|
| 豆瓣 | 0-10 | 直接使用 |
| IMDb | 0-10 | 直接使用 |
| TMDB | 0-10 | 直接使用 |
| 烂番茄 | 0-100% | `value = raw / 10` |
| Metacritic | 0-100 | `value = raw / 10` |

### 6.4 图片分类

- 海报：竖版（宽高比约 2:3）
- 剧照：横版（宽高比约 16:9 或 4:3）

---

## 七、已知问题与解决方案

### 7.1 豆瓣图片下载失败

**问题**：豆瓣图片服务器返回 418 错误

**解决方案**：添加 Referer 头
```python
headers = {
    "Referer": "https://movie.douban.com/",
    "User-Agent": "..."
}
```

### 7.2 TMDB API 连接失败

**问题**：SSL 连接错误

**解决方案**：配置代理
```python
PROXY_ENABLED = True
PROXY_URL = "http://127.0.0.1:7890"
```

### 7.3 烂番茄评论获取失败

**问题**：评论页面结构变化

**解决方案**：尝试多种 CSS 选择器

### 7.4 Metacritic 搜索失败

**问题**：搜索关键词问题

**解决方案**：使用英文原名搜索

---

## 八、断点续传

进度保存在 `progress.json`，支持断点续传：
- 重新运行脚本会自动跳过已完成的来源
- 某个来源失败不影响其他来源

---

## 九、文件清单

```
movie-ingest/
├── main.py                    # 主入口
├── config.py                  # 配置文件
├── progress.py                # 进度管理
├── merger.py                  # 数据合并
├── downloader.py              # 图片下载
├── reviewer.py                # 审阅文件生成
├── sources/                   # 各来源爬取模块
│   ├── douban.py
│   ├── tmdb.py
│   ├── omdb.py
│   ├── baike.py
│   ├── wikipedia.py
│   ├── rotten_tomatoes.py
│   └── metacritic.py
├── utils/                     # 工具函数
│   ├── logger.py
│   ├── hash.py
│   └── id_generator.py
├── data/                      # 数据存储目录
├── FIELD-MAPPING.md           # 字段映射文档
├── PROJECT-PLAN.md            # 整体方案文档
├── README.md                  # 本文档
└── USAGE.md                   # 使用说明（本文档）
```

---

## 十、版本历史

### v1.0.0 (2026-05-05)

- 实现豆瓣、TMDB、OMDb、百度百科、Wikipedia、烂番茄、Metacritic 爬取
- 实现数据合并与去重
- 实现图片下载（支持代理）
- 实现断点续传
- 实现演职人员格式转换
