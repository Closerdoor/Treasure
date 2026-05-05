# 电影数据多源爬取工具 - 问题记录与决策

本文档记录开发过程中遇到的重要问题、解决方案和技术决策。

---

## 一、豆瓣相关问题

### 1.1 详情页解析失败

**问题描述**：
- 豆瓣详情页解析时，大部分字段返回 `None`
- 原因：`info` 变量在解析前未定义，导致后续代码无法执行

**解决方案**：
- 在解析开始时先获取 `info = soup.select_one("#info")`
- 确保所有依赖 `info` 的代码都在 `if info:` 块内

**代码位置**：`sources/douban.py:158`

---

### 1.2 标题包含英文

**问题描述**：
- 豆瓣标题格式为"中文 英文"（如"星际穿越 Interstellar"）
- 数据库要求 `title` 只存储中文标题

**解决方案**：
```python
import re
chinese_match = re.match(r'^([\u4e00-\u9fa5]+)', full_title)
if chinese_match:
    result["title"] = chinese_match.group(1)
```

**决策**：
- `title`: 只取中文部分
- `original_title`: 从豆瓣"原名"字段获取，或从标题提取英文部分

---

### 1.3 图片下载返回 418 错误

**问题描述**：
- 豆瓣图片服务器返回 HTTP 418 (I'm a teapot)
- 这是豆瓣的反爬机制

**解决方案**：
```python
headers = {
    "Referer": "https://movie.douban.com/",
    "User-Agent": "Mozilla/5.0 ..."
}
```

**决策**：所有豆瓣图片请求必须携带 Referer 头

---

### 1.4 图片 URL 使用 HTTP 失败

**问题描述**：
- 将 HTTPS 改为 HTTP 后，图片下载失败
- 错误：`Cannot connect to host img2.doubanio.com:80`

**解决方案**：
- 保持使用 HTTPS
- 添加代理支持
- 添加 Referer 头

---

## 二、TMDB 相关问题

### 2.1 API 连接失败

**问题描述**：
- 错误：`Cannot connect to host api.themoviedb.org:443 ssl:default`
- SSL 连接错误

**解决方案**：
```python
# 配置代理
PROXY_ENABLED = True
PROXY_URL = "http://127.0.0.1:7890"

# 禁用 SSL 验证
connector = aiohttp.TCPConnector(ssl=False)
async with aiohttp.ClientSession(connector=connector) as session:
    async with session.get(url, proxy=proxy) as response:
        ...
```

**决策**：
- 使用代理访问 TMDB API
- 禁用 SSL 验证（避免证书问题）

---

## 三、Wikipedia 相关问题

### 3.1 搜索失败

**问题描述**：
- 使用中文标题搜索 Wikipedia 失败
- 错误：`net::ERR_ABORTED`

**解决方案**：
- 等待页面加载完成
- 增加超时时间
- 检查是否跳转到搜索页面

---

### 3.2 标识符包含"[编辑]"

**问题描述**：
- Wikipedia 词条名包含"[编辑]"后缀
- 如"星际穿越[编辑]"

**解决方案**：
```python
title_text = re.sub(r'\[编辑\]$', '', title_text)
```

---

## 四、烂番茄相关问题

### 4.1 搜索失败

**问题描述**：
- 使用中文标题搜索烂番茄失败
- 烂番茄是英文站点

**解决方案**：
- 使用英文原名搜索
- 优先级：`original_title` > `title`

---

### 4.2 评论获取失败

**问题描述**：
- 评论页面 CSS 选择器不正确
- 返回 0 条评论

**解决方案**：
- 尝试多种 CSS 选择器
- 使用 `data-qa` 属性选择器

```python
review_items = soup.select(".review-row")
if not review_items:
    review_items = soup.select("div[data-qa='review-item']")
```

---

## 五、Metacritic 相关问题

### 5.1 搜索失败

**问题描述**：
- 使用中文标题搜索 Metacritic 失败
- 使用英文原名也搜索失败

**可能原因**：
- Metacritic 搜索算法问题
- 页面结构变化

**当前状态**：待解决

---

## 六、百度百科相关问题

### 6.1 标题为空

**问题描述**：
- 百度百科词条标题返回空字符串

**解决方案**：
- 尝试多种选择器
- 如果标题为空，从 URL 提取

```python
title_elem = soup.select_one("h1") or soup.select_one(".lemmaTitle")
if not title_text:
    # 从 URL 提取
    match = re.search(r"/item/([^/]+)", url)
    if match:
        title_text = unquote(match.group(1))
```

---

## 七、数据合并问题

### 7.1 国家/地区处理

**问题描述**：
- 豆瓣提供多个国家（如"美国 / 英国 / 加拿大"）
- 数据库要求只保留一个

**解决方案**：
- 从上映日期中提取最早上映的地区
- 忽略电影节、首映等特殊上映

```python
def _extract_country_from_release_dates(self, release_dates):
    # 过滤电影节等特殊上映
    valid_dates = [rd for rd in release_dates 
                   if not any(kw in rd.get("location", "") 
                             for kw in ["电影节", "首映", "festival"])]
    # 按日期排序，取最早的
    valid_dates.sort(key=lambda x: x.get("date", ""))
    return valid_dates[0].get("location", "") if valid_dates else ""
```

**决策**：
- 优先使用上映日期中的地区
- 如果没有上映日期，使用豆瓣的国家字段

---

### 7.2 标识符格式

**问题描述**：
- 百度百科和 Wikipedia 的标识符应该是搜索关键词，不是 ID

**解决方案**：
- `baike`: 存储词条名（如"星际穿越"）
- `wikipedia_zh`: 存储词条名（如"星际穿越"）

**决策**：
- 豆瓣、IMDb、TMDB 使用数字 ID
- 百度百科、Wikipedia 使用词条名

---

## 八、演职人员格式转换

### 8.1 TMDB 部门映射

**问题描述**：
- TMDB 的部门名称与数据库不一致

**解决方案**：
```python
department_map = {
    "Directing": ("direction", "director", "导演"),
    "Writing": ("writing", "writer", "编剧"),
    "Production": ("production", "producer", "制片人"),
    "Camera": ("camera", "cinematographer", "摄影"),
    "Editing": ("editing", "editor", "剪辑"),
    "Actors": ("cast", "actor", "演员")
}
```

---

## 九、代理配置

### 9.1 代理使用场景

| 来源 | 是否需要代理 | 原因 |
|------|-------------|------|
| 豆瓣 | 否 | 国内站点 |
| TMDB | 是 | 国外站点，SSL 问题 |
| OMDb | 是 | 国外站点 |
| 百度百科 | 否 | 国内站点 |
| Wikipedia | 是 | 国外站点 |
| 烂番茄 | 是 | 国外站点 |
| Metacritic | 是 | 国外站点 |

### 9.2 代理配置方式

```python
# config.py
PROXY_ENABLED = True
PROXY_URL = "http://127.0.0.1:7890"

# 使用代理
async with session.get(url, proxy=self.proxy) as response:
    ...
```

---

## 十、技术决策记录

### 10.1 为什么使用 Playwright 而不是 requests

**决策**：使用 Playwright

**原因**：
1. 豆瓣需要登录才能查看完整信息
2. 部分内容需要 JavaScript 渲染
3. 可以保存 Cookie 实现持久登录
4. 更好的反爬能力

---

### 10.2 为什么一部电影一个目录

**决策**：每部电影生成独立目录

**原因**：
1. 便于管理和审阅
2. 原始数据分开存储，便于调试
3. 符合数据库设计，便于导入

---

### 10.3 为什么使用 JSON 而不是 CSV

**决策**：使用 JSON

**原因**：
1. 支持嵌套结构（如评分、上映日期）
2. 更好的 Unicode 支持
3. 与数据库 JSON 字段一致

---

### 10.4 图片下载并发数

**决策**：并发数 5

**原因**：
1. 避免触发反爬机制
2. 减少服务器压力
3. 平衡速度和稳定性

---

## 十一、待解决问题

### 11.1 Metacritic 搜索失败

**状态**：待解决

**可能方案**：
1. 调研 Metacritic 搜索页面结构
2. 使用 Google 搜索结果
3. 跳过 Metacritic

---

### 11.2 烂番茄评论获取

**状态**：部分解决

**问题**：评论数量为 0

**可能方案**：
1. 调研评论页面结构
2. 使用 API（如果有）

---

### 11.3 图片下载不完整

**状态**：已知问题

**问题**：只下载了部分图片（30 张中的 25 张）

**原因**：
1. 部分图片 URL 失效
2. 网络问题
3. 服务器断开连接

**决策**：接受部分下载，后续可手动补充

---

## 十二、性能优化

### 12.1 并发控制

```python
semaphore = asyncio.Semaphore(5)  # 限制并发数
```

### 12.2 延迟控制

```python
MIN_DELAY = 1.0  # 最小延迟
MAX_DELAY = 3.0  # 最大延迟
PAGE_DELAY = 2.0  # 页面间延迟
```

### 12.3 超时控制

```python
timeout = aiohttp.ClientTimeout(total=30)  # 30 秒超时
```

---

文档版本：v1.0
创建日期：2026-05-05
