# 电影数据多源爬取工具

从多个来源爬取电影数据，用于个人收藏馆网站数据录入。

## 数据来源

| 来源 | 数据类型 | 爬取方式 |
|------|----------|----------|
| 豆瓣 | 基本信息、评分、短评、长评、图片、标签、相关推荐 | Playwright |
| TMDB | 基本信息、演职人员、图片、视频、原声 | REST API |
| OMDb | 评分、分级、获奖 | REST API |
| 百度百科 | 基本信息补充 | Playwright |
| Wikipedia | 基本信息、获奖、名言名句 | Playwright |
| 烂番茄 | 评分、评论 | Playwright |
| Metacritic | 评分、评论 | Playwright |

## 安装依赖

```bash
pip install playwright beautifulsoup4 aiohttp pillow
playwright install chromium
```

## 使用方法

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

### 3. 登录豆瓣

首次运行会打开浏览器，需要手动登录豆瓣：
1. 在浏览器中登录豆瓣账号
2. 回到终端按回车继续
3. Cookie 会自动保存，下次运行无需重新登录

## 输出结构

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
    ├── images/                    # 图片
    │   ├── poster-main.jpg        # 主海报
    │   ├── poster-001.jpg         # 补充海报
    │   ├── still-001.jpg          # 剧照
    │   └── people/                # 人物头像
    │       └── p000001-avatar.jpg
    └── review.md                  # 审阅文件（有冲突时生成）
```

## 配置说明

编辑 `config.py` 修改配置：

```python
# API Keys
TMDB_API_KEY = "your_tmdb_api_key"
OMDB_API_KEY = "your_omdb_api_key"

# 爬取配置
COMMENTS_PER_SOURCE = 20      # 每个来源的评论数
REVIEWS_PER_SOURCE = 20       # 每个来源的影评数

# 延迟配置（秒）
MIN_DELAY = 1.0
MAX_DELAY = 3.0
PAGE_DELAY = 2.0

# 浏览器配置
HEADLESS = False              # 是否无头模式
USE_CHROME = True             # 是否使用系统 Chrome
```

## 断点续传

进度保存在 `progress.json`，支持断点续传：
- 重新运行脚本会自动跳过已完成的来源
- 某个来源失败不影响其他来源

## 数据冲突

当检测到字段冲突时，会生成 `review.md` 审阅文件：
- 打开审阅文件查看冲突详情
- 选择正确的值并标记确认
- 重新运行脚本会等待人工确认

## 字段映射

详见 `FIELD-MAPPING.md`，记录了爬取数据与数据库字段的对应关系。

## 整体方案

详见 `PROJECT-PLAN.md`，记录了完整的设计方案和流程。

## 注意事项

1. **豆瓣登录**：需要登录才能查看完整信息
2. **反爬限制**：烂番茄和 Metacritic 有反爬机制，速度较慢
3. **图片下载**：会自动去重（URL、文件名、内容哈希）
4. **错误重试**：每个来源失败会重试 3 次，然后跳过
5. **数据合并**：豆瓣优先级最高，TMDB 补充演职人员和图片

## 依赖说明

- `playwright`：浏览器自动化，用于爬取动态页面
- `beautifulsoup4`：HTML 解析
- `aiohttp`：异步 HTTP 客户端，用于 API 调用和图片下载
- `pillow`：图片处理，用于判断图片类型（海报/剧照）
