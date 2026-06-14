# -*- coding: utf-8 -*-
"""
电影数据多源爬取工具 - 主入口

推荐使用 crawl.py（统一入口，按数据源一次性采集）：
python crawl.py --movie-name "社交网络" --year 2010

当前职责边界：
- main.py / crawl.py 只负责电影采集、raw/staging 生成和采集阶段资源下载。
- 录入 .local/treasure.db 的正式 Python 入口由 database.py 承担。
- generated 导出、site/public/assets 发布资源同步、Astro 构建不属于本目录职责。
"""
import sys

if sys.platform == 'win32':
    import os
    os.environ['PYTHONUTF8'] = '1'

import asyncio
from crawl import MovieCrawler
from media_profiles import supported_schema_types
from utils import Logger


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="电影数据多源爬取工具")
    
    parser.add_argument("--movie-name", type=str, help="通过影片名称搜索并爬取（推荐）")
    parser.add_argument("--year", type=int, help="年份（配合 --movie-name 使用，用于验证）")
    parser.add_argument("--douban-id", type=str, help="指定豆瓣 ID 爬取")
    parser.add_argument("--title", type=str, default="", help="电影标题（配合 --douban-id 使用）")
    parser.add_argument("--work-id", type=str, help="作品 ID（配合 --douban-id 使用）")
    parser.add_argument("--schema-type", choices=sorted(supported_schema_types()), default="live_action_movie", help="媒体作品类型")
    
    args = parser.parse_args()
    
    if not args.movie_name and not args.douban_id:
        parser.print_help()
        return
    
    async def run():
        crawler = MovieCrawler()
        
        try:
            await crawler.init()
            
            if args.movie_name:
                await crawler.run_by_movie_name(args.movie_name, args.year, args.schema_type)
            elif args.douban_id:
                await crawler.run_by_douban_id(args.douban_id, args.title, args.work_id or "", args.schema_type)
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
