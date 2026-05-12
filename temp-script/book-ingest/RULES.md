# 书籍数据爬取规则

> ⚠️ **重要提示**：每次操作此目录下的文件时，必须先阅读并遵守以下规则

---

## 一、数据源优先级规则

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
- 其他数据源网站（如 Goodreads、当当网等）如果需要登录或验证
- **通知用户处理**，不要自动跳过或使用未验证的数据

---

## 二、数据来源标注规则

### 1. 字段来源追踪
获取的所有数据信息，必须一一标注好与数据库字段的对应关系，并注明来源。

### 2. 标注格式
在代码中使用 `source` 字段标注数据来源：

```python
{
    "title": "三体",
    "title_source": "douban",
    "author": ["刘慈欣"],
    "author_source": "douban",
    "wordCount": 880000,
    "wordCount_source": "dangdang",
    ...
}
```

### 3. 数据来源对照表

| 字段 | 主要来源 | 备用来源 | 说明 |
|-----|---------|---------|------|
| title（中文名） | 豆瓣 | 当当网 | 优先豆瓣 |
| originalTitle（原名） | OpenLibrary | Goodreads | 外文网站 |
| author（作者） | 豆瓣 | 百度百科 | 合并中英文名 |
| translator（译者） | 豆瓣 | - | - |
| publisher（出版社） | 豆瓣 | 当当网 | - |
| publishDate（出版日期） | 豆瓣 | OpenLibrary | - |
| pageCount（页数） | 豆瓣 | OpenLibrary | - |
| wordCount（字数） | 当当网 | 中国图书网 | 中文书籍 |
| isbn（ISBN） | 豆瓣 | OpenLibrary | - |
| rating（评分） | 豆瓣 | Goodreads | 各平台评分 |
| summary（简介） | 豆瓣 | 当当网 | 优先豆瓣 |
| authorIntro（作者简介） | 百度百科 | Goodreads | - |
| cover（封面） | 豆瓣 | OpenLibrary | 优先豆瓣高清图 |
| tags（标签） | 豆瓣 | Goodreads | 中文标签 |
| awards（获奖） | Goodreads | 当当网 | - |
| series（系列） | Goodreads | 当当网 | - |
| quotes（名句） | 百度百科 | Wikipedia | - |

### 4. 作者/译者数据来源

| 字段 | 中文名 | 英文名 | 简介 | 头像 |
|-----|-------|-------|-----|-----|
| 作者 | 豆瓣 | OpenLibrary | 百度百科 | OpenLibrary |
| 译者 | 豆瓣 | - | 百度百科 | - |

**说明**：
- 中文名从国内网站获取（豆瓣、百度百科）
- 英文名、头像从外文网站获取（OpenLibrary、Goodreads）
- 作者简介从百度百科获取

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

### 1. Prisma Schema 字段命名
- 数据库字段使用**下划线命名**（snake_case）
- 代码中使用**驼峰命名**（camelCase）
- 写入数据库时转换

### 2. 字段映射表

| Staging JSON | Prisma Schema | 类型 | 说明 |
|-------------|---------------|-----|------|
| id | id | String | 书籍 ID |
| title | title | String | 中文标题 |
| originalTitle | original_title | String? | 原标题 |
| author | author | Json | 作者列表 |
| translator | translator | Json | 译者列表 |
| publisher | publisher | String? | 出版社 |
| publishDate | publish_date | String? | 出版日期 |
| pageCount | page_count | Int? | 页数 |
| wordCount | word_count | Int? | 字数 |
| isbn | isbn | String? | ISBN |
| summary | summary | Json? | 简介 |
| authorIntro | author_intro | Json? | 作者简介 |
| tags | tags | Json | 标签列表 |
| awards | awards | Json? | 获奖列表 |
| series | series | Json? | 系列信息 |
| quotes | quotes | Json? | 名句列表 |
| doubanId | douban_id | String? | 豆瓣 ID |
| goodreadsId | goodreads_id | String? | Goodreads ID |
| openlibraryId | openlibrary_id | String? | OpenLibrary ID |
| doubanRating | douban_rating | Float? | 豆瓣评分 |
| goodreadsRating | goodreads_rating | Float? | Goodreads 评分 |
| images | images | Json? | 封面图片 |
| reviews | reviews | Json? | 书评 |

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
    required_fields = ['title', 'author']
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
book-ingest/
├── RULES.md           # 本规则文档（必读）
├── sources/           # 数据源爬虫
│   ├── douban_book.py # 豆瓣读书爬虫
│   ├── openlibrary.py # OpenLibrary API
│   ├── baike.py       # 百度百科
│   ├── wikipedia.py   # Wikipedia
│   ├── goodreads.py   # Goodreads
│   ├── dangdang.py    # 当当网
│   └── bookchina.py   # 中国图书网
├── merger.py          # 数据合并模块
├── database.py        # 数据库导入模块
├── downloader.py      # 封面下载模块
├── config.py          # 配置文件
├── utils/             # 工具函数
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

### 1. 豆瓣反爬虫机制

#### 1.1 图片下载返回 HTTP 418
**问题**：下载豆瓣图片（封面等）时返回 HTTP 418 错误

**原因**：豆瓣检测到请求缺少 Referer 头

**解决方案**：添加 Referer 头
```python
headers = {
    'Referer': 'https://book.douban.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
```

#### 1.2 页面加载失败
**解决方案**：
- 使用 `wait_until="networkidle"` 等待网络请求完成
- 添加适当的延迟（3-5 秒）
- 实现重试机制（5s→10s→30s）

### 2. Goodreads 反爬虫机制

#### 2.1 需要登录
**问题**：Goodreads 部分内容需要登录才能查看

**解决方案**：
- 使用非 headless 模式
- 通知用户手动登录
- 保存 Cookie 供后续使用

#### 2.2 API 限流
**问题**：Goodreads API 有请求频率限制

**解决方案**：
- 添加请求延迟（1-2 秒）
- 使用 API Key（如有）

### 3. 当当网反爬虫机制

#### 3.1 验证码
**问题**：频繁访问可能触发验证码

**解决方案**：
- 控制请求频率
- 使用非 headless 模式处理验证码

### 4. 中国图书网反爬虫机制

#### 4.1 访问限制
**问题**：可能有 IP 访问频率限制

**解决方案**：
- 添加请求延迟
- 必要时使用代理

### 5. 通用反爬虫应对策略

| 问题 | 解决方案 |
|-----|---------|
| 请求频率限制 | 添加随机延迟（1-3 秒） |
| IP 封禁 | 使用代理（config.PROXY_URL） |
| User-Agent 检测 | 随机切换 User-Agent |
| Referer 检测 | 添加正确的 Referer 头 |
| Cookie 验证 | 保持会话状态 |
| 验证码 | 通知用户手动处理 |

### 6. 请求头配置模板

```python
# 豆瓣请求头
DOUBAN_HEADERS = {
    'Referer': 'https://book.douban.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# Goodreads 请求头
GOODREADS_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# 当当网请求头
DANGDANG_HEADERS = {
    'Referer': 'http://www.dangdang.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}
```

---

## 八、检查清单

每次爬取任务开始前，确认以下事项：

- [ ] 已阅读本规则文档
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
| 封面获取失败 | 检查图片 URL 是否正确 |
| 页面加载失败 | 检查 wait_until 参数，增加延迟 |
| 数据不完整 | 检查选择器是否正确，页面结构是否变化 |

### 2. Goodreads 相关

| 问题 | 排查步骤 |
|-----|---------|
| 需要登录 | 切换到非 headless 模式，通知用户登录 |
| 找不到书籍 | 使用 ISBN 或英文标题搜索 |
| 评分获取失败 | 检查页面结构是否变化 |

### 3. 当当网相关

| 问题 | 排查步骤 |
|-----|---------|
| 验证码拦截 | 控制请求频率，手动处理验证码 |
| 字数缺失 | 该书籍可能没有字数信息 |
| 找不到书籍 | 使用 ISBN 或精确标题搜索 |

### 4. 数据合并相关

| 问题 | 排查步骤 |
|-----|---------|
| 作者不匹配 | 使用名字匹配，检查是否同一人 |
| 字数冲突 | 优先当当网，备用中国图书网 |
| 获奖信息冲突 | 合并所有来源的获奖信息 |

---

## 十、数据源优先级汇总

| 数据源 | 优先级 | 主要用途 |
|--------|--------|----------|
| 豆瓣读书 | 最高 | 基本信息、评分、书评、封面、标签 |
| OpenLibrary | 高 | 英文信息、作者、封面、ISBN |
| Goodreads | 高 | 英文评分、获奖、系列、书评 |
| 当当网 | 中 | 字数、获奖、系列、简介 |
| 百度百科 | 中 | 作者简介、名句 |
| Wikipedia | 低 | 名句、获奖补充 |
| 中国图书网 | 低 | 字数补充、出版社详情 |

---

**最后更新**：2026-05-10
