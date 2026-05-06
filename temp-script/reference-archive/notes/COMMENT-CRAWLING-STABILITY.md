# 评论爬取稳定性分析

## 来源
`douban-top250` 项目的评论爬取实现

## 核心问题
豆瓣评论爬取容易触发反爬虫机制，导致：
- 403 Forbidden
- IP 被临时封禁
- 验证码拦截

## 稳定方案

### 1. 分页逻辑
```python
# 短评 URL
url = f"https://movie.douban.com/subject/{movie_id}/comments?start={start}&limit=20&sort=new_score&status=P"

# 影评 URL
url = f"https://movie.douban.com/subject/{movie_id}/reviews?start={start}"
```

关键参数：
- `start=0, 20, 40, ...`：分页偏移
- `limit=20`：每页 20 条
- `sort=new_score`：按热度排序（而非时间）
- `status=P`：已看过

### 2. 延迟控制
```python
import random

# 每页之间延迟 2-5 秒
await asyncio.sleep(random.uniform(2.0, 5.0))
```

### 3. 选择器
```python
# 短评
items = soup.select(".comment-item")

# 影评
items = soup.select(".review-list > div")
```

### 4. 评分提取
豆瓣评分通过 CSS class 表示：
```python
# 短评评分
rating_elem = item.select_one(".rating")
rating_class = rating_elem.get("class", [])  # ["allstar50", "rating"]

# 影评评分
rating_elem = item.select_one(".main-title-rating")
rating_class = rating_elem.get("class", [])  # ["allstar50", "main-title-rating"]

# 提取数字
for cls in rating_class:
    if "allstar" in cls:
        rating = cls.replace("allstar", "").replace("0rating", "")
        # allstar50 → 5
        # allstar40 → 4
```

### 5. 进度保存
每页完成后保存进度，支持断点续爬：
```python
# 保存已爬取的评论数
progress["comments_crawled"] = len(comments)
save_progress(progress)
```

## 当前 movie-ingest 状态

### 已实现
- ✅ 分页逻辑正确
- ✅ 延迟控制（2-5 秒）
- ✅ 选择器正确
- ✅ 评分提取正确

### 无需修改
当前实现已足够稳定，参考代码仅作备用。

## 集成建议

如果需要增强稳定性，可以：

1. **添加重试机制**
```python
max_retries = 3
for attempt in range(max_retries):
    try:
        await page.goto(url, timeout=60000)
        break
    except:
        if attempt < max_retries - 1:
            await asyncio.sleep(10)
```

2. **添加验证码检测**
```python
if "验证码" in await page.title():
    print("触发验证码，暂停爬取")
    await asyncio.sleep(300)  # 等待 5 分钟
```

3. **降低爬取频率**
```python
# 从 2-5 秒增加到 5-10 秒
await asyncio.sleep(random.uniform(5.0, 10.0))
```

## 参考文件
- `code-snippets/comment-crawling-stable.py`：完整实现
- `complete-files/douban-top250-main.py`：原始实现
