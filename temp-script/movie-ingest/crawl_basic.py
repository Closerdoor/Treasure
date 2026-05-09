# -*- coding: utf-8 -*-
"""
模块 1：爬取基本信息

功能：
- 豆瓣详情（标题、年份、评分、简介等）
- TMDB 详情 + 演职员
- OMDb 详情 + 评分
- 百度百科
- Wikipedia

使用方法：
python crawl_basic.py --test
python crawl_basic.py --douban-id 1292052

注意：爬取完成后生成 staging JSON 文件，不会自动写入数据库。
需要单独运行导入命令：python import_to_db.py --work-id 0101000001
"""
import os
import sys

# Windows UTF-8 兼容：必须在其他 import 之前设置
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

import asyncio
import json
import random
import io
from pathlib import Path
from typing import Dict, Any

import config
from utils import Logger, generate_work_id
from progress import ProgressManager
from merger import DataMerger
from database import TreasureDB
from sources.douban import DoubanCrawler
from sources.tmdb import TMDBClient
from sources.omdb import OMDbClient
from sources.baike import BaikeCrawler
from sources.wikipedia import WikipediaCrawler


class BasicCrawler:
    """基本信息爬取器"""
    
    def __init__(self):
        self.progress_manager = ProgressManager()
        self.merger = DataMerger()
        
        self.douban: DoubanCrawler = None
        self.tmdb: TMDBClient = None
        self.omdb: OMDbClient = None
        self.baike: BaikeCrawler = None
        self.wikipedia: WikipediaCrawler = None
        
    async def init(self):
        Logger.info("正在初始化基本信息爬取器...")
        
        Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        
        self.progress_manager.load()
        
        self.douban = DoubanCrawler()
        await self.douban.init_browser()
        await self.douban.ensure_login()
        
        self.tmdb = TMDBClient()
        self.omdb = OMDbClient()
        
        self.baike = BaikeCrawler(self.douban.page)
        self.wikipedia = WikipediaCrawler(self.douban.page)
        
        Logger.success("初始化完成")
        
    async def close(self):
        if self.douban:
            await self.douban.close()
            
    async def crawl_basic(self, douban_id: str, title: str = "") -> Dict[str, Any]:
        Logger.info(f"开始爬取基本信息: {title or douban_id}")
        
        raw_data = {}
        
        try:
            self.progress_manager.update_source_status(douban_id, "douban", "in_progress")
            
            douban_detail = await self.douban.crawl_detail(douban_id)
            raw_data["douban"] = douban_detail
            
            if douban_detail.get("title"):
                title = douban_detail["title"]
            imdb_id = douban_detail.get("imdb_id", "")
            
            self.progress_manager.update_source_status(douban_id, "douban", "done")
            
        except Exception as e:
            Logger.error(f"豆瓣爬取失败: {e}")
            self.progress_manager.update_source_status(douban_id, "douban", "error")
            imdb_id = ""
            
        if imdb_id:
            try:
                self.progress_manager.update_source_status(douban_id, "tmdb", "in_progress")
                
                tmdb_data = await self.tmdb.get_all(imdb_id)
                raw_data["tmdb"] = tmdb_data
                
                self.progress_manager.update_source_status(douban_id, "tmdb", "done")
                
            except Exception as e:
                Logger.error(f"TMDB 爬取失败: {e}")
                self.progress_manager.update_source_status(douban_id, "tmdb", "error")
                
            try:
                self.progress_manager.update_source_status(douban_id, "omdb", "in_progress")
                
                omdb_data = await self.omdb.get_by_imdb(imdb_id)
                raw_data["omdb"] = omdb_data
                
                self.progress_manager.update_source_status(douban_id, "omdb", "done")
                
            except Exception as e:
                Logger.error(f"OMDb 爬取失败: {e}")
                self.progress_manager.update_source_status(douban_id, "omdb", "error")
        
        try:
            self.progress_manager.update_source_status(douban_id, "baike", "in_progress")
            
            baike_data = await self.baike.crawl(title)
            raw_data["baike"] = baike_data
            
            self.progress_manager.update_source_status(douban_id, "baike", "done")
            
        except Exception as e:
            Logger.error(f"百度百科爬取失败: {e}")
            self.progress_manager.update_source_status(douban_id, "baike", "error")
            
        try:
            self.progress_manager.update_source_status(douban_id, "wikipedia", "in_progress")
            
            original_title = raw_data.get("douban", {}).get("original_title", "")
            if not original_title:
                original_title = raw_data.get("tmdb", {}).get("detail", {}).get("original_title", "")
            
            wikipedia_data = await self.wikipedia.crawl(title, original_title)
            raw_data["wikipedia"] = wikipedia_data
            
            self.progress_manager.update_source_status(douban_id, "wikipedia", "done")
            
        except Exception as e:
            Logger.error(f"Wikipedia 爬取失败: {e}")
            self.progress_manager.update_source_status(douban_id, "wikipedia", "error")
            
        return raw_data
        
    async def process_movie(self, douban_id: str, title: str = "", work_id: str = None) -> bool:
        """
        处理单部电影（爬取基本信息 + 合并 + 保存 staging JSON）
        
        注意：不会自动写入数据库，需要单独运行导入命令
        
        Args:
            douban_id: 豆瓣 ID
            title: 电影标题
            work_id: 作品 ID（可选，不提供则自动生成）
            
        Returns:
            是否成功
        """
        try:
            if self.progress_manager.is_basic_completed(douban_id):
                Logger.info(f"跳过已完成基本信息: {title or douban_id}")
                return True
                
            if not work_id:
                work_id = self.progress_manager.get_work_id(douban_id)
                if not work_id:
                    work_id = generate_work_id()
                    self.progress_manager.update_work_id(douban_id, work_id)
            
            self.progress_manager.update_status(douban_id, "in_progress")
            
            raw_data = await self.crawl_basic(douban_id, title)
            
            for source, data in raw_data.items():
                if data:
                    self.merger.save_raw_data(work_id, source, data)
            
            merged_data = self.merger.merge(work_id, raw_data)
            
            conflicts = self.merger.detect_conflicts(raw_data)
            if conflicts:
                from reviewer import Reviewer
                reviewer = Reviewer(config.OUTPUT_DIR)
                reviewer.generate_review_file(work_id, title, conflicts)
                Logger.warning(f"检测到 {len(conflicts)} 个冲突，已生成审阅文件")
            
            self.merger.save_merged_data(work_id, merged_data)
            
            self.progress_manager.mark_basic_completed(douban_id, True)
            self.progress_manager.update_status(douban_id, "completed")
            
            Logger.success(f"基本信息爬取完成: {title or douban_id}")
            Logger.info(f"Staging 文件已保存，如需导入数据库请运行: python import_to_db.py --work-id {work_id}")
            return True
            
        except Exception as e:
            Logger.error(f"处理电影失败: {title or douban_id} - {e}")
            import traceback
            traceback.print_exc()
            return False
            
    async def run_test(self):
        Logger.info("="*60)
        Logger.info("测试模式：爬取单部电影基本信息")
        Logger.info("="*60)
        
        test_movie = config.TEST_MOVIE
        douban_id = test_movie["douban_id"]
        title = test_movie["title"]
        
        self.progress_manager.init_movies([{
            "douban_id": douban_id,
            "title": title
        }])
        
        success = await self.process_movie(douban_id, title)
        
        if success:
            work_id = self.progress_manager.get_work_id(douban_id)
            Logger.success(f"测试完成！Staging 文件已保存到: .local/staging/video/movie/{work_id}.json")
        else:
            Logger.error("测试失败")
            
    async def run_by_douban_id(self, douban_id: str, title: str = "", work_id: str = None):
        """爬取指定豆瓣 ID 的电影"""
        Logger.info("="*60)
        Logger.info(f"爬取指定电影: {title or douban_id}")
        Logger.info("="*60)
        
        self.progress_manager.init_movies([{
            "douban_id": douban_id,
            "title": title or douban_id
        }])
        
        success = await self.process_movie(douban_id, title, work_id)
        
        if success:
            work_id = self.progress_manager.get_work_id(douban_id)
            Logger.success(f"爬取完成！Staging 文件已保存到: .local/staging/video/movie/{work_id}.json")
        else:
            Logger.error("爬取失败")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="爬取电影基本信息")
    parser.add_argument("--test", action="store_true", help="测试模式（爬取单部电影）")
    parser.add_argument("--douban-id", type=str, help="指定豆瓣 ID 爬取")
    parser.add_argument("--title", type=str, default="", help="电影标题（配合 --douban-id 使用）")
    parser.add_argument("--work-id", type=str, help="作品 ID（配合 --douban-id 使用）")
    
    args = parser.parse_args()
    
    crawler = BasicCrawler()
    
    try:
        asyncio.run(crawler.init())
        
        if args.test:
            asyncio.run(crawler.run_test())
        elif args.douban_id:
            asyncio.run(crawler.run_by_douban_id(args.douban_id, args.title, args.work_id))
        else:
            parser.print_help()
    finally:
        asyncio.run(crawler.close())


if __name__ == "__main__":
    main()