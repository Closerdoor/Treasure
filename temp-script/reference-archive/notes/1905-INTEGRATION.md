# 1905 电影网集成说明

## 来源
`python-crawler-main` 项目的 1905 电影网爬虫

## 1905 电影网特点

### 优势
1. **国内权威电影资料库**：官方背景，数据可靠
2. **访问速度快**：国内服务器，无需代理
3. **数据质量高**：专业编辑维护
4. **无需登录**：公开访问
5. **中文友好**：原生中文内容

### 劣势
1. **覆盖有限**：主要是国产电影和引进大片
2. **评分参考价值低**：用户基数小
3. **评论数量少**：不如豆瓣活跃

## 数据字段

| 1905 字段 | movie-ingest 字段 | 说明 |
|-----------|-------------------|------|
| title | title | 中文标题 |
| rating | ratings_json["1905"] | 1905 评分 |
| director | credits["directors"] | 导演 |
| actors | credits["actors"] | 演员 |
| genres | genres_json | 类型 |
| summary | synopsis_text | 简介（补充） |
| poster | images_json | 海报（补充） |

## 集成方案

### 1. 新建爬虫模块
```
movie-ingest/sources/m1905.py
```

### 2. 使用时机
- **主要用途**：补充国产电影数据
- **次要用途**：获取中文海报、简介
- **不用于**：评分（参考价值低）、评论（数量少）

### 3. 爬取流程
```python
# 1. 搜索电影
url = m1905.search(title)

# 2. 获取详情
data = m1905.get_detail(url)

# 3. 合并数据
if data.get("summary"):
    raw_data["synopsis_text"] = data["summary"]
    
if data.get("poster"):
    images_json["m1905"] = {"url": data["poster"]}
```

### 4. 优先级
```
豆瓣 > TMDB > OMDb > 1905
```

1905 作为补充数据源，优先级最低。

## API 设计

```python
class M1905Crawler:
    def __init__(self):
        self.base_url = "https://www.1905.com"
    
    def search(self, title: str) -> Optional[str]:
        """搜索电影，返回详情页 URL"""
        pass
    
    def get_detail(self, url: str) -> Dict:
        """获取电影详情"""
        pass
    
    def get_top_movies(self, page: int = 1) -> List[Dict]:
        """获取热门电影列表"""
        pass
```

## 选择器

```python
# 标题
title_elem = soup.select_one('h1')

# 评分
rating_elem = soup.select_one('.score')

# 导演
director_elem = soup.select_one('.director a')

# 演员
actors = [a.text.strip() for a in soup.select('.actor a')]

# 类型
genres = [a.text.strip() for a in soup.select('.type a')]

# 简介
summary_elem = soup.select_one('.summary')

# 海报
poster_elem = soup.select_one('.poster img')
```

## 使用建议

### 适合场景
- 国产电影（主旋律、国产大片）
- 引进大片（好莱坞、欧洲）
- 纪录片（央视制作）

### 不适合场景
- 小众艺术电影
- 外语电影（非引进）
- 老电影（资料缺失）

## 注意事项

1. **访问频率**：国内服务器，可以适当提高频率
2. **编码**：使用 `utf-8`
3. **解析器**：推荐 `lxml`（速度快）
4. **代理**：不需要

## 参考文件
- `code-snippets/1905-spider-snippet.py`：完整实现
- `complete-files/python-crawler-1905.py`：原始实现
