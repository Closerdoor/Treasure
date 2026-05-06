# 电影数据源调研报告

## 一、数据源概览

| 站点 | 官方 API | 免费 | 第三方 API | Python 库 | 爬取风险 |
|------|----------|------|-----------|-----------|----------|
| **豆瓣** | ❌ 无 | - | - | 自写爬虫 | 中 |
| **TMDB** | ✅ 有 | ✅ 免费 | - | tmdbsimple | 无风险 |
| **IMDb** | ✅ 有 | ❌ 付费 | ✅ OMDb | Cinemagoer | 高 |
| **烂番茄** | ❌ 无 | - | ✅ 社区 API | rottentomatoes-python | 中 |
| **Metacritic** | ❌ 无 | - | ⚠️ 不稳定 | pycritic | 中 |

---

## 二、TMDB（推荐主数据源）

### 基本信息
- **官网**: https://www.themoviedb.org/
- **API 文档**: https://developer.themoviedb.org/docs
- **申请地址**: https://www.themoviedb.org/settings/api

### 特点
- 完全免费（非商业用途）
- 数据丰富：电影、TV、人物
- 支持多语言（包括中文）
- 提供 `imdb_id` 字段，可关联 IMDb
- 每日 ID 导出功能

### API 限制
- 请求频率: 约 40 请求/秒
- 缓存数据不得超过 6 个月
- 需标注 TMDB 来源

### Python 库
```bash
pip install tmdbsimple
```

```python
import tmdbsimple as tmdb
tmdb.API_KEY = 'YOUR_API_KEY'

# 搜索电影
search = tmdb.Search()
response = search.movie(query='The Matrix')

# 获取详情
movie = tmdb.Movies(603)
response = movie.info()
```

### 主要端点
| 端点 | 说明 |
|------|------|
| `/search/movie` | 搜索电影 |
| `/movie/{id}` | 电影详情 |
| `/movie/{id}/credits` | 演职人员 |
| `/movie/{id}/images` | 图片 |
| `/movie/{id}/videos` | 预告片 |
| `/configuration` | 图片 URL 配置 |

### 图片 URL 构建
```
基础 URL: https://image.tmdb.org/t/p/
完整 URL: https://image.tmdb.org/t/p/w500/xxx.jpg

海报尺寸: w92, w154, w185, w342, w500, w780, original
背景尺寸: w300, w780, w1280, original
```

---

## 三、OMDb API（评分聚合）

### 基本信息
- **官网**: https://www.omdbapi.com/
- **API 文档**: https://www.omdbapi.com/#parameters

### 特点
- 一次请求获取多个评分源
- 包含 IMDb、烂番茄、Metacritic 评分
- 简单易用

### API 限制
- 免费额度: 1,000 次/天
- 付费可提高额度

### 示例响应
```json
{
  "Title": "The Matrix",
  "Year": "1999",
  "Rated": "R",
  "Runtime": "136 min",
  "Genre": "Action, Sci-Fi",
  "Director": "Lana Wachowski, Lilly Wachowski",
  "Actors": "Keanu Reeves, Laurence Fishburne",
  "imdbRating": "8.7",
  "imdbVotes": "1,900,000",
  "imdbID": "tt0133093",
  "Ratings": [
    {"Source": "Internet Movie Database", "Value": "8.7/10"},
    {"Source": "Rotten Tomatoes", "Value": "88%"},
    {"Source": "Metacritic", "Value": "73/100"}
  ]
}
```

### Python 使用
```python
import requests

url = f"http://www.omdbapi.com/?i=tt0133093&apikey=YOUR_KEY"
response = requests.get(url)
data = response.json()
```

---

## 四、烂番茄（Rotten Tomatoes）

### 基本信息
- **官网**: https://www.rottentomatoes.com/
- **官方 API**: 已关闭
- **申请授权**: https://fandango.az1.qualtrics.com/jfe/form/SV_0ieuKEYpn4S7nnM

### 第三方方案

#### 1. rottentomatoes-python 库
```bash
pip install rottentomatoes-python
```

```python
import rottentomatoes as rt

movie = rt.Movie('top gun')
print(movie.tomatometer)     # 影评人评分
print(movie.audience_score)  # 观众评分
print(movie.genres)
print(movie.actors)
```

#### 2. 社区 API
```
端点: https://rotten-tomatoes-api.ue.r.appspot.com

/movie/{movie_name}    # 单个结果
/search/{movie_name}   # 所有匹配结果
```

### 可获取数据
| 字段 | 说明 |
|------|------|
| Tomatometer | 影评人新鲜度 (0-100%) |
| Audience Score | 观众评分 (0-100%) |
| Certified Fresh | 是否认证新鲜 |
| 评论数量 | 影评人/观众评论数 |
| 影评人评论 | 专业影评内容 |

### 风险
- 网站结构变化可能导致爬虫失效
- 建议缓存结果

---

## 五、Metacritic

### 基本信息
- **官网**: https://www.metacritic.com/
- **官方 API**: 无

### 第三方方案

#### 1. pycritic 库
```bash
pip install pycritic
```

```python
import pycritic

scraper = pycritic.Scraper()
resource = scraper.get("http://www.metacritic.com/movie/the-matrix")

print(resource.metascore)   # 媒体评分
print(resource.userscore)   # 用户评分
```

#### 2. 自写爬虫
```bash
pip install cloudscraper beautifulsoup4
```

```python
import cloudscraper
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper()
url = "https://www.metacritic.com/movie/the-matrix"
response = scraper.get(url)
soup = BeautifulSoup(response.text, 'html.parser')
# 解析数据...
```

### 可获取数据
| 字段 | 说明 |
|------|------|
| Metascore | 媒体综合评分 (0-100) |
| 用户评分 | 用户平均评分 (0-10) |
| 评分分布 | 正面/混合/负面比例 |
| 媒体评论 | 各媒体评分和评论摘要 |

### 风险
- 需处理反爬机制
- 建议使用 cloudscraper 绕过 Cloudflare

---

## 六、推荐的数据获取策略

### 架构
```
TMDB API (主数据源)
    │
    ├── 基本信息
    ├── 演员/导演
    ├── 图片 URL
    └── imdb_id
          │
          ▼
OMDb API (评分聚合)
    │
    ├── IMDb 评分
    ├── 烂番茄评分
    └── Metacritic 评分
          │
          ▼
烂番茄爬虫 (可选，详细评论)
    │
    └── 影评人评论内容
          │
          ▼
Metacritic 爬虫 (可选，详细评论)
    │
    └── 媒体评论内容
```

### 数据源分工
| 数据类型 | 数据源 | 方式 |
|----------|--------|------|
| 基本信息 | TMDB | 官方 API |
| 海报/剧照 | TMDB | 官方 API |
| IMDb 评分 | OMDb | 免费 API |
| 烂番茄评分 | OMDb | 免费 API |
| Metacritic 评分 | OMDb | 免费 API |
| 烂番茄评论 | rottentomatoes-python | 爬取 |
| Metacritic 评论 | 自写爬虫 | 爬取 |
| 豆瓣评分 | 自写爬虫 | 爬取 |

---

## 七、相关资源

### 官方文档
- TMDB API: https://developer.themoviedb.org/docs
- OMDb API: https://www.omdbapi.com/#parameters

### Python 库
- tmdbsimple: https://github.com/celiao/tmdbsimple
- rottentomatoes-python: https://github.com/preritdas/rottentomatoes-python
- pycritic: https://github.com/ig3io/pycritic

### 每日数据导出（TMDB）
- 电影 ID: https://files.tmdb.org/p/exports/movie_ids_MM_DD_YYYY.json.gz
- TV ID: https://files.tmdb.org/p/exports/tv_series_ids_MM_DD_YYYY.json.gz
- 人物 ID: https://files.tmdb.org/p/exports/person_ids_MM_DD_YYYY.json.gz
