# -*- coding: utf-8 -*-
"""
模块 2：爬取完整影评

功能：
- 豆瓣短评 + 影评
- TMDB 评论
- 烂番茄评论
- Metacritic 评论

使用方法：
python crawl_reviews.py --work-id 0101000001
python crawl_reviews.py --all
python crawl_reviews.py --missing

注意：爬取完成后更新 staging JSON 文件，不会自动写入数据库。
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
from typing import Dict, Any, List

import config
from utils import Logger
from progress import ProgressManager
from merger import DataMerger
from sources.douban import DoubanCrawler
from sources.tmdb import TMDBClient
from sources.rotten_tomatoes import RottenTomatoesCrawler
from sources.metacritic import MetacriticCrawler


class ReviewsCrawler:
    """影评爬取器"""
    
    def __init__(self):
        self.progress_manager = ProgressManager()
        self.merger = DataMerger()
        
        self.douban: DoubanCrawler = None
        self.tmdb: TMDBClient = None
        self.rotten_tomatoes: RottenTomatoesCrawler = None
        self.metacritic: MetacriticCrawler = None
        
    async def init(self):
        Logger.info("正在初始化影评爬取器...")
        
        Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        
        self.progress_manager.load()
        
        self.douban = DoubanCrawler()
        await self.douban.init_browser()
        await self.douban.ensure_login()
        
        self.tmdb = TMDBClient()
        
        self.rotten_tomatoes = RottenTomatoesCrawler(self.douban.page)
        self.metacritic = MetacriticCrawler(self.douban.page)
        
        Logger.success("初始化完成")
        
    async def close(self):
        if self.douban:
            await self.douban.close()
    
    def load_staging_file(self, work_id: str) -> Dict[str, Any]:
        """加载 staging JSON 文件"""
        staging_dir = Path(__file__).parent.parent.parent / ".local" / "staging" / "video" / "movie"
        filepath = staging_dir / f"{work_id}.json"
        if not filepath.exists():
            raise FileNotFoundError(f"Staging 文件不存在: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def save_staging_file(self, work_id: str, data: Dict[str, Any]):
        """保存 staging JSON 文件"""
        staging_dir = Path(__file__).parent.parent.parent / ".local" / "staging" / "video" / "movie"
        staging_dir.mkdir(parents=True, exist_ok=True)
        filepath = staging_dir / f"{work_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, ensure_ascii=False, indent=2, fp=f)
        Logger.success(f"已更新 staging 文件: {filepath}")
            
    async def crawl_reviews(self, work_id: str, title: str = "", original_title: str = "", 
                            year: int = 0, imdb_id: str = "") -> Dict[str, Any]:
        Logger.info(f"开始爬取影评: {title or work_id}")
        
        raw_data = {}
        
        try:
            self.progress_manager.update_source_status(work_id, "douban_comments", "in_progress")
            
            comments = await self.douban.crawl_comments(work_id, config.COMMENTS_PER_SOURCE)
            raw_data["douban_comments"] = comments
            
            self.progress_manager.update_source_status(work_id, "douban_comments", "done")
            
        except Exception as e:
            Logger.error(f"豆瓣短评爬取失败: {e}")
            self.progress_manager.update_source_status(work_id, "douban_comments", "error")
            
        try:
            self.progress_manager.update_source_status(work_id, "douban_reviews", "in_progress")
            
            reviews = await self.douban.crawl_reviews(work_id, config.REVIEWS_PER_SOURCE)
            raw_data["douban_reviews"] = reviews
            
            self.progress_manager.update_source_status(work_id, "douban_reviews", "done")
            
        except Exception as e:
            Logger.error(f"豆瓣影评爬取失败: {e}")
            self.progress_manager.update_source_status(work_id, "douban_reviews", "error")
            
        if imdb_id:
            try:
                self.progress_manager.update_source_status(work_id, "tmdb_reviews", "in_progress")
                
                movie = await self.tmdb.search_by_imdb(imdb_id)
                if movie:
                    tmdb_id = movie.get("id", 0)
                    tmdb_reviews = await self.tmdb.get_reviews(tmdb_id, config.REVIEWS_PER_SOURCE)
                    raw_data["tmdb_reviews"] = tmdb_reviews
                
                self.progress_manager.update_source_status(work_id, "tmdb_reviews", "done")
                
            except Exception as e:
                Logger.error(f"TMDB 评论爬取失败: {e}")
                self.progress_manager.update_source_status(work_id, "tmdb_reviews", "error")
            
        try:
            self.progress_manager.update_source_status(work_id, "rotten_tomatoes", "in_progress")
            
            rt_data = await self.rotten_tomatoes.crawl(original_title or title, year, config.REVIEWS_PER_SOURCE)
            raw_data["rotten_tomatoes"] = rt_data
            
            self.progress_manager.update_source_status(work_id, "rotten_tomatoes", "done")
            
        except Exception as e:
            Logger.error(f"烂番茄爬取失败: {e}")
            self.progress_manager.update_source_status(work_id, "rotten_tomatoes", "error")
            
        try:
            self.progress_manager.update_source_status(work_id, "metacritic", "in_progress")
            
            mc_data = await self.metacritic.crawl(title, original_title, year, config.REVIEWS_PER_SOURCE)
            raw_data["metacritic"] = mc_data
            
            self.progress_manager.update_source_status(work_id, "metacritic", "done")
            
        except Exception as e:
            Logger.error(f"Metacritic 爬取失败: {e}")
            self.progress_manager.update_source_status(work_id, "metacritic", "error")
            
        return raw_data
        
    async def process_work(self, work_id: str) -> bool:
        try:
            data = self.load_staging_file(work_id)
            
            title = data.get("title", "")
            original_title = data.get("originalTitle", "")
            year = data.get("year", 0)
            imdb_id = data.get("imdbId", "")
            
            raw_data = await self.crawl_reviews(work_id, title, original_title, year, imdb_id)
            
            reviews = []
            
            for c in raw_data.get("douban_comments", []):
                reviews.append({
                    "author": c.get("author"),
                    "source": "豆瓣短评",
                    "date": c.get("date"),
                    "content": c.get("content"),
                    "url": None,
                    "title": None
                })
            
            for r in raw_data.get("douban_reviews", []):
                reviews.append({
                    "author": r.get("author"),
                    "source": "豆瓣长评",
                    "date": r.get("date"),
                    "content": r.get("content"),
                    "url": r.get("url"),
                    "title": r.get("title")
                })
            
            for r in raw_data.get("tmdb_reviews", []):
                reviews.append({
                    "author": r.get("author"),
                    "source": "TMDB",
                    "date": r.get("date"),
                    "content": r.get("content"),
                    "url": r.get("url"),
                    "title": None
                })
            
            for r in raw_data.get("rotten_tomatoes", {}).get("reviews", []):
                reviews.append({
                    "author": r.get("author"),
                    "source": f"烂番茄 · {r.get('source', '')}",
                    "date": r.get("date"),
                    "content": r.get("content"),
                    "url": r.get("url"),
                    "title": None
                })
            
            for r in raw_data.get("metacritic", {}).get("reviews", []):
                reviews.append({
                    "author": r.get("author"),
                    "source": f"Metacritic · {r.get('source', '')}",
                    "date": r.get("date"),
                    "content": r.get("content"),
                    "url": r.get("url"),
                    "title": None
                })
            
            data["reviews"] = reviews
            self.save_staging_file(work_id, data)
            
            Logger.success(f"评论爬取完成: {title} ({len(reviews)} 条)")
            return True
            
        except FileNotFoundError as e:
            Logger.error(str(e))
            return False
        except Exception as e:
            Logger.error(f"处理失败: {work_id} - {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="爬取电影评论")
    parser.add_argument("--work-id", type=str, help="指定作品 ID")
    parser.add_argument("--all", action="store_true", help="爬取所有 staging 文件")
    
    args = parser.parse_args()
    
    crawler = ReviewsCrawler()
    
    try:
        asyncio.run(crawler.init())
        
        if args.work_id:
            asyncio.run(crawler.process_work(args.work_id))
        elif args.all:
            staging_dir = Path(__file__).parent.parent.parent / ".local" / "staging" / "video" / "movie"
            for filepath in sorted(staging_dir.glob("*.json")):
                work_id = filepath.stem
                asyncio.run(crawler.process_work(work_id))
                asyncio.sleep(random.uniform(2, 5))
        else:
            parser.print_help()
    finally:
        asyncio.run(crawler.close())


if __name__ == "__main__":
    main()
