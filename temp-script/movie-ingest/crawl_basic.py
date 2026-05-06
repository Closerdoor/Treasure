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
python crawl_basic.py --top250
python crawl_basic.py --douban-id 1292052
"""
import asyncio
import json
import random
import sys
from pathlib import Path
from typing import Dict, Any

import config
from utils import Logger, generate_work_id
from progress import ProgressManager
from merger import DataMerger
from database import DatabaseManager
from sources.douban import DoubanCrawler
from sources.tmdb import TMDBClient
from sources.omdb import OMDbClient
from sources.baike import BaikeCrawler
from sources.wikipedia import WikipediaCrawler


class BasicCrawler:
    """基本信息爬取器"""
    
    def __init__(self):
        self.progress_manager = ProgressManager()
        self.merger = DataMerger(config.OUTPUT_DIR)
        self.db = DatabaseManager()
        
        # 爬虫实例
        self.douban: DoubanCrawler = None
        self.tmdb: TMDBClient = None
        self.omdb: OMDbClient = None
        self.baike: BaikeCrawler = None
        self.wikipedia: WikipediaCrawler = None
        
    async def init(self):
        """初始化"""
        Logger.info("正在初始化基本信息爬取器...")
        
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
        self.omdb = OMDbClient()
        
        # 初始化其他爬虫（共享豆瓣的 page）
        self.baike = BaikeCrawler(self.douban.page)
        self.wikipedia = WikipediaCrawler(self.douban.page)
        
        Logger.success("初始化完成")
        
    async def close(self):
        """清理资源"""
        if self.douban:
            await self.douban.close()
        if self.db:
            self.db.close()
            
    async def crawl_basic(self, douban_id: str, title: str = "") -> Dict[str, Any]:
        """
        爬取单部电影的基本信息
        
        Args:
            douban_id: 豆瓣 ID
            title: 电影标题（用于日志）
            
        Returns:
            基本信息数据
        """
        Logger.info(f"开始爬取基本信息: {title or douban_id}")
        
        raw_data = {}
        
        # 1. 豆瓣详情
        try:
            self.progress_manager.update_source_status(douban_id, "douban", "in_progress")
            
            douban_detail = await self.douban.crawl_detail(douban_id)
            raw_data["douban"] = douban_detail
            
            # 更新标题和 IMDb ID
            if douban_detail.get("title"):
                title = douban_detail["title"]
            imdb_id = douban_detail.get("imdb_id", "")
            
            self.progress_manager.update_source_status(douban_id, "douban", "done")
            
        except Exception as e:
            Logger.error(f"豆瓣爬取失败: {e}")
            self.progress_manager.update_source_status(douban_id, "douban", "error")
            imdb_id = ""
            
        # 2. TMDB 详情 + 演职员
        if imdb_id:
            try:
                self.progress_manager.update_source_status(douban_id, "tmdb", "in_progress")
                
                tmdb_data = await self.tmdb.get_all(imdb_id)
                raw_data["tmdb"] = tmdb_data
                
                self.progress_manager.update_source_status(douban_id, "tmdb", "done")
                
            except Exception as e:
                Logger.error(f"TMDB 爬取失败: {e}")
                self.progress_manager.update_source_status(douban_id, "tmdb", "error")
                
            # 3. OMDb
            try:
                self.progress_manager.update_source_status(douban_id, "omdb", "in_progress")
                
                omdb_data = await self.omdb.get_by_imdb(imdb_id)
                raw_data["omdb"] = omdb_data
                
                self.progress_manager.update_source_status(douban_id, "omdb", "done")
                
            except Exception as e:
                Logger.error(f"OMDb 爬取失败: {e}")
                self.progress_manager.update_source_status(douban_id, "omdb", "error")
        
        # 4. 百度百科
        try:
            self.progress_manager.update_source_status(douban_id, "baike", "in_progress")
            
            baike_data = await self.baike.crawl(title)
            raw_data["baike"] = baike_data
            
            self.progress_manager.update_source_status(douban_id, "baike", "done")
            
        except Exception as e:
            Logger.error(f"百度百科爬取失败: {e}")
            self.progress_manager.update_source_status(douban_id, "baike", "error")
            
        # 5. Wikipedia
        try:
            self.progress_manager.update_source_status(douban_id, "wikipedia", "in_progress")
            
            # 获取原名
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
        
    async def process_movie(self, douban_id: str, title: str = "") -> bool:
        """
        处理单部电影（爬取基本信息 + 合并 + 保存）
        
        Args:
            douban_id: 豆瓣 ID
            title: 电影标题
            
        Returns:
            是否成功
        """
        try:
            # 检查是否已完成基本信息爬取
            if self.progress_manager.is_basic_completed(douban_id):
                Logger.info(f"跳过已完成基本信息: {title or douban_id}")
                return True
                
            # 生成作品 ID
            work_id = self.progress_manager.get_work_id(douban_id)
            if not work_id:
                work_id = generate_work_id()
                self.progress_manager.update_work_id(douban_id, work_id)
            
            self.progress_manager.update_status(douban_id, "in_progress")
            
            # 爬取基本信息
            raw_data = await self.crawl_basic(douban_id, title)
            
            # 保存原始数据
            for source, data in raw_data.items():
                if data:
                    self.merger.save_raw_data(work_id, source, data)
            
            # 合并数据
            merged_data = self.merger.merge(work_id, raw_data)
            
            # 检测冲突
            conflicts = self.merger.detect_conflicts(raw_data)
            if conflicts:
                from reviewer import Reviewer
                reviewer = Reviewer(config.OUTPUT_DIR)
                reviewer.generate_review_file(work_id, title, conflicts)
                Logger.warning(f"检测到 {len(conflicts)} 个冲突，已生成审阅文件")
            
            # 保存合并数据
            self.merger.save_merged_data(work_id, merged_data)
            
            # 保存到数据库
            sources = [s for s, d in raw_data.items() if d]
            errors = []
            if not raw_data.get("douban"):
                errors.append("豆瓣爬取失败")
            if not raw_data.get("tmdb"):
                errors.append("TMDB 爬取失败")
            
            self.db.save_movie(work_id, merged_data, sources, errors)
            
            # 标记基本信息已完成
            self.progress_manager.mark_basic_completed(douban_id, True)
            self.progress_manager.update_status(douban_id, "completed")
            
            Logger.success(f"基本信息爬取完成: {title or douban_id}")
            return True
            
        except Exception as e:
            Logger.error(f"处理电影失败: {title or douban_id} - {e}")
            import traceback
            traceback.print_exc()
            return False
            
    async def run_test(self):
        """运行测试（单部电影）"""
        Logger.info("="*60)
        Logger.info("测试模式：爬取单部电影基本信息")
        Logger.info("="*60)
        
        test_movie = config.TEST_MOVIE
        douban_id = test_movie["douban_id"]
        title = test_movie["title"]
        
        # 初始化进度
        self.progress_manager.init_movies([{
            "douban_id": douban_id,
            "title": title
        }])
        
        # 处理电影
        success = await self.process_movie(douban_id, title)
        
        if success:
            Logger.success(f"测试完成！数据已保存到: {config.OUTPUT_DIR}/{self.progress_manager.get_movie_progress(douban_id).get('work_id', '')}/")
        else:
            Logger.error("测试失败")
            
    async def run_top250(self, batch_size: int = 10):
        """爬取豆瓣 TOP250"""
        Logger.info("="*60)
        Logger.info("TOP250 模式：爬取基本信息")
        Logger.info("="*60)
        
        # 连接数据库
        self.db.connect()
        self.db.create_table()
        
        # 获取 TOP250 列表
        Logger.info("正在爬取豆瓣 TOP250")
        movies = await self.douban.crawl_top250()
        
        if not movies:
            Logger.error("获取 TOP250 失败")
            return
            
        Logger.success(f"TOP250 爬取完成，共 {len(movies)} 部电影")
        
        # 初始化电影列表
        self.db.init_movies(movies)
        
        # 获取待爬取的电影
        pending_movies = self.db.get_pending_movies()
        
        Logger.info(f"待爬取: {len(pending_movies)} 部")
        
        # 分批处理
        total_batches = (len(pending_movies) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(pending_movies))
            batch = pending_movies[start_idx:end_idx]
            
            Logger.info(f"\n批次 {batch_idx + 1}/{total_batches}：处理 {len(batch)} 部电影")
            
            for movie in batch:
                movie_id = movie.get("id")
                douban_id = movie.get("douban_id")
                title = movie.get("title")
                
                try:
                    # 检查是否已完成基本信息爬取
                    if self.progress_manager.is_basic_completed(douban_id):
                        Logger.info(f"跳过已完成: {title}")
                        continue
                    
                    # 爬取基本信息
                    raw_data = await self.crawl_basic(douban_id, title)
                    
                    # 保存原始数据
                    for source, data in raw_data.items():
                        if data:
                            self.merger.save_raw_data(movie_id, source, data)
                    
                    # 合并数据
                    merged_data = self.merger.merge(movie_id, raw_data)
                    
                    # 检测冲突
                    conflicts = self.merger.detect_conflicts(raw_data)
                    if conflicts:
                        from reviewer import Reviewer
                        reviewer = Reviewer(config.OUTPUT_DIR)
                        reviewer.generate_review_file(movie_id, title, conflicts)
                    
                    # 保存合并数据
                    self.merger.save_merged_data(movie_id, merged_data)
                    
                    # 记录成功的数据源
                    sources = [s for s, d in raw_data.items() if d]
                    
                    # 记录错误
                    errors = []
                    if not raw_data.get("douban"):
                        errors.append("豆瓣爬取失败")
                    if not raw_data.get("tmdb"):
                        errors.append("TMDB API 超时")
                    
                    # 保存到数据库
                    self.db.save_movie(movie_id, merged_data, sources, errors)
                    
                    # 标记基本信息已完成
                    self.progress_manager.mark_basic_completed(douban_id, True)
                    
                    Logger.success(f"完成: {title}")
                    
                except Exception as e:
                    Logger.error(f"失败: {title} - {e}")
                    
                    # 记录错误
                    self.db.save_movie(
                        movie_id,
                        {"title": title},
                        [],
                        [str(e)]
                    )
                    
                    import traceback
                    traceback.print_exc()
                
                # 电影间延迟
                await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            # 批次间延迟
            if batch_idx < total_batches - 1:
                Logger.info(f"\n批次 {batch_idx + 1} 完成，休息 {config.BATCH_DELAY} 秒...")
                await asyncio.sleep(config.BATCH_DELAY)
        
        # 统计结果
        stats = self.db.get_statistics()
        
        Logger.info("="*60)
        Logger.info("基本信息爬取完成！")
        Logger.info(f"总计: {stats['total']} 部")
        Logger.info(f"成功: {stats['completed']} 部")
        Logger.info(f"部分成功: {stats['partial']} 部")
        Logger.info(f"待处理: {stats['pending']} 部")
        Logger.info("="*60)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="爬取电影基本信息")
    parser.add_argument("--test", action="store_true", help="测试模式（爬取单部电影）")
    parser.add_argument("--top250", action="store_true", help="爬取豆瓣 TOP250")
    parser.add_argument("--batch-size", type=int, default=10, help="每批处理数量（默认 10）")
    
    args = parser.parse_args()
    
    crawler = BasicCrawler()
    
    try:
        asyncio.run(crawler.init())
        
        if args.test:
            asyncio.run(crawler.run_test())
        elif args.top250:
            asyncio.run(crawler.run_top250(args.batch_size))
        else:
            parser.print_help()
    finally:
        asyncio.run(crawler.close())


if __name__ == "__main__":
    main()
