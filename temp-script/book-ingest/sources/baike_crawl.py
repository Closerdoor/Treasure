# -*- coding: utf-8 -*-
"""
百度百科爬虫 - 独立脚本

一次性获取全部信息：搜索 + 消歧 + 详情提取
独立浏览器实例，不复用其他数据源的页面

输出字段：
- url, baike_id, baike_title, baike_desc
- title, title_original
- author, country, word_count, year
- publisher, language
- summary
- info (完整信息框字典)
- author_baike_url
- type (类型/体裁)
- serial_status (连载状态)
- serial_platform (首发平台)
- pages, price, binding, isbn (从 info 提取)
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


class BaikeCrawler(BaseCrawler):

    def __init__(self):
        super().__init__(source_name="baike")

    async def crawl(self, title: str) -> Optional[Dict[str, Any]]:
        """
        一次性获取百度百科全部信息

        Args:
            title: 书名

        Returns:
            完整的百度百科数据字典
        """
        if not self.page:
            await self.init_browser()

        Logger.info(f"[baike] 正在搜索: {title}")

        baike_url = await self._search(title)
        if not baike_url:
            Logger.warning(f"[baike] 未找到词条: {title}")
            return None

        data = await self._get_detail(baike_url, title)
        return data

    async def _search(self, title: str) -> Optional[str]:
        """搜索词条"""
        encoded_title = quote(title)
        url = f"{config.BAIKE_BASE_URL}/item/{encoded_title}"

        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            current_url = self.page.url
            if "search" in current_url:
                content = await self.page.content()
                soup = BeautifulSoup(content, "html.parser")

                first_result = soup.select_one(".result-list .result-title a")
                if first_result:
                    href = first_result.get("href", "")
                    if href:
                        url = f"{config.BAIKE_BASE_URL}{href}" if href.startswith("/") else href
                        await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                        current_url = self.page.url
                else:
                    Logger.warning(f"[baike] 未找到词条: {title}")
                    return None

            Logger.success(f"[baike] 找到词条: {current_url}")
            return current_url

        except Exception as e:
            Logger.error(f"[baike] 搜索失败: {e}")
            return None

    async def _get_detail(self, url: str, title: str) -> Dict[str, Any]:
        """获取词条内容"""
        Logger.info(f"[baike] 正在获取内容: {url}")

        result = {"url": url, "title": title, "source": "baike"}

        try:
            await asyncio.sleep(1)
            content = await self.page.content()
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
                novel_link = None

                for link in disambiguation_links:
                    link_text = link.text.strip()
                    if any(kw in link_text for kw in ["长篇小说", "网络小说", "小说", "文学作品"]):
                        novel_link = link
                        break

                if not novel_link:
                    for link in disambiguation_links:
                        link_text = link.text.strip()
                        if any(kw in link_text for kw in ["书", "图书", "原著"]):
                            if not any(ex in link_text for ex in ["游戏", "动画", "电影", "漫画", "剧", "手游", "网游"]):
                                novel_link = link
                                break

                if not novel_link and disambiguation_links:
                    novel_link = disambiguation_links[0]

                if novel_link:
                    href = novel_link.get("href", "")
                    if href:
                        new_url = f"{config.BAIKE_BASE_URL}{href}" if href.startswith("/") else href
                        Logger.info(f"[baike] 跳转到义项页面: {new_url}")
                        await self.page.goto(new_url, timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(2)
                        content = await self.page.content()
                        soup = BeautifulSoup(content, "html.parser")

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
                            result["author"] = author_data.get("title", "")
                        else:
                            result["author"] = str(author_data)

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

                    if "类型" in card_info:
                        result["type"] = str(card_info["类型"])

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

                    if "装帧" in card_info:
                        result["binding"] = str(card_info["装帧"])

                    if "ISBN" in card_info:
                        result["isbn"] = str(card_info["ISBN"])

                description = page_data.get("description", "")
                if description:
                    result["summary"] = description
                else:
                    abstract = page_data.get("abstract", {})
                    summary = self._extract_abstract(abstract)
                    if summary:
                        result["summary"] = summary

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
            items = card.get(side, [])
            for item in items:
                title = item.get('title', '')
                data_list = item.get('data', [])

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