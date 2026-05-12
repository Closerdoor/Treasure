# 书籍数据多源爬取工具

书籍数据录入工具，用于 Treasure 个人收藏馆的书籍数据采集。

---

## 当前状态

**更新时间**: 2026-05-12

| 阶段 | 状态 | 完成率 |
|------|:----:|:------:|
| 基本信息爬取 | ✅ | 100% |
| 数据合并 | ✅ | 100% |
| 数据库导入 | ✅ | 100% |
| 书评爬取 | ⏸️ | 0% |
| 封面下载 | ⏸️ | 0% |

**已爬取书籍**: 3 本（百年孤独、围城、凡人修仙传）

---

## 在工作流中的位置

```
┌─────────────────────────────────────────────────────────────────┐
│                      Treasure 数据工作流                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  temp-script/book-ingest/        ← 当前位置                     │
│  ├── 多源数据爬取（豆瓣/OpenLibrary/百度百科/维基百科/当当网）    │
│  ├── 数据合并与去重                                              │
│  └── 导入 SQLite 数据库                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  .local/treasure.db                                             │
│  └── books / book_person / book_category 表                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  tools/db/export-generated.mjs                                  │
│  └── 导出为 generated/ 目录下的 JSON 文件                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  site/ (Astro 站点)                                             │
│  └── 构建静态页面 → GitHub Pages                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
book-ingest/
├── README.md              # 本文档
├── RULES.md               # 开发规范
├── DATA.md                # 数据字段设计
├── docs/
│   ├── research-notes.md  # 数据源调研笔记
│   └── archive/           # 归档文档
├── main.py                # 主入口
├── config.py              # 配置文件
├── crawl_basic.py         # 基本信息爬取
├── crawl_reviews.py       # 书评爬取
├── merger.py              # 数据合并
├── database.py            # 数据库操作
├── progress.py            # 进度管理
├── downloader.py          # 封面下载
├── sources/               # 数据源爬虫
│   ├── douban_book.py     # 豆瓣读书
│   ├── openlibrary.py     # OpenLibrary API
│   ├── baike.py           # 百度百科
│   ├── wikipedia.py       # 维基百科
│   ├── dangdang.py        # 当当网
│   ├── qidian.py          # 起点中文网
│   ├── goodreads.py       # Goodreads（待实现）
│   └── bookchina.py       # 中国图书网（待实现）
├── utils/                 # 工具函数
│   ├── logger.py
│   ├── id_generator.py
│   └── hash.py
└── data/                  # 爬取数据
    ├── progress.json      # 进度记录
    ├── cookies/           # Cookie 存储
    └── 0200000001/        # 书籍数据目录
        ├── data.json      # 合并后数据
        └── raw/           # 原始数据
```

---

## 脚本功能说明

### 主入口 `main.py`

```bash
# 测试模式（爬取 config.TEST_BOOKS 中的书籍）
python main.py --test

# 批量模式
python main.py --batch

# 只运行基本信息模块
python main.py --test --basic

# 只运行书评模块
python main.py --test --reviews
```

### 核心模块

| 模块 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `crawl_basic.py` | 爬取基本信息 | 豆瓣 ID | 各来源原始数据 |
| `merger.py` | 合并多源数据 | 原始数据 | `data.json` |
| `database.py` | 导入数据库 | `data.json` | SQLite 记录 |
| `progress.py` | 进度管理 | - | `progress.json` |

### 数据源爬虫

| 爬虫 | 数据源 | 方式 | 主要数据 |
|------|--------|------|----------|
| `douban_book.py` | 豆瓣读书 | Playwright | 基本信息、评分、标签 |
| `openlibrary.py` | OpenLibrary | REST API | 英文标题、作者 |
| `baike.py` | 百度百科 | Playwright | 字数、简介 |
| `wikipedia.py` | 维基百科 | Playwright | 原名、国家 |
| `dangdang.py` | 当当网 | Playwright | 价格、ISBN |
| `qidian.py` | 起点中文网 | Playwright | 网络小说数据 |

---

## 数据流

```
豆瓣 ID → crawl_basic.py → raw/*.json
                              ↓
                         merger.py → data.json
                              ↓
                         database.py → SQLite
```

---

## 配置

编辑 `config.py` 修改配置：

```python
# 测试书籍
TEST_BOOKS = [
    {"douban_id": "6082808", "title": "百年孤独"},
    {"douban_id": "1008145", "title": "围城"},
]

# 浏览器配置
HEADLESS = True
PROXY_ENABLED = True
PROXY_URL = "http://127.0.0.1:7890"

# 延迟配置（秒）
MIN_DELAY = 2.0
MAX_DELAY = 5.0
```

---

## 断点续传

进度保存在 `data/progress.json`：

- 重新运行会自动跳过已完成的来源
- 某个来源失败不影响其他来源
- 支持增量爬取

---

## 爬取流程

```
豆瓣读书详情页 → OpenLibrary API → 百度百科 → Wikipedia → 数据合并 → 封面下载
     │                │               │            │            │            │
     ▼                ▼               ▼            ▼            ▼            ▼
 基本信息          英文标题        作者简介      获奖/名句    data.json    cover-main.jpg
 评分/标签         作者英文名      字数          原名/国家    冲突检测     补充封面
 书评 20 条        封面            获奖信息      词条 URL     作者去重     作者头像
 系列/推荐         ISBN 匹配
```

---

## 已知问题

| 问题 | 说明 | 状态 |
|------|------|:----:|
| OpenLibrary 限制 | 部分书籍无英文数据（如百年孤独） | ⚠️ 已知 |
| 作者名称格式不统一 | 豆瓣返回带国籍前缀，需清洗 | ⚠️ 已知 |
| 封面未下载 | `images` 字段仅存储路径 | ⏸️ 待实现 |
| 书评未爬取 | `reviews` 字段为空数组 | ⏸️ 待实现 |

---

## 相关文档

- [RULES.md](./RULES.md) - 开发规范、数据源优先级、反爬策略
- [DATA.md](./DATA.md) - 数据库字段设计、字段映射、JSON 格式规范
- [docs/research-notes.md](./docs/research-notes.md) - 数据源调研笔记
