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


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r"\s+", "", str(value))
    value = value.replace("：", ":")
    return value.strip()


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

            expected_title = _normalize_text(title)
            expected_author = _normalize_text(author)
            candidates = []
            results = soup.select(".book-img-text ul li, li.res-book-item, .res-book-item")

            for index, result in enumerate(results):
                title_elem = (
                    result.select_one(".book-mid-info h3.book-info-title a")
                    or result.select_one(".book-mid-info h4 a")
                    or result.select_one("h3 a[href*='/book/']")
                    or result.select_one("h4 a[href*='/book/']")
                    or result.select_one("a[href*='/book/']")
                )
                author_elem = (
                    result.select_one(".book-mid-info .author a.name")
                    or result.select_one(".author a.name")
                    or result.select_one("a[href*='author']")
                )

                if not title_elem:
                    continue

                result_title = title_elem.get("title") or title_elem.get_text(" ", strip=True)
                result_title = re.sub(r"在线阅读$", "", result_title).strip()
                result_author = author_elem.get_text(" ", strip=True) if author_elem else ""
                normalized_title = _normalize_text(result_title)
                normalized_author = _normalize_text(result_author)

                title_match = (
                    expected_title == normalized_title
                    or expected_title in normalized_title
                    or normalized_title in expected_title
                )
                if not title_match:
                    continue
                if expected_author and expected_author not in normalized_author:
                    continue

                href = title_elem.get("href", "")
                if not href:
                    continue
                if href.startswith("//"):
                    href = "https:" + href
                elif href.startswith("/"):
                    href = "https://www.qidian.com" + href

                score = 0
                if expected_title == normalized_title:
                    score += 100
                elif normalized_title in expected_title:
                    score += 60
                elif expected_title in normalized_title:
                    score += 40
                if expected_author and expected_author == normalized_author:
                    score += 30
                elif expected_author and expected_author in normalized_author:
                    score += 15
                score -= index
                candidates.append((score, href, result_title, result_author))

            if candidates:
                candidates.sort(key=lambda item: item[0], reverse=True)
                _, href, result_title, result_author = candidates[0]
                Logger.success(f"[qidian] 找到: {result_title} / {result_author} -> {href}")
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

            title_elem = soup.select_one("#bookName") or soup.select_one(".book-info h1 em")
            if title_elem:
                result["title"] = title_elem.text.strip()

            author_elem = (
                soup.select_one(".book-info .writer a")
                or soup.select_one(".book-info .writer")
                or soup.select_one(".book-meta .author")
            )
            if author_elem:
                author_name = re.sub(r"^(作者|作 者)\s*[:：]?\s*", "", author_elem.text.strip())
                author_href = author_elem.get("href", "") if author_elem.name == "a" else ""
                if author_href and author_href.startswith("//"):
                    author_href = "https:" + author_href
                result["authors"] = [{"name": author_name, "url": author_href}]

            status_elem = soup.select_one(".book-attribute span") or soup.select_one(".book-info .tag")
            if status_elem:
                result["status"] = status_elem.text.strip()

            word_elem = soup.select_one(".book-info .total-count em") or soup.select_one(".book-info .count em")
            if word_elem:
                word_text = word_elem.text.strip()
                word_match = re.match(r"([\d.]+)\s*万?", word_text)
                if word_match:
                    multiplier = 10000 if "万" in word_text else 1
                    result["word_count"] = int(float(word_match.group(1)) * multiplier)

            category_elem = soup.select_one(".book-info .type")
            if category_elem:
                result["category"] = category_elem.text.strip()
            else:
                categories = [
                    elem.text.strip()
                    for elem in soup.select(".book-attribute a")
                    if elem.text.strip()
                ]
                if categories:
                    result["category"] = " / ".join(categories)

            work_intro = ""
            for elem in soup.select("[class*=intro]"):
                text = re.sub(r"\s+", " ", elem.get_text(" ", strip=True)).strip()
                if "作品简介" in text:
                    work_intro = text.replace("作品简介", "", 1).strip()
                    break
            intro_elem = soup.select_one(".book-info .intro")
            if work_intro:
                result["summary"] = work_intro
            elif intro_elem:
                result["summary"] = intro_elem.text.strip()

            cover_elem = soup.select_one(".book-img a img") or soup.select_one("#bookImg img")
            if cover_elem:
                cover_url = cover_elem.get("src", "")
                if cover_url.startswith("//"):
                    cover_url = "https:" + cover_url
                result["cover_url"] = cover_url

            result["platform"] = "起点中文网"

            # 标签
            tags = []
            tag_elems = soup.select(".book-info .tag a") or soup.select(".tag-wrap a") or soup.select(".book-attribute a")
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
