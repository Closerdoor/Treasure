# -*- coding: utf-8 -*-
"""
电影数据多源爬取工具 - 主入口

使用方法：
1. 安装依赖：pip install playwright beautifulsoup4 aiohttp pillow
2. 安装浏览器：playwright install chromium
3. 运行脚本：python main.py
4. 首次运行会打开浏览器，手动登录豆瓣后按回车继续

模块拆分：
- crawl_basic.py：爬取基本信息（豆瓣、TMDB、OMDb、百度百科、Wikipedia）
- crawl_reviews.py：爬取完整影评（豆瓣短评/影评、TMDB、烂番茄、Metacritic）
- crawl_images.py：爬取图片资源（TMDB、OMDb、豆瓣主海报）
"""
import asyncio
import sys
from pathlib import Path

import config
from utils import Logger


async def run_all(mode: str = "top250", batch_size: int = 10):
    """
    运行所有模块（完整爬取）
    
    Args:
        mode: 模式（test 或 top250）
        batch_size: 每批处理数量
    """
    Logger.info("="*60)
    Logger.info("完整爬取模式：依次运行所有模块")
    Logger.info("="*60)
    
    # 模块 1：爬取基本信息
    Logger.info("\n[1/3] 爬取基本信息...")
    from crawl_basic import BasicCrawler
    
    basic_crawler = BasicCrawler()
    try:
        await basic_crawler.init()
        
        if mode == "test":
            await basic_crawler.run_test()
        elif mode == "top250":
            await basic_crawler.run_top250(batch_size)
    finally:
        await basic_crawler.close()
    
    # 模块 2：爬取影评
    Logger.info("\n[2/3] 爬取完整影评...")
    from crawl_reviews import ReviewsCrawler
    
    reviews_crawler = ReviewsCrawler()
    try:
        await reviews_crawler.init()
        
        if mode == "test":
            await reviews_crawler.run_test()
        elif mode == "top250":
            await reviews_crawler.run_top250(batch_size)
    finally:
        await reviews_crawler.close()
    
    # 模块 3：爬取图片
    Logger.info("\n[3/3] 爬取图片资源...")
    from crawl_images import ImagesCrawler
    
    images_crawler = ImagesCrawler()
    try:
        await images_crawler.init()
        
        if mode == "test":
            await images_crawler.run_test()
        elif mode == "top250":
            await images_crawler.run_top250(batch_size)
    finally:
        await images_crawler.close()
    
    Logger.success("\n完整爬取完成！")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="电影数据多源爬取工具")
    
    # 模式选择
    parser.add_argument("--test", action="store_true", help="测试模式（爬取单部电影）")
    parser.add_argument("--top250", action="store_true", help="爬取豆瓣 TOP250")
    
    # 模块选择
    parser.add_argument("--basic", action="store_true", help="只运行基本信息模块")
    parser.add_argument("--reviews", action="store_true", help="只运行影评模块")
    parser.add_argument("--images", action="store_true", help="只运行图片模块")
    
    # 其他参数
    parser.add_argument("--batch-size", type=int, default=10, help="每批处理数量（默认 10）")
    parser.add_argument("--missing", action="store_true", help="只爬缺失的数据（用于 --reviews 或 --images）")
    
    args = parser.parse_args()
    
    # 确定模式
    mode = "test" if args.test else "top250" if args.top250 else None
    
    if not mode:
        parser.print_help()
        return
    
    # 运行模块
    try:
        if args.basic:
            # 只运行基本信息模块
            from crawl_basic import BasicCrawler
            
            crawler = BasicCrawler()
            asyncio.run(crawler.init())
            
            if mode == "test":
                asyncio.run(crawler.run_test())
            elif mode == "top250":
                asyncio.run(crawler.run_top250(args.batch_size))
                
            asyncio.run(crawler.close())
            
        elif args.reviews:
            # 只运行影评模块
            from crawl_reviews import ReviewsCrawler
            
            crawler = ReviewsCrawler()
            asyncio.run(crawler.init())
            
            if mode == "test":
                asyncio.run(crawler.run_test())
            elif mode == "top250":
                asyncio.run(crawler.run_top250(args.batch_size))
            elif args.missing:
                asyncio.run(crawler.run_missing())
                
            asyncio.run(crawler.close())
            
        elif args.images:
            # 只运行图片模块
            from crawl_images import ImagesCrawler
            
            crawler = ImagesCrawler()
            asyncio.run(crawler.init())
            
            if mode == "test":
                asyncio.run(crawler.run_test())
            elif mode == "top250":
                asyncio.run(crawler.run_top250(args.batch_size))
            elif args.missing:
                asyncio.run(crawler.run_missing())
                
            asyncio.run(crawler.close())
            
        else:
            # 运行所有模块
            asyncio.run(run_all(mode, args.batch_size))
            
    except KeyboardInterrupt:
        Logger.warning("\n用户中断")
    except Exception as e:
        Logger.error(f"运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
