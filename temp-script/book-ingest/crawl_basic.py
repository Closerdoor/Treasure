# -*- coding: utf-8 -*-
"""
基本信息爬取模块

爬取所有数据源 + 下载封面
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List

import config
from utils import Logger, generate_book_id
from progress import ProgressManager
from sources import DoubanBookCrawler, OpenLibraryAPI, BaikeCrawler, WikipediaCrawler
from sources.dangdang import DangdangCrawler
from sources.qidian import QidianCrawler
from merger import DataMerger
from downloaders import CoverDownloader


class BasicCrawler:
    """基本信息爬取"""
    
    def __init__(self):
        self.douban = None
        self.openlibrary = None
        self.dangdang = None
        self.qidian = None
        self.merger = DataMerger()
        self.cover_downloader = CoverDownloader()
        self.progress = ProgressManager()
        
    async def init(self):
        """初始化"""
        self.douban = DoubanBookCrawler()
        await self.douban.init_browser()
        await self.douban.ensure_login()
        self.openlibrary = OpenLibraryAPI()
        
        self.dangdang = DangdangCrawler(self.douban.page)
        self.qidian = QidianCrawler(self.douban.page)
        
        await self.cover_downloader.init()
        
        self.progress.load()
        
    async def close(self):
        """关闭"""
        if self.douban:
            await self.douban.close()
        await self.cover_downloader.close()
        
    async def run_test(self):
        """测试模式"""
        Logger.info("="*60)
        Logger.info("测试模式：爬取测试书籍")
        Logger.info("="*60)
        
        # 初始化浏览器
        await self.init()
        
        # 加载进度并初始化测试书籍
        self.progress.load()
        self.progress.init_books(config.TEST_BOOKS)
        
        for book in config.TEST_BOOKS:
            await self._crawl_book(book)
        
        await self.close()
            
    async def run_batch(self, book_list: List[Dict], batch_size: int = 10):
        """
        批量爬取
        
        Args:
            book_list: 书籍列表 [{douban_id, title}]
            batch_size: 每批数量
        """
        Logger.info("="*60)
        Logger.info(f"批量模式：爬取 {len(book_list)} 本书")
        Logger.info("="*60)
        
        self.progress.init_books(book_list)
        
        for i, book in enumerate(book_list):
            Logger.info(f"\n进度: {i+1}/{len(book_list)}")
            await self._crawl_book(book)
            
            if (i + 1) % batch_size == 0:
                Logger.info(f"\n已完成 {i+1} 本，暂停 {config.BATCH_DELAY} 秒...")
                await asyncio.sleep(config.BATCH_DELAY)
                
    async def _crawl_book(self, book: Dict):
        """
        爬取一本书
        
        Args:
            book: 书籍信息 {douban_id, title}
        """
        douban_id = book.get("douban_id")
        expected_title = book.get("title", "")
        
        if self.progress.is_book_completed(douban_id):
            Logger.info(f"已跳过（已完成）: {expected_title}")
            return
        
        Logger.info(f"\n正在爬取: {expected_title} ({douban_id})")
        
        raw_data = {}
        book_id = self.progress.get_book_id(douban_id)
        
        if not book_id:
            book_id = generate_book_id()
            self.progress.update_book_id(douban_id, book_id)
        
        self.progress.update_status(douban_id, "in_progress")
        
        # 1. 豆瓣读书
        if not self.progress.is_basic_completed(douban_id):
            try:
                self.progress.update_source_status(douban_id, "douban", "in_progress")
                
                douban_data = await self.douban.crawl_detail(douban_id, expected_title)
                raw_data["douban"] = douban_data
                
                self.merger.save_raw_data(book_id, "douban", douban_data)
                self.progress.update_source_status(douban_id, "douban", "done")
                
            except Exception as e:
                Logger.error(f"豆瓣爬取失败: {e}")
                self.progress.update_source_status(douban_id, "douban", "error")
        
        # 2. OpenLibrary
        isbn = raw_data.get("douban", {}).get("isbn", "")
        book_progress = self.progress.get_book_progress(douban_id)
        
        if isbn and book_progress.get("sources", {}).get("openlibrary") == "pending":
            try:
                self.progress.update_source_status(douban_id, "openlibrary", "in_progress")
                
                openlibrary_data = await self.openlibrary.get_book_data(isbn)
                if openlibrary_data:
                    raw_data["openlibrary"] = openlibrary_data
                    self.merger.save_raw_data(book_id, "openlibrary", openlibrary_data)
                
                self.progress.update_source_status(douban_id, "openlibrary", "done")
                
            except Exception as e:
                Logger.error(f"OpenLibrary 爬取失败: {e}")
                self.progress.update_source_status(douban_id, "openlibrary", "error")
        
        # 3. 百度百科
        title = raw_data.get("douban", {}).get("title", expected_title)
        book_progress = self.progress.get_book_progress(douban_id)
        
        if book_progress.get("sources", {}).get("baike") == "pending":
            try:
                self.progress.update_source_status(douban_id, "baike", "in_progress")
                
                baike = BaikeCrawler(self.douban.page)
                baike_url = await baike.search(title)
                
                if baike_url:
                    baike_data = await baike.get_detail(baike_url, title)
                    raw_data["baike"] = baike_data
                    self.merger.save_raw_data(book_id, "baike", baike_data)
                
                self.progress.update_source_status(douban_id, "baike", "done")
                
            except Exception as e:
                Logger.error(f"百度百科爬取失败: {e}")
                self.progress.update_source_status(douban_id, "baike", "error")
        
        # 4. Wikipedia
        book_progress = self.progress.get_book_progress(douban_id)
        
        if book_progress.get("sources", {}).get("wikipedia") == "pending":
            try:
                self.progress.update_source_status(douban_id, "wikipedia", "in_progress")
                
                wikipedia = WikipediaCrawler(self.douban.page)
                original_title = raw_data.get("douban", {}).get("title_original", "")
                wiki_url = await wikipedia.search(title, original_title)
                
                if wiki_url:
                    wiki_data = await wikipedia.get_detail(wiki_url)
                    raw_data["wikipedia"] = wiki_data
                    self.merger.save_raw_data(book_id, "wikipedia", wiki_data)
                
                self.progress.update_source_status(douban_id, "wikipedia", "done")
                
            except Exception as e:
                Logger.error(f"Wikipedia 爬取失败: {e}")
                self.progress.update_source_status(douban_id, "wikipedia", "error")
        
        # 5. 当当网（实体书）
        book_progress = self.progress.get_book_progress(douban_id)
        
        if isbn and book_progress.get("sources", {}).get("dangdang") == "pending":
            try:
                self.progress.update_source_status(douban_id, "dangdang", "in_progress")
                
                dangdang_url = await self.dangdang.search_by_isbn(isbn)
                if not dangdang_url:
                    dangdang_url = await self.dangdang.search_by_title(title)
                
                if dangdang_url:
                    dangdang_data = await self.dangdang.get_detail(dangdang_url)
                    raw_data["dangdang"] = dangdang_data
                    self.merger.save_raw_data(book_id, "dangdang", dangdang_data)
                
                self.progress.update_source_status(douban_id, "dangdang", "done")
                
            except Exception as e:
                Logger.error(f"当当网爬取失败: {e}")
                self.progress.update_source_status(douban_id, "dangdang", "error")
        
        # 6. 起点中文网（网络小说）
        book_progress = self.progress.get_book_progress(douban_id)
        baike_data = raw_data.get("baike", {})
        
        # 判断是否为网络小说（百度百科有"连载平台"字段）
        is_web_novel = baike_data.get("info", {}).get("连载平台") or "起点" in title or "修仙" in title
        
        if is_web_novel and book_progress.get("sources", {}).get("qidian") == "pending":
            try:
                self.progress.update_source_status(douban_id, "qidian", "in_progress")
                
                author = raw_data.get("douban", {}).get("authors", [""])[0] if raw_data.get("douban", {}).get("authors") else ""
                qidian_url = await self.qidian.search(title, author)
                
                if qidian_url:
                    qidian_data = await self.qidian.get_detail(qidian_url)
                    raw_data["qidian"] = qidian_data
                    self.merger.save_raw_data(book_id, "qidian", qidian_data)
                
                self.progress.update_source_status(douban_id, "qidian", "done")
                
            except Exception as e:
                Logger.error(f"起点中文网爬取失败: {e}")
                self.progress.update_source_status(douban_id, "qidian", "error")
        
        # 5. 数据合并
        merged_data = self.merger.merge(book_id, raw_data)
        self.merger.save_merged_data(book_id, merged_data)
        
        # 6. 下载封面
        cover_url = merged_data.get("cover_url")
        if cover_url:
            try:
                cover_path = await self.cover_downloader.download_cover(book_id, cover_url, source="douban")
                if cover_path:
                    Logger.success(f"封面下载成功: {cover_path}")
                    merged_data["cover_local"] = str(cover_path)
            except Exception as e:
                Logger.error(f"封面下载失败: {e}")
        
        # 7. 标记完成
        Logger.success(f"爬取完成: {expected_title}")
        self.progress.mark_basic_completed(douban_id)
        self.progress.mark_data_merged(douban_id)
        self.progress.update_status(douban_id, "completed")
