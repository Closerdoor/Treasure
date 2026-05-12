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
}
```

### 3. 数据来源对照表

| 字段 | 主要来源 | 备用来源 | 说明 |
|-----|---------|---------|------|
| title（中文名） | 豆瓣 | 当当网 | 优先豆瓣 |
| titleOriginal（原名） | OpenLibrary | Goodreads | 外文网站 |
| author（作者） | 豆瓣 | 百度百科 | 合并中英文名 |
| translator（译者） | 豆瓣 | - | - |
| publisher（出版社） | 豆瓣 | 当当网 | - |
| wordCount（字数） | 当当网 | 中国图书网 | 中文书籍 |
| isbn | 豆瓣 | OpenLibrary | - |
| scores（评分） | 豆瓣 | Goodreads | 各平台评分 |
| summary（简介） | 豆瓣 | 当当网 | 优先豆瓣 |
| quotes（名句） | 百度百科 | Wikipedia | - |
| images（封面） | 豆瓣 | OpenLibrary | 优先豆瓣高清图 |

---

## 三、编码规范

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

## 四、错误处理

### 1. 重试机制

```python
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

---

## 五、反爬虫应对措施

### 1. 豆瓣

| 问题 | 解决方案 |
|-----|---------|
| HTTP 418 错误 | 添加 Referer 头 |
| 页面加载失败 | 使用 `wait_until="networkidle"`，添加延迟 |
| 需要登录 | 通知用户手动登录 |

```python
headers = {
    'Referer': 'https://book.douban.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
```

### 2. Goodreads

| 问题 | 解决方案 |
|-----|---------|
| 需要登录 | 使用非 headless 模式，通知用户登录 |
| API 限流 | 添加请求延迟（1-2 秒） |

### 3. 当当网

| 问题 | 解决方案 |
|-----|---------|
| 验证码 | 控制请求频率，手动处理验证码 |

### 4. 通用策略

| 问题 | 解决方案 |
|-----|---------|
| 请求频率限制 | 添加随机延迟（1-3 秒） |
| IP 封禁 | 使用代理（config.PROXY_URL） |
| User-Agent 检测 | 随机切换 User-Agent |
| Referer 检测 | 添加正确的 Referer 头 |

---

## 六、开发规范

### 1. 代码风格

- 使用 Python 3.10+ 语法
- 使用 async/await 异步编程
- 函数添加类型注解
- 添加文档字符串

### 2. 提交规范

- 提交前运行测试
- 提交信息使用中文
- 描述清楚修改内容

---

## 七、检查清单

每次爬取任务开始前，确认以下事项：

- [ ] 已阅读本规则文档
- [ ] 豆瓣数据获取成功
- [ ] 数据来源已标注
- [ ] 中文字符无乱码
- [ ] 字段命名符合规范
- [ ] 数据验证通过
- [ ] 错误日志已记录
- [ ] 反爬虫措施已应用

---

## 八、数据约束

| 约束项 | 要求 |
|--------|------|
| 书评数量 | 每源严格 20 条 |
| 书评排序 | 按热度排序（有用数/点赞数） |
| 封面下载 | 全部封面，原始分辨率 |

---

## 九、封面去重策略

| 维度 | 检查时机 | 说明 |
|------|----------|------|
| URL | 下载前 | 相同 URL 直接跳过 |
| 文件名 | 下载前 | 相同文件名直接跳过 |
| 内容哈希 | 下载后 | 计算 MD5，相同跳过 |
| 跨来源 | 合并时 | 豆瓣和 OpenLibrary 同一封面只保留一份 |

---

## 十、字段冲突检测

检测以下字段冲突：

| 字段 | 冲突条件 | 处理方式 |
|------|----------|----------|
| `year` | 差异 > 1 年 | 生成审阅文件 |
| `summary` | 长度差异 > 50% | 生成审阅文件 |

冲突时生成 `review.md` 审阅文件，供人工确认。

---

## 十一、数据源优先级汇总

| 数据源 | 优先级 | 主要用途 |
|--------|:------:|----------|
| 豆瓣读书 | 最高 | 基本信息、评分、书评、封面、标签 |
| OpenLibrary | 高 | 英文信息、作者、封面、ISBN |
| Goodreads | 高 | 英文评分、获奖、系列、书评 |
| 当当网 | 中 | 字数、获奖、系列、简介 |
| 百度百科 | 中 | 作者简介、名句 |
| Wikipedia | 低 | 名句、获奖补充 |
| 中国图书网 | 低 | 字数补充、出版社详情 |

---

**最后更新**：2026-05-12
