# -*- coding: utf-8 -*-
"""
维基百科爬虫 - 独立脚本

一次性获取全部信息：搜索 + 消歧 + 详情提取
独立浏览器实例，不复用其他数据源的页面

输出字段：
- url, wikipedia_id, title, title_original
- summary (故事大纲), info (完整信息框字典)
- authors (列表), country, language
- quotes
- publisher, year, pages, isbn, series, translators (列表), genre (从 info 提取)
- title_original, other_titles (从翻译版本提取)
- cover_url (书籍封面)
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


def _search_aliases(title: str) -> list[str]:
    aliases = [title]
    for marker in ("：", ":"):
        if marker in title:
            short = title.split(marker, 1)[1].strip()
            if short:
                aliases.append(short)
    cleaned = re.sub(r"（卷[一二三四五六七八九十]+）", "", title).strip()
    if cleaned and cleaned not in aliases:
        aliases.append(cleaned)
    return aliases


def _is_related_title(expected: str, actual: str, summary: str = "") -> bool:
    aliases = _search_aliases(expected)
    actual_text = str(actual or "")
    context = f"{actual_text} {summary or ''}"
    return any(alias and (alias in context or actual_text in alias) for alias in aliases)


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
        if data and not _is_related_title(title, data.get("title", ""), data.get("summary", "")):
            Logger.warning(f"[wikipedia] 词条不匹配，已跳过。预期: {title}, 实际: {data.get('title', '')}")
            return None
        return data

    async def _search(self, title: str, original_title: str = "") -> Optional[str]:
        """搜索词条"""
        search_strategies = []

        for alias in _search_aliases(title):
            search_strategies.append(f"{config.WIKIPEDIA_BASE_URL}/wiki/{quote(alias)}_(小说)")
            search_strategies.append(f"{config.WIKIPEDIA_BASE_URL}/wiki/{quote(alias)}_(书)")
            search_strategies.append(f"{config.WIKIPEDIA_BASE_URL}/wiki/{quote(alias)}")

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
                title_elem = soup.select_one("#firstHeading") or soup.select_one("h1")
                title_text = title_elem.text.strip() if title_elem else ""
                if content_div and _is_related_title(title, title_text, content_div.get_text(" ", strip=True)[:500]):
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

            # 简介：优先取"故事大纲"章节，回退到首段
            content_div = soup.select_one("#mw-content-text")
            if content_div:
                outline_section = None
                for h in soup.select("h2[id], h3[id]"):
                    h_text = h.text.strip()
                    if re.match(r"故事大纲|剧情|情节|Synopsis|Plot", h_text, re.I):
                        outline_section = h
                        break
                if not outline_section:
                    for h in soup.select("h2[id], h3[id]"):
                        h_id = h.get("id", "")
                        if re.match(r"故事大纲|剧情|情节|Synopsis|Plot", h_id, re.I):
                            outline_section = h
                            break
                if outline_section:
                    heading_container = outline_section.parent
                    if heading_container and heading_container.name == "div":
                        section_content = []
                        current = heading_container
                        while current:
                            current = current.find_next_sibling()
                            if not current:
                                break
                            if current.name in ("h2", "h3"):
                                break
                            if current.name == "div" and "mw-heading" in current.get("class", []):
                                break
                            if current.name == "p":
                                text = current.text.strip()
                                if text:
                                    section_content.append(text)
                        if section_content:
                            result["summary"] = "\n".join(section_content)

                if not result.get("summary"):
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
                    ("作者", "authors"),
                    ("Author", "authors"),
                    ("国家", "country"),
                    ("Country", "country"),
                    ("语言", "language"),
                    ("Language", "language"),
                    ("出版商", "publisher"),
                    ("出版机构", "publisher"),
                    ("Publisher", "publisher"),
                    ("出版日期", "year"),
                    ("Published", "year"),
                    ("页数", "pages"),
                    ("Pages", "pages"),
                    ("ISBN", "isbn"),
                    ("系列", "series"),
                    ("Series", "series"),
                    ("译者", "translators"),
                    ("Translator", "translators"),
                    ("类型", "genre"),
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
                        elif target in ("authors", "translators"):
                            items = [a.strip() for a in re.split(r'[、,，\n]', val) if a.strip()]
                            result[target] = items
                        else:
                            result[target] = val

            # 名句
            quotes = []
            quote_section = None
            for h in soup.select("h2[id], h3[id]"):
                h_text = h.text.strip()
                if re.match(r"名言|语录|Quotes", h_text, re.I):
                    quote_section = h
                    break
            if quote_section:
                quote_list = quote_section.find_next("ul")
                if quote_list:
                    for li in quote_list.select("li")[:10]:
                        quotes.append({"text": li.text.strip(), "source": title_text})
            if quotes:
                result["quotes"] = quotes

            # 翻译版本：提取外文原名和别名
            translate_section = None
            for h in soup.select("h2[id]"):
                h_text = h.text.strip()
                if re.match(r"翻译版本|譯本|Translations", h_text, re.I):
                    translate_section = h
                    break
            if translate_section:
                foreign_titles = []
                heading_container = translate_section.parent
                if heading_container and heading_container.name == "div":
                    current = heading_container
                else:
                    current = translate_section
                while current:
                    current = current.find_next_sibling()
                    if not current:
                        break
                    if current.name in ("h2", "h3"):
                        break
                    if current.name == "div" and "mw-heading" in current.get("class", []):
                        break
                    if current.name == "ul":
                        for li in current.select("li"):
                            text = li.text.strip()
                            if not text:
                                continue
                            title_matches = re.findall(r'[《<](.+?)[》>]', text)
                            for t in title_matches:
                                if t and not re.match(r'^[\u4e00-\u9fa5]', t):
                                    foreign_titles.append(t)

                if foreign_titles:
                    result["title_original"] = foreign_titles[0]
                    if len(foreign_titles) > 1:
                        result["other_titles"] = foreign_titles[1:]

            # 封面图片
            if not result.get("cover_url"):
                infobox_img = soup.select_one(".infobox img")
                if infobox_img:
                    src = infobox_img.get("src", "")
                    if src and "badge" not in src and "icon" not in src and "logo" not in src:
                        if src.startswith("//"):
                            src = "https:" + src
                        result["cover_url"] = src

            Logger.success("[wikipedia] 数据获取完成")

        except Exception as e:
            Logger.error(f"[wikipedia] 解析失败: {e}")

        return result
