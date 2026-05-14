# -*- coding: utf-8 -*-
"""
维基百科爬虫 - 独立脚本

一次性获取全部信息：搜索 + 消歧 + 详情提取
独立浏览器实例，不复用其他数据源的页面

输出字段：
- url, wikipedia_id, title, title_original
- summary, info (完整信息框字典)
- author, country, language
- awards, quotes
- publisher, year, pages, isbn, series, translator, genre (从 info 提取)
"""
import asyncio
import random
import re
from typing import Dict, Any, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

import config
from utils import Logger
from sources.base_crawler import BaseCrawler


class WikipediaCrawler(BaseCrawler):

    def __init__(self):
        super().__init__(source_name="wikipedia")

    async def crawl(self, title: str, original_title: str = "") -> Optional[Dict[str, Any]]:
        """
        一次性获取维基百科全部信息

        Args:
            title: 书名（中文）
            original_title: 原名（外文）

        Returns:
            完整的维基百科数据字典
        """
        if not self.page:
            await self.init_browser()

        Logger.info(f"[wikipedia] 正在搜索: {title}")

        wiki_url = await self._search(title, original_title)
        if not wiki_url:
            Logger.warning(f"[wikipedia] 未找到词条: {title}")
            return None

        data = await self._get_detail(wiki_url)
        return data

    async def _search(self, title: str, original_title: str = "") -> Optional[str]:
        """搜索词条"""
        search_strategies = []

        search_strategies.append(f"{config.WIKIPEDIA_BASE_URL}/wiki/{quote(title)}_(小说)")
        search_strategies.append(f"{config.WIKIPEDIA_BASE_URL}/wiki/{quote(title)}_(书)")
        search_strategies.append(f"{config.WIKIPEDIA_BASE_URL}/wiki/{quote(title)}")

        if original_title:
            search_strategies.append(f"{config.WIKIPEDIA_BASE_URL}/wiki/{quote(original_title)}")

        search_strategies.append(f"{config.WIKIPEDIA_BASE_URL}/w/index.php?search={quote(title + ' 小说')}&fulltext=1")

        for i, url in enumerate(search_strategies):
            try:
                Logger.info(f"[wikipedia] 尝试策略 {i + 1}: {url}")
                await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

                current_url = self.page.url
                content = await self.page.content()

                if "search" in current_url or "Special:" in current_url:
                    soup = BeautifulSoup(content, "html.parser")
                    results = soup.select(".mw-search-result-heading a")

                    if results:
                        best_result = None
                        for result in results:
                            result_text = result.text.strip()
                            if title in result_text and any(kw in result_text for kw in ["小说", "书", "作品", "文学"]):
                                best_result = result
                                break

                        if not best_result:
                            for result in results:
                                if title in result.text:
                                    best_result = result
                                    break

                        if best_result:
                            href = best_result.get("href", "")
                            if href:
                                found_url = f"{config.WIKIPEDIA_BASE_URL}{href}" if href.startswith("/") else href
                                Logger.success(f"[wikipedia] 找到词条: {found_url}")
                                return found_url

                    continue

                if "您可以新建这个页面" in content or "新建这个页面" in content:
                    continue

                soup = BeautifulSoup(content, "html.parser")
                content_div = soup.select_one("#mw-content-text")
                if content_div:
                    Logger.success(f"[wikipedia] 找到词条: {current_url}")
                    return current_url

            except Exception as e:
                Logger.warning(f"[wikipedia] 策略 {i + 1} 失败: {e}")
                continue

        Logger.warning(f"[wikipedia] 未找到词条: {title}")
        return None

    async def _get_detail(self, url: str) -> Dict[str, Any]:
        """获取词条内容"""
        Logger.info(f"[wikipedia] 正在获取内容: {url}")

        result = {"url": url, "source": "wikipedia"}

        try:
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            # 词条名
            title_elem = soup.select_one("#firstHeading") or soup.select_one("h1")
            title_text = title_elem.text.strip() if title_elem else ""
            title_text = re.sub(r'\[编辑\]$', '', title_text)
            result["title"] = title_text

            if not re.match(r'^[\u4e00-\u9fa5]', title_text):
                result["title_original"] = title_text

            # 词条 ID
            wiki_id_match = re.search(r'/wiki/(.+)$', url)
            if wiki_id_match:
                result["wikipedia_id"] = wiki_id_match.group(1)

            # 简介
            content_div = soup.select_one("#mw-content-text")
            if content_div:
                paragraphs = content_div.select("p")
                for para in paragraphs:
                    para_text = para.text.strip()
                    if para_text and len(para_text) > 20:
                        if not any(skip in para_text for skip in [
                            "可能出现此提示的其他原因",
                            "维基百科目前没有",
                            "您可以新建这个页面",
                            "本条目需要扩充",
                            "本条目需要精通",
                        ]):
                            result["summary"] = para_text
                            break

            # 信息框
            infobox = soup.select_one(".infobox")
            if infobox:
                rows = infobox.select("tr")
                info = {}
                for row in rows:
                    th = row.select_one("th")
                    td = row.select_one("td")
                    if th and td:
                        key = th.text.strip()
                        value = td.text.strip()
                        info[key] = value

                result["info"] = info

                # 从 info 提取关键字段
                for key, target in [
                    ("原名", "title_original"),
                    ("Original title", "title_original"),
                    ("作者", "author"),
                    ("Author", "author"),
                    ("国家", "country"),
                    ("Country", "country"),
                    ("语言", "language"),
                    ("Language", "language"),
                    ("出版商", "publisher"),
                    ("Publisher", "publisher"),
                    ("出版日期", "year"),
                    ("Published", "year"),
                    ("页数", "pages"),
                    ("Pages", "pages"),
                    ("ISBN", "isbn"),
                    ("系列", "series"),
                    ("Series", "series"),
                    ("译者", "translator"),
                    ("Translator", "translator"),
                    ("体裁", "genre"),
                    ("Genre", "genre"),
                ]:
                    if key in info and key not in result:
                        val = info[key]
                        if target == "year":
                            year_match = re.search(r"(\d{4})", val)
                            if year_match:
                                result[target] = int(year_match.group(1))
                        elif target == "pages":
                            pages_match = re.search(r"(\d+)", val)
                            if pages_match:
                                result[target] = int(pages_match.group(1))
                        else:
                            result[target] = val

            # 获奖
            awards = []
            award_section = soup.find("span", {"id": re.compile(r"获奖|奖项|Awards", re.I)})
            if award_section:
                award_list = award_section.find_next("ul")
                if award_list:
                    for li in award_list.select("li")[:10]:
                        awards.append(li.text.strip())
            if awards:
                result["awards"] = awards

            # 名句
            quotes = []
            quote_section = soup.find("span", {"id": re.compile(r"名言|语录|Quotes", re.I)})
            if quote_section:
                quote_list = quote_section.find_next("ul")
                if quote_list:
                    for li in quote_list.select("li")[:10]:
                        quotes.append({"text": li.text.strip(), "source": title_text})
            if quotes:
                result["quotes"] = quotes

            Logger.success("[wikipedia] 数据获取完成")

        except Exception as e:
            Logger.error(f"[wikipedia] 解析失败: {e}")

        return result