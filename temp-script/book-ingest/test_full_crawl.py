# -*- coding: utf-8 -*-
"""
测试完整爬取流程（跳过豆瓣）
"""
import asyncio
import json
from playwright.async_api import async_playwright
from sources import OpenLibraryAPI, BaikeCrawler, WikipediaCrawler
from merger import DataMerger
from utils import Logger, generate_book_id
import config

async def crawl_book(title: str, isbn: str, original_title: str):
    """爬取一本书"""
    print("\n" + "=" * 60)
    print(f"爬取: {title}")
    print(f"ISBN: {isbn}")
    print("=" * 60)
    
    book_id = generate_book_id()
    raw_data = {}
    
    # 1. OpenLibrary
    print("\n[1] OpenLibrary")
    print("-" * 40)
    api = OpenLibraryAPI()
    ol_data = await api.get_book_data(isbn)
    if ol_data:
        raw_data["openlibrary"] = ol_data
        print(f"标题: {ol_data.get('title')}")
        print(f"作者: {ol_data.get('authors')}")
        print(f"首次出版: {ol_data.get('first_publish_year')}")
        print(f"主题: {ol_data.get('subjects', [])[:5]}")
        print(f"封面: {ol_data.get('cover_url')}")
    else:
        print("未找到数据")
    
    # 2. 百度百科 + Wikipedia (需要浏览器)
    print("\n[2] 百度百科")
    print("-" * 40)
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    
    context_options = {}
    if config.PROXY_ENABLED and config.PROXY_URL:
        context_options["proxy"] = {"server": config.PROXY_URL}
    
    context = await browser.new_context(**context_options)
    page = await context.new_page()
    
    baike = BaikeCrawler(page)
    baike_url = await baike.search(title)
    if baike_url:
        baike_data = await baike.get_detail(baike_url, title)
        if baike_data:
            raw_data["baike"] = baike_data
            print(f"标题: {baike_data.get('baike_title', title)}")
            summary = baike_data.get('summary', '')
            print(f"简介: {summary[:150]}..." if len(summary) > 150 else f"简介: {summary}")
            if baike_data.get('info'):
                print(f"基本信息: {json.dumps(baike_data.get('info'), ensure_ascii=False)[:100]}")
    
    # 3. Wikipedia
    print("\n[3] Wikipedia")
    print("-" * 40)
    wiki = WikipediaCrawler(page)
    wiki_url = await wiki.search(title, original_title)
    if wiki_url:
        wiki_data = await wiki.get_detail(wiki_url)
        if wiki_data:
            raw_data["wikipedia"] = wiki_data
            print(f"标题: {wiki_data.get('title')}")
            summary = wiki_data.get('summary', '')
            print(f"简介: {summary[:150]}..." if len(summary) > 150 else f"简介: {summary}")
            if wiki_data.get('info'):
                print(f"基本信息: {json.dumps(wiki_data.get('info'), ensure_ascii=False)[:100]}")
    
    await browser.close()
    await playwright.stop()
    
    # 4. 合并数据
    print("\n[4] 合并数据")
    print("-" * 40)
    merger = DataMerger()
    merged_data = merger.merge(book_id, raw_data)
    merger.save_merged_data(book_id, merged_data)
    
    print(f"书籍ID: {merged_data.get('id')}")
    print(f"标题: {merged_data.get('title')}")
    print(f"原标题: {merged_data.get('titleOriginal')}")
    print(f"ISBN: {merged_data.get('isbn')}")
    print(f"年份: {merged_data.get('year')}")
    print(f"出版社: {merged_data.get('publisher')}")
    print(f"简介: {merged_data.get('summary', '')[:100]}..." if merged_data.get('summary') else "简介: 无")
    print(f"评分: {merged_data.get('scores')}")
    print(f"外部来源: {merged_data.get('externalSource')}")
    
    return merged_data

async def main():
    # 测试三本书
    books = [
        {"title": "百年孤独", "isbn": "9787544253994", "original_title": "Cien años de soledad"},
        {"title": "围城", "isbn": "9787020024370", "original_title": "Fortress Besieged"},
        {"title": "凡人修仙传", "isbn": "9787539137361", "original_title": "A Record of a Mortal's Journey to Immortality"},
    ]
    
    results = []
    for book in books:
        data = await crawl_book(book["title"], book["isbn"], book["original_title"])
        results.append(data)
    
    print("\n" + "=" * 60)
    print("爬取完成！")
    print("=" * 60)

asyncio.run(main())
