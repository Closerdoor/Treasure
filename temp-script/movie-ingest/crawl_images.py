# -*- coding: utf-8 -*-
"""
模块 3：爬取图片资源

功能：
- TMDB 图片（海报 + 剧照）
- OMDb 海报
- 豆瓣主海报
- 下载图片到本地

使用方法：
python crawl_images.py --top250
python crawl_images.py --missing  # 只爬缺失图片的电影
python crawl_images.py --douban-id 1292052
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
from downloader import ImageDownloader
from database import DatabaseManager
from sources.douban import DoubanCrawler
from sources.tmdb import TMDBClient
from sources.omdb import OMDbClient


class ImagesCrawler:
    """图片爬取器"""
    
    def __init__(self):
        self.progress_manager = ProgressManager()
        self.merger = DataMerger(config.OUTPUT_DIR)
        self.downloader = ImageDownloader(config.OUTPUT_DIR)
        self.db = DatabaseManager()
        
        # 爬虫实例
        self.douban: DoubanCrawler = None
        self.tmdb: TMDBClient = None
        self.omdb: OMDbClient = None
        
    async def init(self):
        """初始化"""
        Logger.info("正在初始化图片爬取器...")
        
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
        
        Logger.success("初始化完成")
        
    async def close(self):
        """清理资源"""
        if self.douban:
            await self.douban.close()
        if self.db:
            self.db.close()
            
    async def crawl_images(self, douban_id: str, title: str = "", imdb_id: str = "") -> Dict[str, Any]:
        """
        爬取单部电影的图片
        
        Args:
            douban_id: 豆瓣 ID
            title: 电影标题
            imdb_id: IMDb ID
            
        Returns:
            图片数据
        """
        Logger.info(f"开始爬取图片: {title or douban_id}")
        
        raw_data = {}
        
        # 1. 豆瓣主海报
        try:
            self.progress_manager.update_source_status(douban_id, "douban_poster", "in_progress")
            
            # 获取豆瓣详情页的主海报
            douban_detail = await self.douban.crawl_detail(douban_id)
            main_poster_url = douban_detail.get("main_poster_url", "")
            
            if main_poster_url:
                raw_data["douban_poster"] = {"url": main_poster_url}
            
            self.progress_manager.update_source_status(douban_id, "douban_poster", "done")
            
        except Exception as e:
            Logger.error(f"豆瓣主海报爬取失败: {e}")
            self.progress_manager.update_source_status(douban_id, "douban_poster", "error")
            
        # 2. TMDB 图片
        if imdb_id:
            try:
                self.progress_manager.update_source_status(douban_id, "tmdb_images", "in_progress")
                
                # 搜索 TMDB ID
                movie = await self.tmdb.search_by_imdb(imdb_id)
                if movie:
                    tmdb_id = movie.get("id", 0)
                    tmdb_images = await self.tmdb.get_images(tmdb_id)
                    raw_data["tmdb_images"] = tmdb_images
                
                self.progress_manager.update_source_status(douban_id, "tmdb_images", "done")
                
            except Exception as e:
                Logger.error(f"TMDB 图片爬取失败: {e}")
                self.progress_manager.update_source_status(douban_id, "tmdb_images", "error")
            
            # 3. OMDb 海报
            try:
                self.progress_manager.update_source_status(douban_id, "omdb_poster", "in_progress")
                
                omdb_data = await self.omdb.get_by_imdb(imdb_id)
                poster_url = omdb_data.get("poster", "")
                
                if poster_url:
                    raw_data["omdb_poster"] = {"url": poster_url}
                
                self.progress_manager.update_source_status(douban_id, "omdb_poster", "done")
                
            except Exception as e:
                Logger.error(f"OMDb 海报爬取失败: {e}")
                self.progress_manager.update_source_status(douban_id, "omdb_poster", "error")
            
        return raw_data
        
    async def process_movie(self, movie: Dict) -> bool:
        """
        处理单部电影（爬取图片 + 下载）
        
        Args:
            movie: 电影信息（从数据库读取）
            
        Returns:
            是否成功
        """
        movie_id = movie.get("id")
        douban_id = movie.get("douban_id")
        title = movie.get("title")
        
        try:
            # 检查是否已完成图片爬取
            if self.progress_manager.is_images_completed(douban_id):
                Logger.info(f"跳过已完成图片: {title}")
                return True
            
            # 从数据库读取基本信息
            basic_info = self.db.get_movie_basic_info(movie_id)
            if not basic_info:
                Logger.error(f"未找到基本信息: {title}")
                return False
                
            imdb_id = basic_info.get("identifiers_json", {}).get("imdb", "")
            
            # 爬取图片
            raw_data = await self.crawl_images(douban_id, title, imdb_id)
            
            # 保存原始数据
            for source, data in raw_data.items():
                if data:
                    self.merger.save_raw_data(movie_id, f"images_{source}", data)
            
            # 准备下载数据
            images_data = {
                "douban": {
                    "main_poster_url": raw_data.get("douban_poster", {}).get("url", "")
                },
                "tmdb": raw_data.get("tmdb_images", {}),
                "omdb": raw_data.get("omdb_poster", {})
            }
            
            # 下载图片
            downloaded = await self.downloader.download_all(movie_id, images_data)
            
            # 更新数据库
            self.db.update_movie_images(movie_id, downloaded)
            
            # 标记图片已完成
            self.progress_manager.mark_images_completed(douban_id, True)
            
            Logger.success(f"图片爬取完成: {title}（海报 {len(downloaded.get('posters', []))} 张，剧照 {len(downloaded.get('stills', []))} 张）")
            return True
            
        except Exception as e:
            Logger.error(f"处理电影失败: {title} - {e}")
            import traceback
            traceback.print_exc()
            return False
            
    async def run_test(self):
        """运行测试（单部电影）"""
        Logger.info("="*60)
        Logger.info("测试模式：爬取单部电影图片")
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
        """爬取缺失图片的电影"""
        Logger.info("="*60)
        Logger.info("补爬模式：爬取缺失图片的电影")
        Logger.info("="*60)
        
        self.db.connect()
        
        # 获取缺失图片的电影
        movies = self.db.get_movies_missing_images()
        
        if not movies:
            Logger.info("所有电影都已爬取图片")
            return
            
        Logger.info(f"找到 {len(movies)} 部电影需要爬取图片")
        
        for movie in movies:
            success = await self.process_movie(movie)
            
            # 电影间延迟
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        Logger.success("补爬完成！")
        
    async def run_top250(self, batch_size: int = 10):
        """爬取豆瓣 TOP250 的图片"""
        Logger.info("="*60)
        Logger.info("TOP250 模式：爬取图片")
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
        
        Logger.success("图片爬取完成！")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="爬取电影图片")
    parser.add_argument("--test", action="store_true", help="测试模式（爬取单部电影）")
    parser.add_argument("--top250", action="store_true", help="爬取豆瓣 TOP250 的图片")
    parser.add_argument("--missing", action="store_true", help="只爬缺失图片的电影")
    parser.add_argument("--batch-size", type=int, default=10, help="每批处理数量（默认 10）")
    
    args = parser.parse_args()
    
    crawler = ImagesCrawler()
    
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
