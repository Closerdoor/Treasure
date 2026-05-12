# -*- coding: utf-8 -*-
"""
电影数据多源爬取工具配置文件
"""
import os
import sys
from pathlib import Path

# Windows UTF-8 兼容：必须在其他 import 之前设置
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

# 项目根目录
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent

# 数据目录（movie-ingest/data/）
DATA_DIR = SCRIPT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
STAGING_DIR = DATA_DIR / "staging"
ASSETS_DIR = DATA_DIR / "assets"
WORK_ASSETS_DIR = ASSETS_DIR / "works"
PEOPLE_ASSETS_DIR = ASSETS_DIR / "people"

# 数据库路径（项目级）
DB_PATH = REPO_ROOT / ".local" / "treasure.db"

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

# 输出目录（兼容旧代码）
OUTPUT_DIR = str(DATA_DIR)
COOKIES_FILE = str(SCRIPT_DIR / "cookies.json")
PROGRESS_FILE = str(SCRIPT_DIR / "progress.json")
ERRORS_FILE = str(SCRIPT_DIR / "errors.json")

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
