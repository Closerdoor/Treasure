# -*- coding: utf-8 -*-
"""
统一爬取入口 - 按数据源一次性采集

流程：
1. 豆瓣（浏览器）→ 详情 + 演职员 + 短评 + 影评 + 海报 + 图片
2. TMDB（API）→ 详情 + 演职员 + 图片 + 评论 + 视频
3. OMDb（API）→ 详情 + 海报
4. 百度百科（浏览器）→ 详情 + 演职员
5. Wikipedia（API）→ 故事 + 演职员
6. 烂番茄（浏览器）→ 评论
7. Metacritic（浏览器）→ 评论
8. 下载图片资源
9. 合并数据，保存 staging

使用方法：
python crawl.py --movie-name "社交网络" --year 2010
python crawl.py --douban-id 3205624
"""
import os
import sys

if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

import asyncio
import json
import random
from pathlib import Path
from typing import Dict, Any, Optional

import config
from utils import Logger, generate_work_id
from media_profiles import apply_profile_defaults, get_profile_by_schema_type, supported_schema_types
from merger import DataMerger
from downloader import ImageDownloader
from progress import ProgressManager

from sources.douban import DoubanCrawler
from sources.tmdb import TMDBClient
from sources.omdb import OMDbClient
from sources.baike import BaikeCrawler
from sources.wikipedia import WikipediaCrawler
from sources.rotten_tomatoes import RottenTomatoesCrawler
from sources.metacritic import MetacriticCrawler


class MovieCrawler:
    def __init__(self):
        self.progress_manager = ProgressManager()
        self.merger = DataMerger()
        self.downloader = ImageDownloader(config.WORK_ASSETS_DIR)
        
        self.douban: Optional[DoubanCrawler] = None
        self.tmdb: Optional[TMDBClient] = None
        self.omdb: Optional[OMDbClient] = None
        self.baike: Optional[BaikeCrawler] = None
        self.wikipedia: Optional[WikipediaCrawler] = None
        self.rotten_tomatoes: Optional[RottenTomatoesCrawler] = None
        self.metacritic: Optional[MetacriticCrawler] = None
    
    async def init(self):
        Logger.info("正在初始化爬取器...")
        
        Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        self.progress_manager.load()
        
        self.douban = DoubanCrawler()
        await self.douban.init_browser()
        await self.douban.ensure_login()
        
        self.tmdb = TMDBClient()
        self.omdb = OMDbClient()
        
        self.baike = BaikeCrawler(self.douban.page)
        self.wikipedia = WikipediaCrawler(self.douban.page)
        self.rotten_tomatoes = RottenTomatoesCrawler(self.douban.page)
        self.metacritic = MetacriticCrawler(self.douban.page)
        
        Logger.success("初始化完成")
    
    async def close(self):
        if self.douban:
            await self.douban.close()
    
    async def crawl_movie(self, douban_id: str, title: str = "", schema_type: str = "live_action_movie") -> Optional[str]:
        profile = get_profile_by_schema_type(schema_type)
        Logger.info("=" * 60)
        Logger.info(f"开始爬取: {title or douban_id} [{profile.label}]")
        Logger.info("=" * 60)
        
        raw_data = {}
        work_id = None
        
        # ── 1. 豆瓣（一次性采集） ──
        Logger.info("\n[1/7] 豆瓣 - 详情 + 演职员 + 分集剧情 + 视频 + 图片 + 短评 + 影评")
        try:
            douban_data = await self.douban.crawl_all(
                douban_id,
                comments_count=config.COMMENTS_PER_SOURCE,
                reviews_count=config.REVIEWS_PER_SOURCE
            )
            raw_data["douban"] = douban_data
            
            detail = douban_data.get("detail", {})
            if not detail.get("title") and getattr(config, "NONINTERACTIVE_BATCH", False):
                raise Exception("豆瓣详情缺少标题，批量验证停止当前条目，避免生成空标题 staging")
            if detail.get("title"):
                title = detail["title"]
            
            imdb_id = detail.get("imdb_id", "")
            
            work_id = self.progress_manager.get_work_id(douban_id)
            if not work_id:
                work_id = generate_work_id(profile.module, profile.submodule)
                self.progress_manager.update_work_id(douban_id, work_id)
            
            self.progress_manager.update_source_status(douban_id, "douban", "done")
            Logger.success(f"豆瓣采集完成: {title}")

            await self._download_douban_avatars_from_raw(work_id, douban_data)
        except Exception as e:
            Logger.error(f"豆瓣采集失败: {e}")
            self.progress_manager.update_source_status(douban_id, "douban", "error")
            self.progress_manager.update_status(douban_id, "error")
            self.progress_manager.save()
            raise
        
        # ── 2. TMDB（API） ──
        Logger.info("\n[2/7] TMDB - 详情 + 演职员 + 图片 + 评论 + 视频")
        if imdb_id:
            try:
                tmdb_data = await self.tmdb.get_all(imdb_id)
                raw_data["tmdb"] = tmdb_data
                self.progress_manager.update_source_status(douban_id, "tmdb", "done")
                Logger.success("TMDB 采集完成")
            except Exception as e:
                Logger.error(f"TMDB 采集失败: {e}")
                self.progress_manager.update_source_status(douban_id, "tmdb", "error")
        
        # ── 3. OMDb（API） ──
        Logger.info("\n[3/7] OMDb - 详情 + 海报")
        if imdb_id:
            try:
                omdb_data = await self.omdb.get_by_imdb(imdb_id)
                raw_data["omdb"] = omdb_data
                self.progress_manager.update_source_status(douban_id, "omdb", "done")
                Logger.success("OMDb 采集完成")
            except Exception as e:
                Logger.error(f"OMDb 采集失败: {e}")
                self.progress_manager.update_source_status(douban_id, "omdb", "error")
        
        # ── 4. 百度百科 ──
        Logger.info("\n[4/7] 百度百科 - 详情 + 演职员")
        try:
            search_term = title or douban_id
            baike_data = await self.baike.crawl(search_term)
            raw_data["baike"] = baike_data
            self.progress_manager.update_source_status(douban_id, "baike", "done")
            Logger.success("百度百科采集完成")
        except Exception as e:
            Logger.error(f"百度百科采集失败: {e}")
            self.progress_manager.update_source_status(douban_id, "baike", "error")
        
        # ── 5. Wikipedia ──
        Logger.info("\n[5/7] Wikipedia - 故事 + 演职员")
        try:
            wiki_data = await self.wikipedia.crawl(title or douban_id)
            raw_data["wikipedia"] = wiki_data
            self.progress_manager.update_source_status(douban_id, "wikipedia", "done")
            Logger.success("Wikipedia 采集完成")
        except Exception as e:
            Logger.error(f"Wikipedia 采集失败: {e}")
            self.progress_manager.update_source_status(douban_id, "wikipedia", "error")
        
        # ── 6. 烂番茄 ──
        Logger.info("\n[6/7] 烂番茄 - 评论")
        original_title = ""
        year = 0
        if raw_data.get("douban", {}).get("detail"):
            original_title = raw_data["douban"]["detail"].get("original_title", "")
            year_str = raw_data["douban"]["detail"].get("year", "")
            if year_str:
                try:
                    year = int(year_str)
                except ValueError:
                    pass
        
        try:
            rt_data = await self.rotten_tomatoes.crawl(
                original_title or title,
                year,
                review_count=config.REVIEWS_PER_SOURCE
            )
            raw_data["rotten_tomatoes"] = rt_data
            self.progress_manager.update_source_status(douban_id, "rotten_tomatoes", "done")
            Logger.success("烂番茄采集完成")
        except Exception as e:
            Logger.error(f"烂番茄采集失败: {e}")
            self.progress_manager.update_source_status(douban_id, "rotten_tomatoes", "error")
        
        # ── 7. Metacritic ──
        Logger.info("\n[7/7] Metacritic - 评论")
        try:
            mc_data = await self.metacritic.crawl(
                original_title or title,
                original_title,
                year,
                review_count=config.REVIEWS_PER_SOURCE
            )
            raw_data["metacritic"] = mc_data
            self.progress_manager.update_source_status(douban_id, "metacritic", "done")
            Logger.success("Metacritic 采集完成")
        except Exception as e:
            Logger.error(f"Metacritic 采集失败: {e}")
            self.progress_manager.update_source_status(douban_id, "metacritic", "error")
        
        # ── 下载图片 ──
        Logger.info("\n下载图片资源...")
        images_result = await self._download_all_images(work_id, raw_data)
        
        # ── 合并数据 ──
        Logger.info("\n合并数据...")
        merged = self.merger.merge(work_id, raw_data)
        merged["module"] = profile.module
        merged["submodule"] = profile.submodule
        merged["schemaType"] = profile.schema_type
        apply_profile_defaults(merged)
        
        if images_result:
            merged["images"] = images_result

        video_thumbnail_map = await self.downloader.download_video_thumbnails(
            work_id,
            merged.get("videos", [])
        )
        for video in merged.get("videos", []):
            thumbnail = video.get("thumbnail")
            if thumbnail in video_thumbnail_map:
                video["thumbnail"] = video_thumbnail_map[thumbnail]
            elif isinstance(thumbnail, str) and thumbnail.startswith(("http://", "https://")):
                video["thumbnail"] = None
        
        # ── 保存 staging ──
        staging_path = config.STAGING_DIR / f"{work_id}.json"
        config.STAGING_DIR.mkdir(parents=True, exist_ok=True)
        with open(staging_path, "w", encoding="utf-8") as f:
            json.dump(merged, ensure_ascii=False, indent=2, fp=f)
        Logger.success(f"Staging 文件已保存: {staging_path}")
        
        # ── 保存原始数据 ──
        raw_dir = config.RAW_DIR / work_id
        raw_dir.mkdir(parents=True, exist_ok=True)
        for source_name, source_data in raw_data.items():
            raw_path = raw_dir / f"{source_name}.json"
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(source_data, ensure_ascii=False, indent=2, fp=f)
        
        # ── 更新进度 ──
        self.progress_manager.update_status(douban_id, "completed")
        self.progress_manager.mark_basic_completed(douban_id, True)
        self.progress_manager.mark_images_downloaded(douban_id, True)
        self.progress_manager.save()
        
        Logger.success(f"\n爬取完成！Staging 文件: data/staging/{work_id}.json")
        return work_id
    
    async def _download_all_images(self, work_id: str, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        images_data = {}
        
        douban_detail = raw_data.get("douban", {}).get("detail", {})
        douban_images = raw_data.get("douban", {}).get("images", {})
        
        images_data["douban"] = {
            "main_poster_url": douban_detail.get("main_poster_url", ""),
            "posters": douban_images.get("posters", []),
            "stills": douban_images.get("stills", []),
            "wallpapers": douban_images.get("wallpapers", [])
        }
        
        tmdb_all = raw_data.get("tmdb", {})
        tmdb_images = dict(tmdb_all.get("images", {}) or {})
        tmdb_images["main_poster_url"] = tmdb_all.get("detail", {}).get("poster", "")
        images_data["tmdb"] = tmdb_images
        
        omdb_data = raw_data.get("omdb", {})
        if omdb_data and omdb_data.get("poster"):
            images_data["omdb"] = {"poster": omdb_data["poster"]}

        rt_ratings = raw_data.get("rotten_tomatoes", {}).get("ratings", {})
        rt_poster = (
            rt_ratings.get("poster")
            or rt_ratings.get("images", {}).get("poster")
            or rt_ratings.get("schema_movie", {}).get("image")
        )
        if rt_poster:
            images_data["rotten_tomatoes"] = {"poster": rt_poster}
        
        asset_dir = config.WORK_ASSETS_DIR / work_id
        asset_dir.mkdir(parents=True, exist_ok=True)
        
        result = await self.downloader.download_all(work_id, images_data)
        
        images = {
            "poster": None,
            "covers": result.get("covers", {}),
            "posters": result.get("posters", []),
            "stills": result.get("stills", []),
            "wallpapers": result.get("wallpapers", []),
            "postersTotal": douban_images.get("posters_total", 0) or len(images_data.get("tmdb", {}).get("posters", [])),
            "stillsTotal": douban_images.get("stills_total", 0) or len(images_data.get("tmdb", {}).get("backdrops", [])),
            "wallpapersTotal": douban_images.get("wallpapers_total", 0)
        }
        
        for source in ["douban", "tmdb", "omdb", "rottenTomatoes"]:
            if images["covers"].get(source):
                images["poster"] = images["covers"][source]
                break
        
        Logger.success(
            f"图片下载完成: 海报 {len(images['posters'])} 张, "
            f"剧照 {len(images['stills'])} 张, "
            f"壁纸 {len(images['wallpapers'])} 张"
        )
        return images

    async def _download_douban_avatars_from_raw(self, work_id: str, douban_data: Dict[str, Any]) -> Dict[str, str]:
        celebrities = douban_data.get("celebrities", {}) or {}
        people = []
        for key in ["directors", "writers", "cast"]:
            people.extend(celebrities.get(key, []) or [])

        result = await self.downloader.download_profiles(work_id, people)
        if result:
            Logger.success(f"豆瓣演职员头像下载完成: {len(result)} 张")
        return result
    
    async def run_by_movie_name(self, movie_name: str, year: int = None, schema_type: str = "live_action_movie"):
        Logger.info(f"通过影片名称爬取: {movie_name}")
        
        douban_info = await self.douban.search_douban_id(movie_name, year)
        
        douban_id = douban_info['doubanId']
        title = douban_info['title']
        
        Logger.info(f"豆瓣 ID: {douban_id}, 标题: {title}")
        
        self.progress_manager.init_movies([{
            "douban_id": douban_id,
            "title": title
        }])
        
        work_id = await self.crawl_movie(douban_id, title, schema_type)
        return work_id
    
    async def run_by_douban_id(self, douban_id: str, title: str = "", work_id: str = "", schema_type: str = "live_action_movie"):
        Logger.info(f"通过豆瓣 ID 爬取: {douban_id}")
        
        self.progress_manager.init_movies([{
            "douban_id": douban_id,
            "title": title or douban_id
        }])
        
        if work_id:
            self.progress_manager.update_work_id(douban_id, work_id)
        
        result_work_id = await self.crawl_movie(douban_id, title, schema_type)
        return result_work_id


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="电影数据统一爬取工具")
    parser.add_argument("--movie-name", type=str, help="通过影片名称搜索并爬取（推荐）")
    parser.add_argument("--year", type=int, help="年份（配合 --movie-name 使用，用于验证）")
    parser.add_argument("--douban-id", type=str, help="指定豆瓣 ID 爬取")
    parser.add_argument("--title", type=str, default="", help="电影标题（配合 --douban-id 使用）")
    parser.add_argument("--work-id", type=str, help="作品 ID（配合 --douban-id 使用）")
    parser.add_argument("--schema-type", choices=sorted(supported_schema_types()), default="live_action_movie", help="媒体作品类型")
    
    args = parser.parse_args()
    
    async def run():
        crawler = MovieCrawler()
        
        try:
            await crawler.init()
            
            if args.movie_name:
                await crawler.run_by_movie_name(args.movie_name, args.year, args.schema_type)
            elif args.douban_id:
                await crawler.run_by_douban_id(args.douban_id, args.title, args.work_id or "", args.schema_type)
            else:
                parser.print_help()
        finally:
            await crawler.close()
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        Logger.warning("\n用户中断")
    except Exception as e:
        Logger.error(f"运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
