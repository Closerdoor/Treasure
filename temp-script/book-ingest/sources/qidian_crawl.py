# -*- coding: utf-8 -*-
"""
起点中文网爬虫 - 独立脚本

一次性获取全部信息：搜索 + 详情
独立浏览器实例，仅适用于网络小说

输出字段：
- url, title, authors[{name, url}]
- status (连载状态), word_count
- category (分类), summary
- cover_url, tags (标签)
- platform (raw留存)
"""
import asyncio
import json
import random
import re
from typing import Dict, Any, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

import config
from utils import Logger
from sources.base_crawler import BaseCrawler


class QidianCrawler(BaseCrawler):

    def __init__(self):
        super().__init__(source_name="qidian")

    async def crawl(self, title: str, author: str = "") -> Optional[Dict[str, Any]]:
        """
        一次性获取起点中文网全部信息

        Args:
            title: 小说名
            author: 作者名（可选，用于精确匹配）

        Returns:
            完整的起点中文网数据字典
        """
        if not self.page:
            await self.init_browser()

        Logger.info(f"[qidian] 正在搜索: {title}")

        book_url = await self._search(title, author)
        if not book_url:
            Logger.warning(f"[qidian] 未找到: {title}")
            return None

        return await self._get_detail(book_url)

    async def _search(self, title: str, author: str = "") -> Optional[str]:
        search_url = f"https://www.qidian.com/so/{quote(title)}.html"
        try:
            await self.page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            results = soup.select(".book-img-text ul li")

            for result in results:
                title_elem = result.select_one(".book-mid-info h4 a")
                author_elem = result.select_one(".book-mid-info .author a.name")

                if title_elem:
                    result_title = title_elem.text.strip()
                    result_author = author_elem.text.strip() if author_elem else ""

                    if title in result_title or result_title in title:
                        if author and author not in result_author:
                            continue

                        href = title_elem.get("href", "")
                        if href:
                            if href.startswith("//"):
                                href = "https:" + href
                            Logger.success(f"[qidian] 找到: {href}")
                            return href

            return None
        except Exception as e:
            Logger.error(f"[qidian] 搜索失败: {e}")
            return None

    async def _get_detail(self, url: str) -> Dict[str, Any]:
        """获取小说详情"""
        Logger.info(f"[qidian] 获取详情: {url}")

        result = {"url": url, "source": "qidian"}

        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            title_elem = soup.select_one(".book-info h1 em")
            if title_elem:
                result["title"] = title_elem.text.strip()

            author_elem = soup.select_one(".book-info .writer a") or soup.select_one(".book-info .writer")
            if author_elem:
                author_name = author_elem.text.replace("作者:", "").strip()
                author_href = author_elem.get("href", "") if author_elem.name == "a" else ""
                if author_href and author_href.startswith("//"):
                    author_href = "https:" + author_href
                result["authors"] = [{"name": author_name, "url": author_href}]

            status_elem = soup.select_one(".book-info .tag")
            if status_elem:
                result["status"] = status_elem.text.strip()

            word_elem = soup.select_one(".book-info .total-count em")
            if word_elem:
                word_text = word_elem.text.strip()
                word_match = re.match(r"([\d.]+)\s*万", word_text)
                if word_match:
                    result["word_count"] = int(float(word_match.group(1)) * 10000)

            category_elem = soup.select_one(".book-info .type")
            if category_elem:
                result["category"] = category_elem.text.strip()

            intro_elem = soup.select_one(".book-info .intro")
            if intro_elem:
                result["summary"] = intro_elem.text.strip()

            cover_elem = soup.select_one(".book-img a img")
            if cover_elem:
                result["cover_url"] = cover_elem.get("src", "")

            result["platform"] = "起点中文网"

            # 标签
            tags = []
            tag_elems = soup.select(".book-info .tag a") or soup.select(".tag-wrap a")
            for tag_elem in tag_elems[:5]:
                tag_name = tag_elem.text.strip()
                if tag_name:
                    tags.append(tag_name)
            if tags:
                result["tags"] = tags

            Logger.success("[qidian] 数据获取完成")

        except Exception as e:
            Logger.error(f"[qidian] 解析失败: {e}")

        return result