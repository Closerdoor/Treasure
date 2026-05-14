# -*- coding: utf-8 -*-
"""
当当网爬虫 - 独立脚本

一次性获取全部信息：搜索 + 详情 + 全部商品信息提取
独立浏览器实例，大幅补齐字段解析

输出字段：
- url, dangdang_id, title, authors, translators
- publisher, isbn, pages, publish_year
- price, original_price
- word_count, series_name
- cover_url, rating
- summary, author_intro, catalog, editor_recommend
- format (开本)
"""
import asyncio
import json
import random
import re
from typing import Dict, Any, Optional
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup

import config
from utils import Logger
from sources.base_crawler import BaseCrawler


class DangdangCrawler(BaseCrawler):

    def __init__(self):
        super().__init__(source_name="dangdang")

    async def crawl(self, isbn: str = None, title: str = None) -> Optional[Dict[str, Any]]:
        """
        一次性获取当当网全部信息

        Args:
            isbn: ISBN 号（优先）
            title: 书名

        Returns:
            完整的当当网数据字典
        """
        if not self.page:
            await self.init_browser()

        book_url = None

        if isbn:
            book_url = await self._search_by_isbn(isbn)

        if not book_url and title:
            book_url = await self._search_by_title(title)

        if not book_url:
            Logger.warning("[dangdang] 未找到书籍")
            return None

        return await self._get_detail(book_url)

    async def _search_by_isbn(self, isbn: str) -> Optional[str]:
        search_url = f"https://search.dangdang.com/?key={isbn}&act=input"
        try:
            Logger.info(f"[dangdang] 搜索 ISBN: {isbn}")
            await self.page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            result = soup.select_one(".shoplist li a")
            if result:
                href = result.get("href", "")
                if href:
                    if href.startswith("//"):
                        href = "https:" + href
                    Logger.success(f"[dangdang] 找到: {href}")
                    return href

            return None
        except Exception as e:
            Logger.error(f"[dangdang] 搜索失败: {e}")
            return None

    async def _search_by_title(self, title: str) -> Optional[str]:
        search_url = f"https://search.dangdang.com/?key={quote(title)}&act=input"
        try:
            Logger.info(f"[dangdang] 搜索: {title}")
            await self.page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            results = soup.select(".shoplist li")
            for result in results:
                link = result.select_one("a")
                title_elem = result.select_one("a")

                if link and title_elem:
                    result_title = title_elem.get("title", "") or title_elem.text.strip()
                    if title in result_title:
                        href = link.get("href", "")
                        if href:
                            if href.startswith("//"):
                                href = "https:" + href
                            Logger.success(f"[dangdang] 找到: {href}")
                            return href

            return None
        except Exception as e:
            Logger.error(f"[dangdang] 搜索失败: {e}")
            return None

    async def _get_detail(self, url: str) -> Dict[str, Any]:
        """获取图书详情"""
        Logger.info(f"[dangdang] 获取详情: {url}")

        result = {"url": url, "source": "dangdang"}

        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            # 滚动到底部加载完整内容
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            # 当当网商品 ID
            dangdang_id_match = re.search(r'/(\d{6,})\.html', url) or re.search(r'id=(\d+)', url)
            if dangdang_id_match:
                result["dangdang_id"] = dangdang_id_match.group(1)

            # 书名
            title_elem = (
                soup.select_one("h1.title")
                or soup.select_one(".product_title h1")
                or soup.select_one("div.name h1")
            )
            if title_elem:
                result["title"] = title_elem.text.strip()

            # 作者
            authors = []
            author_elems = (
                soup.select("span.author a")
                or soup.select("#author a")
                or soup.select(".product_info .author a")
            )
            for elem in author_elems:
                name = elem.text.strip()
                if name and name not in authors:
                    authors.append(name)
            if authors:
                result["authors"] = authors

            # 译者
            translators = []
            translator_elems = (
                soup.select("span.translator a")
                or soup.select("#translator a")
            )
            for elem in translator_elems:
                name = elem.text.strip()
                if name and name not in translators:
                    translators.append(name)
            if translators:
                result["translators"] = translators

            # 出版社
            publisher_elem = (
                soup.select_one(".key a[dd_name='出版社']")
                or soup.select_one(".spc_info a[href*='pub_id']")
                or soup.select_one(".publisher_info a")
            )
            if publisher_elem:
                result["publisher"] = publisher_elem.text.strip()

            # 封面图
            cover_elem = (
                soup.select_one("#main-img img")
                or soup.select_one(".product_img img")
                or soup.select_one("#largePic")
            )
            if cover_elem:
                cover_url = cover_elem.get("src", "") or cover_elem.get("data-src", "")
                if cover_url and cover_url.startswith("//"):
                    cover_url = "https:" + cover_url
                result["cover_url"] = cover_url

            # 价格
            price_elem = soup.select_one(".price_n") or soup.select_one(".price")
            if price_elem:
                price_text = price_elem.text.strip()
                price_match = re.search(r"[\d.]+", price_text)
                if price_match:
                    result["price"] = float(price_match.group())

            # 原价
            original_price_elem = soup.select_one(".price_r") or soup.select_one(".original-price")
            if original_price_elem:
                op_text = original_price_elem.text.strip()
                op_match = re.search(r"[\d.]+", op_text)
                if op_match:
                    result["original_price"] = float(op_match.group())

            # 评分
            rating_elem = soup.select_one(".star a") or soup.select_one(".rating_num")
            if rating_elem:
                rating_text = rating_elem.text.strip()
                rating_match = re.search(r"[\d.]+", rating_text)
                if rating_match:
                    result["rating"] = float(rating_match.group())

            # 详细参数区域
            info_items = soup.select(".key") or soup.select(".spc_info li")
            for item in info_items:
                text = item.text.strip()

                if "ISBN" in text or "国际标准书号" in text:
                    isbn_match = re.search(r"[\d-]{10,}", text)
                    if isbn_match:
                        result["isbn"] = isbn_match.group().replace("-", "")

                if "页数" in text:
                    pages_match = re.search(r"(\d+)\s*页", text)
                    if pages_match:
                        result["pages"] = int(pages_match.group(1))

                if "出版时间" in text or "出版日期" in text:
                    time_match = re.search(r"(\d{4})", text)
                    if time_match:
                        result["publish_year"] = int(time_match.group(1))

                if "开本" in text:
                    result["format"] = text.replace("开本", "").replace("：", "").replace(":", "").strip()

                if "字数" in text:
                    word_match = re.search(r"(\d+)", text)
                    if word_match:
                        result["word_count"] = int(word_match.group(1))

                if "丛书名" in text:
                    series_match = re.search(r"丛书名[：:]\s*(.+)", text)
                    if series_match:
                        result["series_name"] = series_match.group(1).strip()

            # 商品详情区域（内容简介、作者简介、目录等）
            # 尝试从详情标签页提取
            detail_sections = soup.select(".detail_section") or soup.select("#detail")
            for section in detail_sections:
                section_text = section.text.strip()

                if "内容简介" in section_text and not result.get("summary"):
                    summary_elem = section.select_one(".detail_content") or section
                    summary_text = summary_elem.text.replace("内容简介", "").strip()
                    if summary_text:
                        result["summary"] = summary_text[:2000]

                if "作者简介" in section_text and not result.get("author_intro"):
                    intro_elem = section.select_one(".detail_content") or section
                    intro_text = intro_elem.text.replace("作者简介", "").strip()
                    if intro_text:
                        result["author_intro"] = intro_text[:1000]

                if "目录" in section_text and not result.get("catalog"):
                    catalog_elem = section.select_one(".detail_content") or section
                    catalog_text = catalog_elem.text.replace("目录", "").strip()
                    if catalog_text:
                        result["catalog"] = catalog_text[:2000]

                if "编辑推荐" in section_text and not result.get("editor_recommend"):
                    rec_elem = section.select_one(".detail_content") or section
                    rec_text = rec_elem.text.replace("编辑推荐", "").strip()
                    if rec_text:
                        result["editor_recommend"] = rec_text[:1000]

            Logger.success("[dangdang] 数据获取完成")

        except Exception as e:
            Logger.error(f"[dangdang] 解析失败: {e}")

        return result