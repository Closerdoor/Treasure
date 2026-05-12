# -*- coding: utf-8 -*-
"""
书籍数据多源爬取工具 - 主入口

使用方法：
1. 安装依赖：pip install playwright beautifulsoup4 aiohttp pillow
2. 安装浏览器：playwright install chromium
3. 运行脚本：python main.py --test
4. 首次运行会打开浏览器，手动登录豆瓣后按回车继续
"""
import asyncio
import sys
from pathlib import Path

import config
from utils import Logger


async def run_basic(mode: str = "test"):
    """运行基本信息爬取"""
    from crawl_basic import BasicCrawler
    
    crawler = BasicCrawler()
    try:
        await crawler.init()
        
        if mode == "test":
            await crawler.run_test()
        elif mode == "batch":
            book_list = config.TEST_BOOKS
            await crawler.run_batch(book_list)
    finally:
        await crawler.close()


async def run_reviews(mode: str = "test"):
    """运行书评爬取"""
    from crawl_reviews import ReviewsCrawler
    
    crawler = ReviewsCrawler()
    try:
        await crawler.init()
        
        if mode == "test":
            await crawler.run_test()
        elif mode == "batch":
            book_list = config.TEST_BOOKS
            await crawler.run_batch(book_list)
    finally:
        await crawler.close()


async def run_all(mode: str = "test"):
    """运行所有模块"""
    Logger.info("="*60)
    Logger.info("完整爬取模式：依次运行所有模块")
    Logger.info("="*60)
    
    # 模块 1：爬取基本信息
    Logger.info("\n[1/2] 爬取基本信息...")
    await run_basic(mode)
    
    # 模块 2：爬取书评
    Logger.info("\n[2/2] 爬取书评...")
    await run_reviews(mode)
    
    Logger.success("\n完整爬取完成！")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="书籍数据多源爬取工具")
    
    parser.add_argument("--test", action="store_true", help="测试模式（爬取测试书籍）")
    parser.add_argument("--batch", action="store_true", help="批量爬取")
    parser.add_argument("--basic", action="store_true", help="只运行基本信息模块")
    parser.add_argument("--reviews", action="store_true", help="只运行书评模块")
    
    args = parser.parse_args()
    
    mode = "test" if args.test else "batch" if args.batch else None
    
    if not mode:
        parser.print_help()
        return
    
    async def run():
        if args.basic:
            await run_basic(mode)
        elif args.reviews:
            await run_reviews(mode)
        else:
            await run_all(mode)
    
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