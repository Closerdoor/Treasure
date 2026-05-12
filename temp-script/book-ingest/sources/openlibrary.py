# -*- coding: utf-8 -*-
"""
OpenLibrary API 模块
"""
import aiohttp
from typing import Dict, Any, Optional, List

import config
from utils import Logger


class OpenLibraryAPI:
    """OpenLibrary API 调用"""
    
    def __init__(self):
        self.base_url = config.OPENLIBRARY_BASE_URL
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.proxy = config.PROXY_URL if config.PROXY_ENABLED else None
        
    async def search_by_isbn(self, isbn: str) -> Optional[Dict[str, Any]]:
        """
        通过 ISBN 搜索书籍
        
        Args:
            isbn: ISBN 号
            
        Returns:
            搜索结果
        """
        if not isbn:
            return None
            
        url = f"{self.base_url}/search.json?isbn={isbn}"
        
        try:
            connector = aiohttp.TCPConnector(ssl=False) if self.proxy else None
            async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
                async with session.get(url, proxy=self.proxy) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    docs = data.get("docs", [])
                    
                    if not docs:
                        return None
                    
                    return docs[0]
                    
        except Exception as e:
            Logger.warning(f"OpenLibrary 搜索失败: {e}")
            return None
            
    async def get_work(self, work_id: str) -> Optional[Dict[str, Any]]:
        """
        获取作品详情
        
        Args:
            work_id: OpenLibrary Work ID
            
        Returns:
            作品详情
        """
        url = f"{self.base_url}/works/{work_id}.json"
        
        try:
            connector = aiohttp.TCPConnector(ssl=False) if self.proxy else None
            async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
                async with session.get(url, proxy=self.proxy) as response:
                    if response.status != 200:
                        return None
                    
                    return await response.json()
                    
        except Exception as e:
            Logger.warning(f"OpenLibrary 获取作品失败: {e}")
            return None
            
    async def get_author(self, author_id: str) -> Optional[Dict[str, Any]]:
        """
        获取作者信息
        
        Args:
            author_id: OpenLibrary Author ID
            
        Returns:
            作者信息
        """
        url = f"{self.base_url}/authors/{author_id}.json"
        
        try:
            connector = aiohttp.TCPConnector(ssl=False) if self.proxy else None
            async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
                async with session.get(url, proxy=self.proxy) as response:
                    if response.status != 200:
                        return None
                    
                    return await response.json()
                    
        except Exception as e:
            Logger.warning(f"OpenLibrary 获取作者失败: {e}")
            return None
            
    async def get_book_data(self, isbn: str) -> Optional[Dict[str, Any]]:
        """
        获取书籍完整数据
        
        Args:
            isbn: ISBN 号
            
        Returns:
            书籍数据
        """
        Logger.info(f"正在从 OpenLibrary 获取数据: ISBN {isbn}")
        
        search_result = await self.search_by_isbn(isbn)
        if not search_result:
            Logger.warning(f"OpenLibrary 未找到 ISBN: {isbn}")
            return None
        
        result = {
            "isbn": isbn,
            "source": "openlibrary"
        }
        
        # 基本信息
        result["title"] = search_result.get("title", "")
        result["title_original"] = search_result.get("title", "")
        
        # 作者
        author_names = search_result.get("author_name", [])
        result["authors"] = author_names
        
        # 封面
        cover_id = search_result.get("cover_i")
        if cover_id:
            result["cover_url"] = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
        
        # 首次出版年份
        first_publish = search_result.get("first_publish_year")
        if first_publish:
            result["first_publish_year"] = first_publish
        
        # OpenLibrary ID
        work_key = search_result.get("key", "")
        if work_key:
            result["openlibrary_id"] = work_key.replace("/works/", "")
            result["openlibrary_url"] = f"{self.base_url}{work_key}"
        
        # 获取更详细的作品信息
        if work_key:
            work_data = await self.get_work(work_key.replace("/works/", ""))
            if work_data:
                # 简介
                description = work_data.get("description")
                if isinstance(description, dict):
                    result["description"] = description.get("value", "")
                elif isinstance(description, str):
                    result["description"] = description
                
                # 封面列表
                covers = work_data.get("covers", [])
                if covers:
                    result["cover_ids"] = covers
                    result["cover_urls"] = [f"https://covers.openlibrary.org/b/id/{c}-L.jpg" for c in covers[:5]]
                
                # 主题标签
                subjects = work_data.get("subjects", [])
                result["subjects"] = subjects[:10]
        
        Logger.success(f"OpenLibrary 数据获取完成: {result.get('title', '')}")
        return result
        
    async def get_rating(self, work_id: str) -> Optional[float]:
        """
        获取评分
        
        OpenLibrary 评分是 5 分制，需要转换为 10 分制
        
        Args:
            work_id: OpenLibrary Work ID
            
        Returns:
            评分（10 分制）
        """
        url = f"{self.base_url}/works/{work_id}/ratings.json"
        
        try:
            connector = aiohttp.TCPConnector(ssl=False) if self.proxy else None
            async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
                async with session.get(url, proxy=self.proxy) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    avg = data.get("summary", {}).get("average")
                    
                    if avg:
                        # 转换为 10 分制
                        return round(float(avg) * 2, 1)
                    
                    return None
                    
        except Exception as e:
            Logger.warning(f"OpenLibrary 获取评分失败: {e}")
            return None
