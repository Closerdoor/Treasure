# -*- coding: utf-8 -*-
from .douban_crawl import DoubanCrawler
from .openlibrary_crawl import OpenLibraryCrawler
from .baike_crawl import BaikeCrawler
from .wikipedia_crawl import WikipediaCrawler
from .goodreads_crawl import GoodreadsCrawler
from .dangdang_crawl import DangdangCrawler
from .qidian_crawl import QidianCrawler

__all__ = [
    'DoubanCrawler',
    'OpenLibraryCrawler',
    'BaikeCrawler',
    'WikipediaCrawler',
    'GoodreadsCrawler',
    'DangdangCrawler',
    'QidianCrawler',
]