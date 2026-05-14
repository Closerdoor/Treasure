# -*- coding: utf-8 -*-
"""
电影数据多源爬取工具 - 主入口

推荐使用 crawl.py（统一入口，按数据源一次性采集）：
python crawl.py --movie-name "社交网络" --year 2010

旧模块入口（按数据类型分步，会重复登录豆瓣）：
python crawl_basic.py --movie-name "社交网络"
python crawl_reviews.py --work-id 0101000251
python crawl_images.py --work-id 0101000251
"""
import sys

if sys.platform == 'win32':
    import os
    os.environ['PYTHONUTF8'] = '1'

import asyncio
from crawl import MovieCrawler
from utils import Logger


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="电影数据多源爬取工具")
    
    parser.add_argument("--movie-name", type=str, help="通过影片名称搜索并爬取（推荐）")
    parser.add_argument("--year", type=int, help="年份（配合 --movie-name 使用，用于验证）")
    parser.add_argument("--douban-id", type=str, help="指定豆瓣 ID 爬取")
    parser.add_argument("--title", type=str, default="", help="电影标题（配合 --douban-id 使用）")
    parser.add_argument("--work-id", type=str, help="作品 ID（配合 --douban-id 使用）")
    
    args = parser.parse_args()
    
    if not args.movie_name and not args.douban_id:
        parser.print_help()
        return
    
    async def run():
        crawler = MovieCrawler()
        
        try:
            await crawler.init()
            
            if args.movie_name:
                await crawler.run_by_movie_name(args.movie_name, args.year)
            elif args.douban_id:
                await crawler.run_by_douban_id(args.douban_id, args.title, args.work_id or "")
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