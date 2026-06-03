# -*- coding: utf-8 -*-
"""
百度百科爬虫 - 独立脚本

一次性获取全部信息：搜索 + 消歧 + 详情提取
独立浏览器实例，不复用其他数据源的页面

输出字段：
- url, baike_id, baike_title, baike_desc
- title, title_original
- authors (列表), country
- word_count, year
- publisher, language
- summary
- story (内容情节 / 故事情节)
- info (完整信息框字典)
- author_baike_url
- type (类型/体裁)
- serial_status (连载状态)
- serial_platform (首发平台)
- pages, price, isbn (从 info 提取)
"""
import asyncio
import json
import random
import re
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup

import config
from utils import Logger
from sources.base_crawler import BaseCrawler


def _search_aliases(title: str, author: str = "") -> list[str]:
    aliases = [title]
    for marker in ("：", ":"):
        if marker in title:
            short = title.split(marker, 1)[1].strip()
            if short:
                aliases.append(short)
    cleaned = re.sub(r"（卷[一二三四五六七八九十]+）", "", title).strip()
    if cleaned and cleaned not in aliases:
        aliases.append(cleaned)
    for base in list(aliases):
        for suffix in ("小说", "网络小说", "长篇小说"):
            value = f"{base} {suffix}"
            if value not in aliases:
                aliases.append(value)
        if author:
            value = f"{base} {author}"
            if value not in aliases:
                aliases.append(value)
    return aliases


def _is_related_title(expected: str, actual: str, summary: str = "") -> bool:
    if not expected or not actual:
        return False
    aliases = _search_aliases(expected)
    actual_text = str(actual)
    context = f"{actual_text} {summary or ''}"
    return any(alias and (alias in context or actual_text in alias) for alias in aliases)


def _looks_like_non_book_entry(data: Dict[str, Any]) -> bool:
    info = data.get("info") if isinstance(data.get("info"), dict) else {}
    context = " ".join(
        str(value or "")
        for value in [
            data.get("summary"),
            data.get("top_content"),
            data.get("story"),
            data.get("baike_desc"),
            *info.keys(),
            *info.values(),
        ]
    )
    non_book_markers = ["电视剧", "网络剧", "古装剧", "主演", "导演", "执导", "出品公司", "制片地区", "有声小说"]
    book_markers = ["网络小说", "长篇小说", "文学作品", "连载", "起点中文网"]
    return any(marker in context for marker in non_book_markers) and not any(marker in context for marker in book_markers)


def _score_book_candidate(text: str, expected_title: str, author: str = "", href: str = "") -> int:
    context = re.sub(r"\s+", "", str(text or ""))
    href_text = str(href or "")
    score = 0
    for alias in _search_aliases(expected_title):
        alias_key = re.sub(r"\s+", "", alias)
        if alias_key and alias_key in context:
            score += 30
            if context.startswith(alias_key):
                score += 20
            break
    if author:
        author_key = re.sub(r"\s+", "", author)
        if author_key and author_key in context:
            score += 80
    positive_weights = {
        "网络小说": 120,
        "长篇小说": 100,
        "小说": 70,
        "文学作品": 70,
        "起点中文网": 80,
        "连载": 40,
        "完结": 30,
        "作者": 20,
    }
    negative_weights = {
        "电视剧": 140,
        "网络剧": 140,
        "古装剧": 120,
        "电影": 110,
        "动画": 90,
        "动漫": 90,
        "漫画": 90,
        "游戏": 100,
        "手游": 100,
        "网游": 100,
        "有声小说": 80,
        "广播剧": 80,
        "主演": 100,
        "导演": 100,
        "执导": 100,
        "出品公司": 100,
        "制片地区": 100,
    }
    for marker, weight in positive_weights.items():
        if marker in context:
            score += weight
    for marker, weight in negative_weights.items():
        if marker in context:
            score -= weight
    if "fromModule=disambiguation" in href_text:
        score += 10
    return score


class BaikeCrawler(BaseCrawler):

    def __init__(self):
        super().__init__(source_name="baike")

    async def crawl(
        self,
        title: str,
        author: str = "",
        baike_url: str = "",
        baike_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        一次性获取百度百科全部信息

        Args:
            title: 书名

        Returns:
            完整的百度百科数据字典
        """
        manual_data = self._load_manual_html(title)
        if manual_data:
            Logger.success(f"[baike] 已从本地 HTML 解析: {title}")
            return manual_data

        if not self.page:
            await self.init_browser()

        await self._load_baike_cookies()

        Logger.info(f"[baike] 正在搜索: {title}")

        anchor_url = self._build_anchor_url(title, baike_url=baike_url, baike_id=baike_id)
        if anchor_url:
            Logger.info(f"[baike] 使用指定词条锚点: {anchor_url}")
            await self.page.goto(anchor_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            data = await self._get_detail(self.page.url, title, author)
            if data:
                data["_baikeAnchor"] = {"url": anchor_url, "id": str(baike_id or "")}
                return data
            Logger.warning("[baike] 指定词条未通过书籍 / 小说验收，停止保存")
            return None

        tried_urls = set()
        for _ in range(len(_search_aliases(title, author))):
            baike_url = await self._search(title, author, tried_urls)
            if not baike_url:
                break
            tried_urls.add(baike_url)
            data = await self._get_detail(baike_url, title, author)
            if data:
                return data

        wap_url = await self._search_wap_disambiguation(title, author, tried_urls)
        if wap_url:
            data = await self._get_detail(wap_url, title, author)
            if data:
                return data

        Logger.warning(f"[baike] 未找到词条: {title}")
        return None

    def _build_anchor_url(self, title: str, baike_url: str = "", baike_id: str = "") -> str:
        if baike_url:
            return str(baike_url).strip()
        if baike_id and title:
            return f"{config.BAIKE_BASE_URL}/item/{quote(title)}/{quote(str(baike_id).strip())}"
        return ""

    async def _load_baike_cookies(self):
        """加载 Cookie-Editor 导出的百度 Cookie，用于提高通过安全验证的概率。"""
        cookie_file = Path(config.OUTPUT_DIR) / "cookies" / "baike.json"
        if not cookie_file.exists() or not self.context:
            return

        try:
            raw_cookies = json.loads(cookie_file.read_text(encoding="utf-8"))
            if not isinstance(raw_cookies, list):
                Logger.warning(f"[baike] Cookie 文件不是数组，跳过: {cookie_file}")
                return

            same_site_map = {
                "strict": "Strict",
                "lax": "Lax",
                "none": "None",
                "no_restriction": "None",
                "unspecified": "Lax",
            }
            cookies = []
            for item in raw_cookies:
                if not isinstance(item, dict) or not item.get("name"):
                    continue
                cookie = {
                    "name": item.get("name"),
                    "value": item.get("value", ""),
                    "domain": item.get("domain") or ".baidu.com",
                    "path": item.get("path") or "/",
                    "httpOnly": bool(item.get("httpOnly")),
                    "secure": bool(item.get("secure")),
                    "sameSite": same_site_map.get(str(item.get("sameSite", "lax")).lower(), "Lax"),
                }
                if not item.get("session") and item.get("expirationDate"):
                    cookie["expires"] = int(float(item["expirationDate"]))
                cookies.append(cookie)

            if cookies:
                await self.context.add_cookies(cookies)
                Logger.info(f"[baike] 已加载百度 Cookie: {cookie_file} ({len(cookies)} 条)")
        except Exception as e:
            Logger.warning(f"[baike] Cookie 加载失败: {e}")

    def _load_manual_html(self, title: str) -> Optional[Dict[str, Any]]:
        """优先从 data/manual/baike/*.html 解析用户手动保存的百科页面。"""
        manual_dir = Path(config.OUTPUT_DIR) / "manual" / "baike"
        if not manual_dir.exists():
            return None

        for html_file in sorted(manual_dir.glob("*.html")):
            try:
                content = html_file.read_text(encoding="utf-8", errors="ignore")
                soup = BeautifulSoup(content, "html.parser")
                page_title = soup.title.get_text(strip=True) if soup.title else ""
                h1 = soup.select_one("h1")
                h1_text = h1.get_text(strip=True) if h1 else ""
                if title and title not in page_title and title not in h1_text:
                    continue

                data = self._parse_detail_html(content, title, source_url=str(html_file))
                if data:
                    data["_manualHtml"] = str(html_file)
                    return data
            except Exception as e:
                Logger.warning(f"[baike] 本地 HTML 解析失败: {html_file} - {e}")
        return None

    def _extract_page_data_from_content(self, content: str) -> Optional[Dict]:
        """从 HTML 字符串提取 PAGE_DATA JSON。"""
        try:
            start_idx = content.find('window.PAGE_DATA=')
            if start_idx < 0:
                return None
            start_idx += len('window.PAGE_DATA=')
            end_idx = content.find(';</script>', start_idx)
            if end_idx < 0:
                end_idx = content.find('</script>', start_idx)
            if end_idx < 0:
                return None
            return json.loads(content[start_idx:end_idx].strip())
        except Exception as e:
            Logger.warning(f"[baike] 提取 PAGE_DATA 失败: {e}")
            return None

    def _parse_detail_html(self, content: str, title: str, source_url: str = "") -> Optional[Dict[str, Any]]:
        """解析已经取得的百度百科 HTML，供线上页面和本地 HTML 共用。"""
        if (
            "百度安全验证" in content
            or "验证_百度百科" in content
            or "captcha" in source_url
            or "anticrawl" in source_url
        ):
            Logger.warning("[baike] 检测到百度安全验证页，跳过解析")
            return None

        soup = BeautifulSoup(content, "html.parser")
        result = {"url": source_url, "title": title, "source": "baike"}
        page_data = self._extract_page_data_from_content(content)

        if page_data:
            result["baike_id"] = page_data.get("lemmaId")
            result["baike_title"] = page_data.get("lemmaTitle")
            result["baike_desc"] = page_data.get("lemmaDesc")

            card_info = self._extract_card_info(page_data.get("card", {}))
            if card_info:
                result["info"] = card_info

                author_data = card_info.get("作者")
                if author_data:
                    author_name = author_data.get("title", "") if isinstance(author_data, dict) else str(author_data)
                    country_match = re.match(r'[\[【(（]([^\]】)）]+)[\]】)）]', author_name)
                    if country_match:
                        result["country"] = country_match.group(1)
                        author_name = re.sub(r'[\[【(（][^\]】)）]+[\]】)）]', '', author_name).strip()
                    authors = [a.strip() for a in re.split(r'[、，,]', author_name) if a.strip()]
                    if authors:
                        result["authors"] = authors
                        result["author"] = authors[0]

                word_count = self._parse_word_count(card_info)
                if word_count:
                    result["word_count"] = word_count
                if card_info.get("外文名"):
                    result["title_original"] = str(card_info["外文名"])
                year = self._extract_first_publish_year(card_info)
                if year:
                    result["year"] = year
                if card_info.get("出版社"):
                    result["publisher"] = str(card_info["出版社"])
                elif card_info.get("出版机构"):
                    result["publisher"] = str(card_info["出版机构"])
                if card_info.get("语言"):
                    result["language"] = str(card_info["语言"])
                if card_info.get("类型"):
                    result["type"] = str(card_info["类型"])
                if card_info.get("状态"):
                    result["serial_status"] = str(card_info["状态"])
                if card_info.get("首发平台") or card_info.get("连载平台"):
                    result["serial_platform"] = str(card_info.get("首发平台") or card_info.get("连载平台"))
                if card_info.get("页数"):
                    pages_match = re.search(r"(\d+)", str(card_info["页数"]))
                    if pages_match:
                        result["pages"] = int(pages_match.group(1))
                if card_info.get("定价"):
                    result["price"] = str(card_info["定价"])
                if card_info.get("ISBN"):
                    result["isbn"] = str(card_info["ISBN"])

            summary = self._extract_abstract(page_data.get("abstract", {}))
            description = page_data.get("description", "")
            if summary:
                result["summary"] = summary
                result["top_content"] = summary
            elif description and "..." not in description and "…" not in description:
                result["summary"] = description

        if not result.get("baike_title"):
            lemma_title = soup.select_one("h1")
            if lemma_title:
                result["baike_title"] = lemma_title.get_text(strip=True)

        if not result.get("summary"):
            summary_elem = (
                soup.select_one(".J-summary")
                or soup.select_one("[class*='lemmaSummary']")
                or soup.select_one(".lemma-summary")
            )
            if summary_elem:
                result["summary"] = summary_elem.get_text(strip=True)
                result["top_content"] = result["summary"]

        story_titles = ["内容情节", "内容介绍", "故事情节", "作品情节", "故事大纲", "剧情简介"]
        story = self._extract_section_text(soup, story_titles)
        if not story and page_data:
            story = self._extract_section_from_page_data(page_data, story_titles)
        if story:
            result["story"] = story

        author_links = soup.select("a[href*='/item/']")
        for link in author_links:
            link_text = link.get_text(strip=True)
            if "作者" in link_text or link_text in str(result.get("author", "")):
                href = link.get("href", "")
                if href:
                    result["author_baike_url"] = f"{config.BAIKE_BASE_URL}{href}" if href.startswith("/") else href
                    break

        meaningful_keys = {"summary", "story", "info", "author", "authors", "word_count", "title_original", "year"}
        if not any(result.get(key) for key in meaningful_keys):
            Logger.warning("[baike] 未提取到有效百科正文")
            return None
        if not _is_related_title(title, result.get("baike_title", ""), result.get("summary", "")):
            Logger.warning(
                f"[baike] 词条不匹配，已跳过。预期: {title}, 实际: {result.get('baike_title', '')}"
            )
            return None
        if _looks_like_non_book_entry(result):
            Logger.warning(f"[baike] 词条不是书籍 / 网络小说，已跳过: {result.get('baike_title', '')}")
            return None
        return result

    async def _search(self, title: str, author: str = "", skip_urls: set = None) -> Optional[str]:
        """搜索词条"""
        skip_urls = skip_urls or set()
        for alias in _search_aliases(title, author):
            encoded_title = quote(alias)
            url = f"{config.BAIKE_BASE_URL}/item/{encoded_title}"

            try:
                await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

                current_url = self.page.url
                if "error.html" in current_url or "status=404" in current_url:
                    continue
                if current_url in skip_urls:
                    continue
                if current_url.rstrip("/") == config.BAIKE_BASE_URL.rstrip("/"):
                    continue
                if "search" in current_url:
                    content = await self.page.content()
                    soup = BeautifulSoup(content, "html.parser")

                    candidates = []
                    for index, link in enumerate(soup.select(".result-list .result-title a, a[href*='/item/']")):
                        href = link.get("href", "")
                        if not href:
                            continue
                        container = link.find_parent(["div", "li", "section"]) or link
                        text = container.get_text(" ", strip=True)
                        score = _score_book_candidate(text, title, author, href) - index
                        candidates.append((score, href, text))
                    candidates.sort(key=lambda item: item[0], reverse=True)
                    if not candidates or candidates[0][0] <= 0:
                        Logger.warning(f"[baike] 搜索候选未命中书籍义项: {alias}")
                        continue
                    score, href, text = candidates[0]
                    url = f"{config.BAIKE_BASE_URL}{href}" if href.startswith("/") else href
                    Logger.info(f"[baike] 搜索候选评分 {score}: {text[:80]}")
                    await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                    current_url = self.page.url

                Logger.success(f"[baike] 找到词条: {current_url}")
                return current_url

            except Exception as e:
                Logger.error(f"[baike] 搜索失败: {e}")
                continue

        Logger.warning(f"[baike] 未找到词条: {title}")
        return None

    async def _search_wap_disambiguation(self, title: str, author: str = "", skip_urls: set = None) -> Optional[str]:
        """桌面入口误中影视等词条时，从移动百科多义词列表补充查找书籍义项。"""
        skip_urls = skip_urls or set()
        for alias in _search_aliases(title, author):
            url = f"https://wapbaike.baidu.com/item/{quote(alias)}"
            try:
                await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                content = await self.page.content()
                if "百度安全验证" in content or "验证_百度百科" in content:
                    Logger.warning("[baike] 移动百科触发安全验证，停止移动端候选查找")
                    return None
                soup = BeautifulSoup(content, "html.parser")
                candidates = []
                for index, link in enumerate(soup.select("a[href*='/item/']")):
                    href = link.get("href", "")
                    if not href:
                        continue
                    absolute = f"https://wapbaike.baidu.com{href}" if href.startswith("/") else href
                    decoded_href = unquote(absolute)
                    if title not in decoded_href:
                        continue
                    container = link.find_parent(["li", "div", "section"]) or link
                    text = container.get_text(" ", strip=True)
                    score = _score_book_candidate(text, title, author, absolute) - index
                    if score <= 0:
                        continue
                    desktop_url = absolute.replace("https://wapbaike.baidu.com", config.BAIKE_BASE_URL)
                    desktop_url = desktop_url.replace("http://wapbaike.baidu.com", config.BAIKE_BASE_URL)
                    if desktop_url in skip_urls:
                        continue
                    candidates.append((score, desktop_url, text))
                candidates.sort(key=lambda item: item[0], reverse=True)
                if candidates:
                    score, desktop_url, text = candidates[0]
                    Logger.info(f"[baike] 移动百科候选评分 {score}: {text[:80]}")
                    await self.page.goto(desktop_url, timeout=30000, wait_until="domcontentloaded")
                    await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                    Logger.success(f"[baike] 移动百科找到词条: {self.page.url}")
                    return self.page.url
            except Exception as e:
                Logger.error(f"[baike] 移动百科候选查找失败: {e}")
                continue
        return None

    async def _get_detail(self, url: str, title: str, author: str = "") -> Dict[str, Any]:
        """获取词条内容"""
        Logger.info(f"[baike] 正在获取内容: {url}")

        result = {"url": url, "title": title, "source": "baike"}

        try:
            await asyncio.sleep(1)
            content = await self.page.content()
            if (
                "百度安全验证" in content
                or "验证_百度百科" in content
                or "captcha" in self.page.url
                or "anticrawl" in self.page.url
                or "verify" in self.page.url
            ):
                Logger.warning("[baike] 触发百度安全验证，本次不保存稀疏数据")
                return None
            soup = BeautifulSoup(content, "html.parser")

            # 多义词消歧
            disambiguation_links = soup.find_all('a', href=lambda x: x and 'fromModule=disambiguation' in x)

            if not disambiguation_links and "多义词" in content:
                await asyncio.sleep(2)
                content = await self.page.content()
                soup = BeautifulSoup(content, "html.parser")
                disambiguation_links = soup.select('a[href*="fromModule=disambiguation"]')

            if disambiguation_links or "多义词" in content:
                Logger.info("[baike] 检测到多义词页面，查找小说义项...")
                scored_links = []
                for index, link in enumerate(disambiguation_links):
                    href = link.get("href", "")
                    container = link.find_parent(["li", "div", "section"]) or link
                    link_text = container.get_text(" ", strip=True)
                    score = _score_book_candidate(link_text, title, author, href) - index
                    scored_links.append((score, link, link_text))
                scored_links.sort(key=lambda item: item[0], reverse=True)
                novel_link = scored_links[0][1] if scored_links and scored_links[0][0] > 0 else None

                if novel_link:
                    href = novel_link.get("href", "")
                    if href:
                        new_url = f"{config.BAIKE_BASE_URL}{href}" if href.startswith("/") else href
                        Logger.info(f"[baike] 跳转到义项页面: {new_url}")
                        await self.page.goto(new_url, timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(2)
                        content = await self.page.content()
                        soup = BeautifulSoup(content, "html.parser")
                else:
                    Logger.warning("[baike] 多义词页没有可信小说义项，跳过")
                    return None

            parsed = self._parse_detail_html(content, title, source_url=self.page.url)
            if parsed:
                return parsed
            return None

            # 从 PAGE_DATA JSON 提取数据
            page_data = await self._extract_page_data()

            if page_data:
                result["baike_id"] = page_data.get("lemmaId")
                result["baike_title"] = page_data.get("lemmaTitle")
                result["baike_desc"] = page_data.get("lemmaDesc")

                card = page_data.get("card", {})
                card_info = self._extract_card_info(card)
                if card_info:
                    result["info"] = card_info

                    if "作者" in card_info:
                        author_data = card_info["作者"]
                        if isinstance(author_data, dict):
                            author_name = author_data.get("title", "")
                        else:
                            author_name = str(author_data)
                        
                        country_match = re.match(r'[\[【\(（]([^\]】\)）]+)[\]】\)）]', author_name)
                        if country_match:
                            result["country"] = country_match.group(1)
                            author_name = re.sub(r'[\[【\(（][^\]】\)）]+[\]】\)）]', '', author_name).strip()
                        
                        authors = [a.strip() for a in re.split(r'[、,，]', author_name) if a.strip()]
                        result["authors"] = authors

                    word_count = self._parse_word_count(card_info)
                    if word_count:
                        result["word_count"] = word_count

                    if "外文名" in card_info:
                        result["title_original"] = str(card_info["外文名"])

                    year = self._extract_first_publish_year(card_info)
                    if year:
                        result["year"] = year

                    if "出版社" in card_info:
                        result["publisher"] = str(card_info["出版社"])
                    elif "出版机构" in card_info:
                        result["publisher"] = str(card_info["出版机构"])

                    if "语言" in card_info:
                        result["language"] = str(card_info["语言"])

                    for type_key in ("文学体裁", "作品类型", "类型", "体裁"):
                        if type_key in card_info:
                            result["genre"] = str(card_info[type_key])
                            break

                    if "状态" in card_info:
                        result["serial_status"] = str(card_info["状态"])

                    if "首发平台" in card_info or "连载平台" in card_info:
                        result["serial_platform"] = str(card_info.get("首发平台") or card_info.get("连载平台"))

                    if "页数" in card_info:
                        try:
                            pages_match = re.search(r"(\d+)", str(card_info["页数"]))
                            if pages_match:
                                result["pages"] = int(pages_match.group(1))
                        except Exception:
                            pass

                    if "定价" in card_info:
                        result["price"] = str(card_info["定价"])

                    if "ISBN" in card_info:
                        result["isbn"] = str(card_info["ISBN"])

                abstract = page_data.get("abstract", {})
                summary = self._extract_abstract(abstract)
                description = page_data.get("description", "")
                if summary:
                    result["summary"] = summary
                    result["top_content"] = summary
                elif description and "..." not in description and "…" not in description:
                    result["summary"] = description

            # HTML 回退
            if not result.get("baike_title"):
                lemma_title = soup.select_one("h1")
                if lemma_title:
                    result["baike_title"] = lemma_title.text.strip()

            if not result.get("summary"):
                summary_elem = (
                    soup.select_one(".J-summary")
                    or soup.select_one("[class*='lemmaSummary']")
                    or soup.select_one(".lemma-summary")
                )
                if summary_elem:
                    result["summary"] = summary_elem.text.strip()
                    result["top_content"] = result["summary"]

            story_titles = ["内容情节", "内容介绍", "故事情节", "作品情节", "故事大纲", "剧情简介"]
            story = self._extract_section_text(soup, story_titles)
            if not story and page_data:
                story = self._extract_section_from_page_data(page_data, story_titles)
            if story:
                result["story"] = story

            meaningful_keys = {"summary", "story", "info", "author", "authors", "word_count", "title_original", "year"}
            if not any(result.get(key) for key in meaningful_keys):
                Logger.warning("[baike] 未提取到有效百科正文，本次不保存稀疏数据")
                return None

            # 作者百科链接
            author_links = soup.select("a[href*='/item/']")
            for link in author_links:
                link_text = link.get_text(strip=True)
                if "作者" in link_text or link_text in str(result.get("author", "")):
                    href = link.get("href", "")
                    if href:
                        result["author_baike_url"] = f"{config.BAIKE_BASE_URL}{href}"
                        break

            Logger.success("[baike] 数据获取完成")

        except Exception as e:
            Logger.error(f"[baike] 解析失败: {e}")
            return None

        return result

    async def _extract_page_data(self) -> Optional[Dict]:
        """从页面提取 PAGE_DATA JSON"""
        try:
            content = await self.page.content()
            start_idx = content.find('window.PAGE_DATA=')
            if start_idx < 0:
                return None

            start_idx += len('window.PAGE_DATA=')
            end_idx = content.find(';</script>', start_idx)
            if end_idx < 0:
                end_idx = content.find('</script>', start_idx)

            json_str = content[start_idx:end_idx].strip()
            return json.loads(json_str)
        except Exception as e:
            Logger.warning(f"[baike] 提取 PAGE_DATA 失败: {e}")
            return None

    def _extract_card_info(self, card: Dict) -> Dict:
        """从 card 提取信息框数据"""
        result = {}

        if not isinstance(card, dict):
            return result

        def extract_value(d):
            if isinstance(d, dict):
                if d.get('dataType') == 'text':
                    texts = d.get('text', [])
                    return ''.join([t.get('text', '') for t in texts if isinstance(t, dict)])
                elif 'value' in d:
                    return d['value']
                elif 'title' in d:
                    return {'id': d.get('id', ''), 'title': d.get('title', '')}
            return str(d) if d else ''

        for side in ['left', 'right']:
            items = card.get(side, []) or []
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = item.get('title', '')
                data_list = item.get('data', []) or []

                if data_list:
                    values = []
                    for d in data_list:
                        val = extract_value(d)
                        if val:
                            values.append(val)
                    if values:
                        result[title] = values[0] if len(values) == 1 else values

        return result

    def _extract_abstract(self, abstract) -> str:
        """从 abstract 提取简介文本"""
        if isinstance(abstract, dict):
            text_list = abstract.get('text', [])
            return ''.join([t.get('text', '') for t in text_list if isinstance(t, dict)])
        elif isinstance(abstract, str):
            return abstract
        elif isinstance(abstract, list):
            texts = []
            for item in abstract:
                if isinstance(item, dict) and 'text' in item:
                    texts.append(item.get('text', ''))
            return ''.join(texts)
        return ''

    def _clean_section_text(self, text: str) -> str:
        """清理百科正文分节文本，去掉编辑控件、脚注和多余空白。"""
        if not text:
            return ""
        text = re.sub(r"\[\d+(?:-\d+)?\]", "", text)
        text = re.sub(r"(编辑|播报|上传视频|TA说)\s*$", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _looks_like_heading(self, elem) -> bool:
        classes = " ".join(elem.get("class", []))
        text = self._clean_section_text(elem.get_text(" ", strip=True))
        if not text or len(text) > 40:
            return False
        if elem.name in {"h2", "h3"}:
            return True
        return any(key in classes for key in ["para-title", "lemmaTitle", "title", "headline"])

    def _extract_section_text(self, soup: BeautifulSoup, titles) -> str:
        """从 HTML 正文中提取指定标题之后、下一个标题之前的正文。"""
        collecting = False
        chunks = []

        for elem in soup.find_all(["h2", "h3", "div", "p"]):
            text = self._clean_section_text(elem.get_text(" ", strip=True))
            if not text:
                continue

            if self._looks_like_heading(elem):
                if collecting:
                    break
                heading_text = text.replace("目录", "")
                if any(title in heading_text for title in titles):
                    collecting = True
                continue

            if not collecting:
                continue

            classes = " ".join(elem.get("class", []))
            if elem.name == "p" or "para" in classes or "content" in classes:
                if len(text) >= 8 and text not in chunks:
                    chunks.append(text)

        return "\n".join(chunks).strip()

    def _extract_section_from_page_data(self, page_data, titles) -> str:
        """从 PAGE_DATA 结构中兜底提取指定分节。"""
        chunks = []

        def node_text(node) -> str:
            if isinstance(node, str):
                return node
            if isinstance(node, dict):
                if isinstance(node.get("text"), str):
                    return node["text"]
                if isinstance(node.get("title"), str):
                    return node["title"]
            return ""

        def collect_text(node):
            if isinstance(node, str):
                text = self._clean_section_text(node)
                if len(text) >= 8:
                    chunks.append(text)
            elif isinstance(node, dict):
                for key, value in node.items():
                    if key in {"title", "name", "anchor"}:
                        continue
                    collect_text(value)
            elif isinstance(node, list):
                for item in node:
                    collect_text(item)

        def walk(node):
            if isinstance(node, dict):
                label = self._clean_section_text(" ".join(filter(None, [
                    node_text(node.get("title")),
                    node_text(node.get("name")),
                    node_text(node.get("anchor")),
                ])))
                if any(title in label for title in titles):
                    collect_text(node)
                    return True
                return any(walk(value) for value in node.values())
            if isinstance(node, list):
                return any(walk(item) for item in node)
            return False

        walk(page_data)
        deduped = []
        for chunk in chunks:
            if not any(chunk == existing or chunk in existing for existing in deduped):
                deduped.append(chunk)
        return "\n".join(deduped).strip()

    def _parse_word_count(self, card_info: Dict) -> Optional[int]:
        """解析字数"""
        word_text = None
        for key in ["字数", "总字数", "篇幅"]:
            if key in card_info:
                word_text = str(card_info[key])
                break

        if not word_text:
            return None

        word_text = word_text.replace(" ", "").replace("字", "")

        match = re.match(r"([\d.]+)\s*万", word_text)
        if match:
            return int(float(match.group(1)) * 10000)

        match = re.match(r"([\d.]+)\s*千", word_text)
        if match:
            return int(float(match.group(1)) * 1000)

        match = re.match(r"([\d]+)", word_text)
        if match:
            return int(match.group(1))

        return None

    def _extract_first_publish_year(self, card_info: Dict) -> Optional[int]:
        """提取首版时间"""
        year_fields = ["首版时间", "首次出版时间", "首发时间", "出版日期", "出版时间"]

        for field in year_fields:
            if field in card_info:
                year_text = str(card_info[field])
                year_match = re.search(r"(\d{4})", year_text)
                if year_match:
                    return int(year_match.group(1))

        return None
