# 电影数据爬取规则

> ⚠️ **重要提示**：每次操作此目录下的文件时，必须先阅读并遵守以下规则

---

## 十、豆瓣 `misc/sorry` 反爬处理补充

豆瓣有时会在连续访问详情、图片、评论、影评等页面后跳转到 `https://www.douban.com/misc/sorry?...`，页面提示“你访问豆瓣的方式有点像机器人程序”或要求“证明你是人类”。实际调试确认：进入这个状态后，继续自动访问通常会一直失败，只能等待一段时间后再执行，或由用户在浏览器中完成验证后再继续。

必须遵守：

- 立即暂停当前豆瓣采集，不继续刷新、不密集重试。
- 不允许把此时得到的空列表、0 张图片、空评论覆盖已有 raw。
- 记录触发 URL、触发时间、正在采集的数据类型。
- 等待一段时间后重新执行；如果仍然显示验证页，则由用户手动处理。
- 单独补抓图片或评论更容易触发该限制，因此优先在一次浏览器会话里按固定入口完整采集豆瓣数据。

## 一、数据源优先级规则

### 0. 当前脚本职责边界

本目录的正式主链路固定为：

```text
main.py / crawl.py
  -> sources/*.py
  -> downloader.py
  -> merger.py
  -> data/raw/
  -> data/staging/
  -> database.py
  -> .local/treasure.db
```

职责约束：

- `main.py` 与 `crawl.py` 是正式采集入口。
- `sources/*.py` 只处理对应外部数据源，不写数据库。
- `merger.py` 只合并 raw 到 staging，不写数据库、不写发布资源。
- `downloader.py` 只下载采集阶段资源到 `data/assets/`。
- `database.py` 是本目录写入 `.local/treasure.db` 的正式入口。
- `db_tools/import-movie.mjs` 属于旧 JS 入库入口，因会触碰 `site/public/assets`，不得作为当前正式流程使用。
- `generated/` 导出、`site/public/assets/` 发布资源同步、Astro 构建和发布校验都不属于本目录。

修改本目录脚本时，必须保持以上边界。若确实需要越界，应先向用户确认并说明原因、影响范围和替代方案。

### 1. 豆瓣数据优先原则
- **豆瓣是核心数据源**，必须确保豆瓣数据成功获取
- 不管获取什么信息，都要保证豆瓣中的信息有成功获取到，然后再来抉择使用哪个数据源
- 豆瓣获取失败时，**不允许跳过**，必须先解决获取豆瓣信息失败的问题

### 2. 豆瓣失败处理流程
| 失败原因 | 处理方式 |
|---------|---------|
| 需要登录 | 通知用户手动登录，等待用户确认 |
| 被反爬虫限制 | 等待限制解除，调整请求频率 |
| 页面加载失败 | 重试机制（5s→10s→30s），最多 3 次 |
| 数据不完整 | 记录缺失字段，尝试补充来源 |

### 3. 其他数据源登录/验证
- 其他数据源网站（如 TMDB、OMDb、百度百科等）如果需要登录或验证
- **通知用户处理**，不要自动跳过或使用未验证的数据

### 4. 豆瓣 ID 获取与验证规则

> ⚠️ **重要**：豆瓣 ID 必须通过规范流程获取和验证，禁止凭记忆或未验证来源使用

#### 4.1 获取流程

用户只提供影片名，系统必须自动获取豆瓣 ID：

```
输入：影片中文名（可选：英文名、年份）
输出：豆瓣 ID + 豆瓣链接 + 验证结果
```

**Step 1：百度搜索**
- 打开百度
- 搜索 `{影片中文名} 豆瓣`
- 提取搜索结果中的 `movie.douban.com/subject/{id}/` 链接
- 如果没有找到，尝试 `{英文名} 豆瓣`

**Step 2：候选筛选**
- 从搜索结果中提取所有豆瓣电影链接
- 去重，得到候选列表

**Step 3：页面验证**
- 对每个候选链接使用 Playwright 访问
- 如果遇到验证码/登录 → 通知用户处理，等待确认后继续
- 检查页面是否正常（不是 404）
- 提取页面标题、年份

**Step 4：匹配判断**
- 标题是否包含影片名
- 年份是否匹配（如果用户提供了年份）
- 只有一个候选匹配 → 自动采用
- 多个候选匹配 → 列出让用户选择
- 没有候选匹配 → 报错，要求用户手动提供豆瓣链接

**Step 5：记录结果**
- 记录豆瓣 ID
- 记录来源：百度搜索
- 记录验证结果：标题、年份是否匹配

#### 4.2 验证码/登录处理流程

当 Playwright 遇到验证码或登录页面时：

```
1. 暂停自动化流程
2. 保持浏览器窗口打开
3. 通知用户："豆瓣需要登录/验证码，请在浏览器中处理"
4. 等待用户确认："已完成"
5. 继续自动化流程
6. 保存 Cookie，下次复用
```

#### 4.3 记录豆瓣 ID 获取过程

在 staging JSON 或工作流日志中记录：

```json
{
  "doubanId": "3205624",
  "doubanIdSource": "baidu_search",
  "doubanIdSearchQuery": "社交网络 豆瓣",
  "doubanIdCandidates": [
    {
      "id": "3205624",
      "title": "社交网络",
      "year": 2010,
      "matched": true
    }
  ],
  "doubanIdVerified": true,
  "doubanUrl": "https://movie.douban.com/subject/3205624/"
}
```

#### 4.4 禁止事项

| 禁止行为 | 原因 |
|---------|------|
| 凭记忆使用豆瓣 ID | 记忆不可靠，容易出错 |
| 使用未验证的豆瓣 ID | 可能是错误的 ID |
| 跳过验证流程直接爬取 | 无法确认页面是否正确 |
| 使用非规范来源的豆瓣 ID | 来源不可追溯 |

---

## 二、数据来源标注规则

### 1. 字段来源追踪
获取的所有数据信息，必须一一标注好与数据库字段的对应关系，并注明来源。

### 2. 标注格式
在代码中使用 `source` 字段标注数据来源：

```python
{
    "title": "肖申克的救赎",
    "title_source": "douban",
    "year": 1994,
    "year_source": "douban",
    "originalTitle": "The Shawshank Redemption",
    "originalTitle_source": "tmdb",
    ...
}
```

### 3. 数据来源对照表

> 详细字段映射请参考 [DATA.md](./DATA.md) 文档

**核心原则**：
- 中文名从国内网站获取（豆瓣、百度百科）
- 英文名、角色名、头像从外文网站获取（TMDB）
- 百度百科演职员数据不可靠，不作为主要来源

---

## 三、编码规则

### 1. 文件编码
- 所有 Python 文件使用 **UTF-8 编码**
- 文件头部添加编码声明：`# -*- coding: utf-8 -*-`

### 2. 字符串处理
- 中文字符不要出现乱码
- 注意 Windows 编码问题
- 使用 `ensure_ascii=False` 输出 JSON

### 3. 文件读写
```python
# 正确示例
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

### 4. 控制台输出
- 使用 Logger 工具类统一输出
- 避免直接使用 `print()` 输出中文

---

## 四、数据库字段映射

> 详细字段映射请参考 [DATA.md](./DATA.md) 文档

### 1. 命名规范
- 数据库字段使用**下划线命名**（snake_case）
- 代码中使用**驼峰命名**（camelCase）
- 写入数据库时转换

### 2. 新增与更新边界

- 新增作品采集前必须只读查询 `.local/treasure.db`，优先按 `douban_id`、`imdb_id`、`tmdb_id` 判断作品是否已存在。
- 如果作品已存在，默认停止新增流程，不重复采集、不重复入库。
- 已有作品更新必须显式指定 `work_id`、`source` 和字段白名单。
- `refresh-source` 只允许刷新 raw，不直接写库。
- `update-fields` 只能写入白名单字段，未列出的字段必须保持不变。
- 不得把“新增作品”和“已有作品更新”混在同一个默认入口里。
- 覆盖已有主数据、批量改写字段或改变 staging/DB 字段契约前，必须先向用户确认。

---

## 五、错误处理

### 1. 重试机制
```python
# 豆瓣爬虫重试
max_retries = 3
delays = [5, 10, 30]  # 重试延迟（秒）

for attempt in range(max_retries):
    try:
        result = await crawl()
        if validate(result):
            return result
    except Exception as e:
        if attempt < max_retries - 1:
            await asyncio.sleep(delays[attempt])
        else:
            raise
```

### 2. 数据验证
```python
def validate_douban_data(data: Dict) -> bool:
    """验证豆瓣数据完整性"""
    required_fields = ['title', 'year', 'directors', 'casts']
    for field in required_fields:
        if not data.get(field):
            Logger.warning(f"豆瓣数据缺失: {field}")
            return False
    return True
```

### 3. 错误日志
- 使用 Logger 工具类记录错误
- 记录完整的错误堆栈
- 记录请求 URL 和响应状态

---

## 六、开发规范

### 1. 目录结构
```
movie-ingest/
├── RULES.md           # 本规则文档（必读）
├── sources/           # 数据源爬虫
│   ├── douban.py      # 豆瓣爬虫
│   ├── baike.py       # 百度百科爬虫
│   ├── tmdb.py        # TMDB 客户端
│   ├── omdb.py        # OMDb 客户端
│   └── ...
├── merger.py          # 数据合并模块
├── importer.py        # 数据库导入模块
├── config.py          # 配置文件
├── utils.py           # 工具函数
└── main.py            # 主入口
```

### 2. 代码风格
- 使用 Python 3.10+ 语法
- 使用 async/await 异步编程
- 函数添加类型注解
- 添加文档字符串

### 3. 提交规范
- 提交前运行测试
- 提交信息使用中文
- 描述清楚修改内容

---

## 七、反爬虫机制应对措施

> ⚠️ **重要**：以下是在调试过程中遇到的实际问题及解决方案，请务必遵守

### 1. 豆瓣反爬虫机制

#### 1.1 图片下载返回 HTTP 418
**问题**：下载豆瓣图片（头像、海报等）时返回 HTTP 418 错误（"I'm a teapot"）

**原因**：豆瓣检测到请求缺少 Referer 头，认为是爬虫请求

**解决方案**：添加 Referer 头
```python
headers = {
    'Referer': 'https://movie.douban.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
async with session.get(image_url, headers=headers) as response:
    ...
```

**适用场景**：
- 下载演员头像
- 下载电影海报
- 下载剧照

#### 1.2 演职员页面头像提取失败
**问题**：使用 `.avatar img` 选择器无法获取头像

**原因**：豆瓣使用 `background-image` CSS 属性显示头像，而不是 `<img>` 标签

**错误示例**：
```html
<!-- 错误理解 -->
<img class="avatar" src="...">

<!-- 实际结构 -->
<div class="avatar" style="background-image: url(https://img1.doubanio.com/view/celebrity/m/public/p230.webp)">
</div>
```

**解决方案**：提取 style 属性中的 URL
```python
avatar_elem = celeb.select_one(".avatar")
if avatar_elem:
    style = avatar_elem.get("style", "")
    match = re.search(r"url\(([^)]+)\)", style)
    if match:
        avatar_url = match.group(1)
```

#### 1.3 豆瓣页面入口必须固定

豆瓣单源采集必须在一次浏览器会话内按固定入口完成，不能先抓一部分、后续再重新登录补抓：

- 基本信息：`/subject/{douban_id}/`
- 演职员：`/subject/{douban_id}/celebrities`
- 视频：`/subject/{douban_id}/trailer`
- 图片总页：`/subject/{douban_id}/all_photos`
- 剧照：`/subject/{douban_id}/photos?type=S`
- 海报：`/subject/{douban_id}/photos?type=R`
- 壁纸：`/subject/{douban_id}/photos?type=W`
- 好评短评：`/subject/{douban_id}/comments?percent_type=h&limit=20&status=P&sort=new_score`
- 影评：`/subject/{douban_id}/reviews?start={start}&sort=hot`

影评必须先通过 `sort=hot` 列表页确定热度最高的前 20 条，再进入对应影评详情页读取完整正文；不得从未排序列表或非热度排序列表中取详情页链接。

#### 1.4 页面加载失败
**问题**：页面内容获取不完整或为空

**解决方案**：
- 使用 `wait_until="networkidle"` 等待网络请求完成
- 添加适当的延迟（3-5 秒）
- 实现重试机制（5s→10s→30s）

### 2. 百度百科反爬虫机制

#### 2.1 图形验证码
**问题**：访问百度百科时出现图形验证码

**解决方案**：
- 使用非 headless 模式（`headless=False`）
- 增加等待时间让用户手动完成验证
- 通知用户处理，不要自动跳过

```python
print('如果出现验证码请手动完成')
await asyncio.sleep(30)  # 等待用户处理
```

#### 2.2 PAGE_DATA 结构变化
**问题**：验证码通过后，PAGE_DATA 结构从 `card.content` 变为 `card.left/right`

**解决方案**：同时支持两种结构
```python
# 新版结构
content_items = card.get("content") or []
if content_items:
    # 从 content 提取
    ...

# 旧版结构
left_items = card.get("left") or []
right_items = card.get("right") or []
if left_items or right_items:
    # 从 left/right 提取
    ...
```

#### 2.3 演职员数据位置
**问题**：`card.content` 中 `director` 和 `starring` 的 value 为 None

**原因**：部分字段数据在 `text` 数组中，而不是 `value` 字段

**解决方案**：同时检查 `value` 和 `text`
```python
if d.get("dataType") == "lemma":
    name = d.get("value", {}).get("title", "")
elif d.get("dataType") == "text":
    text_list = d.get("text", [])
    for t in text_list:
        if t.get("tag") == "text":
            name = t.get("text", "").strip()
```

#### 2.4 演员数据来源
**问题**：PAGE_DATA 中演员数据不完整

**解决方案**：从 `role` 模块提取演员数据
```python
role_module = soup.find(attrs={'data-module-type': 'role'})
if role_module:
    role_items = role_module.find_all(class_='roleItem_uMbCs')
    # 提取角色名和演员名
```

### 3. TMDB API

#### 3.1 无反爬虫限制
- TMDB API 稳定，无反爬虫机制
- 需要配置 API Key
- 建议作为主要数据源

### 4. 通用反爬虫应对策略

| 问题 | 解决方案 |
|-----|---------|
| 请求频率限制 | 添加随机延迟（1-3 秒） |
| IP 封禁 | 使用代理（config.PROXY_URL） |
| User-Agent 检测 | 随机切换 User-Agent |
| Referer 检测 | 添加正确的 Referer 头 |
| Cookie 验证 | 保持会话状态 |
| 验证码 | 通知用户手动处理 |

### 5. 请求头配置模板

```python
# 豆瓣请求头
DOUBAN_HEADERS = {
    'Referer': 'https://movie.douban.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# 百度百科请求头
BAIKE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}
```

---

## 八、检查清单

每次爬取任务开始前，确认以下事项：

- [ ] 已阅读本规则文档
- [ ] 豆瓣 ID 已通过百度搜索获取
- [ ] 豆瓣 ID 已验证（页面标题匹配）
- [ ] 豆瓣 ID 来源已记录
- [ ] 豆瓣数据获取成功
- [ ] 数据来源已标注
- [ ] 中文字符无乱码
- [ ] 字段命名符合规范
- [ ] 数据验证通过
- [ ] 错误日志已记录
- [ ] 反爬虫措施已应用（Referer、延迟等）

---

## 九、常见问题排查

### 1. 豆瓣相关

| 问题 | 排查步骤 |
|-----|---------|
| HTTP 418 错误 | 检查是否添加了 Referer 头 |
| 头像获取失败 | 检查是否使用 background-image 提取方式 |
| 页面加载失败 | 检查 wait_until 参数，增加延迟 |
| 数据不完整 | 检查选择器是否正确，页面结构是否变化 |

### 2. 百度百科相关

| 问题 | 排查步骤 |
|-----|---------|
| 验证码拦截 | 切换到非 headless 模式，通知用户处理 |
| PAGE_DATA 为空 | 检查是否等待足够时间，页面是否加载完成 |
| 演职员数据缺失 | 检查 card.content 和 card.left/right 两种结构 |
| 角色名缺失 | 检查 role 模块（data-module-type="role"） |

### 3. 数据合并相关

| 问题 | 排查步骤 |
|-----|---------|
| 演员顺序不匹配 | 使用名字匹配，不要按位置对应 |
| 中文名缺失 | 检查豆瓣/百度百科数据 |
| 英文名缺失 | 检查 TMDB 数据 |
| 头像缺失 | 优先 TMDB，备用豆瓣 |

---

**最后更新**：2026-05-13
