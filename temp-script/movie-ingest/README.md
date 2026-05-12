# 电影数据多源爬取工具 (movie-ingest)

> 多源爬取电影数据，写入本地 SQLite 数据库，为 Treasure 收藏馆提供结构化数据。

---

## 第一部分：项目架构概述

### 1.1 movie-ingest 定位

movie-ingest 是一个**独立完整的电影数据处理模块**，职责包括：

1. **爬取数据**：从豆瓣、TMDB、OMDb 等数据源爬取电影信息
2. **合并数据**：多源数据合并，生成统一格式
3. **录入数据库**：将合并后的数据写入 SQLite 数据库

**核心原则**：movie-ingest 目录自包含，所有电影相关数据、脚本都在此目录下。

### 1.2 目录结构

```
movie-ingest/
├── config.py              # 配置文件（路径、API Keys、代理等）
├── main.py                # 主入口（命令行参数解析）
│
├── crawl_basic.py         # 模块1：爬取基本信息
├── crawl_reviews.py       # 模块2：爬取影评
├── crawl_images.py        # 模块3：爬取图片
│
├── merger.py              # 数据合并模块
├── database.py            # 数据库操作类
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
├── db_tools/              # 数据录入工具（Node.js）
│   ├── paths.mjs          # 路径配置
│   ├── import-movie.mjs   # 单部作品录入
│   ├── run-movie-intake-from-tasks.mjs  # 批量摄入
│   ├── run-movie-batch-workflow.mjs     # 批量流程
│   ├── check-movie-ingest-quality.mjs   # 质量检查
│   ├── validate-movie-record.mjs        # 记录验证
│   ├── movie-ingest-contract.mjs        # 数据契约
│   └── ...                               # 其他工具脚本
│
├── data/                  # 数据存储目录
│   ├── raw/               # 第一层：原始数据
│   │   └── {work_id}/
│   │       ├── douban.json
│   │       ├── tmdb.json
│   │       └── ...
│   ├── staging/           # 第二层：合并数据
│   │   └── {work_id}.json
│   └── assets/            # 图片资源
│       ├── works/         # 作品图片
│       └── people/        # 人物头像
│
├── README.md              # 本文档
├── RULES.md               # 开发规范
└── DATA.md                # 数据字段设计
```

### 1.3 数据流

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              movie-ingest 数据流                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   第一层：爬取原始数据                                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  crawl_basic.py                                                      │   │
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
│   │  db_tools/import-movie.mjs                                           │   │
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
- 演职员：豆瓣（中文名）+ TMDB（英文名、角色名、头像）
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
# 测试模式（单部电影）
python main.py --test --basic

# 爬取指定电影
python crawl_basic.py --douban-id 1292052 --title "肖申克的救赎"

# 批量爬取 Top250
python main.py --top250 --basic
```

### 2.4 录入数据库

```bash
# 单部作品录入
node db_tools/import-movie.mjs --work-id 0101000001

# 批量录入所有 staging 数据
node db_tools/import-movie.mjs --all
```

### 2.5 完整流程示例

```bash
# 1. 爬取数据
python crawl_basic.py --douban-id 1292052 --title "肖申克的救赎"

# 2. 数据已保存到 data/staging/0101000001.json

# 3. 录入数据库
node db_tools/import-movie.mjs --work-id 0101000001

# 4. 数据已写入 .local/treasure.db
```

---

## 第三部分：核心模块详解

### 3.1 爬取模块

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
