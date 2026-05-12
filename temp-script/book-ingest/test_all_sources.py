# -*- coding: utf-8 -*-
"""
测试所有非豆瓣数据源
"""
import asyncio
from playwright.async_api import async_playwright
from sources import OpenLibraryAPI, BaikeCrawler, WikipediaCrawler
from utils import Logger
import config

async def test():
    title = "百年孤独"
    isbn = "9787544253994"
    original_title = "Cien años de soledad"
    
    print("=" * 60)
    print(f"测试书籍: {title}")
    print(f"ISBN: {isbn}")
    print("=" * 60)
    
    # 1. OpenLibrary
    print("\n[1] OpenLibrary")
    print("-" * 40)
    api = OpenLibraryAPI()
    ol_data = await api.get_book_data(isbn)
    if ol_data:
        print(f"标题: {ol_data.get('title')}")
        print(f"作者: {ol_data.get('authors')}")
        print(f"首次出版: {ol_data.get('first_publish_year')}")
        print(f"主题: {ol_data.get('subjects', [])[:5]}")
        print(f"封面: {ol_data.get('cover_url')}")
        print(f"链接: {ol_data.get('openlibrary_url')}")
    
    # 2. 百度百科
    print("\n[2] 百度百科")
    print("-" * 40)
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    
    context_options = {}
    if config.PROXY_ENABLED and config.PROXY_URL:
        context_options["proxy"] = {"server": config.PROXY_URL}
        Logger.info(f"使用代理: {config.PROXY_URL}")
    
    context = await browser.new_context(**context_options)
    page = await context.new_page()
    
    baike = BaikeCrawler(page)
    baike_url = await baike.search(title)
    if baike_url:
        baike_data = await baike.get_detail(baike_url, title)
        if baike_data:
            print(f"标题: {baike_data.get('title')}")
            print(f"链接: {baike_data.get('url')}")
            summary = baike_data.get('summary', '')
            print(f"简介: {summary[:200]}..." if len(summary) > 200 else f"简介: {summary}")
    
    # 3. Wikipedia
    print("\n[3] Wikipedia")
    print("-" * 40)
    
    wiki = WikipediaCrawler(page)
    wiki_url = await wiki.search(title, original_title)
    if wiki_url:
        wiki_data = await wiki.get_detail(wiki_url)
        if wiki_data:
            print(f"标题: {wiki_data.get('title')}")
            print(f"链接: {wiki_data.get('url')}")
            summary = wiki_data.get('summary', '')
            print(f"简介: {summary[:200]}..." if len(summary) > 200 else f"简介: {summary}")
    
    await browser.close()
    await playwright.stop()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

asyncio.run(test())
