# -*- coding: utf-8 -*-
"""
测试 OpenLibrary API
"""
import asyncio
from sources import OpenLibraryAPI
from utils import Logger

async def test():
    api = OpenLibraryAPI()
    
    # 测试 ISBN: 9787544253994 (百年孤独)
    isbn = "9787544253994"
    Logger.info(f"测试 OpenLibrary API，ISBN: {isbn}")
    
    data = await api.get_book_data(isbn)
    
    if data:
        Logger.success("获取数据成功")
        print(f"Title: {data.get('title')}")
        print(f"Authors: {data.get('authors')}")
        print(f"ISBN: {data.get('isbn')}")
        print(f"Publisher: {data.get('publisher')}")
        print(f"Year: {data.get('year')}")
        print(f"Rating: {data.get('rating')}")
        print(f"Subjects: {data.get('subjects')}")
    else:
        Logger.error("未找到数据")

asyncio.run(test())
