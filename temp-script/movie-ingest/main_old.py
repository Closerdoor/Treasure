# -*- coding: utf-8 -*-
"""
电影数据多源爬取工具 - 主入口

使用方法：
1. 安装依赖：pip install playwright beautifulsoup4 aiohttp pillow
2. 安装浏览器：playwright install chromium
3. 运行脚本：python main.py
4. 首次运行会打开浏览器，手动登录豆瓣后按回车继续
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
from downloader import ImageDownloader
from reviewer import Reviewer
from database import DatabaseManager
from sources.douban import DoubanCrawler
from sources.tmdb import TMDBClient
from sources.omdb import OMDbClient
from sources.baike import BaikeCrawler
from sources.wikipedia import WikipediaCrawler
from sources.rotten_tomatoes import RottenTomatoesCrawler
from sources.metacritic import MetacriticCrawler


class MovieIngestPipeline:
    """电影数据爬取流水线"""
    
    def __init__(self):
        self.progress_manager = ProgressManager()
        self.merger = DataMerger(config.OUTPUT_DIR)
        self.downloader = ImageDownloader(config.OUTPUT_DIR)
        self.reviewer = Reviewer(config.OUTPUT_DIR)
        self.db = DatabaseManager()
        
        # 爬虫实例
        self.douban: DoubanCrawler = None
        self.tmdb: TMDBClient = None
        self.omdb: OMDbClient = None
        self.baike: BaikeCrawler = None
        self.wikipedia: WikipediaCrawler = None
        self.rotten_tomatoes: RottenTomatoesCrawler = None
        self.metacritic: MetacriticCrawler = None
        
    async def init(self):
        """初始化"""
        Logger.info("正在初始化...")
        
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
        self.rotten_tomatoes = RottenTomatoesCrawler(self.douban.page)
        self.metacritic = MetacriticCrawler(self.douban.page)
        
        Logger.success("初始化完成")
        
    async def close(self):
        """清理资源"""
        if self.douban:
            await self.douban.close()
        if self.db:
            self.db.close()
            
    async def crawl_movie(self, douban_id: str, title: str = "") -> Dict[str, Any]:
        """
        爬取单部电影的所有数据
        
        Args:
            douban_id: 豆瓣 ID
            title: 电影标题（用于日志）
            
        Returns:
            完整数据
        """
        Logger.info(f"开始爬取电影: {title or douban_id}")
        
        raw_data = {}
        
        # 1. 豆瓣
        try:
            self.progress_manager.update_source_status(douban_id, "douban", "in_progress")
            
            # 详情
            douban_detail = await self.douban.crawl_detail(douban_id)
            raw_data["douban"] = douban_detail
            
            # 短评
            comments = await self.douban.crawl_comments(douban_id, config.COMMENTS_PER_SOURCE)
            raw_data["douban"]["comments"] = comments
            
            # 影评
            reviews = await self.douban.crawl_reviews(douban_id, config.REVIEWS_PER_SOURCE)
            raw_data["douban"]["reviews"] = reviews
            
            # 图片：跳过豆瓣图片页面（容易触发反爬虫），只使用主海报和 TMDB 图片
            # images = await self.douban.crawl_images(douban_id)
            raw_data["douban"]["images"] = {
                "posters": [],
                "stills": [],
                "posters_total": 0,
                "stills_total": 0
            }
            
            # 更新标题和 IMDb ID
            if douban_detail.get("title"):
                title = douban_detail["title"]
            imdb_id = douban_detail.get("imdb_id", "")
            
            self.progress_manager.update_source_status(douban_id, "douban", "done")
            
        except Exception as e:
            Logger.error(f"豆瓣爬取失败: {e}")
            self.progress_manager.update_source_status(douban_id, "douban", "error")
            imdb_id = ""
            
        # 2. TMDB
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
            
            # 使用中文标题搜索
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
            
        # 6. 烂番茄
        try:
            self.progress_manager.update_source_status(douban_id, "rotten_tomatoes", "in_progress")
            
            year = raw_data.get("douban", {}).get("year", 0)
            if isinstance(year, str):
                year = int(year) if year.isdigit() else 0
            
            # 获取原名
            original_title = raw_data.get("douban", {}).get("original_title", "")
            if not original_title:
                original_title = raw_data.get("tmdb", {}).get("detail", {}).get("original_title", "")
                
            rt_data = await self.rotten_tomatoes.crawl(original_title or title, year, config.REVIEWS_PER_SOURCE)
            raw_data["rotten_tomatoes"] = rt_data
            
            self.progress_manager.update_source_status(douban_id, "rotten_tomatoes", "done")
            
        except Exception as e:
            Logger.error(f"烂番茄爬取失败: {e}")
            self.progress_manager.update_source_status(douban_id, "rotten_tomatoes", "error")
            
        # 7. Metacritic
        try:
            self.progress_manager.update_source_status(douban_id, "metacritic", "in_progress")
            
            year = raw_data.get("douban", {}).get("year", 0)
            if isinstance(year, str):
                year = int(year) if year.isdigit() else 0
            
            # 获取原名（Metacritic 是英文站点，优先使用原名）
            original_title = raw_data.get("douban", {}).get("original_title", "")
            if not original_title:
                original_title = raw_data.get("tmdb", {}).get("detail", {}).get("original_title", "")
                
            mc_data = await self.metacritic.crawl(title, original_title, year, config.REVIEWS_PER_SOURCE)
            raw_data["metacritic"] = mc_data
            
            self.progress_manager.update_source_status(douban_id, "metacritic", "done")
            
        except Exception as e:
            Logger.error(f"Metacritic 爬取失败: {e}")
            self.progress_manager.update_source_status(douban_id, "metacritic", "error")
            
        return raw_data
        
    async def process_movie(self, douban_id: str, title: str = "") -> bool:
        """
        处理单部电影（爬取 + 合并 + 下载）
        
        Args:
            douban_id: 豆瓣 ID
            title: 电影标题
            
        Returns:
            是否成功
        """
        try:
            # 检查是否已完成
            if self.progress_manager.is_movie_completed(douban_id):
                Logger.info(f"跳过已完成: {title or douban_id}")
                return True
                
            # 生成作品 ID
            work_id = generate_work_id()
            self.progress_manager.update_work_id(douban_id, work_id)
            self.progress_manager.update_status(douban_id, "in_progress")
            
            # 爬取数据
            raw_data = await self.crawl_movie(douban_id, title)
            
            # 保存原始数据
            for source, data in raw_data.items():
                if data:
                    self.merger.save_raw_data(work_id, source, data)
            
            # 合并数据
            merged_data = self.merger.merge(work_id, raw_data)
            
            # 检测冲突
            conflicts = self.merger.detect_conflicts(raw_data)
            if conflicts:
                self.reviewer.generate_review_file(work_id, title, conflicts)
                Logger.warning(f"检测到 {len(conflicts)} 个冲突，已生成审阅文件")
            
            # 保存合并数据
            self.merger.save_merged_data(work_id, merged_data)
            self.progress_manager.mark_data_merged(douban_id, True)
            
            # 下载图片
            images_data = {
                "douban": {
                    **raw_data.get("douban", {}).get("images", {}),
                    "main_poster_url": raw_data.get("douban", {}).get("main_poster_url", "")
                },
                "tmdb": raw_data.get("tmdb", {}).get("images", {}),
                "omdb": raw_data.get("omdb", {})
            }
            
            downloaded = await self.downloader.download_all(work_id, images_data)
            self.progress_manager.mark_images_downloaded(douban_id, True)
            
            # 更新图片列表到 data.json
            if downloaded.get("posters") or downloaded.get("stills"):
                merged_data["images_json"]["posters"] = downloaded.get("posters", [])
                merged_data["images_json"]["stills"] = downloaded.get("stills", [])
                self.merger.save_merged_data(work_id, merged_data)
            
            # 更新状态
            self.progress_manager.update_status(douban_id, "completed")
            
            Logger.success(f"电影处理完成: {title or douban_id}")
            return True
            
        except Exception as e:
            Logger.error(f"处理电影失败: {title or douban_id} - {e}")
            import traceback
            traceback.print_exc()
            return False
            
    async def run_test(self):
        """运行测试（单部电影）"""
        Logger.info("="*60)
        Logger.info("测试模式：爬取单部电影")
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
            
    async def run_batch(self, movie_list: list):
        """
        批量运行
        
        Args:
            movie_list: 电影列表（包含 douban_id, title）
        """
        Logger.info("="*60)
        Logger.info(f"批量模式：爬取 {len(movie_list)} 部电影")
        Logger.info("="*60)
        
        # 初始化进度
        self.progress_manager.init_movies(movie_list)
        
        # 处理每部电影
        for i, movie in enumerate(movie_list, 1):
            douban_id = movie.get("douban_id", "") or movie.get("id", "")
            title = movie.get("title", "")
            
            Logger.info(f"\n进度: {i}/{len(movie_list)}")
            
            success = await self.process_movie(douban_id, title)
            
            if not success:
                Logger.warning(f"跳过失败的电影: {title}")
                
            # 批次延迟
            if i % 10 == 0:
                Logger.info(f"已完成 {i} 部，休息一下...")
                await asyncio.sleep(config.BATCH_DELAY)
                
        # 输出摘要
        summary = self.progress_manager.get_summary()
        Logger.info("="*60)
        Logger.info(f"爬取完成！")
        Logger.info(f"总计: {summary['total']} 部")
        Logger.info(f"成功: {summary['completed']} 部")
        Logger.info(f"失败: {summary['pending']} 部")
        Logger.info("="*60)
        
    async def run_top250(self, batch_size: int = 10):
        """
        爬取豆瓣 TOP250（分批执行）
        
        Args:
            batch_size: 每批数量（默认 10 部）
        """
        Logger.info("="*60)
        Logger.info("TOP250 模式")
        Logger.info("="*60)
        
        # 初始化数据库
        self.db.create_table()
        
        # 获取 TOP250 列表
        movies = await self.douban.crawl_top250()
        
        if not movies:
            Logger.error("获取 TOP250 列表失败")
            return
        
        # 初始化电影到数据库
        self.db.init_movies(movies)
        
        # 获取待爬取的电影
        pending_movies = self.db.get_pending_movies()
        
        if not pending_movies:
            Logger.info("所有电影已爬取完成")
            return
        
        Logger.info(f"待爬取: {len(pending_movies)} 部")
        
        # 分批处理
        total_batches = (len(pending_movies) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start = batch_idx * batch_size
            end = min(start + batch_size, len(pending_movies))
            batch = pending_movies[start:end]
            
            Logger.info("="*60)
            Logger.info(f"批次 {batch_idx + 1}/{total_batches} ({start + 1}-{end}/{len(pending_movies)})")
            Logger.info("="*60)
            
            for i, movie in enumerate(batch, 1):
                movie_id = movie.get("id")
                douban_id = movie.get("douban_id")
                title = movie.get("title")
                
                Logger.info(f"\n[{start + i}/{len(pending_movies)}] {title}")
                
                # 爬取数据
                try:
                    raw_data = await self.crawl_movie(douban_id, title)
                    
                    # 保存原始数据
                    for source, data in raw_data.items():
                        if data:
                            self.merger.save_raw_data(movie_id, source, data)
                    
                    # 合并数据
                    merged_data = self.merger.merge(movie_id, raw_data)
                    
                    # 下载图片
                    images_data = {
                        "douban": {
                            **raw_data.get("douban", {}).get("images", {}),
                            "main_poster_url": raw_data.get("douban", {}).get("main_poster_url", "")
                        },
                        "tmdb": raw_data.get("tmdb", {}).get("images", {}),
                        "omdb": raw_data.get("omdb", {})
                    }
                    
                    downloaded = await self.downloader.download_all(movie_id, images_data)
                    
                    # 更新图片列表
                    if downloaded.get("posters") or downloaded.get("stills"):
                        merged_data["images_json"]["posters"] = downloaded.get("posters", [])
                        merged_data["images_json"]["stills"] = downloaded.get("stills", [])
                    
                    # 检测冲突
                    conflicts = self.merger.detect_conflicts(raw_data)
                    if conflicts:
                        self.reviewer.generate_review_file(movie_id, title, conflicts)
                        Logger.warning(f"检测到 {len(conflicts)} 个冲突")
                    
                    # 统计成功的数据源
                    sources = [k for k, v in raw_data.items() if v]
                    
                    # 统计错误
                    errors = []
                    if not raw_data.get("tmdb"):
                        errors.append("TMDB API 超时")
                    if not raw_data.get("metacritic", {}).get("rating"):
                        errors.append("Metacritic 获取失败")
                    
                    # 保存到数据库
                    self.db.save_movie(movie_id, merged_data, sources, errors)
                    
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
        
        # 输出统计
        stats = self.db.get_statistics()
        Logger.info("="*60)
        Logger.info("爬取完成！")
        Logger.info(f"总计: {stats['total']} 部")
        Logger.info(f"成功: {stats['completed']} 部")
        Logger.info(f"部分成功: {stats['partial']} 部")
        Logger.info(f"待处理: {stats['pending']} 部")
        Logger.info("="*60)


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="电影数据多源爬取工具")
    parser.add_argument("--test", action="store_true", help="测试模式（爬取单部电影）")
    parser.add_argument("--top250", action="store_true", help="爬取豆瓣 TOP250")
    parser.add_argument("--batch-size", type=int, default=10, help="每批数量（默认 10）")
    
    args = parser.parse_args()
    
    pipeline = MovieIngestPipeline()
    
    try:
        await pipeline.init()
        
        if args.top250:
            # TOP250 模式
            await pipeline.run_top250(batch_size=args.batch_size)
        elif args.test:
            # 测试模式
            await pipeline.run_test()
        else:
            # 默认测试模式
            await pipeline.run_test()
        
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main())
