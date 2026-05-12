# -*- coding: utf-8 -*-
"""
测试百度百科
"""
import asyncio
from playwright.async_api import async_playwright
from sources import BaikeCrawler
from utils import Logger
import config

async def test():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    
    baike = BaikeCrawler(page)
    
    # 测试搜索百年孤独
    title = "百年孤独"
    Logger.info(f"测试百度百科搜索: {title}")
    
    baike_url = await baike.search(title)
    
    if baike_url:
        Logger.success(f"找到百度百科: {baike_url}")
        
        data = await baike.get_detail(baike_url, title)
        
        if data:
            Logger.success("获取数据成功")
            print(f"Title: {data.get('title')}")
            print(f"Summary: {data.get('summary', '')[:100]}...")
            print(f"URL: {data.get('url')}")
        else:
            Logger.error("获取详情失败")
    else:
        Logger.error("未找到百度百科")
    
    await browser.close()
    await playwright.stop()

asyncio.run(test())
