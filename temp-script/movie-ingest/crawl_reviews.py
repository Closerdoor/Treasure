# -*- coding: utf-8 -*-
"""
模块 2：爬取完整影评

功能：
- 豆瓣短评 + 影评
- TMDB 评论
- 烂番茄评论
- Metacritic 评论

使用方法：
python crawl_reviews.py --top250
python crawl_reviews.py --missing  # 只爬缺失评论的电影
python crawl_reviews.py --douban-id 1292052
"""
import asyncio
import json
import random
import sys
from pathlib import Path
from typing import Dict, Any, List

import config
from utils import Logger
from progress import ProgressManager
from merger import DataMerger
from database import DatabaseManager
from sources.douban import DoubanCrawler
from sources.tmdb import TMDBClient
from sources.rotten_tomatoes import RottenTomatoesCrawler
from sources.metacritic import MetacriticCrawler


class ReviewsCrawler:
    """影评爬取器"""
    
    def __init__(self):
        self.progress_manager = ProgressManager()
        self.merger = DataMerger(config.OUTPUT_DIR)
        self.db = DatabaseManager()
        
        # 爬虫实例
        self.douban: DoubanCrawler = None
        self.tmdb: TMDBClient = None
        self.rotten_tomatoes: RottenTomatoesCrawler = None
        self.metacritic: MetacriticCrawler = None
        
    async def init(self):
        """初始化"""
        Logger.info("正在初始化影评爬取器...")
        
        # 创建输出目录
        Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        
        # 加载进度
        self.progress_manager.load()
        
        # 初始化豆瓣爬虫
        self.douban = DoubanCrawler()
        await self.douban.init_browser()
        await self.douban.ensure_login()
        
        # 初始化 API 客户端
        self.tmdb = TMDBClient()
        
        # 初始化其他爬虫（共享豆瓣的 page）
        self.rotten_tomatoes = RottenTomatoesCrawler(self.douban.page)
        self.metacritic = MetacriticCrawler(self.douban.page)
        
        Logger.success("初始化完成")
        
    async def close(self):
        """清理资源"""
        if self.douban:
            await self.douban.close()
        if self.db:
            self.db.close()
            
    async def crawl_reviews(self, douban_id: str, title: str = "", original_title: str = "", year: int = 0, imdb_id: str = "") -> Dict[str, Any]:
        """
        爬取单部电影的评论
        
        Args:
            douban_id: 豆瓣 ID
            title: 电影标题
            original_title: 原名
            year: 年份
            imdb_id: IMDb ID
            
        Returns:
            评论数据
        """
        Logger.info(f"开始爬取影评: {title or douban_id}")
        
        raw_data = {}
        
        # 1. 豆瓣短评
        try:
            self.progress_manager.update_source_status(douban_id, "douban_comments", "in_progress")
            
            comments = await self.douban.crawl_comments(douban_id, config.COMMENTS_PER_SOURCE)
            raw_data["douban_comments"] = comments
            
            self.progress_manager.update_source_status(douban_id, "douban_comments", "done")
            
        except Exception as e:
            Logger.error(f"豆瓣短评爬取失败: {e}")
            self.progress_manager.update_source_status(douban_id, "douban_comments", "error")
            
        # 2. 豆瓣影评
        try:
            self.progress_manager.update_source_status(douban_id, "douban_reviews", "in_progress")
            
            reviews = await self.douban.crawl_reviews(douban_id, config.REVIEWS_PER_SOURCE)
            raw_data["douban_reviews"] = reviews
            
            self.progress_manager.update_source_status(douban_id, "douban_reviews", "done")
            
        except Exception as e:
            Logger.error(f"豆瓣影评爬取失败: {e}")
            self.progress_manager.update_source_status(douban_id, "douban_reviews", "error")
            
        # 3. TMDB 评论
        if imdb_id:
            try:
                self.progress_manager.update_source_status(douban_id, "tmdb_reviews", "in_progress")
                
                # 搜索 TMDB ID
                movie = await self.tmdb.search_by_imdb(imdb_id)
                if movie:
                    tmdb_id = movie.get("id", 0)
                    tmdb_reviews = await self.tmdb.get_reviews(tmdb_id, config.REVIEWS_PER_SOURCE)
                    raw_data["tmdb_reviews"] = tmdb_reviews
                
                self.progress_manager.update_source_status(douban_id, "tmdb_reviews", "done")
                
            except Exception as e:
                Logger.error(f"TMDB 评论爬取失败: {e}")
                self.progress_manager.update_source_status(douban_id, "tmdb_reviews", "error")
            
        # 4. 烂番茄评论
        try:
            self.progress_manager.update_source_status(douban_id, "rotten_tomatoes", "in_progress")
            
            rt_data = await self.rotten_tomatoes.crawl(original_title or title, year, config.REVIEWS_PER_SOURCE)
            raw_data["rotten_tomatoes"] = rt_data
            
            self.progress_manager.update_source_status(douban_id, "rotten_tomatoes", "done")
            
        except Exception as e:
            Logger.error(f"烂番茄爬取失败: {e}")
            self.progress_manager.update_source_status(douban_id, "rotten_tomatoes", "error")
            
        # 5. Metacritic 评论
        try:
            self.progress_manager.update_source_status(douban_id, "metacritic", "in_progress")
            
            mc_data = await self.metacritic.crawl(title, original_title, year, config.REVIEWS_PER_SOURCE)
            raw_data["metacritic"] = mc_data
            
            self.progress_manager.update_source_status(douban_id, "metacritic", "done")
            
        except Exception as e:
            Logger.error(f"Metacritic 爬取失败: {e}")
            self.progress_manager.update_source_status(douban_id, "metacritic", "error")
            
        return raw_data
        
    async def process_movie(self, movie: Dict) -> bool:
        """
        处理单部电影（爬取评论 + 保存）
        
        Args:
            movie: 电影信息（从数据库读取）
            
        Returns:
            是否成功
        """
        movie_id = movie.get("id")
        douban_id = movie.get("douban_id")
        title = movie.get("title")
        
        try:
            # 检查是否已完成评论爬取
            if self.progress_manager.is_reviews_completed(douban_id):
                Logger.info(f"跳过已完成评论: {title}")
                return True
            
            # 从数据库读取基本信息
            basic_info = self.db.get_movie_basic_info(movie_id)
            if not basic_info:
                Logger.error(f"未找到基本信息: {title}")
                return False
                
            original_title = basic_info.get("original_title", "")
            year = basic_info.get("year", 0)
            imdb_id = basic_info.get("identifiers_json", {}).get("imdb", "")
            
            # 爬取评论
            raw_data = await self.crawl_reviews(
                douban_id, title, original_title, year, imdb_id
            )
            
            # 保存原始数据
            for source, data in raw_data.items():
                if data:
                    self.merger.save_raw_data(movie_id, f"reviews_{source}", data)
            
            # 合并评论数据
            reviews_data = self._merge_reviews(raw_data)
            
            # 更新数据库
            self.db.update_movie_reviews(movie_id, reviews_data)
            
            # 标记评论已完成
            self.progress_manager.mark_reviews_completed(douban_id, True)
            
            Logger.success(f"评论爬取完成: {title}")
            return True
            
        except Exception as e:
            Logger.error(f"处理电影失败: {title} - {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def _merge_reviews(self, raw_data: Dict) -> Dict:
        """合并评论数据"""
        reviews = {
            "douban_comments": raw_data.get("douban_comments", []),
            "douban_reviews": raw_data.get("douban_reviews", []),
            "tmdb": raw_data.get("tmdb_reviews", []),
            "rotten_tomatoes": raw_data.get("rotten_tomatoes", {}).get("reviews", []),
            "metacritic": raw_data.get("metacritic", {}).get("reviews", [])
        }
        
        return reviews
        
    async def run_test(self):
        """运行测试（单部电影）"""
        Logger.info("="*60)
        Logger.info("测试模式：爬取单部电影评论")
        Logger.info("="*60)
        
        test_movie = config.TEST_MOVIE
        douban_id = test_movie["douban_id"]
        title = test_movie["title"]
        
        # 从数据库读取电影信息
        self.db.connect()
        movie = self.db.get_movie_by_douban_id(douban_id)
        
        if not movie:
            Logger.error(f"未找到电影: {title}")
            return
            
        success = await self.process_movie(movie)
        
        if success:
            Logger.success("测试完成！")
        else:
            Logger.error("测试失败")
            
    async def run_missing(self):
        """爬取缺失评论的电影"""
        Logger.info("="*60)
        Logger.info("补爬模式：爬取缺失评论的电影")
        Logger.info("="*60)
        
        self.db.connect()
        
        # 获取缺失评论的电影
        movies = self.db.get_movies_missing_reviews()
        
        if not movies:
            Logger.info("所有电影都已爬取评论")
            return
            
        Logger.info(f"找到 {len(movies)} 部电影需要爬取评论")
        
        for movie in movies:
            success = await self.process_movie(movie)
            
            # 电影间延迟
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        Logger.success("补爬完成！")
        
    async def run_top250(self, batch_size: int = 10):
        """爬取豆瓣 TOP250 的评论"""
        Logger.info("="*60)
        Logger.info("TOP250 模式：爬取评论")
        Logger.info("="*60)
        
        self.db.connect()
        
        # 获取所有电影
        movies = self.db.get_all_movies()
        
        if not movies:
            Logger.error("未找到电影，请先运行 crawl_basic.py")
            return
            
        Logger.info(f"总计 {len(movies)} 部电影")
        
        # 分批处理
        total_batches = (len(movies) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(movies))
            batch = movies[start_idx:end_idx]
            
            Logger.info(f"\n批次 {batch_idx + 1}/{total_batches}：处理 {len(batch)} 部电影")
            
            for movie in batch:
                await self.process_movie(movie)
                
                # 电影间延迟
                await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            # 批次间延迟
            if batch_idx < total_batches - 1:
                Logger.info(f"\n批次 {batch_idx + 1} 完成，休息 {config.BATCH_DELAY} 秒...")
                await asyncio.sleep(config.BATCH_DELAY)
        
        Logger.success("评论爬取完成！")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="爬取电影评论")
    parser.add_argument("--test", action="store_true", help="测试模式（爬取单部电影）")
    parser.add_argument("--top250", action="store_true", help="爬取豆瓣 TOP250 的评论")
    parser.add_argument("--missing", action="store_true", help="只爬缺失评论的电影")
    parser.add_argument("--batch-size", type=int, default=10, help="每批处理数量（默认 10）")
    
    args = parser.parse_args()
    
    crawler = ReviewsCrawler()
    
    try:
        asyncio.run(crawler.init())
        
        if args.test:
            asyncio.run(crawler.run_test())
        elif args.top250:
            asyncio.run(crawler.run_top250(args.batch_size))
        elif args.missing:
            asyncio.run(crawler.run_missing())
        else:
            parser.print_help()
    finally:
        asyncio.run(crawler.close())


if __name__ == "__main__":
    main()
