# Browser Config

> Purpose: 记录项目中 Playwright 浏览器的统一配置，确保所有需要浏览器自动化的脚本使用一致的配置。
> Status: active
> Scope: 浏览器启动参数、代理配置、重试规则、Cookie 管理
> Out of scope: 具体爬虫逻辑、页面解析规则
> Update triggers: 浏览器配置变化、代理地址变化、重试规则变化
> Priority: 4

## 统一配置规则

**所有需要访问浏览器的脚本都必须使用本文档定义的配置，不得自行定义不同的浏览器参数。**

---

## 浏览器启动配置

### 基础参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `headless` | `False` | 显示浏览器窗口，便于手动登录和调试 |
| `slow_mo` | `100` | 操作延迟 100ms，避免被反爬检测 |
| `viewport` | `1920x1080` | 视口大小 |
| `user_agent` | 随机选择 | 从预设列表中随机选择，模拟真实用户 |

### 浏览器选择

| 参数 | 值 | 说明 |
|------|-----|------|
| `USE_CHROME` | `True` | 优先使用系统安装的 Chrome |
| `CHROME_PATH` | `C:\Program Files\Google\Chrome\Application\chrome.exe` | Chrome 可执行文件路径 |

### User-Agent 列表

```python
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]
```

---

## 代理配置

### 基础参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `PROXY_ENABLED` | `True` | 启用代理 |
| `PROXY_URL` | `http://127.0.0.1:7890` | 本地代理地址 |

### 代理使用规则

1. **默认行为**：所有网络请求默认通过代理
2. **重试规则**：如果访问失败，自动加上代理地址重试
3. **重试次数**：最多重试 3 次

---

## 延迟配置

| 参数 | 值 | 说明 |
|------|-----|------|
| `MIN_DELAY` | `2.0` | 最小延迟（秒） |
| `MAX_DELAY` | `5.0` | 最大延迟（秒） |
| `PAGE_DELAY` | `4.0` | 页面间延迟（秒） |
| `BATCH_DELAY` | `10.0` | 批次间延迟（秒） |

---

## Cookie 管理

### 存储位置

```
temp-script/movie-ingest/cookies.json
```

### 管理规则

1. **首次运行**：打开浏览器，等待手动登录
2. **登录成功后**：自动保存 Cookie 到 `cookies.json`
3. **后续运行**：自动加载已保存的 Cookie
4. **Cookie 过期**：重新打开登录页，等待手动登录

---

## 启动代码模板

所有需要浏览器自动化的脚本应使用以下模板：

```python
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import random

# 配置
HEADLESS = False
SLOW_MO = 100
USE_CHROME = True
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROXY_ENABLED = True
PROXY_URL = "http://127.0.0.1:7890"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # ... 其他 User-Agent
]

async def init_browser(self):
    """初始化浏览器"""
    self.playwright = await async_playwright().start()
    
    # 启动浏览器
    if USE_CHROME:
        self.browser = await self.playwright.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO,
            executable_path=CHROME_PATH
        )
    else:
        self.browser = await self.playwright.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO
        )
    
    # 创建上下文
    user_agent = random.choice(USER_AGENTS)
    self.context = await self.browser.new_context(
        user_agent=user_agent,
        viewport={"width": 1920, "height": 1080}
    )
    
    # 创建页面
    self.page = await self.context.new_page()

async def close(self):
    """关闭浏览器"""
    if self.browser:
        await self.browser.close()
    if self.playwright:
        await self.playwright.stop()
```

---

## 访问失败重试规则

**强制规则**：如果页面访问失败，必须自动加上代理地址重试。

### 重试逻辑模板

```python
MAX_RETRIES = 3
RETRY_DELAY = 5.0

async def goto_with_retry(self, url: str) -> bool:
    """带重试的页面访问"""
    for attempt in range(MAX_RETRIES):
        try:
            # 第一次尝试：不使用代理
            if attempt == 0:
                await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                return True
            else:
                # 重试：使用代理
                await self.page.goto(
                    url, 
                    timeout=60000, 
                    wait_until="domcontentloaded"
                )
                return True
        except Exception as e:
            Logger.warning(f"访问失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
    
    Logger.error(f"访问失败，已重试 {MAX_RETRIES} 次: {url}")
    return False
```

### API 请求重试模板

```python
async def fetch_with_retry(self, url: str, params: dict = None) -> Optional[dict]:
    """带重试的 API 请求"""
    proxy = PROXY_URL if PROXY_ENABLED else None
    
    for attempt in range(MAX_RETRIES):
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params, proxy=proxy) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        Logger.warning(f"API 错误 (尝试 {attempt + 1}): {response.status}")
        except Exception as e:
            Logger.warning(f"请求失败 (尝试 {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
    
    return None
```

---

## 现有实现参考

当前项目中已实现此配置的脚本：

- `temp-script/movie-ingest/sources/douban.py` - 豆瓣爬虫
- `temp-script/movie-ingest/sources/baike.py` - 百度百科爬虫
- `temp-script/movie-ingest/sources/wikipedia.py` - Wikipedia 爬虫
- `temp-script/movie-ingest/sources/rotten_tomatoes.py` - 烂番茄爬虫
- `temp-script/movie-ingest/sources/metacritic.py` - Metacritic 爬虫

---

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026-05-09 | 初始版本，从 movie-ingest 提取统一配置 |
