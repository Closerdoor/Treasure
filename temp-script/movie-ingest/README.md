# 电影数据多源爬取工具 (movie-ingest)

> 多源爬取电影数据，写入本地 SQLite 数据库，为 Treasure 收藏馆提供结构化数据。

---

## 当前有效职责与入口

本目录现在只承担电影采集工坊职责，边界到 `.local/treasure.db` 为止：

```text
影片输入 / 豆瓣 ID 验证
  -> 多数据源采集
  -> data/raw/{work_id}/
  -> data/staging/{work_id}.json
  -> data/assets/
  -> .local/treasure.db
```

不属于本目录的职责：

- 不导出 `generated/`。
- 不维护 `site/public/assets/` 发布资源。
- 不运行 Astro 构建。
- 不做 GitHub Pages 发布校验。

这些后续流程由仓库根目录的 `tools/db/export-generated.mjs`、`generated/` 和 `site/` 承担。

当前实际脚本分工：

| 路径 | 当前职责 | 状态 |
|---|---|---|
| `main.py` | 命令行入口，调度 `MovieCrawler` | 正式入口 |
| `crawl.py` | 统一采集编排：豆瓣、TMDB、OMDb、百科、Wikipedia、烂番茄、Metacritic、图片下载、staging 输出 | 正式入口 |
| `sources/*.py` | 单一数据源客户端 / 爬虫 | 正式组件 |
| `merger.py` | 多源 raw 合并为 staging JSON | 正式组件 |
| `downloader.py` | 采集阶段图片下载到 `data/assets/` | 正式组件 |
| `database.py` | staging 导入 `.local/treasure.db` | 正式 DB 入口 |
| `progress.py` | 采集进度记录 | 正式组件 |
| `name_matcher.py` | 豆瓣中文人物与 TMDB 人物匹配 | 正式组件 |
| `config.py` | 本目录路径、API、代理、浏览器、数量限制配置 | 正式配置 |
| `db_tools/import-movie.mjs` | 旧 JS 入库入口，会触碰站点资源目录 | legacy，默认禁止直接运行 |
| `db_tools/paths.mjs` | 旧 JS 入口路径常量 | legacy 配套 |

当前不存在 `crawl_basic.py`、`crawl_reviews.py`、`crawl_images.py`、`full_match.py`、`fix_person_avatars.py`、`download_missing_avatars.py`、`update_avatar_paths.py` 等旧文档中曾提到的脚本。后续说明应以本节为准。

---

## 第一部分：项目架构概述

### 1.1 movie-ingest 定位

movie-ingest 是一个**独立完整的电影数据处理模块**，职责包括：

1. **爬取数据**：从豆瓣、TMDB、OMDb 等数据源爬取电影信息
2. **合并数据**：多源数据合并，生成统一格式
3. **录入数据库**：将合并后的数据写入 SQLite 数据库

**核心原则**：movie-ingest 目录自包含到“采集与入库”为止。进入 `generated/`、`site/public/assets/` 或 Astro 构建之后的工作不在本目录内处理。

### 1.2 目录结构

```
movie-ingest/
├── config.py              # 配置文件（路径、API Keys、代理等）
├── main.py                # 主入口（命令行参数解析）
├── crawl.py               # 统一采集编排入口
├── merger.py              # 数据合并模块
├── database.py            # 数据库操作类（正式 DB 入库层）
├── downloader.py          # 图片下载模块
├── progress.py            # 进度管理模块
├── name_matcher.py        # 人物名字匹配模块
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
├── db_tools/              # legacy JS 入库入口，默认禁止直接运行
│   ├── paths.mjs          # legacy 路径常量
│   └── import-movie.mjs   # legacy 脚本，会触碰 site/public/assets
│
├── data/                  # 数据存储目录
│   ├── raw/               # 第一层：原始数据
│   │   └── {work_id}/
│   │       ├── douban.json
│   │       ├── tmdb.json
│   │       └── ...
│   ├── staging/           # 第二层：合并数据
│   │   └── {work_id}.json
│   └── assets/            # 图片下载缓存（最终同步到 .local/assets/）
│       ├── works/         # 作品图片（海报、剧照）
│       └── people/        # 人物头像
│
├── README.md              # 本文档
├── RULES.md               # 开发规范
└── DATA.md                # 数据字段设计
```

**注意**：`data/assets/` 是采集阶段下载缓存目录。它不等于发布资源目录；发布资源仍由仓库根目录的导出脚本从主数据源生成。

### 1.3 数据流

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              movie-ingest 数据流                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   第一层：爬取原始数据                                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  main.py / crawl.py                                                  │   │
│   │  豆瓣 ──────┐                                                        │   │
│   │  TMDB ──────┼──────▶ data/raw/{work_id}/                             │   │
│   │  OMDb ──────┤              ├── douban.json                           │   │
│   │  百度百科 ──┤              ├── tmdb.json                             │   │
│   │  Wikipedia ─┘              └── ...                                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│   第二层：合并数据                                                            │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  merger.py                                                           │   │
│   │  读取 raw/*.json                                                     │   │
│   │  按优先级合并（豆瓣 > TMDB > 其他）                                    │   │
│   │  匹配演职员中文名和英文名                                             │   │
│   │                        ──────▶ data/staging/{work_id}.json           │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│   第三层：录入数据库                                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  database.py                                                         │   │
│   │  读取 staging/{work_id}.json                                         │   │
│   │  写入 .local/treasure.db                                             │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**数据优先级规则**：
- 中文名：豆瓣 > 百度百科
- 英文名：TMDB > OMDb
- 年份：豆瓣 > TMDB
- 地区/语言：豆瓣（最准确）
- 演职员：豆瓣（中文名、英文名、角色名、头像）+ TMDB（英文名、角色名、头像）
- 评分：各平台独立记录

---

## 第二部分：使用方法

### 2.1 安装依赖

```bash
# Python 依赖
pip install playwright beautifulsoup4 aiohttp pillow
playwright install chromium

# Node.js 依赖（用于 db_tools）
npm install better-sqlite3
```

### 2.2 配置

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

### 2.3 爬取数据

```bash
# 通过影片名搜索豆瓣 ID 并采集（推荐）
python main.py --movie-name "社交网络" --year 2010

# 已知豆瓣 ID 时采集
python main.py --douban-id 3205624 --title "社交网络" --work-id 0101000252
```

### 2.4 录入数据库

当前正式 DB 入库层是 `database.py`。它提供 `TreasureDB.import_movie(movie_data)`，用于把 staging JSON 写入 `.local/treasure.db`。

`db_tools/import-movie.mjs` 是 legacy JS 入口，默认禁止直接运行；后续如需要命令行导入，应在 Python 主链路上补一个只调用 `database.py` 的薄 CLI，而不是恢复 JS 入口。

### 2.5 完整流程示例

```bash
# 1. 爬取数据
python main.py --movie-name "社交网络" --year 2010

# 2. 数据保存到 data/raw/{work_id}/ 与 data/staging/{work_id}.json

# 3. 使用 database.py 的 TreasureDB.import_movie(movie_data) 写入 .local/treasure.db
```

---

## 第三部分：核心模块详解

### 3.1 爬取模块

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `main.py` | 命令行入口 | 影片名或豆瓣 ID | 调用 `MovieCrawler` |
| `crawl.py` | 统一采集编排 | 豆瓣 ID / 影片名 | `data/raw/{work_id}/`、`data/staging/{work_id}.json`、`data/assets/` |
| `sources/*.py` | 单数据源采集 | 来源查询参数 | raw source data |

**crawl.py 详细功能**：
- 爬取豆瓣详情页、演职员页、视频页、图片页、短评页、影评页
- 调用 TMDB API 获取演职员、图片、视频
- 调用 OMDb API 获取评分、分级
- 爬取百度百科补充基本信息
- 爬取 Wikipedia 获取获奖、名言名句
- 爬取烂番茄、Metacritic 获取评分

**豆瓣页面采集契约**：

| 页面 | URL 模板 | 采集内容 |
|------|----------|----------|
| 基本信息 | `https://movie.douban.com/subject/{douban_id}/` | 标题、原名、年份、评分、类型、国家/地区、语言、片长、上映日期、别名、IMDb ID、简介、主海报 URL、标签、推荐 |
| 演职员 | `https://movie.douban.com/subject/{douban_id}/celebrities` | 导演、编剧、全部演员、角色、中英文名、豆瓣人物 ID、头像 URL |
| 视频 | `https://movie.douban.com/subject/{douban_id}/trailer` | 视频名称、视频链接、封面图片、时长 |
| 图片总页 | `https://movie.douban.com/subject/{douban_id}/all_photos` | 图片入口页访问校验 |
| 剧照 | `https://movie.douban.com/subject/{douban_id}/photos?type=S` | 全量剧照 URL、原图候选 URL、总数 |
| 海报 | `https://movie.douban.com/subject/{douban_id}/photos?type=R` | 全量海报 URL、原图候选 URL、总数 |
| 壁纸 | `https://movie.douban.com/subject/{douban_id}/photos?type=W` | 全量壁纸 URL、原图候选 URL、总数 |
| 好评短评 | `https://movie.douban.com/subject/{douban_id}/comments?percent_type=h&limit=20&status=P&sort=new_score` | 好评筛选下按热门/有用排序的前 20 条短评 |
| 影评 | `https://movie.douban.com/subject/{douban_id}/reviews?start={start}&sort=hot` | 先按热度排序获取前 20 条影评条目，再进入影评详情页读取完整正文 |

### 3.2 数据处理模块

| 模块 | 职责 | 说明 |
|------|------|------|
| `merger.py` | 数据合并 | 合并各来源数据，解决冲突，生成统一格式 |
| `database.py` | 数据库操作 | 写入 works、person、work_person 等表 |
| `downloader.py` | 图片下载 | 下载海报、剧照、人物头像到 `data/assets/` |
| `progress.py` | 进度管理 | 记录爬取进度，支持断点续传 |

### 3.3 人物匹配模块

| 模块 | 职责 | 说明 |
|------|------|------|
| `name_matcher.py` | 人物名字匹配 | 匹配豆瓣中文名和 TMDB 英文名 |

### 3.4 数据源爬虫

| 数据源 | 爬取方式 | 数据类型 | 反爬机制 |
|--------|---------|---------|---------|
| 豆瓣 | Playwright | 基本信息、评分、演职员、视频、剧照、海报、壁纸、短评、影评 | 需要登录、Referer 检测 |
| TMDB | REST API | 演职员、图片、视频、原声 | 无（需 API Key） |
| OMDb | REST API | 评分、分级、获奖 | 无（需 API Key） |
| 百度百科 | Playwright | 基本信息补充 | 验证码 |
| Wikipedia | Playwright | 获奖、名言名句 | 无 |
| 烂番茄 | Playwright | 评分、评论 | 有 |
| Metacritic | Playwright | 评分、评论 | 有 |

### 3.5 使用方法

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

#### 2.5.3 单部电影采集

```bash
python main.py --movie-name "社交网络" --year 2010
```

也可以在已确认豆瓣 ID 后直接采集：

```bash
python main.py --douban-id 3205624 --title "社交网络" --work-id 0101000252
```

#### 2.5.4 批量模式

当前 `main.py` 不提供 Top250 批量参数。批量采集应后续单独设计任务清单入口，并且必须满足：

- 每条任务记录豆瓣 ID 获取与验证过程。
- 运行前量化任务总数、预计采集来源和任何数量限制。
- 不在批量脚本中导出 `generated/`、写 `site/public/assets/` 或运行 Astro 构建。

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

### 2.7 当前状态

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
