# Reference Archive

从参考项目中提取的有价值内容，用于 movie-ingest 项目集成。

## 目录结构

```
reference-archive/
├── complete-files/     # 完整文件（保留原始实现）
├── code-snippets/      # 代码片段（提取关键功能）
├── notes/              # 说明文档（集成指南）
└── README.md           # 本文件
```

## 内容概览

### complete-files（完整文件）

| 文件 | 来源 | 功能 |
|------|------|------|
| douban-top250-main.py | douban-top250 | 豆瓣 TOP250 爬虫主程序 |
| douban-top250-config.py | douban-top250 | 豆瓣 TOP250 配置文件 |
| python-crawler-1905.py | python-crawler-main | 1905 电影网爬虫 |
| python-crawler-imdb.py | python-crawler-main | IMDb 爬虫 |
| sklearn-sentiment.py | nlp-sentiment-analysis-master | 情感分析完整实现 |
| stopwords.txt | nlp-sentiment-analysis-master | 中文停用词表 |

### code-snippets（代码片段）

| 文件 | 功能 | 集成位置 |
|------|------|----------|
| image-crawling-stable.py | 稳定的图片爬取方案 | douban.py |
| comment-crawling-stable.py | 稳定的评论爬取方案 | douban.py |
| httpx-download.py | httpx 图片下载 | downloader.py |
| csv-export.py | CSV 导出功能 | database.py |
| 1905-spider-snippet.py | 1905 电影网爬虫 | sources/m1905.py |
| sentiment-analysis-snippet.py | 评论情感分析 | analyzer.py |
| topic-cluster.py | 评论主题聚类 | analyzer.py |

### notes（说明文档）

| 文件 | 内容 |
|------|------|
| IMAGE-CRAWLING-STABILITY.md | 图片爬取稳定性分析 |
| COMMENT-CRAWLING-STABILITY.md | 评论爬取稳定性分析 |
| 1905-INTEGRATION.md | 1905 电影网集成说明 |
| CSV-EXPORT-GUIDE.md | CSV 导出指南 |
| HTTPX-DOWNLOAD-GUIDE.md | httpx 下载指南 |
| SENTIMENT-ANALYSIS-GUIDE.md | 情感分析指南 |
| TOPIC-CLUSTER-GUIDE.md | 主题聚类指南 |
| DATA-SOURCES-RESEARCH.md | 数据源调研报告 |
| INTEGRATION-GUIDE.md | 集成指南（总览） |

## 参考项目来源

### 1. douban-top250
- **来源**：GitHub 搜索 "douban top250"
- **价值**：稳定的豆瓣爬取方案、图片爬取、评论爬取
- **归档内容**：
  - 完整主程序
  - 配置文件
  - 图片爬取代码片段
  - 评论爬取代码片段
  - httpx 下载代码片段
  - CSV 导出代码片段

### 2. python-crawler-main
- **来源**：GitHub 搜索 "python crawler movie"
- **价值**：1905 电影网爬虫、IMDb 爬虫
- **归档内容**：
  - 1905 电影网完整爬虫
  - IMDb 完整爬虫
  - 1905 代码片段

### 3. nlp-sentiment-analysis-master
- **来源**：GitHub 搜索 "sentiment analysis chinese"
- **价值**：评论情感分析、关键词提取、主题聚类
- **归档内容**：
  - 情感分析完整实现
  - 停用词表
  - 情感分析代码片段
  - 主题聚类代码片段

## 集成优先级

### 高优先级
1. **图片爬取稳定性**：解决 TMDB 图片下载不稳定问题

### 中优先级
2. **httpx 下载**：替换 aiohttp，提升下载稳定性
3. **CSV 导出**：方便数据查看和备份

### 低优先级
4. **1905 电影网**：补充国产电影数据
5. **情感分析**：评论分析功能
6. **主题聚类**：评论主题分组

## 使用方式

### 1. 查看说明文档
```bash
# 图片爬取稳定性
cat notes/IMAGE-CRAWLING-STABILITY.md

# 集成指南
cat notes/INTEGRATION-GUIDE.md
```

### 2. 查看代码片段
```bash
# 图片爬取稳定方案
cat code-snippets/image-crawling-stable.py

# 评论爬取稳定方案
cat code-snippets/comment-crawling-stable.py
```

### 3. 查看完整文件
```bash
# douban-top250 主程序
cat complete-files/douban-top250-main.py

# 1905 电影网爬虫
cat complete-files/python-crawler-1905.py
```

## 集成步骤

详见 `notes/INTEGRATION-GUIDE.md`

## 注意事项

1. **不要直接复制粘贴**：理解代码逻辑后，适配到 movie-ingest
2. **保持向后兼容**：新功能可选启用，不影响现有功能
3. **测试验证**：每集成一个功能，测试验证
4. **逐步集成**：按优先级逐步集成，不要一次性集成所有功能

## 更新记录

- 2025-05-05：创建 reference-archive 目录
- 2025-05-05：归档 douban-top250 有价值内容
- 2025-05-05：归档 python-crawler-main 有价值内容
- 2025-05-05：归档 nlp-sentiment-analysis-master 有价值内容
- 2025-05-05：完成所有说明文档
- 2025-05-05：归档主题聚类代码片段
- 2025-05-05：清理所有参考项目，只保留 movie-ingest 和 reference-archive
- 2025-05-05：归档数据源调研报告，清理临时文件