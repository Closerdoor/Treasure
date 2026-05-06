# 集成指南

## 目标
将 reference-archive 中的代码片段整合到 movie-ingest 项目

## 集成优先级

### 高优先级（建议立即集成）
1. **图片爬取稳定性** → 解决 TMDB 图片下载不稳定问题
2. **评论爬取稳定性** → 当前已足够稳定，无需修改

### 中优先级（可选集成）
3. **httpx 下载** → 替换 aiohttp，提升下载稳定性
4. **CSV 导出** → 方便数据查看和备份

### 低优先级（未来扩展）
5. **1905 电影网** → 补充国产电影数据
6. **情感分析** → 评论分析功能

## 集成步骤

### 1. 图片爬取稳定性（高优先级）

**问题**：TMDB API 经常超时，导致图片和演职员缺失

**方案**：参考 douban-top250 的图片爬取方案

**步骤**：
```python
# 1. 在 douban.py 中添加图片页面访问
async def crawl_images_stable(self, page, movie_id: str) -> List[Dict]:
    """稳定的图片爬取方案"""
    url = f"https://movie.douban.com/subject/{movie_id}/photos?type=S"
    
    await page.goto(url, timeout=60000)
    await asyncio.sleep(3)
    
    content = await page.content()
    soup = BeautifulSoup(content, "html.parser")
    
    items = soup.select(".cover a")
    images = []
    
    for i, item in enumerate(items[:20]):  # 最多 20 张
        img_url = item.select_one("img")["src"]
        # 替换为高清版本
        img_url = img_url.replace("/m/", "/l/")
        
        images.append({
            "url": img_url,
            "type": "still",
            "index": i + 1
        })
    
    return images

# 2. 在 main.py 中调用
if not raw_data.get("images"):
    # TMDB 失败时，使用豆瓣图片
    raw_data["images"] = await self.douban.crawl_images_stable(page, douban_id)
```

**风险**：豆瓣图片页面可能触发反爬虫

**缓解**：
- 延迟 3-5 秒
- 失败时跳过，不中断流程
- 仅在 TMDB 失败时使用

### 2. httpx 下载（中优先级）

**步骤**：
```bash
# 1. 安装 httpx
pip install httpx

# 2. 修改 downloader.py
# 将 aiohttp 替换为 httpx

# 3. 测试
python main.py --test-download
```

**详见**：HTTPX-DOWNLOAD-GUIDE.md

### 3. CSV 导出（中优先级）

**步骤**：
```python
# 1. 在 database.py 中添加导出方法
def export_to_csv(self, output_dir: str = "output"):
    """导出数据到 CSV"""
    pass

# 2. 在 main.py 中添加命令行参数
python main.py --export-csv

# 3. 测试
python main.py --export-csv --output-dir output
```

**详见**：CSV-EXPORT-GUIDE.md

### 4. 1905 电影网（低优先级）

**步骤**：
```python
# 1. 新建 sources/m1905.py
class M1905Crawler:
    pass

# 2. 在 main.py 中集成
self.m1905 = M1905Crawler()

# 3. 在爬取流程中调用
m1905_url = self.m1905.search(title)
if m1905_url:
    m1905_data = self.m1905.get_detail(m1905_url)
```

**详见**：1905-INTEGRATION.md

### 5. 情感分析（低优先级）

**步骤**：
```bash
# 1. 安装依赖
pip install jieba scikit-learn

# 2. 新建 analyzer.py
class CommentAnalyzer:
    pass

# 3. 在数据库中添加字段
ALTER TABLE crawled_movies ADD COLUMN sentiment_json TEXT;

# 4. 在爬取流程中调用
analysis = self.analyzer.analyze_movie_comments(reviews_json)
```

**详见**：SENTIMENT-ANALYSIS-GUIDE.md

## 集成顺序建议

### 第一阶段（立即）
1. 图片爬取稳定性（解决 TMDB 超时问题）

### 第二阶段（可选）
2. httpx 下载（提升下载稳定性）
3. CSV 导出（方便数据查看）

### 第三阶段（未来扩展）
4. 1905 电影网（补充国产电影）
5. 情感分析（评论分析功能）

## 集成注意事项

### 1. 不要一次性集成所有功能
- 按优先级逐步集成
- 每集成一个功能，测试验证
- 确保不影响现有功能

### 2. 保持向后兼容
- 新功能可选启用
- 默认配置保持现有行为
- 添加命令行参数控制

### 3. 测试覆盖
- 每个新功能添加测试
- 测试失败场景
- 测试边界情况

### 4. 文档更新
- 更新 README.md
- 更新使用说明
- 记录集成决策

## 验证清单

集成后验证：
- [ ] 爬取流程正常
- [ ] 图片下载成功
- [ ] 评论获取完整
- [ ] 数据库写入正确
- [ ] CSV 导出正确
- [ ] 无新增错误

## 参考文件

- `notes/IMAGE-CRAWLING-STABILITY.md`：图片爬取稳定性
- `notes/COMMENT-CRAWLING-STABILITY.md`：评论爬取稳定性
- `notes/HTTPX-DOWNLOAD-GUIDE.md`：httpx 下载指南
- `notes/CSV-EXPORT-GUIDE.md`：CSV 导出指南
- `notes/1905-INTEGRATION.md`：1905 电影网集成
- `notes/SENTIMENT-ANALYSIS-GUIDE.md`：情感分析指南