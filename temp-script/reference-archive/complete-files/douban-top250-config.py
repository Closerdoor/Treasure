# -*- coding: utf-8 -*-
"""
豆瓣电影 TOP250 爬虫配置文件
"""

# 基础 URL
BASE_URL = "https://movie.douban.com"
TOP250_URL = f"{BASE_URL}/top250"
LOGIN_URL = "https://accounts.douban.com/passport/login"

# 输出目录
OUTPUT_DIR = "output"
IMAGES_DIR = f"{OUTPUT_DIR}/images"

# 输出文件
COOKIES_FILE = f"{OUTPUT_DIR}/cookies.json"
PROGRESS_FILE = f"{OUTPUT_DIR}/progress.json"
MOVIES_JSON = f"{OUTPUT_DIR}/movies.json"
MOVIES_CSV = f"{OUTPUT_DIR}/movies.csv"
COMMENTS_JSON = f"{OUTPUT_DIR}/comments.json"
COMMENTS_CSV = f"{OUTPUT_DIR}/comments.csv"
REVIEWS_JSON = f"{OUTPUT_DIR}/reviews.json"
REVIEWS_CSV = f"{OUTPUT_DIR}/reviews.csv"

# 爬取配置
COMMENTS_PER_MOVIE = 20      # 每部电影爬取的短评数
REVIEWS_PER_MOVIE = 20       # 每部电影爬取的影评数

# 延迟配置（秒）
MIN_DELAY = 1.0
MAX_DELAY = 3.0
PAGE_DELAY = 2.0             # 每页之间的延迟
BATCH_DELAY = 5.0            # 每批次（10部电影）后的延迟

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 5.0

# 浏览器配置
HEADLESS = False             # 是否无头模式（False = 显示浏览器窗口）
SLOW_MO = 100                # 操作延迟（毫秒），便于观察
USE_CHROME = True            # 是否使用系统 Chrome（True = 使用系统安装的 Chrome）

# User-Agent 列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]
