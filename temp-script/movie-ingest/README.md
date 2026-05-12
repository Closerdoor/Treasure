# 电影数据多源爬取工具 (movie-ingest)

> 多源爬取电影数据，写入本地 SQLite 数据库，为 Treasure 收藏馆提供结构化数据。

---

## 第一部分：项目架构概述

### 1.1 Treasure 项目整体架构

Treasure 是一个"精选型个人收藏馆"网站，采用 DB-first 的静态站流程：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Treasure 数据流                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────┐ │
│   │  temp-script │    │    SQLite    │    │  generated   │    │  Astro  │ │
│   │  数据获取    │───▶│   主数据库   │───▶│   静态JSON   │───▶│  静态站 │ │
│   └──────────────┘    └──────────────┘    └──────────────┘    └─────────┘ │
│         │                    │                    │                │       │
│         │               .local/             generated/        site/       │
│         │             treasure.db          entries/          public/      │
│         │                                indexes/           assets/      │
│         ▼                    ▼                    ▼                ▼       │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │                         GitHub Pages                                 │ │
│   └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**各层职责**：

| 层级 | 目录 | 职责 |
|------|------|------|
| 数据获取 | `temp-script/` | 爬虫、解析、实验脚本 |
| 主数据库 | `.local/treasure.db` | 本地结构化主数据源 |
| 静态JSON | `generated/` | Astro 可读取的数据中转层 |
| 静态站 | `site/` | Astro 生成的静态页面 |
| 发布 | GitHub Pages | 公开访问的静态站点 |

### 1.2 movie-ingest 在架构中的位置

```
┌─────────────────────────────────────────────────────────────────┐
│                        temp-script/                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    movie-ingest/                             ││
│  │                                                              ││
│  │   输入                      输出                             ││
│  │   ┌─────────────┐          ┌─────────────────┐              ││
│  │   │ 豆瓣 ID     │          │ .local/         │              ││
│  │   │ IMDb ID     │─────────▶│ treasure.db     │              ││
│  │   │ TMDB ID     │          │ .local/assets/  │              ││
│  │   └─────────────┘          └─────────────────┘              ││
│  │                                                              ││
│  │   数据源：豆瓣、TMDB、OMDb、百度百科、Wikipedia、烂番茄、Metacritic  ││
│  │                                                              ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ tools/db/       │
                    │ export-generated│
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ generated/      │
                    │ site/public/    │
                    └─────────────────┘
```

**定位**：movie-ingest 是数据获取与整理层，负责从多个公开数据源爬取电影数据，整理后写入本地 SQLite 数据库。

**核心职责**：
1. 从豆瓣、TMDB 等数据源爬取电影基本信息、演职员、评分、图片等
2. 合并多源数据，解决冲突，生成统一格式
3. 写入 `.local/treasure.db` 数据库
4. 下载图片资源到 `.local/assets/`

### 1.3 与其他模块的关系

| 模块 | 关系 | 说明 |
|------|------|------|
| `prisma/schema.prisma` | 表结构定义 | 定义 works、person、work_person 等表结构 |
| `.local/treasure.db` | 数据输出 | movie-ingest 的最终输出目标 |
| `.local/assets/` | 图片存储 | 海报、剧照、人物头像的存储位置 |
| `tools/db/export-generated.mjs` | 下游消费者 | 从数据库导出 JSON 给 Astro 使用 |
| `generated/` | 间接输出 | 通过 export-generated 生成 |

---

## 第二部分：movie-ingest 功能详解

### 2.1 目录结构

```
movie-ingest/
├── config.py              # 配置文件（API Keys、代理、延迟等）
├── main.py                # 主入口（命令行参数解析）
│
├── crawl_basic.py         # 模块1：爬取基本信息
├── crawl_reviews.py       # 模块2：爬取影评
├── crawl_images.py        # 模块3：爬取图片
│
├── merger.py              # 数据合并模块
├── database.py            # 数据库操作模块
├── downloader.py          # 图片下载模块
├── progress.py            # 进度管理模块
│
├── name_matcher.py        # 人物名字匹配模块
├── full_match.py          # 全量人物 TMDB ID 匹配脚本
├── fix_person_avatars.py  # 修复人物头像脚本
├── download_missing_avatars.py  # 下载缺失头像脚本
├── update_avatar_paths.py # 更新头像路径脚本
│
├── sources/               # 数据源爬虫
│   ├── douban.py          # 豆瓣爬虫（Playwright）
│   ├── tmdb.py            # TMDB 客户端（REST API）
│   ├── omdb.py            # OMDb 客户端（REST API）
│   ├── baike.py           # 百度百科爬虫（Playwright）
│   ├── wikipedia.py       # Wikipedia 爬虫（Playwright）
│   ├── rotten_tomatoes.py # 烂番茄爬虫（Playwright）
│   └── metacritic.py      # Metacritic 爬虫（Playwright）
│
├── utils/                 # 工具模块
│   ├── logger.py          # 日志工具
│   ├── id_generator.py    # ID 生成器
│   └── hash.py            # 哈希工具
│
├── data/                  # 爬取数据存储（临时）
│   └── {work_id}/
│       ├── raw/           # 原始数据（各来源 JSON）
│       └── images/        # 图片资源
│
├── README.md              # 本文档
├── RULES.md               # 开发规范
├── DATA.md                # 数据字段设计
└── .progress.json         # 进度记录文件
```

### 2.2 核心模块职责

#### 2.2.1 爬取模块

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `crawl_basic.py` | 爬取基本信息 | 豆瓣 ID | `raw/*.json` |
| `crawl_reviews.py` | 爬取影评 | 豆瓣 ID | `raw/*.json`（补充） |
| `crawl_images.py` | 爬取图片 | TMDB ID | `images/` |

**crawl_basic.py 详细功能**：
- 爬取豆瓣详情页（标题、年份、评分、简介、演职员等）
- 调用 TMDB API 获取演职员、图片、视频
- 调用 OMDb API 获取评分、分级
- 爬取百度百科补充基本信息
- 爬取 Wikipedia 获取获奖、名言名句
- 爬取烂番茄、Metacritic 获取评分

#### 2.2.2 数据处理模块

| 模块 | 职责 | 说明 |
|------|------|------|
| `merger.py` | 数据合并 | 合并各来源数据，解决冲突，生成统一格式 |
| `database.py` | 数据库操作 | 写入 works、person、work_person 等表 |
| `downloader.py` | 图片下载 | 下载海报、剧照、人物头像 |
| `progress.py` | 进度管理 | 记录爬取进度，支持断点续传 |

#### 2.2.3 人物匹配模块

| 模块 | 职责 | 说明 |
|------|------|------|
| `name_matcher.py` | 人物名字匹配 | 匹配豆瓣中文名和 TMDB 英文名 |
| `full_match.py` | 全量人物匹配 | 为所有人物匹配 TMDB ID |
| `fix_person_avatars.py` | 修复头像 | 修复人物头像路径 |
| `download_missing_avatars.py` | 下载缺失头像 | 下载 TMDB 头像 |
| `update_avatar_paths.py` | 更新头像路径 | 更新数据库中的头像路径 |

### 2.3 数据源爬虫

| 数据源 | 爬取方式 | 数据类型 | 反爬机制 |
|--------|---------|---------|---------|
| 豆瓣 | Playwright | 基本信息、评分、演职员、评论 | 需要登录、Referer 检测 |
| TMDB | REST API | 演职员、图片、视频、原声 | 无（需 API Key） |
| OMDb | REST API | 评分、分级、获奖 | 无（需 API Key） |
| 百度百科 | Playwright | 基本信息补充 | 验证码 |
| Wikipedia | Playwright | 获奖、名言名句 | 无 |
| 烂番茄 | Playwright | 评分、评论 | 有 |
| Metacritic | Playwright | 评分、评论 | 有 |

### 2.4 数据流与处理流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据处理流程                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌───────────┐                                                            │
│   │  豆瓣 ID  │                                                            │
│   └─────┬─────┘                                                            │
│         │                                                                   │
│         ▼                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      crawl_basic.py                                 │   │
│   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │   │
│   │  │  豆瓣   │  │  TMDB   │  │  OMDb   │  │ 百度百科 │  │Wikipedia│  │   │
│   │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  │   │
│   │       │            │            │            │            │        │   │
│   │       └────────────┴────────────┴────────────┴────────────┘        │   │
│   │                                │                                    │   │
│   │                                ▼                                    │   │
│   │                        ┌───────────────┐                            │   │
│   │                        │  raw/*.json   │                            │   │
│   │                        └───────────────┘                            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         merger.py                                   │   │
│   │                                                                     │   │
│   │   1. 读取各来源 JSON                                                │   │
│   │   2. 按优先级合并字段（豆瓣 > TMDB > 其他）                          │   │
│   │   3. 匹配演职员中文名和英文名                                        │   │
│   │   4. 生成统一格式数据                                               │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        database.py                                  │   │
│   │                                                                     │   │
│   │   1. 写入 works 表（作品主表）                                       │   │
│   │   2. 写入 person 表（人物主表）                                      │   │
│   │   3. 写入 work_person 表（演职关系）                                 │   │
│   │   4. 写入 category 表（类型/标签）                                   │   │
│   │   5. 写入 work_category 表（类型关联）                               │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│                            ┌─────────────────┐                              │
│                            │ .local/         │                              │
│                            │ treasure.db     │                              │
│                            │ assets/         │                              │
│                            └─────────────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**数据优先级规则**：
- 中文名：豆瓣 > 百度百科
- 英文名：TMDB > OMDb
- 年份：豆瓣 > TMDB
- 地区/语言：豆瓣（最准确）
- 演职员：豆瓣（中文名）+ TMDB（英文名、角色名、头像）
- 评分：各平台独立记录

### 2.5 使用方法

#### 2.5.1 安装依赖

```bash
pip install playwright beautifulsoup4 aiohttp pillow
playwright install chromium
```

#### 2.5.2 配置

编辑 `config.py`：

```python
# API Keys
TMDB_API_KEY = "your_tmdb_api_key"
OMDB_API_KEY = "your_omdb_api_key"

# 代理配置（TMDB API 需要代理）
PROXY_ENABLED = True
PROXY_URL = "http://127.0.0.1:7890"

# 浏览器配置
HEADLESS = False  # 首次运行建议 False，方便登录豆瓣
USE_CHROME = True  # 使用系统 Chrome
```

#### 2.5.3 测试模式（单部电影）

```bash
python main.py --test --basic
```

默认测试电影为《星际穿越》，可在 `config.py` 中修改：

```python
TEST_MOVIE = {
    "douban_id": "1889243",
    "title": "星际穿越",
    "imdb_id": "tt0816692"
}
```

#### 2.5.4 批量模式（Top250）

```bash
# 完整爬取（基本信息 + 影评 + 图片）
python main.py --top250

# 只爬取基本信息
python main.py --top250 --basic

# 只爬取影评
python main.py --top250 --reviews

# 只爬取图片
python main.py --top250 --images
```

#### 2.5.5 登录豆瓣

首次运行会打开浏览器，需要手动登录豆瓣：
1. 在浏览器中登录豆瓣账号
2. 回到终端按回车继续
3. Cookie 会自动保存，下次运行无需重新登录

### 2.6 配置说明

```python
# config.py 主要配置项

# API Keys
TMDB_API_KEY = "..."      # TMDB API Key（必需）
OMDB_API_KEY = "..."      # OMDb API Key（可选）

# 代理配置
PROXY_ENABLED = True      # 是否启用代理
PROXY_URL = "http://127.0.0.1:7890"  # 代理地址

# 爬取配置
COMMENTS_PER_SOURCE = 20  # 每个来源的评论数
REVIEWS_PER_SOURCE = 20   # 每个来源的影评数

# 延迟配置（秒）
MIN_DELAY = 2.0           # 最小延迟
MAX_DELAY = 5.0           # 最大延迟
PAGE_DELAY = 4.0          # 页面切换延迟
BATCH_DELAY = 10.0        # 批次间隔延迟

# 浏览器配置
HEADLESS = False          # 是否无头模式
USE_CHROME = True         # 是否使用系统 Chrome
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
```

### 2.7 输出结构

爬取数据存储在 `.local/` 目录下，分为三个层级：

```
.local/
│
├── raw/                           # 第一层：原始数据（各数据源独立存储）
│   └── {work_id}/                 # 每部作品一个目录（如 0101000001）
│       ├── douban.json            # 豆瓣原始数据
│       ├── tmdb.json              # TMDB 原始数据（含 detail、credits、images、videos）
│       ├── omdb.json              # OMDb 原始数据
│       ├── baike.json             # 百度百科原始数据
│       ├── wikipedia.json         # Wikipedia 原始数据
│       ├── rotten_tomatoes.json   # 烂番茄原始数据
│       └── metacritic.json        # Metacritic 原始数据
│
├── staging/                       # 第二层：合并后的中间数据
│   └── video/
│       └── movie/
│           └── {work_id}.json     # 合并后的统一格式（驼峰命名）
│
├── assets/                        # 图片资源
│   ├── works/                     # 作品图片（海报、剧照等）
│   │   └── {work_id}/
│   │       ├── poster-main.webp
│   │       └── backdrop-001.jpg
│   └── people/                    # 人物头像
│       └── tmdb-{id}-avatar.jpg
│
└── treasure.db                    # 第三层：最终数据库（SQLite）
```

**数据流转过程**：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据流转过程                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  crawl_basic.py                                                      │   │
│   │                                                                      │   │
│   │  豆瓣 ──────┐                                                        │   │
│   │  TMDB ──────┼──────▶ .local/raw/{work_id}/                           │   │
│   │  OMDb ──────┤              ├── douban.json                           │   │
│   │  百度百科 ──┤              ├── tmdb.json                             │   │
│   │  Wikipedia ─┘              ├── omdb.json                             │   │
│   │                            └── ...                                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  merger.py                                                           │   │
│   │                                                                      │   │
│   │  读取 raw/*.json                                                     │   │
│   │  按优先级合并（豆瓣 > TMDB > 其他）                                   │   │
│   │  匹配演职员中文名和英文名                                             │   │
│   │                              ──────▶ .local/staging/video/movie/     │   │
│   │                                        └── {work_id}.json            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  database.py                                                         │   │
│   │                                                                      │   │
│   │  读取 staging/{work_id}.json                                         │   │
│   │  驼峰转下划线命名                                                     │   │
│   │  写入 works、person、work_person 等表                                │   │
│   │                              ──────▶ .local/treasure.db              │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**核对数据时的使用方法**：

| 需求 | 查看位置 |
|------|---------|
| 查看某数据源的原始数据 | `.local/raw/{work_id}/{source}.json` |
| 查看合并后的统一数据 | `.local/staging/video/movie/{work_id}.json` |
| 查看最终数据库数据 | `.local/treasure.db`（可用 SQLite 工具查询） |
| 查看图片资源 | `.local/assets/works/{work_id}/` 或 `.local/assets/people/` |

**原始数据文件说明**：

| 文件 | 内容 | 用途 |
|------|------|------|
| `douban.json` | 豆瓣详情页完整数据 | 中文名、评分、简介、演职员中文名 |
| `tmdb.json` | TMDB API 返回的 detail + credits + images + videos | 英文名、角色名、头像、图片、视频 |
| `omdb.json` | OMDb API 返回数据 | IMDb 评分、烂番茄、Metascore、分级 |
| `baike.json` | 百度百科词条数据 | 补充简介、演职员 |
| `wikipedia.json` | Wikipedia 词条数据 | 获奖、名言名句 |
| `rotten_tomatoes.json` | 烂番茄页面数据 | 烂番茄评分、评论共识 |
| `metacritic.json` | Metacritic 页面数据 | Metascore、用户评分 |

### 2.8 当前状态

**数据统计**（截至 2026-05-12）：

| 项目 | 数量 |
|------|------|
| 已爬取电影 | 250 部 |
| 人物总数 | 11,546 人 |
| 有 TMDB ID 人物 | 11,546 人（100%） |
| 有头像人物 | 7,604 人（66%） |

**数据库状态**：

| 表 | 记录数 |
|------|--------|
| works | 250 |
| person | 11,546 |
| work_person | 12,999 |
| category | 28 |
| work_category | 698 |

**已知问题**：
- 约 3,942 人无头像（TMDB 上无 profile_path）
- 部分烂番茄、Metacritic 数据因反爬机制未获取

### 2.9 开发规范

详见 [RULES.md](./RULES.md)，包含：
- 数据源优先级规则
- 编码规范
- 错误处理
- 反爬虫应对措施
- 检查清单

### 2.10 数据字段设计

详见 [DATA.md](./DATA.md)，包含：
- 数据库表结构
- 字段映射表
- 各数据源字段说明
- 数据来源对照表
