# -*- coding: utf-8 -*-
"""
书籍数据多源爬取工具配置文件
"""
import os
import sys
from pathlib import Path

# Windows UTF-8 兼容
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

# 基础 URL
DOUBAN_BASE_URL = "https://book.douban.com"
DOUBAN_LOGIN_URL = "https://accounts.douban.com/passport/login"
OPENLIBRARY_BASE_URL = "https://openlibrary.org"
BAIKE_BASE_URL = "https://baike.baidu.com"
WIKIPEDIA_BASE_URL = "https://zh.wikipedia.org"
GOODREADS_BASE_URL = "https://www.goodreads.com"
DANGDANG_BASE_URL = "http://www.dangdang.com"
BOOKCHINA_BASE_URL = "http://www.bookschina.com"

# 输出目录
OUTPUT_DIR = Path(__file__).parent / "data"
COOKIES_FILE = OUTPUT_DIR / "cookies.json"  # book-ingest 自己的 cookies
PROGRESS_FILE = OUTPUT_DIR / "progress.json"
ERRORS_FILE = OUTPUT_DIR / "errors.json"

# 爬取配置
REVIEWS_PER_SOURCE = 20

# 延迟配置（秒）
MIN_DELAY = 2.0
MAX_DELAY = 5.0
PAGE_DELAY = 4.0
BATCH_DELAY = 10.0

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 5.0

# 图片下载配置
IMAGE_DOWNLOAD_CONCURRENCY = 5
IMAGE_TIMEOUT = 30

# 代理配置
PROXY_ENABLED = True
PROXY_URL = "http://127.0.0.1:7890"

# 浏览器配置
HEADLESS = True
SLOW_MO = 50
USE_CHROME = False
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SKIP_LOGIN = True  # 跳过登录（豆瓣可直接访问时启用）

# User-Agent 列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# ID 配置
BOOK_ID_PREFIX = "0200"  # 书籍 ID 前缀（02=书模块，00=无子模块）
BOOK_SERIES_ID_PREFIX = "0299"  # 系列 ID 前缀
PERSON_ID_PREFIX = "p"

# 测试书籍配置
TEST_BOOKS = [
    {"douban_id": "6082808", "title": "百年孤独"},
    {"douban_id": "1008145", "title": "围城"},
    {"douban_id": "4192766", "title": "凡人修仙传"},
]
