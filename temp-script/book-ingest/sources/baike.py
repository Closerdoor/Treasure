# -*- coding: utf-8 -*-
"""
百度百科爬虫（书籍专用）
"""
import asyncio
import json
import random
import re
from typing import Dict, Any, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.async_api import Page

import config
from utils import Logger


class BaikeCrawler:
    """百度百科爬虫"""
    
    def __init__(self, page: Page):
        self.page = page
        self.base_url = config.BAIKE_BASE_URL
        
    async def search(self, title: str) -> Optional[str]:
        """
        搜索词条
        
        Args:
            title: 书名
            
        Returns:
            词条 URL 或 None
        """
        Logger.info(f"正在搜索百度百科: {title}")
        
        encoded_title = quote(title)
        url = f"{self.base_url}/item/{encoded_title}"
        
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
                        url = f"{self.base_url}{href}" if href.startswith("/") else href
                        await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                        current_url = self.page.url
                else:
                    Logger.warning(f"百度百科未找到词条: {title}")
                    return None
            
            # 返回实际跳转后的 URL
            Logger.success(f"找到百度百科词条: {current_url}")
            return current_url
            
        except Exception as e:
            Logger.error(f"百度百科搜索失败: {e}")
            return None
            
    async def get_detail(self, url: str, title: str) -> Dict[str, Any]:
        """
        获取词条内容
        
        Args:
            url: 词条 URL
            title: 书名
            
        Returns:
            词条数据
        """
        Logger.info(f"正在获取百度百科内容: {url}")
        
        result = {
            "url": url,
            "title": title,
            "source": "baike"
        }
        
        try:
            # 等待页面加载完成
            await asyncio.sleep(1)
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 检查是否是多义词页面，需要选择小说义项
            # 使用 href 包含 fromModule=disambiguation 的链接
            disambiguation_links = soup.find_all('a', href=lambda x: x and 'fromModule=disambiguation' in x)
            
            # 如果没有找到义项链接，等待一下再试
            if not disambiguation_links and "多义词" in content:
                await asyncio.sleep(2)
                content = await self.page.content()
                soup = BeautifulSoup(content, "html.parser")
                disambiguation_links = soup.select('a[href*="fromModule=disambiguation"]')
            
            if disambiguation_links or "多义词" in content:
                Logger.info("检测到多义词页面，查找小说义项...")
                # 优先查找包含"小说"、"网络小说"等关键词的义项（排除游戏、动画等）
                novel_link = None
                for link in disambiguation_links:
                    link_text = link.text.strip()
                    # 优先级最高的关键词
                    if any(keyword in link_text for keyword in ["长篇小说", "网络小说", "小说", "文学作品"]):
                        novel_link = link
                        break
                
                # 如果没找到，尝试更宽泛的关键词（但要排除游戏、动画等）
                if not novel_link:
                    for link in disambiguation_links:
                        link_text = link.text.strip()
                        if any(keyword in link_text for keyword in ["书", "图书", "原著"]):
                            if not any(exclude in link_text for exclude in ["游戏", "动画", "电影", "漫画", "剧", "手游", "网游"]):
                                novel_link = link
                                break
                
                # 如果没找到小说义项，选择第一个
                if not novel_link and disambiguation_links:
                    novel_link = disambiguation_links[0]
                
                if novel_link:
                    href = novel_link.get("href", "")
                    if href:
                        new_url = f"{self.base_url}{href}" if href.startswith("/") else href
                        Logger.info(f"跳转到义项页面: {new_url}")
                        await self.page.goto(new_url, timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(2)
                        content = await self.page.content()
                        soup = BeautifulSoup(content, "html.parser")
            
            # 尝试从 PAGE_DATA JSON 提取数据（新版百度百科）
            page_data = await self._extract_page_data()
            
            if page_data:
                result["baike_id"] = page_data.get("lemmaId")
                result["baike_title"] = page_data.get("lemmaTitle")
                result["baike_desc"] = page_data.get("lemmaDesc")
                
                # 从 card 提取信息框
                card = page_data.get("card", {})
                card_info = self._extract_card_info(card)
                if card_info:
                    result["info"] = card_info
                    
                    # 提取作者
                    if "作者" in card_info:
                        author_data = card_info["作者"]
                        if isinstance(author_data, dict):
                            author_name = author_data.get("title", "")
                            result["author"] = author_name
                            # 从作者名推断国家（如"【哥伦比亚】加西亚·马尔克斯"）
                            country = self._extract_country_from_author(author_name)
                            if country:
                                result["country"] = country
                        else:
                            result["author"] = str(author_data)
                            country = self._extract_country_from_author(str(author_data))
                            if country:
                                result["country"] = country
                    
                    # 提取字数（支持多种格式）
                    word_count = self._parse_word_count(card_info)
                    if word_count:
                        result["word_count"] = word_count
                    
                    # 提取外文名
                    if "外文名" in card_info:
                        result["title_original"] = str(card_info["外文名"])
                    
                    # 提取首版时间（优先级最高）
                    year = self._extract_first_publish_year(card_info)
                    if year:
                        result["year"] = year
                    
                    # 提取出版社
                    if "出版社" in card_info:
                        result["publisher"] = str(card_info["出版社"])
                    elif "出版机构" in card_info:
                        result["publisher"] = str(card_info["出版机构"])
                    
                    # 提取语言
                    if "语言" in card_info:
                        result["language"] = str(card_info["语言"])
                
                # 从 description 提取简介（新版百度百科）
                description = page_data.get("description", "")
                if description:
                    result["summary"] = description
                else:
                    # 尝试从 abstract 提取
                    abstract = page_data.get("abstract", {})
                    summary = self._extract_abstract(abstract)
                    if summary:
                        result["summary"] = summary
            
            # 如果 JSON 提取失败，尝试传统 HTML 解析
            if not result.get("baike_title"):
                lemma_title = soup.select_one("h1")
                if lemma_title:
                    result["baike_title"] = lemma_title.text.strip()
            
            if not result.get("summary"):
                summary_elem = (soup.select_one(".J-summary") or 
                               soup.select_one("[class*='lemmaSummary']") or
                               soup.select_one(".lemma-summary"))
                if summary_elem:
                    result["summary"] = summary_elem.text.strip()
            
            # 获取作者简介（查找作者词条链接）
            author_links = soup.select("a[href*='/item/']")
            for link in author_links:
                link_text = link.get_text(strip=True)
                if "作者" in link_text or link_text in result.get("author", ""):
                    href = link.get("href", "")
                    if href:
                        result["author_baike_url"] = f"{self.base_url}{href}"
                        break
            
            Logger.success(f"百度百科数据获取完成")
            
        except Exception as e:
            Logger.error(f"百度百科解析失败: {e}")
            
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
            Logger.warning(f"提取 PAGE_DATA 失败: {e}")
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
        """从 abstract 或 description 提取简介文本"""
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
        """
        解析字数（支持多种格式）
        
        格式示例：
        - "22.8万" → 228000
        - "253千字" → 253000
        - "771.25万" → 7712500
        - "25.3万字" → 253000
        - "360千字" → 360000
        """
        word_text = None
        for key in ["字数", "总字数", "篇幅"]:
            if key in card_info:
                word_text = str(card_info[key])
                break
        
        if not word_text:
            return None
        
        word_text = word_text.replace(" ", "").replace("字", "")
        
        # 格式1: "771.25万" 或 "22.8万"
        match = re.match(r"([\d.]+)\s*万", word_text)
        if match:
            return int(float(match.group(1)) * 10000)
        
        # 格式2: "253千字" 或 "360千"
        match = re.match(r"([\d.]+)\s*千", word_text)
        if match:
            return int(float(match.group(1)) * 1000)
        
        # 格式3: 纯数字（假设单位为字）
        match = re.match(r"([\d]+)", word_text)
        if match:
            return int(match.group(1))
        
        return None
    
    def _extract_first_publish_year(self, card_info: Dict) -> Optional[int]:
        """
        提取首版时间（优先级最高）
        
        字段映射：
        - 首版时间 → year
        - 首次出版时间 → year
        - 首发时间 → year（网络小说）
        - 出版日期 → year（实体书，如果无首版时间）
        """
        year_fields = [
            "首版时间",
            "首次出版时间",
            "首发时间",
            "出版日期",
            "出版时间"
        ]
        
        for field in year_fields:
            if field in card_info:
                year_text = str(card_info[field])
                year_match = re.search(r"(\d{4})", year_text)
                if year_match:
                    return int(year_match.group(1))
        
        return None
    
    def _extract_country_from_author(self, author_name: str) -> Optional[str]:
        """
        从作者名推断国家
        
        格式示例：
        - "【哥伦比亚】加西亚·马尔克斯" → "哥伦比亚"
        - "[哥伦比亚] 加西亚·马尔克斯" → "哥伦比亚"
        - "（美）海明威" → "美"
        """
        if not author_name:
            return None
        
        # 匹配【国家】或[国家]或（国家）格式
        match = re.match(r"^[【\[（\(]([^】\]\)）]+)[】\]\)）]", author_name)
        if match:
            return match.group(1)
        
        return None
        
    async def get_author_intro(self, author_name: str) -> Optional[str]:
        """
        获取作者简介
        
        Args:
            author_name: 作者名
            
        Returns:
            作者简介
        """
        Logger.info(f"正在获取作者简介: {author_name}")
        
        url = await self.search(author_name)
        if not url:
            return None
        
        try:
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            summary_elem = soup.select_one(".lemma-summary")
            if summary_elem:
                return summary_elem.text.strip()
            
        except Exception as e:
            Logger.warning(f"获取作者简介失败: {e}")
            
        return None
