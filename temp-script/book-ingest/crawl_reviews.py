# -*- coding: utf-8 -*-
"""
书评爬取模块
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List

import config
from utils import Logger
from progress import ProgressManager
from sources import DoubanBookCrawler
from merger import DataMerger


class ReviewsCrawler:
    """书评爬取"""
    
    def __init__(self):
        self.douban = DoubanBookCrawler()
        self.merger = DataMerger()
        self.progress = ProgressManager()
        
    async def init(self):
        """初始化"""
        await self.douban.init_browser()
        await self.douban.ensure_login()
        self.progress.load()
        
    async def close(self):
        """关闭"""
        await self.douban.close()
        
    async def run_test(self):
        """测试模式"""
        Logger.info("="*60)
        Logger.info("测试模式：爬取测试书评")
        Logger.info("="*60)
        
        for book in config.TEST_BOOKS:
            await self._crawl_reviews(book)
            
    async def run_batch(self, book_list: List[Dict]):
        """批量爬取书评"""
        Logger.info("="*60)
        Logger.info(f"批量模式：爬取书评")
        Logger.info("="*60)
        
        for book in book_list:
            await self._crawl_reviews(book)
            
    async def _crawl_reviews(self, book: Dict):
        """爬取书评"""
        douban_id = book.get("douban_id")
        title = book.get("title", "")
        
        book_progress = self.progress.get_book_progress(douban_id)
        if not book_progress:
            Logger.warning(f"未找到进度记录: {title}")
            return
        
        if book_progress.get("reviews_crawled"):
            Logger.info(f"已跳过（书评已爬取）: {title}")
            return
        
        book_id = book_progress.get("book_id")
        if not book_id:
            Logger.warning(f"未找到书籍 ID: {title}")
            return
        
        Logger.info(f"\n正在爬取书评: {title}")
        
        reviews = []
        
        # 爬取短评
        try:
            comments = await self.douban.crawl_comments(douban_id, config.REVIEWS_PER_SOURCE)
            reviews.extend(comments)
        except Exception as e:
            Logger.error(f"短评爬取失败: {e}")
        
        # 爬取长评
        try:
            long_reviews = await self.douban.crawl_reviews(douban_id, config.REVIEWS_PER_SOURCE)
            reviews.extend(long_reviews)
        except Exception as e:
            Logger.error(f"长评爬取失败: {e}")
        
        # 保存书评
        if reviews:
            raw_file = Path(config.OUTPUT_DIR) / book_id / "raw" / "reviews.json"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text(
                json.dumps(reviews, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            
            Logger.success(f"已保存 {len(reviews)} 条书评")
            self.progress.mark_reviews_completed(douban_id)
        else:
            Logger.warning(f"未获取到书评")