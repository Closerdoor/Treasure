# -*- coding: utf-8 -*-
"""
Wikipedia 电影词条采集。

Wikipedia 作为剧情、信息框、获奖/发行资料的补充源。采集层保留信息框原始字段，
同时输出一组标准化字段，方便后续和豆瓣、TMDB、OMDb 做合并核对。
"""
import asyncio
import random
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote, unquote, urljoin

from bs4 import BeautifulSoup, Tag
from playwright.async_api import Page

import config
from utils import Logger


class WikipediaCrawler:
    """Wikipedia 电影词条采集器。"""

    MOVIE_HINTS = (
        "导演", "執導", "监制", "劇本", "编剧", "主演", "上映", "片长",
        "directed", "starring", "release", "running time", "film"
    )

    PLOT_HEADINGS = ("剧情", "劇情", "故事", "情节", "劇情簡介", "剧情简介", "Plot", "Synopsis")
    AWARD_HEADINGS = (
        "获奖", "獲獎", "奖项", "獎項", "荣誉", "榮譽", "Awards", "Accolades"
    )

    INFOBOX_ALIASES = {
        "导演": "directors",
        "導演": "directors",
        "监制": "producers",
        "監製": "producers",
        "制片": "producers",
        "剧本": "writers",
        "劇本": "writers",
        "编剧": "writers",
        "編劇": "writers",
        "原著": "based_on",
        "主演": "cast",
        "配乐": "music",
        "配樂": "music",
        "摄影": "cinematography",
        "攝影": "cinematography",
        "剪辑": "editors",
        "剪輯": "editors",
        "制片商": "production_companies",
        "製片商": "production_companies",
        "片长": "runtime",
        "片長": "runtime",
        "产地": "countries",
        "產地": "countries",
        "语言": "languages",
        "語言": "languages",
        "上映日期": "release_dates",
        "发行商": "distributors",
        "發行商": "distributors",
        "预算": "budget",
        "預算": "budget",
        "票房": "box_office",
        "续作": "sequels",
        "續集": "sequels",
    }

    def __init__(self, page: Page):
        self.page = page
        self.base_url = config.WIKIPEDIA_BASE_URL

    async def search(self, title: str, original_title: str = "") -> Optional[str]:
        """搜索并返回最可能的电影词条 URL。"""
        Logger.info(f"正在搜索 Wikipedia: {title}")

        search_titles = [
            f"{title} (电影)",
            f"{title} (電影)",
            f"{title} (film)",
            f"{original_title} (film)" if original_title else None,
            original_title if original_title else None,
            title,
        ]

        for search_title in [item for item in search_titles if item]:
            url = f"{self.base_url}/wiki/{quote(search_title)}"
            try:
                await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

                resolved = await self._resolve_search_page()
                if resolved:
                    await self.page.goto(resolved, timeout=30000, wait_until="domcontentloaded")
                    await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                    url = resolved

                if await self._is_movie_page():
                    Logger.success(f"找到 Wikipedia 电影词条: {self.page.url}")
                    return self.page.url
            except Exception as e:
                Logger.warning(f"Wikipedia 搜索 '{search_title}' 失败: {e}")

        Logger.warning(f"Wikipedia 未找到电影词条: {title}")
        return None

    async def _resolve_search_page(self) -> Optional[str]:
        current_url = self.page.url
        if "search=" not in current_url and "Special:" not in current_url:
            return None

        soup = BeautifulSoup(await self.page.content(), "html.parser")
        first_result = soup.select_one(".mw-search-result-heading a")
        if first_result and first_result.get("href"):
            return urljoin(self.base_url, first_result["href"])
        return None

    async def _is_movie_page(self) -> bool:
        """判断当前页面是否像电影词条。"""
        try:
            soup = BeautifulSoup(await self.page.content(), "html.parser")
            if soup.select_one("#noarticletext"):
                return False

            infobox_text = self._clean_text(soup.select_one(".infobox").get_text(" ", strip=True)) if soup.select_one(".infobox") else ""
            if any(hint.lower() in infobox_text.lower() for hint in self.MOVIE_HINTS):
                return True

            for heading in soup.find_all(["h2", "h3"]):
                if self._heading_matches(heading, self.PLOT_HEADINGS):
                    return True
            return False
        except Exception:
            return False

    async def get_detail(self, url: str) -> Dict[str, Any]:
        """获取 Wikipedia 词条详情。"""
        Logger.info(f"正在获取 Wikipedia 内容: {url}")

        result: Dict[str, Any] = {
            "url": url,
            "source": "wikipedia",
        }

        try:
            if self.page.url != url:
                await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            soup = BeautifulSoup(await self.page.content(), "html.parser")
            title = self._extract_title(soup)
            result["title"] = title
            result["wikipedia_id"] = self._extract_wikipedia_id(url)
            result["summary"] = self._extract_summary(soup)
            result["lead_paragraphs"] = self._extract_lead_paragraphs(soup)[:3]

            plot = self._extract_section_text(soup, self.PLOT_HEADINGS)
            if plot:
                result["plot"] = plot

            infobox = self._extract_infobox(soup)
            if infobox:
                result["infobox"] = infobox
                result.update(infobox)
                result.update(self._normalize_infobox(infobox))

            result["awards"] = self._extract_awards(soup)
            result["quotes"] = self._extract_quotes(soup)
            result["categories"] = self._extract_categories(soup)

            Logger.success("Wikipedia 内容获取完成")
        except Exception as e:
            Logger.error(f"Wikipedia 内容获取失败: {e}")

        return result

    def _extract_title(self, soup: BeautifulSoup) -> str:
        title_elem = soup.select_one("#firstHeading") or soup.select_one("h1")
        return self._clean_text(title_elem.get_text(" ", strip=True)) if title_elem else ""

    def _extract_wikipedia_id(self, url: str) -> str:
        match = re.search(r"/wiki/(.+)$", url)
        return unquote(match.group(1)).replace("_", " ") if match else ""

    def _extract_summary(self, soup: BeautifulSoup) -> str:
        content = (
            soup.select_one("#mw-content-text .mw-parser-output")
            or soup.select_one("#mw-content-text")
            or soup.select_one(".mw-parser-output")
        )
        if not content:
            return ""

        paragraphs = []
        for elem in content.children:
            if isinstance(elem, Tag) and elem.name in ["h2", "h3"]:
                break
            if not isinstance(elem, Tag):
                continue
            candidates = [elem] if elem.name == "p" else elem.find_all("p", recursive=True)
            for p in candidates:
                text = self._clean_text(p.get_text(" ", strip=True))
                if text and not text.startswith("坐标"):
                    paragraphs.append(text)
                    break
            if paragraphs:
                break

        if not paragraphs:
            for p in content.find_all("p"):
                if p.find_parent(["table", "style", "script"]):
                    continue
                text = self._clean_text(p.get_text(" ", strip=True))
                if text and not text.startswith("坐标"):
                    paragraphs.append(text)
                    break

        return paragraphs[0] if paragraphs else ""

    def _extract_lead_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        content = (
            soup.select_one("#mw-content-text .mw-parser-output")
            or soup.select_one("#mw-content-text")
            or soup.select_one(".mw-parser-output")
        )
        if not content:
            return []
        paragraphs = []
        for elem in content.children:
            if isinstance(elem, Tag) and elem.name in ["h2", "h3"]:
                break
            if not isinstance(elem, Tag):
                continue
            candidates = [elem] if elem.name == "p" else elem.find_all("p", recursive=True)
            for p in candidates:
                if p.find_parent(["table", "style", "script"]):
                    continue
                text = self._clean_text(p.get_text(" ", strip=True))
                if text and not text.startswith("坐标"):
                    paragraphs.append(text)
        return self._dedupe(paragraphs)

    def _extract_infobox(self, soup: BeautifulSoup) -> Dict[str, str]:
        infobox = soup.select_one(".infobox")
        if not infobox:
            return {}

        data = {}
        for row in infobox.select("tr"):
            th = row.select_one("th")
            td = row.select_one("td")
            if not th or not td:
                continue
            key = self._clean_label(th.get_text(" ", strip=True))
            value = self._clean_text(td.get_text("\n", strip=True))
            if key and value:
                data[key] = value
        return data

    def _normalize_infobox(self, infobox: Dict[str, str]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for raw_key, raw_value in infobox.items():
            key = self._clean_label(raw_key)
            target = self.INFOBOX_ALIASES.get(key)
            if not target:
                continue
            if target in {
                "directors", "producers", "writers", "cast", "music", "cinematography",
                "editors", "production_companies", "countries", "languages", "distributors",
                "sequels"
            }:
                normalized[target] = self._split_people_or_items(raw_value)
            else:
                normalized[target] = raw_value
        return normalized

    def _extract_section_text(self, soup: BeautifulSoup, headings: tuple[str, ...]) -> str:
        heading = self._find_heading(soup, headings)
        if not heading:
            return ""

        paragraphs = []
        for elem in heading.find_all_next():
            if elem is heading:
                continue
            if isinstance(elem, Tag) and elem.name in ["h2", "h3"]:
                break
            if isinstance(elem, Tag) and elem.name == "p":
                text = self._clean_text(elem.get_text(" ", strip=True))
                if text:
                    paragraphs.append(text)
        return "\n\n".join(paragraphs)

    def _extract_awards(self, soup: BeautifulSoup) -> List[str]:
        heading = self._find_heading(soup, self.AWARD_HEADINGS)
        if not heading:
            return []

        awards = []
        for elem in heading.find_all_next():
            if elem is heading:
                continue
            if isinstance(elem, Tag) and elem.name in ["h2", "h3"]:
                break
            if isinstance(elem, Tag) and elem.name == "li":
                text = self._clean_text(elem.get_text(" ", strip=True))
                if text:
                    awards.append(text)
            elif isinstance(elem, Tag) and elem.name == "tr":
                cells = [
                    self._clean_text(cell.get_text(" ", strip=True))
                    for cell in elem.find_all(["th", "td"], recursive=False)
                ]
                cells = [cell for cell in cells if cell]
                if cells:
                    awards.append(" | ".join(cells))
            elif isinstance(elem, Tag) and elem.name == "p":
                text = self._clean_text(elem.get_text(" ", strip=True))
                if text:
                    awards.append(text)
        return self._dedupe(awards)

    def _extract_quotes(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        quotes = []
        for quote_elem in soup.select("blockquote"):
            text = self._clean_text(quote_elem.get_text(" ", strip=True))
            if text:
                quotes.append({"text": text, "source": "wikipedia"})
        return quotes

    def _extract_categories(self, soup: BeautifulSoup) -> List[str]:
        categories = []
        for anchor in soup.select("#mw-normal-catlinks a"):
            text = self._clean_text(anchor.get_text(" ", strip=True))
            if text and text != "分类":
                categories.append(text)
        return categories

    def _find_heading(self, soup: BeautifulSoup, headings: tuple[str, ...]) -> Optional[Tag]:
        for heading in soup.find_all(["h2", "h3"]):
            if self._heading_matches(heading, headings):
                return heading
        return None

    def _heading_matches(self, heading: Tag, headings: tuple[str, ...]) -> bool:
        text = self._clean_text(heading.get_text(" ", strip=True))
        text = re.sub(r"\[.*?\]", "", text)
        return any(item.lower() in text.lower() for item in headings)

    def _split_people_or_items(self, value: str) -> List[str]:
        value = re.sub(r"\[[^\]]+\]", "", value or "")
        pieces = re.split(r"\n|、|,|，|;|；", value)
        return self._dedupe([self._clean_text(piece) for piece in pieces if self._clean_text(piece)])

    def _dedupe(self, items: List[str]) -> List[str]:
        result = []
        for item in items:
            if item not in result:
                result.append(item)
        return result

    def _clean_label(self, text: str) -> str:
        text = self._clean_text(text)
        text = re.sub(r"\[[^\]]+\]", "", text)
        return text.replace("\xa0", "")

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\[[^\]]+\]", "", text or "")
        return re.sub(r"[ \t\r\f\v]+", " ", text).strip()

    async def crawl(self, title: str, original_title: str = "") -> Dict[str, Any]:
        """完整采集流程。"""
        result = {
            "title": title,
            "source": "wikipedia",
        }

        url = await self.search(title, original_title)
        if url:
            result = await self.get_detail(url)

        return result
