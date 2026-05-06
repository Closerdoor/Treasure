# 模块拆分说明

## 概述

已将 movie-ingest 脚本拆分为 3 个独立模块，保持功能逻辑不变。

## 模块说明

### 1. crawl_basic.py - 爬取基本信息

**功能**：
- 豆瓣详情（标题、年份、评分、简介等）
- TMDB 详情 + 演职员
- OMDb 详情 + 评分
- 百度百科
- Wikipedia

**数据源**：
- douban（detail）
- tmdb（detail + credits）
- omdb
- baike
- wikipedia

**命令**：
```bash
# 测试模式
python crawl_basic.py --test

# 爬取 TOP250
python crawl_basic.py --top250

# 指定批次大小
python crawl_basic.py --top250 --batch-size 20
```

**输出**：
- 基本信息 JSON
- 演职员 JSON
- 评分 JSON

---

### 2. crawl_reviews.py - 爬取完整影评

**功能**：
- 豆瓣短评 + 影评
- TMDB 评论
- 烂番茄评论
- Metacritic 评论

**数据源**：
- douban（comments + reviews）
- tmdb（reviews）
- rotten_tomatoes
- metacritic

**命令**：
```bash
# 测试模式
python crawl_reviews.py --test

# 爬取 TOP250
python crawl_reviews.py --top250

# 只爬缺失评论的电影
python crawl_reviews.py --missing
```

**依赖**：
- 需要基本信息中的 `title`、`original_title`、`year`

---

### 3. crawl_images.py - 爬取图片资源

**功能**：
- TMDB 图片（海报 + 剧照）
- OMDb 海报
- 豆瓣主海报
- 下载图片到本地

**数据源**：
- tmdb（images）
- omdb（poster）
- douban（main_poster_url）

**命令**：
```bash
# 测试模式
python crawl_images.py --test

# 爬取 TOP250
python crawl_images.py --top250

# 只爬缺失图片的电影
python crawl_images.py --missing
```

**依赖**：
- 需要基本信息中的 `imdb_id`、`douban_id`

---

## 主入口 - main.py

**完整爬取**（依次运行所有模块）：
```bash
# 测试模式
python main.py --test

# 爬取 TOP250
python main.py --top250
```

**单独运行模块**：
```bash
# 只运行基本信息模块
python main.py --top250 --basic

# 只运行影评模块
python main.py --top250 --reviews

# 只运行图片模块
python main.py --top250 --images

# 补爬缺失的评论
python main.py --reviews --missing

# 补爬缺失的图片
python main.py --images --missing
```

---

## 数据库扩展

新增字段：
- `basic_crawled`：基本信息是否已爬取（0/1）
- `reviews_crawled`：评论是否已爬取（0/1）
- `images_crawled`：图片是否已爬取（0/1）

---

## 进度管理扩展

新增方法：
- `mark_basic_completed(douban_id)`：标记基本信息已完成
- `mark_reviews_completed(douban_id)`：标记评论已完成
- `mark_images_completed(douban_id)`：标记图片已完成
- `is_basic_completed(douban_id)`：检查基本信息是否已完成
- `is_reviews_completed(douban_id)`：检查评论是否已完成
- `is_images_completed(douban_id)`：检查图片是否已完成

---

## 使用场景

### 场景 1：首次完整爬取
```bash
python main.py --top250
```
依次运行：基本信息 → 影评 → 图片

### 场景 2：只爬基本信息（快速）
```bash
python main.py --top250 --basic
```
只爬基本信息，跳过评论和图片

### 场景 3：补爬缺失的评论
```bash
python main.py --reviews --missing
```
只爬缺失评论的电影

### 场景 4：补爬缺失的图片
```bash
python main.py --images --missing
```
只爬缺失图片的电影

### 场景 5：分步爬取
```bash
# 第一步：爬基本信息
python crawl_basic.py --top250

# 第二步：爬评论
python crawl_reviews.py --top250

# 第三步：爬图片
python crawl_images.py --top250
```

---

## 优势

1. **灵活性**：可以单独运行任意模块
2. **增量爬取**：支持补爬缺失数据
3. **断点续爬**：每个模块独立跟踪进度
4. **快速验证**：可以先爬基本信息验证数据质量
5. **降低风险**：模块独立失败不影响其他模块

---

## 文件结构

```
movie-ingest/
├── main.py              # 主入口（调用 3 个模块）
├── main_old.py          # 旧版本（备份）
├── crawl_basic.py       # 模块 1：爬取基本信息
├── crawl_reviews.py     # 模块 2：爬取完整影评
├── crawl_images.py      # 模块 3：爬取图片资源
├── database.py          # 数据库管理（已扩展）
├── progress.py          # 进度管理（已扩展）
├── merger.py            # 数据合并
├── downloader.py        # 图片下载
├── sources/             # 数据源爬虫
│   ├── douban.py
│   ├── tmdb.py
│   ├── omdb.py
│   ├── baike.py
│   ├── wikipedia.py
│   ├── rotten_tomatoes.py
│   └── metacritic.py
└── utils/               # 工具函数
```

---

## 注意事项

1. **依赖关系**：模块 2/3 依赖模块 1 的数据
2. **数据库字段**：需要先添加新字段（已自动完成）
3. **进度文件**：每个模块共享同一个 progress.json
4. **浏览器实例**：每个模块独立启动浏览器

---

## 已修复的问题

- ✅ TMDB API 代理问题（get_credits、get_images、get_videos 已添加代理）
- ✅ 数据库字段扩展（basic_crawled、reviews_crawled、images_crawled）
- ✅ 进度管理扩展（模块级别跟踪）
- ✅ 模块拆分（保持功能逻辑不变）
