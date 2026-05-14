# -*- coding: utf-8 -*-
"""
OpenLibrary 爬虫 - 独立脚本

一次性获取全部信息：search + work + rating + author
纯 REST API，无需浏览器

输出字段：
- isbn, title, title_original, authors, translators
- cover_url, cover_urls, cover_ids
- first_publish_year, publisher, language
- openlibrary_id, openlibrary_url
- description, subjects
- rating, rating_count
- author_details (作者详情列表)
"""
import aiohttp
from typing import Dict, Any, Optional, List

import config
from utils import Logger


class OpenLibraryCrawler:

    def __init__(self):
        self.base_url = config.OPENLIBRARY_BASE_URL
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.proxy = config.PROXY_URL if config.PROXY_ENABLED else None
        self.session: Optional[aiohttp.ClientSession] = None

    async def init(self):
        if self.session is None:
            connector = aiohttp.TCPConnector(ssl=False) if self.proxy else None
            self.session = aiohttp.ClientSession(timeout=self.timeout, connector=connector)

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def crawl(self, isbn: str) -> Optional[Dict[str, Any]]:
        """
        一次性获取 OpenLibrary 全部信息

        Args:
            isbn: ISBN 号

        Returns:
            完整的 OpenLibrary 数据字典
        """
        await self.init()

        Logger.info(f"[openlibrary] 正在获取数据: ISBN {isbn}")

        search_result = await self._search_by_isbn(isbn)
        if not search_result:
            Logger.warning(f"[openlibrary] 未找到 ISBN: {isbn}")
            return None

        result = {
            "isbn": isbn,
            "source": "openlibrary",
        }

        result["title"] = search_result.get("title", "")
        result["title_original"] = search_result.get("title", "")

        result["authors"] = search_result.get("author_name", [])

        result["translators"] = search_result.get("translator_name", [])

        cover_id = search_result.get("cover_i")
        if cover_id:
            result["cover_url"] = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

        first_publish = search_result.get("first_publish_year")
        if first_publish:
            result["first_publish_year"] = first_publish

        result["publisher"] = search_result.get("publisher", [])
        if isinstance(result["publisher"], list) and result["publisher"]:
            result["publisher"] = result["publisher"][0]

        result["language"] = search_result.get("language", [])
        if isinstance(result["language"], list) and result["language"]:
            result["language"] = result["language"][0]

        work_key = search_result.get("key", "")
        if work_key:
            result["openlibrary_id"] = work_key.replace("/works/", "")
            result["openlibrary_url"] = f"{self.base_url}{work_key}"

        if work_key:
            work_data = await self._get_work(work_key.replace("/works/", ""))
            if work_data:
                description = work_data.get("description")
                if isinstance(description, dict):
                    result["description"] = description.get("value", "")
                elif isinstance(description, str):
                    result["description"] = description

                covers = work_data.get("covers", [])
                if covers:
                    result["cover_ids"] = covers
                    result["cover_urls"] = [f"https://covers.openlibrary.org/b/id/{c}-L.jpg" for c in covers[:5]]

                subjects = work_data.get("subjects", [])
                result["subjects"] = subjects[:10]

            rating_data = await self._get_rating(work_key.replace("/works/", ""))
            if rating_data is not None:
                result["rating"] = rating_data

            rating_count = await self._get_rating_count(work_key.replace("/works/", ""))
            if rating_count is not None:
                result["rating_count"] = rating_count

        author_keys = search_result.get("author_key", [])
        if author_keys:
            author_details = []
            for author_key in author_keys[:5]:
                author_data = await self._get_author(author_key)
                if author_data:
                    author_details.append(author_data)
            if author_details:
                result["author_details"] = author_details

        Logger.success(f"[openlibrary] 数据获取完成: {result.get('title', '')}")
        return result

    async def _search_by_isbn(self, isbn: str) -> Optional[Dict]:
        url = f"{self.base_url}/search.json?isbn={isbn}"
        try:
            async with self.session.get(url, proxy=self.proxy) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                docs = data.get("docs", [])
                return docs[0] if docs else None
        except Exception as e:
            Logger.warning(f"[openlibrary] 搜索失败: {e}")
            return None

    async def _get_work(self, work_id: str) -> Optional[Dict]:
        url = f"{self.base_url}/works/{work_id}.json"
        try:
            async with self.session.get(url, proxy=self.proxy) as response:
                if response.status != 200:
                    return None
                return await response.json()
        except Exception as e:
            Logger.warning(f"[openlibrary] 获取作品失败: {e}")
            return None

    async def _get_author(self, author_id: str) -> Optional[Dict]:
        url = f"{self.base_url}/authors/{author_id}.json"
        try:
            async with self.session.get(url, proxy=self.proxy) as response:
                if response.status != 200:
                    return None
                return await response.json()
        except Exception as e:
            Logger.warning(f"[openlibrary] 获取作者失败: {e}")
            return None

    async def _get_rating(self, work_id: str) -> Optional[float]:
        url = f"{self.base_url}/works/{work_id}/ratings.json"
        try:
            async with self.session.get(url, proxy=self.proxy) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                avg = data.get("summary", {}).get("average")
                if avg:
                    return round(float(avg) * 2, 1)
                return None
        except Exception:
            return None

    async def _get_rating_count(self, work_id: str) -> Optional[int]:
        url = f"{self.base_url}/works/{work_id}/ratings.json"
        try:
            async with self.session.get(url, proxy=self.proxy) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                count = data.get("summary", {}).get("count")
                return int(count) if count else None
        except Exception:
            return None