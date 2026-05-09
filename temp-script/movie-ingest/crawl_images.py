# -*- coding: utf-8 -*-
"""
模块 3：爬取图片资源

功能：
- TMDB 图片（海报 + 剧照）
- OMDb 海报
- 豆瓣主海报
- 下载图片到本地

使用方法：
python crawl_images.py --work-id 0101000001
python crawl_images.py --all

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
from downloader import ImageDownloader
from sources.douban import DoubanCrawler
from sources.tmdb import TMDBClient
from sources.omdb import OMDbClient


class ImagesCrawler:
    """图片爬取器"""
    
    def __init__(self):
        self.progress_manager = ProgressManager()
        self.merger = DataMerger()
        self.downloader = ImageDownloader(config.OUTPUT_DIR)
        
        self.douban: DoubanCrawler = None
        self.tmdb: TMDBClient = None
        self.omdb: OMDbClient = None
        
    async def init(self):
        Logger.info("正在初始化图片爬取器...")
        
        Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        
        self.progress_manager.load()
        
        self.douban = DoubanCrawler()
        await self.douban.init_browser()
        await self.douban.ensure_login()
        
        self.tmdb = TMDBClient()
        self.omdb = OMDbClient()
        
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
    
    def get_asset_dir(self, work_id: str) -> Path:
        """获取资源目录"""
        asset_dir = Path(__file__).parent.parent.parent / ".local" / "assets" / "video" / "movie" / work_id
        asset_dir.mkdir(parents=True, exist_ok=True)
        return asset_dir
            
    async def crawl_images(self, work_id: str, title: str = "", imdb_id: str = "") -> Dict[str, Any]:
        Logger.info(f"开始爬取图片: {title or work_id}")
        
        raw_data = {}
        
        try:
            self.progress_manager.update_source_status(work_id, "douban_poster", "in_progress")
            
            douban_detail = await self.douban.crawl_detail(work_id)
            main_poster_url = douban_detail.get("main_poster_url", "")
            
            if main_poster_url:
                raw_data["main_poster_url"] = main_poster_url
            
            self.progress_manager.update_source_status(work_id, "douban_poster", "done")
            
        except Exception as e:
            Logger.error(f"豆瓣海报爬取失败: {e}")
            self.progress_manager.update_source_status(work_id, "douban_poster", "error")
            
        if imdb_id:
            try:
                self.progress_manager.update_source_status(work_id, "tmdb_images", "in_progress")
                
                movie = await self.tmdb.search_by_imdb(imdb_id)
                if movie:
                    tmdb_id = movie.get("id", 0)
                    images = await self.tmdb.get_images(tmdb_id)
                    raw_data["tmdb_images"] = images
                
                self.progress_manager.update_source_status(work_id, "tmdb_images", "done")
                
            except Exception as e:
                Logger.error(f"TMDB 图片爬取失败: {e}")
                self.progress_manager.update_source_status(work_id, "tmdb_images", "error")
            
            try:
                self.progress_manager.update_source_status(work_id, "omdb_poster", "in_progress")
                
                omdb_data = await self.omdb.get_by_imdb(imdb_id)
                if omdb_data and omdb_data.get("poster"):
                    raw_data["omdb_poster"] = omdb_data.get("poster")
                
                self.progress_manager.update_source_status(work_id, "omdb_poster", "done")
                
            except Exception as e:
                Logger.error(f"OMDb 海报爬取失败: {e}")
                self.progress_manager.update_source_status(work_id, "omdb_poster", "error")
            
        return raw_data
        
    async def process_work(self, work_id: str) -> bool:
        try:
            data = self.load_staging_file(work_id)
            
            title = data.get("title", "")
            imdb_id = data.get("imdbId", "")
            
            raw_data = await self.crawl_images(work_id, title, imdb_id)
            
            asset_dir = self.get_asset_dir(work_id)
            
            images = data.get("images", {
                "poster": None,
                "posters": [],
                "stills": [],
                "wallpapers": [],
                "postersTotal": 0,
                "stillsTotal": 0
            })
            
            if raw_data.get("main_poster_url"):
                poster_path = asset_dir / "poster-main.jpg"
                await self.downloader.download(raw_data["main_poster_url"], str(poster_path))
                images["poster"] = "poster-main.jpg"
            
            tmdb_images = raw_data.get("tmdb_images", {})
            
            for idx, poster in enumerate(tmdb_images.get("posters", [])[:10]):
                url = poster.get("url", "")
                if url:
                    ext = ".jpg"
                    poster_path = asset_dir / f"poster-{idx+1:02d}{ext}"
                    await self.downloader.download(url, str(poster_path))
                    images["posters"].append(f"poster-{idx+1:02d}{ext}")
            
            for idx, backdrop in enumerate(tmdb_images.get("backdrops", [])[:10]):
                url = backdrop.get("url", "")
                if url:
                    ext = ".jpg"
                    still_path = asset_dir / f"still-{idx+1:02d}{ext}"
                    await self.downloader.download(url, str(still_path))
                    images["stills"].append(f"still-{idx+1:02d}{ext}")
            
            data["images"] = images
            self.save_staging_file(work_id, data)
            
            Logger.success(f"图片爬取完成: {title}")
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
    
    parser = argparse.ArgumentParser(description="爬取电影图片")
    parser.add_argument("--work-id", type=str, help="指定作品 ID")
    parser.add_argument("--all", action="store_true", help="爬取所有 staging 文件")
    
    args = parser.parse_args()
    
    crawler = ImagesCrawler()
    
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
