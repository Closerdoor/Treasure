# 书籍数据多源爬取工具

从多个来源爬取书籍数据，用于个人收藏馆网站数据录入。

## 数据来源

| 来源 | 数据类型 | 爬取方式 |
|------|----------|----------|
| 豆瓣读书 | 基本信息、评分、书评、封面、标签 | Playwright |
| OpenLibrary | 英文信息、作者、封面、ISBN | REST API |
| 百度百科 | 作者简介、字数 | Playwright |
| Wikipedia | 获奖、经典语录 | Playwright |

## 安装依赖

```bash
pip install playwright beautifulsoup4 aiohttp pillow
playwright install chromium
```

## 使用方法

### 1. 测试模式

```bash
python main.py --test
```

默认测试书籍为《三体》和《百年孤独》，可在 `config.py` 中修改：

```python
TEST_BOOKS = [
    {"douban_id": "2567638", "title": "三体"},
    {"douban_id": "105906", "title": "百年孤独"},
]
```

### 2. 批量模式

```bash
python main.py --batch
```

### 3. 单独模块

```bash
# 只爬取基本信息
python main.py --test --basic

# 只爬取书评
python main.py --test --reviews
```

### 4. 登录豆瓣

首次运行会打开浏览器，需要手动登录豆瓣：
1. 在浏览器中登录豆瓣账号
2. 回到终端按回车继续
3. Cookie 会自动保存，下次运行无需重新登录

## 输出结构

每本书生成一个独立目录：

```
data/
└── 0200000001/                    # 书籍 ID
    ├── data.json                  # 合并后的完整数据
    ├── raw/                       # 原始数据
    │   ├── douban.json
    │   ├── openlibrary.json
    │   ├── baike.json
    │   └── wikipedia.json
    └── images/                    # 封面
        ├── cover-main.jpg         # 主封面
        └── cover-002.jpg          # 补充封面
```

## 配置说明

编辑 `config.py` 修改配置：

```python
# 爬取配置
REVIEWS_PER_SOURCE = 20      # 每个来源的书评数

# 延迟配置（秒）
MIN_DELAY = 2.0
MAX_DELAY = 5.0
PAGE_DELAY = 4.0

# 浏览器配置
HEADLESS = False              # 是否无头模式
USE_CHROME = True             # 是否使用系统 Chrome
```

## 断点续传

进度保存在 `progress.json`，支持断点续传：
- 重新运行脚本会自动跳过已完成的来源
- 某个来源失败不影响其他来源

## 字段映射

详见 `FIELD-MAPPING.md`，记录了爬取数据与数据库字段的对应关系。

## 整体方案

详见 `PROJECT-PLAN.md`，记录了完整的设计方案和流程。

## 注意事项

1. **豆瓣登录**：需要登录才能查看完整信息
2. **OpenLibrary 限流**：公共 API 有请求限制，建议控制频率
3. **图片下载**：会自动去重（URL、文件名、内容哈希）
4. **错误重试**：每个来源失败会重试 3 次，然后跳过
5. **数据合并**：豆瓣优先级最高，OpenLibrary 补充英文数据

## 依赖说明

- `playwright`：浏览器自动化，用于爬取动态页面
- `beautifulsoup4`：HTML 解析
- `aiohttp`：异步 HTTP 客户端，用于 API 调用和图片下载
- `pillow`：图片处理
