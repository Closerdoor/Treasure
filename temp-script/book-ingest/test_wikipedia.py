# -*- coding: utf-8 -*-
"""
测试 Wikipedia
"""
import asyncio
from playwright.async_api import async_playwright
from sources import WikipediaCrawler
from utils import Logger
import config

async def test():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    
    context_options = {}
    if config.PROXY_ENABLED and config.PROXY_URL:
        context_options["proxy"] = {"server": config.PROXY_URL}
        Logger.info(f"使用代理: {config.PROXY_URL}")
    
    context = await browser.new_context(**context_options)
    page = await context.new_page()
    
    wiki = WikipediaCrawler(page)
    
    # 测试搜索百年孤独
    title = "百年孤独"
    original_title = "Cien años de soledad"
    Logger.info(f"测试 Wikipedia 搜索: {title}")
    
    wiki_url = await wiki.search(title, original_title)
    
    if wiki_url:
        Logger.success(f"找到 Wikipedia: {wiki_url}")
        
        data = await wiki.get_detail(wiki_url)
        
        if data:
            Logger.success("获取数据成功")
            print(f"Title: {data.get('title')}")
            print(f"Summary: {data.get('summary', '')[:100]}...")
            print(f"URL: {data.get('url')}")
        else:
            Logger.error("获取详情失败")
    else:
        Logger.error("未找到 Wikipedia")
    
    await browser.close()
    await playwright.stop()

asyncio.run(test())
