# 图片爬取稳定性分析

## 问题背景

当前 `movie-ingest` 项目中，图片爬取存在以下问题：

1. **跳过豆瓣图片页面**：为了避免触发反爬虫，直接跳过了豆瓣图片页面
2. **图片来源单一**：只依赖豆瓣主海报 + OMDb + TMDB
3. **图片数量少**：通常只有 2-3 张海报，剧照缺失

## 解决方案对比

### 方案 A：当前方案（跳过豆瓣图片页面）

**实现**：
```python
# movie-ingest/main.py
# 跳过豆瓣图片页面，只使用主海报和 TMDB/OMDb
images_data = {
    "douban": {
        "main_poster_url": douban.get("main_poster_url")
    },
    "tmdb": tmdb.get("images", {}),
    "omdb": omdb
}
```

**优点**：
- ✅ 稳定，不会触发反爬虫
- ✅ 速度快

**缺点**：
- ❌ 图片数量少（通常 2-3 张）
- ❌ 剧照缺失
- ❌ 依赖 TMDB API（不稳定）

---

### 方案 B：douban-top250 方案（访问图片页面）

**实现**：
```python
# reference-archive/code-snippets/image-crawling-stable.py

async def crawl_images_stable(page, movie_id: str):
    url = f"https://movie.douban.com/subject/{movie_id}/photos?type=S"
    
    await page.goto(url, timeout=60000)
    await asyncio.sleep(random.uniform(2, 5))
    
    content = await page.content()
    soup = BeautifulSoup(content, "html.parser")
    
    images = []
    items = soup.select(".cover a")  # 关键选择器
    
    for item in items:
        img_elem = item.select_one("img")
        thumb_url = img_elem.get("src", "")
        origin_url = thumb_url.replace("/m/", "/raw/")  # 关键转换
        
        # 类型判断
        type_class = item.get("class", [])
        img_type = "other"
        for cls in type_class:
            if "poster" in cls:
                img_type = "poster"
            elif "still" in cls:
                img_type = "still"
        
        images.append({
            "type": img_type,
            "origin_url": origin_url
        })
    
    return images
```

**优点**：
- ✅ 图片数量多（通常 20-50 张）
- ✅ 包含海报和剧照
- ✅ 不依赖 TMDB API

**缺点**：
- ❌ 可能触发反爬虫
- ❌ 需要增加延迟时间

---

## 稳定性对比

| 指标 | 方案 A（跳过） | 方案 B（访问） |
|------|---------------|---------------|
| **图片数量** | 2-3 张 | 20-50 张 |
| **剧照数量** | 0 张 | 10-30 张 |
| **触发反爬虫概率** | 低 | 中 |
| **依赖外部 API** | 是（TMDB） | 否 |
| **稳定性** | 高 | 中 |

---

## 改进建议

### 短期方案（推荐）

**混合方案**：优先使用方案 B，失败后降级到方案 A

```python
async def crawl_images_hybrid(page, movie_id: str):
    try:
        # 尝试访问豆瓣图片页面
        images = await crawl_images_stable(page, movie_id)
        
        if len(images) < 5:
            # 图片太少，可能被拦截，降级到主海报
            raise Exception("图片数量过少，可能被拦截")
        
        return images
        
    except Exception as e:
        # 降级：只获取主海报
        print(f"豆瓣图片页面访问失败，降级到主海报: {e}")
        
        # 从详情页获取主海报
        detail = await crawl_detail(page, movie_id)
        return [{
            "type": "poster",
            "origin_url": detail.get("main_poster_url", "")
        }]
```

### 长期方案

1. **增加延迟**：图片页面访问间隔 3-5 秒
2. **分批访问**：每爬取 10 部电影后休息 1 分钟
3. **失败重试**：失败后等待 5 分钟重试
4. **代理轮换**：使用代理池轮换 IP

---

## 集成步骤

### 步骤 1：修改 `douban.py`

```python
# movie-ingest/sources/douban.py

async def crawl_images(self, douban_id: str) -> Dict:
    """
    爬取图片（混合方案）
    """
    try:
        # 方案 B：访问图片页面
        url = f"{config.DOUBAN_BASE_URL}/subject/{douban_id}/photos?type=S"
        await self.page.goto(url, timeout=60000)
        await asyncio.sleep(random.uniform(3, 6))
        
        content = await self.page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        items = soup.select(".cover a")
        
        if len(items) < 5:
            raise Exception("图片数量过少")
        
        posters = []
        stills = []
        
        for item in items:
            img_elem = item.select_one("img")
            if not img_elem:
                continue
            
            thumb_url = img_elem.get("src", "")
            origin_url = thumb_url.replace("/m/", "/raw/")
            
            type_class = item.get("class", [])
            img_type = "other"
            for cls in type_class:
                if "poster" in cls:
                    img_type = "poster"
                elif "still" in cls:
                    img_type = "still"
            
            if img_type == "poster":
                posters.append({"origin_url": origin_url, "type": "poster"})
            elif img_type == "still":
                stills.append({"origin_url": origin_url, "type": "still"})
        
        return {
            "posters": posters,
            "stills": stills,
            "posters_total": len(posters),
            "stills_total": len(stills)
        }
        
    except Exception as e:
        Logger.warning(f"豆瓣图片页面访问失败，降级到主海报: {e}")
        
        # 降级：返回空列表，使用主海报
        return {
            "posters": [],
            "stills": [],
            "posters_total": 0,
            "stills_total": 0
        }
```

### 步骤 2：修改 `main.py`

```python
# movie-ingest/main.py

# 恢复豆瓣图片爬取
images = await self.douban.crawl_images(douban_id)
raw_data["douban"]["images"] = images
```

---

## 风险评估

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 触发反爬虫 | 中 | 高 | 增加延迟、降级方案 |
| 图片页面 403 | 低 | 中 | 等待 5 分钟后重试 |
| 图片数量少 | 低 | 低 | 使用 TMDB/OMDb 补充 |

---

## 测试建议

1. **小规模测试**：先测试 10 部电影
2. **监控触发率**：记录触发反爬虫的次数
3. **调整延迟**：根据触发率调整延迟时间
4. **评估效果**：对比图片数量和质量

---

## 结论

**推荐方案**：混合方案（优先方案 B，失败降级到方案 A）

**预期效果**：
- 图片数量：从 2-3 张增加到 20-50 张
- 剧照数量：从 0 张增加到 10-30 张
- 稳定性：保持高稳定性（失败后降级）
