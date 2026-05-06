# -*- coding: utf-8 -*-
"""
电影数据多源爬取工具配置文件
"""

# API Keys
TMDB_API_KEY = "3a4e78fb56ab8fda8244aa3c96272534"
OMDB_API_KEY = "2149f22c"

# 基础 URL
DOUBAN_BASE_URL = "https://movie.douban.com"
DOUBAN_LOGIN_URL = "https://accounts.douban.com/passport/login"
BAIKE_BASE_URL = "https://baike.baidu.com"
WIKIPEDIA_BASE_URL = "https://zh.wikipedia.org"
ROTTEN_TOMATOES_BASE_URL = "https://www.rottentomatoes.com"
METACRITIC_BASE_URL = "https://www.metacritic.com"

# 输出目录
OUTPUT_DIR = "data"
COOKIES_FILE = "cookies.json"
PROGRESS_FILE = "progress.json"
ERRORS_FILE = "errors.json"

# 爬取配置
COMMENTS_PER_SOURCE = 20
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
HEADLESS = False
SLOW_MO = 100
USE_CHROME = True
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# User-Agent 列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# 图片分类比例阈值
POSTER_RATIO_MIN = 0.6
POSTER_RATIO_MAX = 0.8

# 测试电影配置
TEST_MOVIE = {
    "douban_id": "1889243",
    "title": "星际穿越",
    "imdb_id": "tt0816692"
}
